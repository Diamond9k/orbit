"""Interruption and resumption, with isolated data.

What the code, not the task board, prevents when a piece of Orbit restarts mid-session:
the clock does not restart, the session is not lost, a repeated stop changes nothing.
Each test runs against the throwaway database named in tests/conftest.py.
"""
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
    """Signed up, a machine added, a session started and ready."""
    client.post("/signup", data={"email": "r@b.co", "password": "longenough"}, follow_redirects=False)
    r = client.post("/hosts", data={"name": "Box", "gpu": "RTX 4090", "vram_gb": 24})
    token = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()
    client.post("/api/hosts/heartbeat", data={"token": token})
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
    heartbeat, starts the model again and posts ready again. The clock still runs from the first ready."""
    token = _ready_session(client)
    first = _stamp(4 * 60 + 30)  # ready four and a half minutes ago
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", first)
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json()["session"]["id"] == 1  # the same session, not a new one
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200  # ready, again
    assert _query("SELECT ready_at FROM sessions WHERE id = 1")[0]["ready_at"] == first
    client.post("/sessions/1/stop", follow_redirects=False)
    s = _query("SELECT minutes, end_reason FROM sessions WHERE id = 1")[0]
    assert (s["minutes"], s["end_reason"]) == (5, "stopped")


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


def test_a_repeated_stop_changes_nothing(client):
    """Stop pressed twice, or a retry after a timeout: the first stop is the one on the record."""
    _ready_session(client)
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(90))
    client.post("/sessions/1/stop", follow_redirects=False)
    first = [tuple(r) for r in _query("SELECT minutes, ended_at, end_reason FROM sessions WHERE id = 1")]
    assert first[0][0] == 2 and first[0][2] == "stopped"   # 90 seconds rounds up to 2 minutes
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(900))
    client.post("/sessions/1/stop", follow_redirects=False)
    client.post("/sessions/1/stop", follow_redirects=False)
    assert [tuple(r) for r in _query("SELECT minutes, ended_at, end_reason FROM sessions WHERE id = 1")] == first
