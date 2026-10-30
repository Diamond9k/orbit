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

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import auth, db, fit, ledger

DEV = os.environ.get("ORBIT_DEV") == "1"
ORBIT_CUT_PERCENT = int(os.environ.get("ORBIT_CUT_PERCENT", "20"))  # Orbit's share of each session
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
BASE_URL = os.environ.get("ORBIT_BASE_URL", "http://localhost:8000")
STORE_AMOUNTS_CENTS = [500, 1000, 2500]  # what the store offers, in dollars of hardware time
HOST_TIMEOUT_SECONDS = int(os.environ.get("ORBIT_HOST_TIMEOUT", "180"))  # unseen this long mid-session: the host is gone
MESSAGE_MAX_CHARS = 96000  # one chat message, either direction: 64000 characters of text once sealed into an envelope
LONGPOLL_MAX_SECONDS = 25  # how long a messages request may wait for something new

HERE = Path(__file__).parent


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    yield


app = FastAPI(title="Orbit", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.filters["dollars"] = lambda cents: f"-${-cents / 100:,.2f}" if cents < 0 else f"${cents / 100:,.2f}"


def get_db():
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


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
    resp.set_cookie("orbit_flash", exc.message, max_age=30, httponly=True, samesite="lax")
    return resp


def take_flash(request: Request) -> str | None:
    return request.cookies.get("orbit_flash")


# ---------- pages ----------

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, user=Depends(current_user)):
    return render(request, "signup.html", user=user, error=None)


@app.post("/signup")
def signup(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_db)):
    try:
        uid = auth.create_user(conn, email, password)
    except sqlite3.IntegrityError:
        return render(request, "signup.html", user=None, error="that email already has an account")
    except ValueError as e:
        return render(request, "signup.html", user=None, error=str(e))
    resp = RedirectResponse("/account", status_code=303)
    resp.set_cookie(auth.COOKIE, auth.make_cookie(uid), httponly=True, samesite="lax")
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(current_user)):
    return render(request, "login.html", user=user, error=None)


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), conn=Depends(get_db)):
    uid = auth.check_login(conn, email, password)
    if uid is None:
        return render(request, "login.html", user=None, error="wrong email or password")
    resp = RedirectResponse("/account", status_code=303)
    resp.set_cookie(auth.COOKIE, auth.make_cookie(uid), httponly=True, samesite="lax")
    return resp


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
    resp = render(request, "account.html", user=user, _conn=conn, balance=ledger.balance(conn, acct),
                  history=ledger.history(conn, acct, 20), sessions=sessions, hosts=hosts,
                  host_earned=host_earned, flash=take_flash(request))
    resp.delete_cookie("orbit_flash")
    return resp


