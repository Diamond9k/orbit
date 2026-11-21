"""The scoreboard: the numbers the goal is measured by, straight from the database.

Orbit carries no money since 2026-11-20 (docs/decisions/2026-11-20-self-hosting-only.md), so
the board counts use: people, their machines, and the sessions they ran on them.

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
        return {"db": db_path, "exists": False, "users": 0, "machines": 0, "machines_online": 0,
                "sessions": 0, "minutes": 0}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    q = lambda sql: conn.execute(sql).fetchone()[0]
    out = {
        "db": db_path, "exists": True,
        "users": int(q("SELECT COUNT(*) FROM users")),
        "machines": int(q("SELECT COUNT(*) FROM hosts WHERE status != 'removed'")),
        "machines_online": int(q("SELECT COUNT(*) FROM hosts WHERE status IN ('online','busy')")),
        "sessions": int(q("SELECT COUNT(*) FROM sessions")),
        "minutes": int(q("SELECT COALESCE(SUM(minutes), 0) FROM sessions")),
    }
    conn.close()
    return out


if __name__ == "__main__":
    print(json.dumps(read(os.environ.get("ORBIT_DB", sys.argv[1] if len(sys.argv) > 1 else "orbit.db")), indent=2))
