"""Orbit web app. FastAPI, SQLite, plain HTML pages."""
import asyncio
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import auth, db, fit, ledger, sandbox

SANDBOX = sandbox.ENABLED  # the public demo: guests, test funds, simulated machines. See sandbox.py.
DEV = os.environ.get("ORBIT_DEV") == "1"
ORBIT_CUT_PERCENT = int(os.environ.get("ORBIT_CUT_PERCENT", "20"))  # Orbit's share of each session
# The sandbox never takes a card, whatever keys are set.
STRIPE_SECRET_KEY = "" if SANDBOX else os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = "" if SANDBOX else os.environ.get("STRIPE_WEBHOOK_SECRET", "")
BASE_URL = os.environ.get("ORBIT_BASE_URL", "http://localhost:8000")
STORE_AMOUNTS_CENTS = [500, 1000, 2500]  # what the store offers, in dollars of hardware time
HOST_TIMEOUT_SECONDS = int(os.environ.get("ORBIT_HOST_TIMEOUT", "180"))  # unseen this long mid-session: the host is gone
MESSAGE_MAX_CHARS = 96000  # one chat message, either direction: 64000 characters of text once sealed into an envelope
if SANDBOX:
    MESSAGE_MAX_CHARS = sandbox.MESSAGE_MAX_CHARS
TEST_FUNDS_CENTS = 1000  # the one amount the test-funds button gives
MODEL_MAX_CHARS = 200
NAME_MAX_CHARS = 60  # a machine's name or GPU, as typed by its host
REPO_URL = "https://github.com/Diamond9k/orbit"
LONGPOLL_MAX_SECONDS = 25  # how long a messages request may wait for something new

HERE = Path(__file__).parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    yield


# No generated API pages: the routes are not a public API, and the fewer doors the better.
app = FastAPI(title="Orbit", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.filters["dollars"] = lambda cents: f"-${-cents / 100:,.2f}" if cents < 0 else f"${cents / 100:,.2f}"
templates.env.filters["who"] = lambda email: ("Guest " + email[6:14]) if email.endswith("@sandbox.invalid") else email
templates.env.filters["gb"] = lambda n: f"{n:g}"  # 24.0 reads as 24
templates.env.globals.update(sandbox=SANDBOX, repo_url=REPO_URL)

_db_ready = False


def get_db():
    global _db_ready
    if not _db_ready:  # some hosts never send the startup event; make sure the tables exist anyway
        db.init()
        _db_ready = True
    conn = db.connect()
    try:
        if SANDBOX:
            sandbox.tick(conn, end_session)
        yield conn
    finally:
        conn.close()


# ---------- the same protection on every reply ----------

# Everything a page loads comes from this server: no CDN, no inline script, no inline style.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; form-action 'self' https://checkout.stripe.com; frame-ancestors 'none'; "
       "base-uri 'none'; object-src 'none'")
# Called by programs, not by pages: the host program and Stripe. They carry their own proof.
MACHINE_PATHS = ("/api/hosts/", "/stripe/webhook")


def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"


def _foreign(request: Request) -> bool:
    """True when a browser says this request was sent by a page on another site."""
    source = request.headers.get("origin") or request.headers.get("referer")
    if not source or source == "null":
        return source == "null"
    return urlsplit(source).netloc.lower() != request.headers.get("host", "").lower()


@app.middleware("http")
async def protect(request: Request, call_next):
    path = request.url.path
    # A form or fetch from another site must not act as the signed-in person. The cookie is
    # SameSite=Lax already; this is the second lock.
    if request.method not in ("GET", "HEAD", "OPTIONS") and not path.startswith(MACHINE_PATHS) and _foreign(request):
        return JSONResponse({"detail": "this request came from another site"}, status_code=403)
    resp = await call_next(request)
    h = resp.headers
    h.setdefault("Content-Security-Policy", CSP)
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "same-origin")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if is_https(request):
        h.setdefault("Strict-Transport-Security", "max-age=31536000")
    # Pages and JSON carry a person's balance and sessions: never kept by a shared cache.
    h.setdefault("Cache-Control", "public, max-age=3600" if path.startswith("/static/") else "no-store")
    if SANDBOX:
        h.setdefault("X-Robots-Tag", "noindex")
    return resp


def sign_in(request: Request, resp, uid: int):
    resp.set_cookie(auth.COOKIE, auth.make_cookie(uid), max_age=auth.COOKIE_MAX_AGE, httponly=True,
                    samesite="lax", secure=is_https(request))
    return resp


