"""Double-entry ledger. The only code that moves money.

Rule: every posting is a list of (account, amount_cents) rows that sum to
zero, written in one transaction. Nothing else changes a balance.

Accounts:
  user:<id>        hardware time a user has paid for and not yet used
  host:<id>        what a host has earned and not yet been paid out
  orbit:revenue    Orbit's cut
  stripe:clearing  money received from cards, before it becomes user balance
  dev:faucet       test funds, only when ORBIT_DEV=1
"""
import sqlite3
import uuid

from .db import tx


class LedgerError(ValueError):
    pass


def post(conn: sqlite3.Connection, rows: list[tuple[str, int]], memo: str = "",
         once: str | None = None) -> str | None:
    """Write one balancing set of rows. Returns its txn_id.

    With `once`, the posting happens at most once for that key, ever: the key is claimed in the
    same transaction as the rows, so two callers racing (a retried Stripe event, two sweeps)
    cannot both post. The loser gets None and nothing is written.
    """
    if len(rows) < 2:
        raise LedgerError("a posting needs at least two rows")
    if any(not isinstance(amt, int) for _, amt in rows):
        raise LedgerError("amounts must be whole cents")
    if sum(amt for _, amt in rows) != 0:
        raise LedgerError("rows must sum to zero")
    txn_id = uuid.uuid4().hex
    with tx(conn):
        if once is not None:
            claimed = conn.execute("INSERT OR IGNORE INTO ledger_once (key, txn_id) VALUES (?, ?)", (once, txn_id))
            if claimed.rowcount == 0:
                return None
        conn.executemany(
            "INSERT INTO ledger (txn_id, account, amount_cents, memo) VALUES (?, ?, ?, ?)",
            [(txn_id, acct, amt, memo) for acct, amt in rows],
        )
    return txn_id


def posted(conn: sqlite3.Connection, once: str) -> bool:
    """True when a posting with this `once` key has been written."""
    return conn.execute("SELECT 1 FROM ledger_once WHERE key = ?", (once,)).fetchone() is not None


def balance(conn: sqlite3.Connection, account: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS b FROM ledger WHERE account = ?", (account,)
    ).fetchone()
    return int(row["b"])


def history(conn: sqlite3.Connection, account: str, limit: int = 50) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM ledger WHERE account = ? ORDER BY id DESC LIMIT ?", (account, limit)
    ).fetchall()


def verify(conn: sqlite3.Connection) -> list[str]:
    """Return txn_ids whose rows do not sum to zero. Empty list means the books balance."""
    rows = conn.execute(
        "SELECT txn_id FROM ledger GROUP BY txn_id HAVING SUM(amount_cents) != 0"
    ).fetchall()
    return [r["txn_id"] for r in rows]
