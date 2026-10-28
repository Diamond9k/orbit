"""Orbit web app. FastAPI, SQLite, plain HTML pages."""
import math
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
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
    import stripe
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "bad signature")
    if event["type"] == "checkout.session.completed":
        s = event["data"]["object"]
        uid = int(s["metadata"]["user_id"])
        cents = int(s["amount_total"])
        already = conn.execute("SELECT 1 FROM ledger WHERE memo = ? LIMIT 1", (f"stripe:{s['id']}",)).fetchone()
        if not already:
            ledger.post(conn, [("stripe:clearing", -cents), (f"user:{uid}", cents)], memo=f"stripe:{s['id']}")
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
    s = conn.execute(
        "SELECT s.*, h.name AS host_name, h.gpu, h.vram_gb, h.price_cents_per_hour "
        "FROM sessions s JOIN hosts h ON h.id = s.host_id WHERE s.id = ? AND s.user_id = ?",
        (sid, user["id"]),
    ).fetchone()
    if s is None:
        raise HTTPException(404)
    balance = ledger.balance(conn, f"user:{user['id']}")
    minutes_left = balance * 60 // s["price_cents_per_hour"] if s["price_cents_per_hour"] else 0
    started_epoch = int(datetime.fromisoformat(s["started_at"]).replace(tzinfo=timezone.utc).timestamp())
    return render(request, "session.html", user=user, _conn=conn, s=s, balance=balance,
                  minutes_left=minutes_left, started_epoch=started_epoch)


def settle_session(conn: sqlite3.Connection, sid: int, user_id: int) -> None:
    """End a session and move the money: user pays, host earns, Orbit takes its cut."""
    with db.tx(conn):
        s = conn.execute(
            "SELECT s.*, h.price_cents_per_hour FROM sessions s JOIN hosts h ON h.id = s.host_id "
            "WHERE s.id = ? AND s.user_id = ? AND s.ended_at IS NULL", (sid, user_id)
        ).fetchone()
        if s is None:
            raise HTTPException(404, "no running session with that id")
        started = datetime.fromisoformat(s["started_at"]).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        minutes = max(1, math.ceil((now - started).total_seconds() / 60))
        cost = math.ceil(s["price_cents_per_hour"] * minutes / 60)
        cut = cost * ORBIT_CUT_PERCENT // 100
        conn.execute("UPDATE sessions SET ended_at = ?, minutes = ?, cost_cents = ? WHERE id = ?",
                     (now.strftime("%Y-%m-%d %H:%M:%S"), minutes, cost, sid))
        conn.execute("UPDATE hosts SET status = 'online' WHERE id = ?", (s["host_id"],))
    # Separate transaction, posted by the one function allowed to move money.
    ledger.post(conn, [(f"user:{user_id}", -cost), (f"host:{s['host_id']}", cost - cut), ("orbit:revenue", cut)],
                memo=f"session:{sid}")


@app.post("/sessions/{sid}/stop")
def stop_session(sid: int, user=Depends(require_user), conn=Depends(get_db)):
    settle_session(conn, sid, user["id"])
    return RedirectResponse(f"/sessions/{sid}", status_code=303)


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
    """The host program calls this every minute while it is ready for work."""
    cur = conn.execute(
        "UPDATE hosts SET last_seen = datetime('now'), status = CASE WHEN status = 'busy' THEN 'busy' ELSE 'online' END "
        "WHERE token = ? AND status != 'removed'", (token,)
    )
    if cur.rowcount == 0:
        raise HTTPException(401, "unknown host token")
    return {"ok": True}


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