def current_user(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    uid = auth.read_cookie(request.cookies.get(auth.COOKIE))
    if uid is None:
        return None
    return conn.execute("SELECT id, email FROM users WHERE id = ?", (uid,)).fetchone()


def require_user(user=Depends(current_user)):
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def clean_model(raw: str) -> str:
    """Accept a model name or a Hugging Face URL and return 'owner/name [extra]'."""
    m = raw.strip()
    m = re.sub(r"^https?://(www\.)?huggingface\.co/", "", m)
    m = re.sub(r"/(tree|blob|resolve)/[^ ]*", "", m)
    return m.strip("/ ")


_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/ -]*")


def valid_model(model: str) -> bool:
    """A cleaned model name made only of what Hugging Face names are made of.

    The name ends up on a host's command line, so nothing else is let through.
    """
    return len(model) <= MODEL_MAX_CHARS and _MODEL.fullmatch(model) is not None


def hosts_scope(conn: sqlite3.Connection, user) -> tuple[str, tuple]:
    """SQL (and its values) for the machines this person may see. Everything, outside the sandbox."""
    return sandbox.scope(conn, user) if SANDBOX else ("1 = 1", ())


def nav_ctx(conn: sqlite3.Connection, user) -> dict:
    """What every page shows in the nav: balance and running session."""
    if not user:
        return {"nav_balance": None, "nav_active": None}
    active = conn.execute(
        "SELECT s.id, h.name AS host_name FROM sessions s JOIN hosts h ON h.id = s.host_id "
        "WHERE s.user_id = ? AND s.ended_at IS NULL", (user["id"],)
    ).fetchone()
    return {"nav_balance": ledger.balance(conn, f"user:{user['id']}"), "nav_active": active}


def render(request: Request, name: str, **ctx):
    ctx.setdefault("dev", DEV)
    ctx.setdefault("nav_balance", None)
    ctx.setdefault("nav_active", None)
    conn = ctx.pop("_conn", None)
    if conn is not None:
        ctx.update(nav_ctx(conn, ctx.get("user")))
    return templates.TemplateResponse(request, name, ctx)


class UserError(Exception):
    """A problem to show the person in plain words, on the page they were on."""
    def __init__(self, message: str, back: str = "/"):
        self.message, self.back = message, back


@app.exception_handler(UserError)
async def _user_error(request: Request, exc: UserError):
    resp = RedirectResponse(exc.back, status_code=303)
    resp.set_cookie("orbit_flash", exc.message, max_age=30, httponly=True, samesite="lax", secure=is_https(request))
    return resp


def take_flash(request: Request) -> str | None:
    return request.cookies.get("orbit_flash")


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    """A missing page gets a page, not a line of JSON. Everything else is answered as before."""
    if exc.status_code == 404 and request.method == "GET" and "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(request, "error.html", {"user": None, "dev": DEV, "nav_balance": None,
                                                                  "nav_active": None}, status_code=404)
    return await http_exception_handler(request, exc)


# ---------- the sandbox door ----------

@app.post("/sandbox/enter")
def sandbox_enter(request: Request, user=Depends(current_user), conn=Depends(get_db)):
    """One click, no email: a guest account with test funds. Only exists in the sandbox."""
    if not SANDBOX:
        raise HTTPException(404)
    if user is not None:
        return RedirectResponse("/", status_code=303)
    return sign_in(request, RedirectResponse("/?model=" + quote(sandbox_example()), status_code=303), sandbox.enter(conn))


def sandbox_example() -> str:
    return "bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M"


@app.get("/about", response_class=HTMLResponse)
def about(request: Request, user=Depends(current_user), conn=Depends(get_db)):
    return render(request, "about.html", user=user, _conn=conn, cut=ORBIT_CUT_PERCENT)


# ---------- pages ----------

def accounts_open():
    """Email and password accounts do not exist in the sandbox: it keeps nobody's details."""
    if SANDBOX:
        raise HTTPException(status_code=303, headers={"Location": "/"})


@app.get("/signup", response_class=HTMLResponse, dependencies=[Depends(accounts_open)])
def signup_page(request: Request, user=Depends(current_user)):
    if user is not None:  # already signed in: this page used to fail with an error
        return RedirectResponse("/account", status_code=303)
    return render(request, "signup.html", user=user, error=None)


@app.post("/signup", dependencies=[Depends(accounts_open)])
def signup(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_db)):
    try:
        uid = auth.create_user(conn, email, password)
    except sqlite3.IntegrityError:
        return render(request, "signup.html", user=None, error="that email already has an account")
    except ValueError as e:
        return render(request, "signup.html", user=None, error=str(e))
    return sign_in(request, RedirectResponse("/account", status_code=303), uid)


