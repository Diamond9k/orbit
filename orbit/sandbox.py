"""Sandbox mode: the whole loop with nothing real behind it. On with ORBIT_SANDBOX=1.

Made for a public demo address. In the sandbox:
  - a visitor enters as a guest with one click. No email or password is asked for or kept.
  - each guest gets simulated machines of their own. No host program can connect, and no model
    runs. A simulated machine does the real key exchange (host/seal.py) and sends scripted
    replies that say they are scripted.
  - a guest sees only their own machines, as everywhere in Orbit.
  - the data is thrown away: a session ends when its page is closed, and everything is wiped
    when the store grows past the limits below or the server restarts.

The simulated machine's key lives in this process, next to Orbit. So the sandbox shows how the
sealing works, not the privacy it gives when the machine is your own, and the session page says
exactly that.
"""
import importlib.util
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from . import auth, db

ENABLED = os.environ.get("ORBIT_SANDBOX") == "1"

# What a guest starts with: name, GPU, GPU memory in GB. Stand-ins for machines a person might own.
MACHINES = [
    ("Sandbox workstation", "RTX A6000", 48),
    ("Sandbox desktop", "RTX 4090", 24),
    ("Sandbox laptop", "RTX 4060 Laptop", 8),
]
LOAD_SECONDS = 3              # how long the simulated machine takes to say "ready"
IDLE_SECONDS = 120            # a session whose page stopped asking is ended after this long
MAX_GUESTS = 300              # past these, the sandbox is wiped and starts again
MAX_MESSAGES = 4000
MAX_MACHINES_PER_GUEST = 5
MESSAGE_MAX_CHARS = 12000     # one sealed envelope; about 8000 characters of text

_lock = threading.RLock()
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


def reset(conn: sqlite3.Connection) -> None:
    """Throw everything away and start again."""
    with _lock:
        with db.tx(conn):
            for table in ("messages", "sessions", "hosts", "users"):
                conn.execute(f"DELETE FROM {table}")
        _hosts.clear()


def tick(conn: sqlite3.Connection, end_session) -> None:
    """Keep the sandbox running. Called on every request; does its work at most once a second.

    `end_session` is the app's own function, so a sandbox session is closed by the same code
    as a real one.
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
        # Every machine here is simulated, so a free one is always online.
        conn.execute("UPDATE hosts SET status = 'online', last_seen = datetime('now') WHERE status IN ('offline', 'online')")
        # A busy machine is kept alive only while its session page keeps asking (see step). When the
        # page is closed the session ends, counted up to the last time the page was there.
        idle = conn.execute(
            "SELECT s.*, h.last_seen FROM sessions s JOIN hosts h ON h.id = s.host_id "
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
    """A new guest with simulated machines of their own. Returns the user id."""
    name = f"guest-{secrets.token_hex(4)}@sandbox.invalid"
    uid = auth.create_user(conn, name, secrets.token_urlsafe(32))  # the password is thrown away: a guest cannot sign in again
    conn.executemany(
        "INSERT INTO hosts (owner_id, name, gpu, vram_gb, token, status, last_seen) VALUES (?, ?, ?, ?, ?, 'online', datetime('now'))",
        [(uid, machine, gpu, vram, secrets.token_urlsafe(24)) for machine, gpu, vram in MACHINES])
    return uid


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
            _say(conn, sid, st["sealer"].hello({"kind": "none", "note": "sandbox: simulated machine"}))
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
                # An envelope this machine cannot open (a key from another tab, or out of order). A real host
                # program answers the same way: a plain notice, and it stays sealed.
                _say(conn, sid, "The simulated machine could not open that message. Reload the page and send it again.")


def _say(conn: sqlite3.Connection, sid: int, body: str) -> None:
    conn.execute("INSERT INTO messages (session_id, sender, body) VALUES (?, 'host', ?)", (sid, body))


def _reply(model: str, words: int, envelope_chars: int, n: int, sealed: bool) -> str:
    """What the simulated machine says. Every sentence must be exactly true."""
    word = "word" if words == 1 else "words"
    if not sealed:
        return (f"Scripted reply {n}. No model runs in the sandbox. Your message of {words} {word} "
                "arrived unsealed, so the relay could read it.")
    if n == 1:
        return ("This is a scripted reply. No model runs in the sandbox.\n\n"
                "What happened to your message: your browser sealed it with a key made for this session. "
                f"The relay stored and passed on an envelope of {envelope_chars} characters. The simulated "
                f"machine opened it and counted {words} {word}. This reply came back to you sealed the same way.\n\n"
                f"On your own machine, {model} runs there and answers here. The key stays on that machine, "
                "so the only computer that reads your words is yours.")
    return (f"Scripted reply {n}. Envelope of {envelope_chars} characters in, {words} {word} read by the "
            "simulated machine, reply sealed on the way back. No model wrote this.")
