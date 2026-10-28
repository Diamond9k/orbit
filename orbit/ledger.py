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


def post(conn: sqlite3.Connection, rows: list[tuple[str, int]], memo: str = "") -> str:
    if len(rows) < 2:
        raise LedgerError("a posting needs at least two rows")
    if any(not isinstance(amt, int) for _, amt in rows):
        raise LedgerError("amounts must be whole cents")
    if sum(amt for _, amt in rows) != 0:
        raise LedgerError("rows must sum to zero")
    txn_id = uuid.uuid4().hex
    with tx(conn):
        conn.executemany(
            "INSERT INTO ledger (txn_id, account, amount_cents, memo) VALUES (?, ?, ?, ?)",
            [(txn_id, acct, amt, memo) for acct, amt in rows],
        )
    return txn_id


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