@app.get("/login", response_class=HTMLResponse, dependencies=[Depends(accounts_open)])
def login_page(request: Request, user=Depends(current_user)):
    if user is not None:  # already signed in: this page used to fail with an error
        return RedirectResponse("/account", status_code=303)
    return render(request, "login.html", user=user, error=None)


@app.post("/login", dependencies=[Depends(accounts_open)])
def login(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_db)):
    uid = auth.check_login(conn, email, password)
    if uid is None:
        return render(request, "login.html", user=None, error="wrong email or password")
    return sign_in(request, RedirectResponse("/account", status_code=303), uid)


@app.post("/logout")
def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(auth.COOKIE)
    return resp


@app.get("/account", response_class=HTMLResponse)
def account(request: Request, user=Depends(require_user), conn=Depends(get_db)):
    sweep(conn)
    acct = f"user:{user['id']}"
    sessions = conn.execute(
        "SELECT s.*, h.name AS host_name FROM sessions s JOIN hosts h ON h.id = s.host_id "
        "WHERE s.user_id = ? ORDER BY s.id DESC LIMIT 20", (user["id"],)
    ).fetchall()
    hosts = conn.execute("SELECT * FROM hosts WHERE owner_id = ? AND status != 'removed' ORDER BY id", (user["id"],)).fetchall()
    host_earned = {h["id"]: ledger.balance(conn, f"host:{h['id']}") for h in hosts}
    total_sessions = conn.execute("SELECT COUNT(*) AS n FROM sessions WHERE user_id = ?", (user["id"],)).fetchone()["n"]
    resp = render(request, "account.html", user=user, _conn=conn, balance=ledger.balance(conn, acct),
                  history=ledger.history(conn, acct, 20), sessions=sessions, hosts=hosts,
                  host_earned=host_earned, total_sessions=total_sessions, flash=take_flash(request))
    resp.delete_cookie("orbit_flash")
    return resp


@app.get("/store", response_class=HTMLResponse)
def store(request: Request, user=Depends(require_user), conn=Depends(get_db)):
    where, args = hosts_scope(conn, user)
    cheapest = conn.execute(
        f"SELECT MIN(price_cents_per_hour) AS p FROM hosts WHERE status IN ('online', 'busy') AND {where}", args
    ).fetchone()["p"]
    resp = render(request, "store.html", user=user, _conn=conn, amounts=STORE_AMOUNTS_CENTS,
                  cheapest=cheapest, stripe_ready=bool(STRIPE_SECRET_KEY), test_funds=TEST_FUNDS_CENTS,
                  balance=ledger.balance(conn, f"user:{user['id']}"), flash=take_flash(request))
    resp.delete_cookie("orbit_flash")
    return resp


@app.post("/store/checkout")
def checkout(amount_cents: int = Form(...), user=Depends(require_user)):
    if amount_cents not in STORE_AMOUNTS_CENTS:
        raise HTTPException(400, "not an offered amount")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "card payments are not set up yet")
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price_data": {"currency": "usd", "unit_amount": amount_cents,
                                    "product_data": {"name": "Orbit hardware time"}}, "quantity": 1}],
        success_url=f"{BASE_URL}/account",
        cancel_url=f"{BASE_URL}/store",
        metadata={"user_id": str(user["id"])},
    )
    return RedirectResponse(session.url, status_code=303)


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, conn=Depends(get_db)):
    # Without the signing secret nothing can be checked. An empty secret would let anyone sign
    # their own "payment", so the door stays shut until Stripe is set up.
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "card payments are not set up yet")
    import stripe
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "bad signature")
    if event["type"] == "checkout.session.completed":
        s = event["data"]["object"]
        try:
            uid = int(s["metadata"]["user_id"])
            cents = int(s["amount_total"])
            paid = s["payment_status"] == "paid" and s["currency"] == "usd"
        except (KeyError, TypeError, ValueError):
            raise HTTPException(400, "not a checkout Orbit started")
        # Only money that arrived, in an amount the store offers, for an account that exists.
        known = conn.execute("SELECT 1 FROM users WHERE id = ?", (uid,)).fetchone()
        if paid and known and cents in STORE_AMOUNTS_CENTS:
            already = conn.execute("SELECT 1 FROM ledger WHERE memo = ? LIMIT 1", (f"stripe:{s['id']}",)).fetchone()
            if not already:
                ledger.post(conn, [("stripe:clearing", -cents), (f"user:{uid}", cents)], memo=f"stripe:{s['id']}")
    return {"ok": True}


