"""The scoreboard: the numbers the goal is measured by, straight from the ledger.

    python swarm/scoreboard.py            prints JSON
    ORBIT_DB=path python swarm/scoreboard.py
"""
import json
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {"db": db_path, "exists": False, "hosts_paid_cents": 0, "hosts_earned_test_cents": 0,
                "paid_out_cents": 0, "sessions": 0, "sessions_by_strangers": 0, "hosts_online": 0,
                "hosts_listed": 0, "users": 0}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    q = lambda sql: conn.execute(sql).fetchone()[0]
    # Hosts paid: what hosts earned from sessions run by someone other than the host's owner,
    # paid for with money that was never dev test funds. Everything else a host earned is
    # test money and is shown apart, so Cooper paying Cooper never looks like progress.
    # Money that actually left Orbit to a host is a negative host row with memo 'payout:...'
    # (no code writes those yet; the number is here so the day it does, the board is ready).
    real_session_earnings = (
        "SELECT COALESCE(SUM(l.amount_cents),0) FROM ledger l JOIN sessions s ON l.memo = 'session:' || s.id "
        "JOIN hosts h ON h.id = s.host_id WHERE l.account = 'host:' || s.host_id AND l.amount_cents > 0 "
        "AND s.user_id != h.owner_id "
        "AND NOT EXISTS (SELECT 1 FROM ledger d WHERE d.account = 'user:' || s.user_id AND d.memo = 'dev test funds')")
    hosts_paid = q(real_session_earnings)
    hosts_earned_all = q("SELECT COALESCE(SUM(amount_cents),0) FROM ledger WHERE account LIKE 'host:%' AND amount_cents > 0")
    paid_out = q("SELECT COALESCE(-SUM(amount_cents),0) FROM ledger WHERE account LIKE 'host:%' AND amount_cents < 0 AND memo LIKE 'payout:%'")
    dev_funded_users = q("SELECT COUNT(DISTINCT account) FROM ledger WHERE memo = 'dev test funds' AND account LIKE 'user:%'")
    out = {
        "db": db_path, "exists": True,
        "hosts_paid_cents": int(hosts_paid),
        "hosts_earned_test_cents": int(hosts_earned_all - hosts_paid),
        "paid_out_cents": int(paid_out),
        "sessions": int(q("SELECT COUNT(*) FROM sessions")),
        "sessions_by_strangers": int(q(
            "SELECT COUNT(*) FROM sessions s JOIN hosts h ON h.id = s.host_id WHERE s.user_id != h.owner_id")),
        "hosts_online": int(q("SELECT COUNT(*) FROM hosts WHERE status IN ('online','busy')")),
        "hosts_listed": int(q("SELECT COUNT(*) FROM hosts WHERE status != 'removed'")),
        "users": int(q("SELECT COUNT(*) FROM users")),
        "dev_funded_users": int(dev_funded_users),
    }
    conn.close()
    return out


if __name__ == "__main__":
    print(json.dumps(read(os.environ.get("ORBIT_DB", sys.argv[1] if len(sys.argv) > 1 else "orbit.db")), indent=2))
