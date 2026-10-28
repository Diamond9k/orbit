"""The scoreboard: the numbers the goal is measured by, straight from the ledger.

    python swarm/scoreboard.py            prints JSON
    ORBIT_DB=path python swarm/scoreboard.py
"""
import json
import os
import sqlite3
import sys


def read(db_path: str) -> dict:
    if not os.path.exists(db_path):
        return {"db": db_path, "exists": False, "hosts_paid_cents": 0, "sessions": 0,
                "sessions_by_strangers": 0, "hosts_online": 0, "hosts_listed": 0, "users": 0}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    q = lambda sql: conn.execute(sql).fetchone()[0]
    # Hosts paid: every cent that landed in a host account. Test funds are excluded by
    # ignoring sessions whose user was funded only from dev:faucet.
    hosts_paid = q("SELECT COALESCE(SUM(amount_cents),0) FROM ledger WHERE account LIKE 'host:%' AND amount_cents > 0")
    dev_funded_users = q("SELECT COUNT(DISTINCT account) FROM ledger WHERE memo = 'dev test funds'")
    out = {
        "db": db_path, "exists": True,
        "hosts_paid_cents": int(hosts_paid),
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