@app.post("/store/dev-funds")
def dev_funds(amount_cents: int = Form(...), user=Depends(require_user), conn=Depends(get_db)):
    """Test funds. Only exists when ORBIT_DEV=1 or in the sandbox. One fixed amount, never a typed one."""
    if not (DEV or SANDBOX):
        raise HTTPException(404)
    if amount_cents != TEST_FUNDS_CENTS:
        raise HTTPException(400, "not an offered amount")
    if SANDBOX and ledger.balance(conn, f"user:{user['id']}") >= sandbox.FUNDS_CAP_CENTS:
        raise UserError("You have plenty of test funds already. Use some first.", "/store")
    ledger.post(conn, [("dev:faucet", -amount_cents), (f"user:{user['id']}", amount_cents)],
                memo="sandbox test funds" if SANDBOX else "dev test funds")
    return RedirectResponse("/account", status_code=303)


# ---------- run a model ----------

@app.get("/", response_class=HTMLResponse)
@app.get("/run", response_class=HTMLResponse)
def run_page(request: Request, model: str = "", user=Depends(current_user), conn=Depends(get_db)):
    model = clean_model(model)
    results, need_quant, bad_model = [], False, False
    where, args = hosts_scope(conn, user)
    if model and not valid_model(model):
        model, bad_model = "", True
    if model:
        params, quant = fit.parse(model)
        need_quant = params is not None and quant is None
        hosts = conn.execute(f"SELECT * FROM hosts WHERE status IN ('online', 'busy') AND {where} "
                             "ORDER BY price_cents_per_hour", args).fetchall()
        results = [(h, fit.check(model, h["vram_gb"])) for h in hosts]
        order = {"fits": 0, "tight": 1, "unknown": 2, "too_big": 3}
        results.sort(key=lambda r: (r[0]["status"] != "online", order[r[1].verdict]))
    online = conn.execute(f"SELECT COUNT(*) AS n FROM hosts WHERE status = 'online' AND {where}", args).fetchone()["n"]
    balance = ledger.balance(conn, f"user:{user['id']}") if user else 0
    active, recent = None, []
    if user:
        active = conn.execute(
            "SELECT s.*, h.name AS host_name FROM sessions s JOIN hosts h ON h.id = s.host_id "
            "WHERE s.user_id = ? AND s.ended_at IS NULL", (user["id"],)
        ).fetchone()
        recent = [r["model"] for r in conn.execute(
            "SELECT model, MAX(id) AS m FROM sessions WHERE user_id = ? GROUP BY model ORDER BY m DESC LIMIT 5",
            (user["id"],)).fetchall()]
    flash = take_flash(request)
    stale = SANDBOX and user is None and bool(request.cookies.get(auth.COOKIE))
    if stale:  # a guest whose account went with the last wipe or restart
        flash = "The sandbox started again and your guest account went with it. Enter again to carry on."
    if bad_model:
        flash = "That does not look like a model name. Use the name from Hugging Face, like owner/model."
    resp = render(request, "run.html", user=user, model=model, results=results, balance=balance,
                  active=active, recent=recent, hosts_online=online, need_quant=need_quant,
                  flash=flash, example=sandbox_example(), _conn=conn)
    resp.delete_cookie("orbit_flash")
    if stale:
        resp.delete_cookie(auth.COOKIE)
    return resp


@app.post("/sessions/start")
def start_session(model: str = Form(...), host_id: int = Form(...), user=Depends(require_user), conn=Depends(get_db)):
    model = clean_model(model)
    if not model:
        raise UserError("Type a model name first.", "/")
    if not valid_model(model):
        raise UserError("That does not look like a model name. Use the name from Hugging Face, like owner/model.", "/")
    back = "/?model=" + quote(model)
    where, args = hosts_scope(conn, user)
    with db.tx(conn):
        running = conn.execute("SELECT id FROM sessions WHERE user_id = ? AND ended_at IS NULL", (user["id"],)).fetchone()
        if running:
            raise UserError("You already have a session running. Stop it before starting another.", f"/sessions/{running['id']}")
        host = conn.execute(f"SELECT * FROM hosts WHERE id = ? AND {where}", (host_id, *args)).fetchone()
        if host is None or host["status"] != "online":
            raise UserError("That machine just went offline or got taken. Pick another.", back)
        if ledger.balance(conn, f"user:{user['id']}") < host["price_cents_per_hour"]:
            raise UserError(f"You need at least one hour on this machine ({host['price_cents_per_hour'] / 100:.2f} dollars) to start. Add time first.", back)
        if fit.check(model, host["vram_gb"]).verdict == "too_big":
            raise UserError("That model does not fit on this machine.", back)
        conn.execute("UPDATE hosts SET status = 'busy' WHERE id = ?", (host_id,))
        if SANDBOX:  # the simulated machine was "seen" the moment it was booked
            conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE id = ?", (host_id,))
        cur = conn.execute("INSERT INTO sessions (user_id, host_id, model) VALUES (?, ?, ?)",
                           (user["id"], host_id, model))
        sid = cur.lastrowid
    return RedirectResponse(f"/sessions/{sid}", status_code=303)


