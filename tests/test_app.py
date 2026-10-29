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
    # no money yet: can't start. Friendly redirect back with a message, not an error code.
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 303 and "orbit_flash" in r.headers.get("set-cookie", "")
    page = client.get("/?model=x/Model-7B-Q4_K_M", cookies={"orbit_flash": "You need at least one hour"}).text
    assert "You need at least one hour" in page
    # add test funds and start
    client.post("/store/dev-funds", data={"amount_cents": 1000}, follow_redirects=False)
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/sessions/1"
    # a second session is refused while one runs, and sends you to the running one
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/sessions/1"
    page = client.get("/sessions/1", cookies={"orbit_flash": "You already have a session running"}).text
    assert "You already have a session running" in page
    # the host program says the model is loaded; billing starts now
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    # stop: one minute minimum at $0.60/h = 1 cent, host gets 80%, orbit 20%
    r = client.post("/sessions/1/stop", follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/sessions/1").text
    assert "Minutes used" in page and ">ended<" in page
    assert client.get("/health").json()["ok"] is True
    acct = client.get("/account").text
    assert "$9.99" in acct


def test_hugging_face_url_is_cleaned(client):
    from orbit.app import clean_model
    assert clean_model("https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF") == "bartowski/Qwen2.5-7B-Instruct-GGUF"
    assert clean_model("https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/tree/main") == "bartowski/Qwen2.5-7B-Instruct-GGUF"
    assert clean_model("  bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M ") == "bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M"


def test_remove_host(client):
    client.post("/signup", data={"email": "h@b.co", "password": "longenough"}, follow_redirects=False)
    client.post("/hosts", data={"name": "Old", "gpu": "RX 580", "vram_gb": 16, "price_dollars_per_hour": 1})
    assert "Old" in client.get("/hosts").text
    r = client.post("/hosts/1/remove", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/account"
    assert "Old" not in client.get("/hosts").text


def test_dotenv_loader_does_not_override(tmp_path, monkeypatch):
    from orbit.__main__ import load_dotenv
    f = tmp_path / ".env"
    f.write_text("# comment\nORBIT_TEST_A=hello\nORBIT_TEST_B='quoted'\nORBIT_TEST_C=keep\n")
    monkeypatch.setenv("ORBIT_TEST_C", "already")
    monkeypatch.delenv("ORBIT_TEST_A", raising=False)
    load_dotenv(f)
    assert os.environ["ORBIT_TEST_A"] == "hello"
    assert os.environ["ORBIT_TEST_B"] == "quoted"
    assert os.environ["ORBIT_TEST_C"] == "already"


def _start_session(client):
    import re
    client.post("/signup", data={"email": "r@b.co", "password": "longenough"}, follow_redirects=False)
    r = client.post("/hosts", data={"name": "Box", "gpu": "RTX 4090", "vram_gb": 24, "price_dollars_per_hour": 0.60})
    token = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()
    client.post("/api/hosts/heartbeat", data={"token": token})
    client.post("/store/dev-funds", data={"amount_cents": 1000}, follow_redirects=False)
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.headers["location"] == "/sessions/1"
    return token


def test_no_charge_before_machine_is_ready(client):
    token = _start_session(client)
    assert "Waiting for the machine. You are not being charged." in client.get("/sessions/1").text
    assert client.post("/api/hosts/ready", data={"token": "nope"}).status_code == 404
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    conn = db.connect("test_app.db")
    assert conn.execute("SELECT ready_at FROM sessions WHERE id = 1").fetchone()["ready_at"] is not None
    conn.close()
    assert "Waiting for the machine" not in client.get("/sessions/1").text


def test_stop_before_ready_charges_nothing(client):
    _start_session(client)
    client.post("/sessions/1/stop", follow_redirects=False)
    conn = db.connect("test_app.db")
    s = conn.execute("SELECT minutes, cost_cents FROM sessions WHERE id = 1").fetchone()
    conn.close()
    assert (s["minutes"], s["cost_cents"]) == (0, 0)
    assert "$10.00" in client.get("/account").text
    # no running session left, so ready is refused
    assert client.post("/api/hosts/ready", data={"token": "anything"}).status_code == 404


def test_old_database_gets_ready_at(tmp_path):
    import sqlite3
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY, user_id INTEGER, host_id INTEGER, model TEXT, "
                "started_at TEXT, ended_at TEXT, minutes INTEGER, cost_cents INTEGER)")
    old.execute("INSERT INTO sessions (user_id, host_id, model) VALUES (1, 1, 'm')")
    old.commit()
    old.close()
    db.init(path)
    db.init(path)  # running it twice is safe
    conn = db.connect(path)
    assert "ready_at" in {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
    assert conn.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
    conn.close()