@app.get("/store", response_class=HTMLResponse)
def store(request: Request, user=Depends(require_user), conn=Depends(get_db)):
    cheapest = conn.execute(
        "SELECT MIN(price_cents_per_hour) AS p FROM hosts WHERE status != 'offline'"
    ).fetchone()["p"]
    return render(request, "store.html", user=user, _conn=conn, amounts=STORE_AMOUNTS_CENTS,
                  cheapest=cheapest, stripe_ready=bool(STRIPE_SECRET_KEY),
                  balance=ledger.balance(conn, f"user:{user['id']}"))


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
    # Fail closed: with no secret set, a signature made with an empty key would check out, so
    # anyone could credit themselves. Refuse until the secret is configured.
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "STRIPE_WEBHOOK_SECRET is not set")
    import stripe
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "bad signature")
    # A completed checkout is not always a paid one (delayed methods finish later and send
    # async_payment_succeeded). Credit only money Stripe says has arrived, once per checkout.
    if event["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        s = event["data"]["object"]
        if "payment_status" in s and s["payment_status"] == "paid":
            uid = int(s["metadata"]["user_id"])
            cents = int(s["amount_total"])
            ledger.post(conn, [("stripe:clearing", -cents), (f"user:{uid}", cents)],
                        memo=f"stripe:{s['id']}", once=f"stripe:{s['id']}")
    return {"ok": True}


@app.post("/store/dev-funds")
def dev_funds(amount_cents: int = Form(...), user=Depends(require_user), conn=Depends(get_db)):
    """Test funds. Only exists when ORBIT_DEV=1."""
    if not DEV:
        raise HTTPException(404)
    ledger.post(conn, [("dev:faucet", -amount_cents), (f"user:{user['id']}", amount_cents)], memo="dev test funds")
    return RedirectResponse("/account", status_code=303)


# ---------- run a model ----------

@app.get("/", response_class=HTMLResponse)
@app.get("/run", response_class=HTMLResponse)
def run_page(request: Request, model: str = "", user=Depends(current_user), conn=Depends(get_db)):
    model = clean_model(model)
    results, need_quant = [], False
    if model:
        params, quant = fit.parse(model)
        need_quant = params is not None and quant is None
        hosts = conn.execute("SELECT * FROM hosts WHERE status IN ('online', 'busy') ORDER BY price_cents_per_hour").fetchall()
        results = [(h, fit.check(model, h["vram_gb"])) for h in hosts]
        order = {"fits": 0, "tight": 1, "unknown": 2, "too_big": 3}
        results.sort(key=lambda r: (r[0]["status"] != "online", order[r[1].verdict]))
    online = conn.execute("SELECT COUNT(*) AS n FROM hosts WHERE status = 'online'").fetchone()["n"]
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
    resp = render(request, "run.html", user=user, model=model, results=results, balance=balance,
                  active=active, recent=recent, hosts_online=online, need_quant=need_quant,
                  flash=take_flash(request), _conn=conn)
    resp.delete_cookie("orbit_flash")
    return resp


@app.post("/sessions/start")
def start_session(model: str = Form(...), host_id: int = Form(...), user=Depends(require_user), conn=Depends(get_db)):
    model = clean_model(model)
    back = f"/?model={model}"
    if not model:
        raise UserError("Type a model name first.", "/")
    with db.tx(conn):
        running = conn.execute("SELECT id FROM sessions WHERE user_id = ? AND ended_at IS NULL", (user["id"],)).fetchone()
        if running:
            raise UserError("You already have a session running. Stop it before starting another.", f"/sessions/{running['id']}")
        host = conn.execute("SELECT * FROM hosts WHERE id = ?", (host_id,)).fetchone()
        if host is None or host["status"] != "online":
            raise UserError("That machine just went offline or got taken. Pick another.", back)
        if ledger.balance(conn, f"user:{user['id']}") < host["price_cents_per_hour"]:
            raise UserError(f"You need at least one hour on this machine ({host['price_cents_per_hour'] / 100:.2f} dollars) to start. Add time first.", back)
        if fit.check(model, host["vram_gb"]).verdict == "too_big":
            raise UserError("That model does not fit on this machine.", back)
        conn.execute("UPDATE hosts SET status = 'busy' WHERE id = ?", (host_id,))
        cur = conn.execute("INSERT INTO sessions (user_id, host_id, model) VALUES (?, ?, ?)",
                           (user["id"], host_id, model))
        sid = cur.lastrowid
    return RedirectResponse(f"/sessions/{sid}", status_code=303)


@app.get("/sessions/{sid}", response_class=HTMLResponse)
def session_page(request: Request, sid: int, user=Depends(require_user), conn=Depends(get_db)):
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
    cost = s["cost_cents"]
    cut = cost * ORBIT_CUT_PERCENT // 100
    # Posted by the one function allowed to move money, at most once per session even when
    # two sweeps race for it.
    txn = ledger.post(conn, [(f"user:{s['user_id']}", -cost), (f"host:{s['host_id']}", cost - cut), ("orbit:revenue", cut)],
                      memo=f"session:{sid}", once=f"session:{sid}")
    return txn is not None


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
        "AND NOT EXISTS (SELECT 1 FROM ledger_once o WHERE o.key = 'session:' || s.id)").fetchall()
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


