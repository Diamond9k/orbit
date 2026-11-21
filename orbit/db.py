"""SQLite connection and schema. One file on disk, nothing else to run."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("ORBIT_DB", "orbit.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    pw_hash     BLOB NOT NULL,
    pw_salt     BLOB NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A person's own machine. Only its owner sees it and runs models on it. No price: Orbit has no money in it.
CREATE TABLE IF NOT EXISTS hosts (
    id                   INTEGER PRIMARY KEY,
    owner_id             INTEGER NOT NULL REFERENCES users(id),
    name                 TEXT NOT NULL,
    gpu                  TEXT NOT NULL,
    vram_gb              REAL NOT NULL,
    token                TEXT NOT NULL UNIQUE,
    status               TEXT NOT NULL DEFAULT 'offline',  -- offline | online | busy
    last_seen            TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One model running on one of the person's machines.
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    host_id     INTEGER NOT NULL REFERENCES hosts(id),
    model       TEXT NOT NULL,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    minutes     INTEGER,
    ready_at    TEXT,  -- when the machine said the model is loaded; the clock starts here
    end_reason  TEXT   -- stopped | host_lost | sandbox_idle
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);

-- The conversation in flight between a browser and a host program. Orbit relays bodies
-- without reading them and deletes a session's messages when the session ends.
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    sender      TEXT NOT NULL,     -- user | host
    body        TEXT NOT NULL,     -- opaque to Orbit
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id, id);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    # One connection per request, used by one request at a time. The request's dependency and
    # its handler may run on different threads (a sync dependency feeding an async handler), so
    # SQLite's same-thread check is turned off; nothing shares a connection across requests.
    conn = sqlite3.connect(path or DB_PATH, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init(path: str | None = None) -> None:
    conn = connect(path)
    try:
        # An older database is brought up to date first, so the indexes below find their columns.
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'sessions'").fetchone():
            migrate(conn)
        conn.executescript(SCHEMA)
    finally:
        conn.close()


def migrate(conn: sqlite3.Connection) -> None:
    """Bring an existing orbit.db up to the current schema. Safe to run every start."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
    if "ready_at" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN ready_at TEXT")
    if "end_reason" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN end_reason TEXT")
    # Orbit carried prices and a ledger until 2026-11-20 (docs/decisions/2026-11-20-self-hosting-only.md).
    # The price and cost columns go. An old ledger table is left where it is: it is history, and
    # nothing reads it any more.
    if "cost_cents" in cols:
        conn.execute("ALTER TABLE sessions DROP COLUMN cost_cents")
    if "price_cents_per_hour" in {r["name"] for r in conn.execute("PRAGMA table_info(hosts)")}:
        conn.execute("ALTER TABLE hosts DROP COLUMN price_cents_per_hour")


@contextmanager
def tx(conn: sqlite3.Connection):
    """Run a block inside one SQLite transaction."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
