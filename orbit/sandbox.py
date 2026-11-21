"""Sandbox mode: the whole product loop with nothing real behind it. On with ORBIT_SANDBOX=1.

Made for a public demo address. In the sandbox:
  - a visitor enters as a guest with one click. No email or password is asked for or kept.
  - money is test funds only. Stripe is off, whatever keys are set.
  - machines are simulated. No host program can connect, and no model runs. A simulated host
    does the real key exchange (host/seal.py) and sends scripted replies that say they are scripted.
  - a visitor sees the sandbox machines and the ones they listed, never another visitor's text.
  - the data is thrown away: a session ends when its page is closed, and everything is wiped
    when the store grows past the limits below or the server restarts.

The simulated host's key lives in this process, next to Orbit. So the sandbox shows how the
sealing works, not the privacy it gives with a real host, and the session page says exactly that.
"""
import importlib.util
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from . import auth, db, ledger

ENABLED = os.environ.get("ORBIT_SANDBOX") == "1"

SYSTEM_EMAIL = "machines@sandbox.invalid"
# name, GPU, GPU memory in GB, price in cents per hour. Sandbox numbers, labelled as such on the pages.
MACHINES = [
    ("Sandbox 8 GB", "Radeon RX 580", 8, 15),
    ("Sandbox 12 GB", "RTX 3060", 12, 25),
    ("Sandbox 24 GB", "RTX 4090", 24, 60),
    ("Sandbox 48 GB", "RTX A6000", 48, 110),
]
START_FUNDS_CENTS = 1000      # what a guest starts with
FUNDS_CAP_CENTS = 5000        # no more test funds above this balance
LOAD_SECONDS = 3              # how long the simulated machine takes to say "ready"
IDLE_SECONDS = 120            # a session whose page stopped asking is ended after this long
MAX_GUESTS = 300              # past these, the sandbox is wiped and starts again
MAX_MESSAGES = 4000
MAX_MACHINES_PER_GUEST = 3
MESSAGE_MAX_CHARS = 12000     # one sealed envelope; about 8000 characters of text

_lock = threading.RLock()
_system_id: int | None = None
_last_tick = 0.0
_hosts: dict[int, dict] = {}  # session id -> the simulated host's sealer and how far it has read
_seal = None