@app.get("/sessions/{sid}", response_class=HTMLResponse)
def session_page(request: Request, sid: int, user=Depends(require_user), conn=Depends(get_db)):
    if SANDBOX and conn.execute("SELECT 1 FROM sessions WHERE id = ? AND user_id = ?", (sid, user["id"])).fetchone():
        sandbox.step(conn, sid)
    sweep(conn)
    s = conn.execute(
        "SELECT s.*, h.name AS host_name, h.gpu, h.vram_gb, h.price_cents_per_hour "
        "FROM sessions s JOIN hosts h ON h.id = s.host_id WHERE s.id = ? AND s.user_id = ?",
        (sid, user["id"]),
    ).fetchone()
    if s is None:
        raise HTTPException(404)
    balance = ledger.balance(conn, f"user:{user['id']}")
    minutes_left = affordable_minutes(balance, s["price_cents_per_hour"])
    ready_epoch = int(_utc(s["ready_at"]).timestamp()) if s["ready_at"] else None
    resp = render(request, "session.html", user=user, _conn=conn, s=s, balance=balance,
                  minutes_left=minutes_left, ready_epoch=ready_epoch, flash=take_flash(request))
    resp.delete_cookie("orbit_flash")
    return resp


# ---------- ending sessions and moving the money ----------

def _utc(stamp: str) -> datetime:
    """A 'YYYY-MM-DD HH:MM:SS' stamp from SQLite's datetime('now') as an aware UTC time."""
    return datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def affordable_minutes(balance_cents: int, price_cents_per_hour: int) -> int:
    """The most whole minutes a balance covers at this price, rounded the way the bill is."""
    if price_cents_per_hour <= 0 or balance_cents <= 0:
        return 0
    m = balance_cents * 60 // price_cents_per_hour
    while m > 0 and math.ceil(price_cents_per_hour * m / 60) > balance_cents:
        m -= 1
    return m


def end_session(conn: sqlite3.Connection, s: sqlite3.Row, end: datetime, reason: str,
                minutes: int | None = None, host_status: str = "online") -> bool:
    """Close one running session as of `end` and move the money. False if it was already closed.

    `s` is a sessions row joined with the host's price_cents_per_hour. Time is counted from the
    moment the host said ready, one minute minimum; a session the host never got ready costs
    nothing. The row is closed first, in one transaction that only one caller can win, then the
    charge is posted. If the process dies between the two, sweep() posts the missing charge.
    """
    if s["ready_at"] is None:
        minutes = cost = 0
    else:
        if minutes is None:
            minutes = max(1, math.ceil((end - _utc(s["ready_at"])).total_seconds() / 60))
        cost = math.ceil(s["price_cents_per_hour"] * minutes / 60)
    with db.tx(conn):
        cur = conn.execute(
            "UPDATE sessions SET ended_at = ?, minutes = ?, cost_cents = ?, end_reason = ? "
            "WHERE id = ? AND ended_at IS NULL",
            (end.strftime("%Y-%m-%d %H:%M:%S"), minutes, cost, reason, s["id"]))
        if cur.rowcount == 0:
            return False
        conn.execute("UPDATE hosts SET status = ? WHERE id = ? AND status = 'busy'", (host_status, s["host_id"]))
        conn.execute("DELETE FROM messages WHERE session_id = ?", (s["id"],))
    post_session_charge(conn, s["id"])
    return True


def post_session_charge(conn: sqlite3.Connection, sid: int) -> bool:
    """Move the money for an ended session, once: user pays, host earns, Orbit takes its cut.

    Safe to call again. A session whose rows exist (memo session:<id>) is left alone, so a
    retry never bills twice. Returns True when rows were posted.
    """
    s = conn.execute("SELECT user_id, host_id, cost_cents FROM sessions WHERE id = ? AND ended_at IS NOT NULL",
                     (sid,)).fetchone()
    if s is None or not s["cost_cents"]:
        return False
    if conn.execute("SELECT 1 FROM ledger WHERE memo = ? LIMIT 1", (f"session:{sid}",)).fetchone():
        return False
    cost = s["cost_cents"]
    cut = cost * ORBIT_CUT_PERCENT // 100
    # Posted by the one function allowed to move money.
    ledger.post(conn, [(f"user:{s['user_id']}", -cost), (f"host:{s['host_id']}", cost - cut), ("orbit:revenue", cut)],
                memo=f"session:{sid}")
    return True


