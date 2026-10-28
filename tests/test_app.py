import os
os.environ["ORBIT_DEV"] = "1"
os.environ["ORBIT_DB"] = "test_app.db"

import pytest
from fastapi.testclient import TestClient

from orbit import db
from orbit.app import app


@pytest.fixture
def client():
    if os.path.exists("test_app.db"):
        os.remove("test_app.db")
    db.init("test_app.db")
    with TestClient(app) as c:
        yield c
    for f in ("test_app.db", "test_app.db-wal", "test_app.db-shm"):
        if os.path.exists(f):
            os.remove(f)


def test_full_loop(client):
    # sign up
    r = client.post("/signup", data={"email": "a@b.co", "password": "longenough"}, follow_redirects=False)
    assert r.status_code == 303
    # list a machine and bring it online
    r = client.post("/hosts", data={"name": "Box", "gpu": "RTX 4090", "vram_gb": 24, "price_dollars_per_hour": 0.60})
    assert r.status_code == 200
    import re
    token = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {"ok": True}
    # no money yet: can't start
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 402
    # add test funds and start
    client.post("/store/dev-funds", data={"amount_cents": 1000}, follow_redirects=False)
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/sessions/1"
    # a second session is refused while one runs
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 409
    # stop: one minute minimum at $0.60/h = 1 cent, host gets 80%, orbit 20%
    r = client.post("/sessions/1/stop", follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/sessions/1").text
    assert "Minutes used" in page and ">ended<" in page
    assert client.get("/health").json()["ok"] is True
    acct = client.get("/account").text
    assert "$9.99" in acct
