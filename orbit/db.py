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

-- Double-entry ledger. Every txn_id groups rows that sum to zero.
CREATE TABLE IF NOT EXISTS ledger (
    id           INTEGER PRIMARY KEY,
    txn_id       TEXT NOT NULL,
    account      TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    memo         TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ledger_account ON ledger(account);
CREATE INDEX IF NOT EXISTS ledger_txn ON ledger(txn_id);

-- A machine someone is offering. Owned by a user.
CREATE TABLE IF NOT EXISTS hosts (
    id                   INTEGER PRIMARY KEY,
    owner_id             INTEGER NOT NULL REFERENCES users(id),
    name                 TEXT NOT NULL,
    gpu                  TEXT NOT NULL,
    vram_gb              REAL NOT NULL,
    price_cents_per_hour INTEGER NOT NULL,
    token                TEXT NOT NULL UNIQUE,
    status               TEXT NOT NULL DEFAULT 'offline',  -- offline | online | busy
    last_seen            TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One user, one host, exclusive for the session.
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    host_id     INTEGER NOT NULL REFERENCES hosts(id),
    model       TEXT NOT NULL,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    minutes     INTEGER,
    cost_cents  INTEGER,
    ready_at    TEXT  -- when the host said the model is loaded; billing starts here
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init(path: str | None = None) -> None:
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        migrate(conn)
    finally:
        conn.close()


def migrate(conn: sqlite3.Connection) -> None:
    """Bring an existing orbit.db up to the current schema. Safe to run every start."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
    if "ready_at" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN ready_at TEXT")


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