@app.get("/sessions/{sid}/messages")
async def read_messages(sid: int, after: int = 0, wait: float = 0, user=Depends(require_user), conn=Depends(get_db)):
    """Messages after `after`. With wait > 0 the request is held up to that many seconds for a new one."""
    deadline = time.monotonic() + min(max(wait, 0), LONGPOLL_MAX_SECONDS)
    while True:
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
    hosts = conn.execute("SELECT * FROM hosts WHERE status != 'removed' ORDER BY status DESC, price_cents_per_hour").fetchall()
    return render(request, "hosts.html", user=user, hosts=hosts, error=None, new_token=None, _conn=conn)


@app.post("/hosts", response_class=HTMLResponse)
def add_host(request: Request, name: str = Form(...), gpu: str = Form(...), vram_gb: float = Form(...),
             price_dollars_per_hour: float = Form(...), user=Depends(require_user), conn=Depends(get_db)):
    price_cents = int(round(price_dollars_per_hour * 100))
    if not name.strip() or not gpu.strip() or vram_gb <= 0 or price_cents <= 0:
        hosts = conn.execute("SELECT * FROM hosts ORDER BY status DESC").fetchall()
        return render(request, "hosts.html", user=user, hosts=hosts, error="fill in every field", new_token=None, _conn=conn)
    token = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO hosts (owner_id, name, gpu, vram_gb, price_cents_per_hour, token) VALUES (?, ?, ?, ?, ?, ?)",
        (user["id"], name.strip(), gpu.strip(), vram_gb, price_cents, token),
    )
    hosts = conn.execute("SELECT * FROM hosts WHERE status != 'removed' ORDER BY status DESC, price_cents_per_hour").fetchall()
    return render(request, "hosts.html", user=user, hosts=hosts, error=None, new_token=token, _conn=conn)


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

@app.post("/api/hosts/heartbeat")
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


@app.post("/api/hosts/ready")
def host_ready(token: str = Form(...), conn=Depends(get_db)):
    """The host program calls this once the model is loaded. Billing starts now, not before."""
    s = _host_session(conn, token)
    if s is None:
        raise HTTPException(404, "unknown host token or no running session")
    conn.execute("UPDATE sessions SET ready_at = COALESCE(ready_at, datetime('now')) WHERE id = ?", (s["id"],))
    conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE token = ?", (token,))
    return {"ok": True}


@app.post("/api/hosts/inbox")
async def host_inbox(token: str = Form(...), after: int = Form(0), wait: float = Form(0), conn=Depends(get_db)):
    """The host program asks for the conversation after message `after`, holding up to `wait` seconds.

    Asking counts as proof of life, like a heartbeat. The reply also names the running session,
    so the host learns at once when it ended and can stop the model.
    """
    cur = conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE token = ? AND status != 'removed'", (token,))
    if cur.rowcount == 0:
        raise HTTPException(401, "unknown host token")
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


@app.post("/api/hosts/reply")
def host_reply(token: str = Form(...), session_id: int = Form(...), body: str = Form(...), conn=Depends(get_db)):
    """The host program posts the model's answer for the running session."""
    s = _host_session(conn, token)
    if s is None or s["id"] != session_id:
        raise HTTPException(404, "unknown host token or no such running session")
    if len(body) > MESSAGE_MAX_CHARS:
        raise HTTPException(413, "message too long")
    cur = conn.execute("INSERT INTO messages (session_id, sender, body) VALUES (?, 'host', ?)", (session_id, body))
    conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE token = ?", (token,))
    return {"id": cur.lastrowid}


@app.post("/api/hosts/offline")
def go_offline(token: str = Form(...), conn=Depends(get_db)):
    cur = conn.execute("UPDATE hosts SET status = 'offline' WHERE token = ? AND status != 'busy'", (token,))
    if cur.rowcount == 0:
        raise HTTPException(409, "unknown token or host is mid-session")
    return {"ok": True}


@app.get("/health")
def health(conn=Depends(get_db)):
    bad = ledger.verify(conn)
    return {"ok": not bad, "unbalanced_txns": bad}