def seal():
    """host/seal.py, the same file a real host program uses. Needs the cryptography package."""
    global _seal
    if _seal is None:
        path = Path(__file__).resolve().parent.parent / "host" / "seal.py"
        spec = importlib.util.spec_from_file_location("orbit_host_seal", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _seal = module
    return _seal


def system_id(conn: sqlite3.Connection) -> int:
    """The account that owns the sandbox machines. Nobody can sign in to it. Seeds on first use."""
    global _system_id
    with _lock:
        if _system_id is not None:
            return _system_id
        row = conn.execute("SELECT id FROM users WHERE email = ?", (SYSTEM_EMAIL,)).fetchone()
        if row is None:
            uid = auth.create_user(conn, SYSTEM_EMAIL, secrets.token_urlsafe(32))
            conn.executemany(
                "INSERT INTO hosts (owner_id, name, gpu, vram_gb, price_cents_per_hour, token, status, last_seen) "
                "VALUES (?, ?, ?, ?, ?, ?, 'online', datetime('now'))",
                [(uid, name, gpu, vram, price, secrets.token_urlsafe(24)) for name, gpu, vram, price in MACHINES])
        else:
            uid = int(row["id"])
        _system_id = uid
        return uid


def reset(conn: sqlite3.Connection) -> None:
    """Throw everything away and start again."""
    global _system_id
    with _lock:
        with db.tx(conn):
            for table in ("messages", "sessions", "hosts", "ledger", "users"):
                conn.execute(f"DELETE FROM {table}")
        _system_id = None
        _hosts.clear()
        system_id(conn)


def tick(conn: sqlite3.Connection, end_session) -> None:
    """Keep the sandbox running. Called on every request; does its work at most once a second.

    `end_session` is the app's own function, so a sandbox session is closed and charged by the
    same code as a real one.
    """
    global _last_tick
    with _lock:
        now = time.monotonic()
        if now - _last_tick < 1:
            return
        _last_tick = now
        guests = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        messages = conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
        if guests > MAX_GUESTS or messages > MAX_MESSAGES:
            reset(conn)
        system_id(conn)
        # Every machine here is simulated, so a free one is always online.
        conn.execute("UPDATE hosts SET status = 'online', last_seen = datetime('now') WHERE status IN ('offline', 'online')")
        # A busy machine is kept alive only while its session page keeps asking (see step). When the
        # page is closed the session ends, charged up to the last time the page was there.
        idle = conn.execute(
            "SELECT s.*, h.price_cents_per_hour, h.last_seen FROM sessions s JOIN hosts h ON h.id = s.host_id "
            "WHERE s.ended_at IS NULL AND COALESCE(h.last_seen, s.started_at) < datetime('now', ?)",
            (f"-{IDLE_SECONDS} seconds",)).fetchall()
        for s in idle:
            end_session(conn, s, _stamp(s["last_seen"] or s["started_at"], s["ready_at"]), "sandbox_idle")
            _hosts.pop(s["id"], None)


def _stamp(last_seen: str, ready_at: str | None):
    from datetime import datetime, timezone
    seen = datetime.fromisoformat(last_seen).replace(tzinfo=timezone.utc)
    if ready_at is None:
        return seen
    return max(seen, datetime.fromisoformat(ready_at).replace(tzinfo=timezone.utc))


def enter(conn: sqlite3.Connection) -> int:
    """A new guest with test funds. Returns the user id."""
    system_id(conn)
    name = f"guest-{secrets.token_hex(4)}@sandbox.invalid"
    uid = auth.create_user(conn, name, secrets.token_urlsafe(32))  # the password is thrown away: a guest cannot sign in again
    ledger.post(conn, [("dev:faucet", -START_FUNDS_CENTS), (f"user:{uid}", START_FUNDS_CENTS)], memo="sandbox test funds")
    return uid


def scope(conn: sqlite3.Connection, user) -> tuple[str, tuple]:
    """SQL for the machines a visitor may see: the sandbox machines and their own."""
    return "(owner_id = ? OR owner_id = ?)", (system_id(conn), user["id"] if user else -1)


def step(conn: sqlite3.Connection, sid: int) -> None:
    """Play the host for one running session: say ready, offer a key, answer what was said.

    Called while the session page asks for messages, so nothing here needs a background task.
    """
    with _lock:
        s = conn.execute(
            "SELECT id, model, host_id, ready_at, "
            "(julianday('now') - julianday(started_at)) * 86400 AS age FROM sessions WHERE id = ? AND ended_at IS NULL",
            (sid,)).fetchone()
        if s is None:
            _hosts.pop(sid, None)
            return
        conn.execute("UPDATE hosts SET last_seen = datetime('now') WHERE id = ?", (s["host_id"],))
        if s["ready_at"] is None:
            if s["age"] < LOAD_SECONDS:
                return
            conn.execute("UPDATE sessions SET ready_at = datetime('now') WHERE id = ? AND ready_at IS NULL", (sid,))
        st = _hosts.get(sid)
        if st is None:
            # First visit, or this process restarted and lost the key: start a new epoch with a new key.
            if len(_hosts) > 500:
                _hosts.clear()
            last = conn.execute("SELECT COALESCE(MAX(id), 0) AS m FROM messages WHERE session_id = ?", (sid,)).fetchone()["m"]
            st = _hosts[sid] = {"sealer": seal().Sealer(sid, "host"), "after": last, "answered": 0}
            _say(conn, sid, st["sealer"].hello({"kind": "none", "note": "sandbox: simulated host"}))
        sealer = st["sealer"]
        rows = conn.execute("SELECT id, body FROM messages WHERE session_id = ? AND sender = 'user' AND id > ? ORDER BY id",
                            (sid, st["after"])).fetchall()
        for r in rows:
            st["after"] = r["id"]
            env = seal().parse(r["body"])
            try:
                if env is not None and env["t"] == "hello":
                    sealer.accept(env)
                    continue
                if env is not None:
                    words = len(sealer.unseal(env).split())
                    st["answered"] += 1
                    _say(conn, sid, sealer.seal(_reply(s["model"], words, len(r["body"]), st["answered"], True)))
                else:
                    st["answered"] += 1
                    _say(conn, sid, _reply(s["model"], len(r["body"].split()), len(r["body"]), st["answered"], False))
            except seal().SealError:
                # An envelope this host cannot open (a key from another tab, or out of order). A real host
                # program answers the same way: a plain notice, and it stays sealed.
                _say(conn, sid, "The simulated host could not open that message. Reload the page and send it again.")


def _say(conn: sqlite3.Connection, sid: int, body: str) -> None:
    conn.execute("INSERT INTO messages (session_id, sender, body) VALUES (?, 'host', ?)", (sid, body))


def _reply(model: str, words: int, envelope_chars: int, n: int, sealed: bool) -> str:
    """What the simulated host says. Every sentence must be exactly true (rule 5)."""
    word = "word" if words == 1 else "words"
    if not sealed:
        return (f"Scripted reply {n}. No model runs in the sandbox. Your message of {words} {word} "
                "arrived unsealed, so Orbit could read it.")
    if n == 1:
        return ("This is a scripted reply. No model runs in the sandbox.\n\n"
                "What happened to your message: your browser sealed it with a key made for this session. "
                f"Orbit stored and passed on an envelope of {envelope_chars} characters. The simulated host "
                f"opened it and counted {words} {word}. This reply came back to you sealed the same way.\n\n"
                f"With a real host, {model} runs on the host's machine and answers here. The host's key "
                "stays on that machine, so Orbit relays envelopes it cannot open.")
    return (f"Scripted reply {n}. Envelope of {envelope_chars} characters in, {words} {word} read by the "
            "simulated host, reply sealed on the way back. No model wrote this.")