def sweep(conn: sqlite3.Connection) -> None:
    """End sessions that cannot go on, and post any charge that went missing.

    A session ends on its own when the hardware time runs out (charged exactly the minutes the
    balance covered) or when the host has not been heard from for HOST_TIMEOUT_SECONDS (charged
    only up to the last moment it was reachable). Because the end time is computed, not "now",
    a sweep that runs late never costs the user more. Runs on every heartbeat and page load,
    so nothing depends on a timer.
    """
    now = utcnow()
    running = conn.execute(
        "SELECT s.*, h.price_cents_per_hour, h.last_seen FROM sessions s JOIN hosts h ON h.id = s.host_id "
        "WHERE s.ended_at IS NULL").fetchall()
    for s in running:
        seen = _utc(s["last_seen"]) if s["last_seen"] else _utc(s["started_at"])
        if (now - seen).total_seconds() > HOST_TIMEOUT_SECONDS:
            end = seen if s["ready_at"] is None else max(seen, _utc(s["ready_at"]))
            end_session(conn, s, end, "host_lost", host_status="offline")
            continue
        if s["ready_at"] is not None:
            covered = affordable_minutes(ledger.balance(conn, f"user:{s['user_id']}"), s["price_cents_per_hour"])
            ran = (now - _utc(s["ready_at"])).total_seconds() / 60
            if ran > covered:
                end_session(conn, s, _utc(s["ready_at"]) + timedelta(minutes=covered), "out_of_time", minutes=covered)
    # A charge is posted right after its session closes. One that is still missing a minute
    # later was lost to a crash between the two steps; post it now.
    unposted = conn.execute(
        "SELECT s.id FROM sessions s WHERE s.ended_at IS NOT NULL AND s.cost_cents > 0 "
        "AND s.ended_at < datetime('now', '-60 seconds') "
        "AND NOT EXISTS (SELECT 1 FROM ledger l WHERE l.memo = 'session:' || s.id)").fetchall()
    for r in unposted:
        post_session_charge(conn, r["id"])


@app.post("/sessions/{sid}/stop")
def stop_session(sid: int, user=Depends(require_user), conn=Depends(get_db)):
    sweep(conn)  # if time already ran out, the sweep ends it at the cutoff, never later
    s = conn.execute(
        "SELECT s.*, h.price_cents_per_hour FROM sessions s JOIN hosts h ON h.id = s.host_id "
        "WHERE s.id = ? AND s.user_id = ? AND s.ended_at IS NULL", (sid, user["id"])
    ).fetchone()
    if s is not None:
        end_session(conn, s, utcnow(), "stopped")
    elif not conn.execute("SELECT 1 FROM sessions WHERE id = ? AND user_id = ?", (sid, user["id"])).fetchone():
        raise HTTPException(404, "no session with that id")
    return RedirectResponse(f"/sessions/{sid}", status_code=303)


# ---------- the conversation: relayed, not read ----------
# The browser and the host program exchange message bodies through Orbit. Orbit stores a body
# only until it is delivered and the session ends, and never interprets it. Bodies are plain
# text today; sealing them end to end is a change to the browser and the host program only.

def _messages_after(conn: sqlite3.Connection, sid: int, after: int) -> list[dict]:
    rows = conn.execute("SELECT id, sender, body, created_at FROM messages WHERE session_id = ? AND id > ? ORDER BY id",
                        (sid, after)).fetchall()
    return [{"id": r["id"], "sender": r["sender"], "body": r["body"], "at": r["created_at"]} for r in rows]


@app.post("/sessions/{sid}/messages")
def send_message(sid: int, body: str = Form(...), user=Depends(require_user), conn=Depends(get_db)):
    sweep(conn)
    s = conn.execute("SELECT ready_at FROM sessions WHERE id = ? AND user_id = ? AND ended_at IS NULL",
                     (sid, user["id"])).fetchone()
    if s is None:
        raise HTTPException(409, "this session is over")
    if s["ready_at"] is None:
        raise HTTPException(409, "the machine is still loading the model")
    body = body.strip()
    if not body:
        raise HTTPException(400, "empty message")
    if len(body) > MESSAGE_MAX_CHARS:
        raise HTTPException(413, "message too long")
    cur = conn.execute("INSERT INTO messages (session_id, sender, body) VALUES (?, 'user', ?)", (sid, body))
    return {"id": cur.lastrowid}


def _own_session(conn: sqlite3.Connection, sid: int, user) -> bool:
    return conn.execute("SELECT 1 FROM sessions WHERE id = ? AND user_id = ?", (sid, user["id"])).fetchone() is not None


