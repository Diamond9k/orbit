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

-- Postings that must happen at most once (a Stripe payment, a session's charge), keyed by
-- what caused them. Claimed in the same transaction as the ledger rows.
CREATE TABLE IF NOT EXISTS ledger_once (
    key     TEXT PRIMARY KEY,
    txn_id  TEXT NOT NULL
);

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
    ready_at    TEXT,  -- when the host said the model is loaded; billing starts here
    end_reason  TEXT   -- stopped | out_of_time | host_lost
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
        conn.executescript(SCHEMA)
        migrate(conn)
    finally:
        conn.close()


def migrate(conn: sqlite3.Connection) -> None:
    """Bring an existing orbit.db up to the current schema. Safe to run every start."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
    if "ready_at" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN ready_at TEXT")
    if "end_reason" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN end_reason TEXT")
    # Postings made before ledger_once existed claim their keys now, so a retry after the
    # upgrade still finds them already posted.
    conn.execute("INSERT OR IGNORE INTO ledger_once (key, txn_id) SELECT memo, MIN(txn_id) FROM ledger "
                 "WHERE memo LIKE 'stripe:%' OR memo LIKE 'session:%' GROUP BY memo")


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
