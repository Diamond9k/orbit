"""Who can call what. Host tokens are kept only as hashes, and every route refuses a stranger.

From the recon (agent-os-finds batches 2 and 5): tokens stored hashed, and one test that walks
every route so a new one cannot ship without its check.
"""
import os
import re

import pytest
from fastapi.testclient import TestClient

from orbit import auth, db
from orbit.app import app

DB = os.environ["ORBIT_DB"]


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


def _query(sql, *args):
    conn = db.connect(DB)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _list_host(client):
    client.post("/signup", data={"email": "h@b.co", "password": "longenough"}, follow_redirects=False)
    r = client.post("/hosts", data={"name": "Box", "gpu": "RTX 4090", "vram_gb": 24, "price_dollars_per_hour": 0.60})
    return re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()


def test_the_token_is_shown_once_and_stored_only_as_a_hash(client):
    token = _list_host(client)
    stored = _query("SELECT token FROM hosts")[0]["token"]
    assert stored == auth.token_key(token) and token not in stored
    assert client.post("/api/hosts/heartbeat", data={"token": token}).status_code == 200
    # the stored value is not a token: presenting it gets nowhere
    assert client.post("/api/hosts/heartbeat", data={"token": stored}).status_code == 401


def test_tokens_stored_before_hashing_still_work_after_the_upgrade(client):
    token = _list_host(client)
    conn = db.connect(DB)
    conn.execute("UPDATE hosts SET token = ?", (token,))  # how a 2026-10-29 orbit.db holds it
    db.migrate(conn)
    db.migrate(conn)  # safe to run every start: hashes once, not twice
    conn.close()
    assert _query("SELECT token FROM hosts")[0]["token"] == auth.token_key(token)
    assert client.post("/api/hosts/heartbeat", data={"token": token}).status_code == 200


HOST_ROUTES = sorted(r.path for r in app.routes if getattr(r, "path", "").startswith("/api/hosts/"))


def test_the_host_routes_are_the_ones_this_file_knows():
    # A new host route must be added here, which means deciding how it refuses a stranger.
    assert HOST_ROUTES == ["/api/hosts/heartbeat", "/api/hosts/inbox", "/api/hosts/offline",
                           "/api/hosts/ready", "/api/hosts/reply"]


@pytest.mark.parametrize("path", HOST_ROUTES)
def test_every_host_route_refuses_a_wrong_or_removed_token(client, path):
    token = _list_host(client)
    client.post("/api/hosts/heartbeat", data={"token": token})
    before = _query("SELECT status, last_seen FROM hosts")[0]
    form = {"after": 0, "wait": 0, "session_id": 1, "body": "x"}
    for bad in ("nope", "", auth.token_key(token)):
        r = client.post(path, data={"token": bad, **form})
        assert r.status_code in (401, 404, 409, 422), (path, bad, r.status_code)
    assert tuple(_query("SELECT status, last_seen FROM hosts")[0]) == tuple(before)
    client.post("/hosts/1/remove", follow_redirects=False)
    r = client.post(path, data={"token": token, **form})
    assert r.status_code in (401, 404, 409), (path, r.status_code)


SIGNED_IN_PAGES = [("GET", "/account"), ("GET", "/store"), ("GET", "/sessions/1"),
                   ("POST", "/sessions/1/stop"), ("GET", "/sessions/1/messages"),
                   ("POST", "/sessions/1/messages"), ("POST", "/hosts/1/remove"),
                   ("POST", "/store/dev-funds"), ("POST", "/store/checkout"), ("POST", "/sessions/start")]


@pytest.mark.parametrize("method,path", SIGNED_IN_PAGES)
def test_signed_in_routes_send_a_stranger_to_sign_in(client, method, path):
    r = client.request(method, path, follow_redirects=False,
                       data={"model": "x/M-7B", "host_id": 1, "amount_cents": 500, "body": "hi"} if method == "POST" else None)
    assert r.status_code == 303 and r.headers["location"] == "/login", (method, path, r.status_code)