@app.get("/sessions/{sid}/messages")
async def read_messages(sid: int, after: int = 0, wait: float = 0, user=Depends(require_user), conn=Depends(get_db)):
    """Messages after `after`. With wait > 0 the request is held up to that many seconds for a new one."""
    if wait != wait:  # NaN compares false with everything and would hold the request for ever
        wait = 0
    deadline = time.monotonic() + min(max(wait, 0), LONGPOLL_MAX_SECONDS)
    simulated = SANDBOX and _own_session(conn, sid, user)
    while True:
        if simulated:
            sandbox.step(conn, sid)  # the simulated host answers while the page waits
        sweep(conn)
        s = conn.execute("SELECT ready_at, ended_at, end_reason FROM sessions WHERE id = ? AND user_id = ?",
                         (sid, user["id"])).fetchone()
        if s is None:
            raise HTTPException(404)
        msgs = _messages_after(conn, sid, after)
        if msgs or s["ended_at"] or time.monotonic() >= deadline:
            return {"ready": s["ready_at"] is not None, "ended": s["ended_at"] is not None,
                    "end_reason": s["end_reason"], "messages": msgs}
        await asyncio.sleep(0.5)


# ---------- hosts ----------

@app.get("/hosts", response_class=HTMLResponse)
def hosts_page(request: Request, user=Depends(current_user), conn=Depends(get_db)):
    return render(request, "hosts.html", user=user, hosts=_listed(conn, user), error=None, new_token=None, _conn=conn)


def _listed(conn: sqlite3.Connection, user) -> list[sqlite3.Row]:
    where, args = hosts_scope(conn, user)
    return conn.execute(f"SELECT * FROM hosts WHERE status != 'removed' AND {where} "
                        "ORDER BY status DESC, price_cents_per_hour", args).fetchall()


@app.post("/hosts", response_class=HTMLResponse)
def add_host(request: Request, name: str = Form(...), gpu: str = Form(...), vram_gb: float = Form(...),
             price_dollars_per_hour: float = Form(...), user=Depends(require_user), conn=Depends(get_db)):
    def refuse(why: str):
        return render(request, "hosts.html", user=user, hosts=_listed(conn, user), error=why, new_token=None, _conn=conn)

    name, gpu = " ".join(name.split()), " ".join(gpu.split())
    if not name or not gpu:
        return refuse("fill in every field")
    if len(name) > NAME_MAX_CHARS or len(gpu) > NAME_MAX_CHARS:
        return refuse(f"keep the name and the GPU under {NAME_MAX_CHARS} characters")
    # `not (a <= x <= b)` also refuses NaN and infinity, which a plain `x <= 0` lets through.
    if not (1 <= vram_gb <= 2048):
        return refuse("GPU memory must be between 1 and 2048 GB")
    if not (0.01 <= price_dollars_per_hour <= 1000):
        return refuse("price per hour must be between $0.01 and $1,000")
    price_cents = int(round(price_dollars_per_hour * 100))
    if SANDBOX and conn.execute("SELECT COUNT(*) AS n FROM hosts WHERE owner_id = ? AND status != 'removed'",
                                (user["id"],)).fetchone()["n"] >= sandbox.MAX_MACHINES_PER_GUEST:
        return refuse(f"the sandbox lets a guest list {sandbox.MAX_MACHINES_PER_GUEST} machines")
    token = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO hosts (owner_id, name, gpu, vram_gb, price_cents_per_hour, token) VALUES (?, ?, ?, ?, ?, ?)",
        (user["id"], name, gpu, vram_gb, price_cents, token),
    )
    return render(request, "hosts.html", user=user, hosts=_listed(conn, user), error=None, new_token=token, _conn=conn)


@app.post("/hosts/{hid}/remove")
def remove_host(hid: int, user=Depends(require_user), conn=Depends(get_db)):
    with db.tx(conn):
        h = conn.execute("SELECT * FROM hosts WHERE id = ? AND owner_id = ?", (hid, user["id"])).fetchone()
        if h is None:
            raise UserError("That machine is not yours or does not exist.", "/account")
        if h["status"] == "busy":
            raise UserError("That machine is in a session. Wait for it to end.", "/account")
        if conn.execute("SELECT 1 FROM sessions WHERE host_id = ? LIMIT 1", (hid,)).fetchone():
            # Keep the row for the ledger history; just take it off the list for good.
            conn.execute("UPDATE hosts SET status = 'removed', token = token || ':removed' WHERE id = ?", (hid,))
        else:
            conn.execute("DELETE FROM hosts WHERE id = ?", (hid,))
    return RedirectResponse("/account", status_code=303)


