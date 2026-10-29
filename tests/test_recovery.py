"""Interruption and resumption, with isolated data.

What the code, not the task board, prevents when a piece of Orbit restarts mid-session:
the clock does not restart, the session is not lost, a repeated stop does not bill twice.
Each test runs against the throwaway database named in tests/conftest.py.
"""
import math
import os
import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from orbit import db
from orbit.app import app

DB = os.environ["ORBIT_DB"]
assert DB != "orbit.db"


def _clean():
    for f in (DB, DB + "-wal", DB + "-shm"):
        if os.path.exists(f):
            os.remove(f)


@pytest.fixture
def client():
    _clean()
    db.init(DB)
    with TestClient(app) as c:
        yield c
    _clean()


def _stamp(seconds_ago):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _ready_session(client):
    """Signed up, a machine listed at $0.60 an hour, $10.00 of time, a session started and ready."""
    client.post("/signup", data={"email": "r@b.co", "password": "longenough"}, follow_redirects=False)
    r = client.post("/hosts", data={"name": "Box", "gpu": "RTX 4090", "vram_gb": 24, "price_dollars_per_hour": 0.60})
    token = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()
    client.post("/api/hosts/heartbeat", data={"token": token})
    client.post("/store/dev-funds", data={"amount_cents": 1000}, follow_redirects=False)
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.headers["location"] == "/sessions/1"
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    return token


def _query(sql, *args):
    conn = db.connect(DB)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _set(sql, *args):
    conn = db.connect(DB)
    conn.execute(sql, args)
    conn.close()


def test_a_restarted_host_program_does_not_restart_the_clock(client):
    """The host program crashes and comes back mid-session: it hears the same session in its
    heartbeat, starts the model again and posts ready again. Billing still runs from the first ready."""
    token = _ready_session(client)
    first = _stamp(4 * 60 + 30)  # ready four and a half minutes ago
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", first)
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json()["session"]["id"] == 1  # the same session, not a new one
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200  # ready, again
    assert _query("SELECT ready_at FROM sessions WHERE id = 1")[0]["ready_at"] == first
    client.post("/sessions/1/stop", follow_redirects=False)
    s = _query("SELECT minutes, cost_cents, end_reason FROM sessions WHERE id = 1")[0]
    assert (s["minutes"], s["cost_cents"], s["end_reason"]) == (5, 5, "stopped")  # 5 minutes at $0.60 an hour


def test_a_restarted_orbit_keeps_the_running_session(client):
    """Orbit itself restarts: the session, its clock and the conversation are in the database, not in memory."""
    token = _ready_session(client)
    before = _query("SELECT ready_at FROM sessions WHERE id = 1")[0]["ready_at"]
    assert client.post("/sessions/1/messages", data={"body": "still here?"}).status_code == 200
    with TestClient(app) as restarted:  # a second start of the app on the same database
        restarted.post("/login", data={"email": "r@b.co", "password": "longenough"}, follow_redirects=False)
        page = restarted.get("/sessions/1")
        assert page.status_code == 200 and "running" in page.text
        assert restarted.post("/api/hosts/heartbeat", data={"token": token}).json()["session"]["id"] == 1
        inbox = restarted.post("/api/hosts/inbox", data={"token": token, "after": 0}).json()
        assert [m["body"] for m in inbox["messages"]] == ["still here?"]
    assert _query("SELECT ready_at, ended_at FROM sessions WHERE id = 1")[0]["ready_at"] == before
    assert _query("SELECT ended_at FROM sessions WHERE id = 1")[0]["ended_at"] is None


def test_a_repeated_stop_bills_once(client):
    """Stop pressed twice, or a retry after a timeout: one charge, the ledger still sums to zero."""
    _ready_session(client)
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(90))
    client.post("/sessions/1/stop", follow_redirects=False)
    rows_after_first = _query("SELECT account, amount_cents FROM ledger WHERE memo = 'session:1' ORDER BY id")
    balance_after_first = _query("SELECT COALESCE(SUM(amount_cents), 0) AS b FROM ledger WHERE account = 'user:1'")[0]["b"]
    assert rows_after_first and sum(r["amount_cents"] for r in rows_after_first) == 0
    client.post("/sessions/1/stop", follow_redirects=False)
    client.post("/sessions/1/stop", follow_redirects=False)
    assert _query("SELECT account, amount_cents FROM ledger WHERE memo = 'session:1' ORDER BY id") == rows_after_first
    assert _query("SELECT COALESCE(SUM(amount_cents), 0) AS b FROM ledger WHERE account = 'user:1'")[0]["b"] == balance_after_first
    s = _query("SELECT minutes, cost_cents FROM sessions WHERE id = 1")[0]
    assert (s["minutes"], s["cost_cents"]) == (2, math.ceil(60 * 2 / 60))  # 90 seconds rounds up to 2 minutes