# ---------- API for the host program (step 2) ----------

def host_api_open():
    """No host program may connect to the sandbox: its machines are simulated."""
    if SANDBOX:
        raise HTTPException(403, "this is the Orbit sandbox: its machines are simulated and host programs cannot connect")


@app.post("/api/hosts/heartbeat", dependencies=[Depends(host_api_open)])
def heartbeat(token: str = Form(...), conn=Depends(get_db)):
    """The host program calls this every few seconds while it is ready for work.

    The reply names the session this machine should be running, so the host program knows
    which model to load: {"session": {"id": ..., "model": ...}} or {"session": null}.
    """
    cur = conn.execute(
        "UPDATE hosts SET last_seen = datetime('now'), status = CASE WHEN status = 'busy' THEN 'busy' ELSE 'online' END "
        "WHERE token = ? AND status != 'removed'", (token,)
    )
    if cur.rowcount == 0:
        raise HTTPException(401, "unknown host token")
    sweep(conn)
    s = _host_session(conn, token)
    return {"session": {"id": s["id"], "model": s["model"]} if s else None}


def _host_session(conn: sqlite3.Connection, token: str):
    return conn.execute(
        "SELECT s.id, s.model, s.ready_at FROM sessions s JOIN hosts h ON h.id = s.host_id "
        "WHERE h.token = ? AND h.status != 'removed' AND s.ended_at IS NULL", (token,)
    ).fetchone()


@app.post("/api/hosts/ready", dependencies=[Depends(host_api_open)])
def host_ready(token: str = Form(...), conn=Depends(get_db)):
    """The host program calls this once the model is loaded. Billing starts now, not before."""
    s = _host_session(conn, token)
    if s is None:
        raise HTTPException(404, "unknown host token or no running session")
    conn.execute("UPDATE sessions SET ready_at = COALESCE(ready_at, datetime('now')) WHERE id = ?", (s["id"],))
    conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE token = ?", (token,))
    return {"ok": True}


@app.post("/api/hosts/inbox", dependencies=[Depends(host_api_open)])
async def host_inbox(token: str = Form(...), after: int = Form(0), wait: float = Form(0), conn=Depends(get_db)):
    """The host program asks for the conversation after message `after`, holding up to `wait` seconds.

    Asking counts as proof of life, like a heartbeat. The reply also names the running session,
    so the host learns at once when it ended and can stop the model.
    """
    cur = conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE token = ? AND status != 'removed'", (token,))
    if cur.rowcount == 0:
        raise HTTPException(401, "unknown host token")
    if wait != wait:  # NaN
        wait = 0
    deadline = time.monotonic() + min(max(wait, 0), LONGPOLL_MAX_SECONDS)
    while True:
        sweep(conn)
        s = _host_session(conn, token)
        if s is None:
            return {"session": None, "messages": []}
        msgs = _messages_after(conn, s["id"], after)
        if msgs or time.monotonic() >= deadline:
            return {"session": {"id": s["id"], "model": s["model"]}, "messages": msgs}
        await asyncio.sleep(0.5)
        # Still connected, still alive: keep last_seen honest while the request is held, so a
        # host that vanishes is charged for up to the moment it was last here, not 20 s early.
        conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE token = ?", (token,))


@app.post("/api/hosts/reply", dependencies=[Depends(host_api_open)])
def host_reply(token: str = Form(...), session_id: int = Form(...), body: str = Form(...), conn=Depends(get_db)):
    """The host program posts the model's answer for the running session."""
    s = _host_session(conn, token)
    if s is None or s["id"] != session_id:
        raise HTTPException(404, "unknown host token or no such running session")
    if not body.strip():
        raise HTTPException(400, "empty message")
    if len(body) > MESSAGE_MAX_CHARS:
        raise HTTPException(413, "message too long")
    cur = conn.execute("INSERT INTO messages (session_id, sender, body) VALUES (?, 'host', ?)", (session_id, body))
    conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE token = ?", (token,))
    return {"id": cur.lastrowid}


@app.post("/api/hosts/offline", dependencies=[Depends(host_api_open)])
def go_offline(token: str = Form(...), conn=Depends(get_db)):
    cur = conn.execute("UPDATE hosts SET status = 'offline' WHERE token = ? AND status != 'busy'", (token,))
    if cur.rowcount == 0:
        raise HTTPException(409, "unknown token or host is mid-session")
    return {"ok": True}


@app.get("/health")
def health(conn=Depends(get_db)):
    bad = ledger.verify(conn)
    return {"ok": not bad, "unbalanced_txns": len(bad), "sandbox": SANDBOX}
