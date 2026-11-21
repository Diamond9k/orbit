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
    r = client.post("/hosts", data={"name": "Box", "gpu": "Quadro Zed", "vram_gb": 24})
    assert r.status_code == 200
    import re
    token = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {"session": None}
    # a machine that is not there: a friendly redirect back with a message, not an error code
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 99}, follow_redirects=False)
    assert r.status_code == 303 and "orbit_flash" in r.headers.get("set-cookie", "")
    page = client.get("/?model=x/Model-7B-Q4_K_M", cookies={"orbit_flash": "That machine is offline"}).text
    assert "That machine is offline" in page
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/sessions/1"
    # a second session is refused while one runs, and sends you to the running one
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/sessions/1"
    page = client.get("/sessions/1", cookies={"orbit_flash": "You already have a session running"}).text
    assert "You already have a session running" in page
    # the host program says the model is loaded; the clock starts now
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    r = client.post("/sessions/1/stop", follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/sessions/1").text
    assert "Minutes used" in page and ">ended<" in page
    assert client.get("/health").json()["ok"] is True
    acct = client.get("/account").text
    assert "x/Model-7B-Q4_K_M" in acct and "$" not in acct      # one minute on the record, and no money anywhere


def test_nobody_else_can_see_or_use_a_machine(client):
    token = _start_session(client)
    client.post("/sessions/1/stop", follow_redirects=False)
    client.post("/api/hosts/heartbeat", data={"token": token})
    with TestClient(app) as other:
        other.post("/signup", data={"email": "o@b.co", "password": "longenough"}, follow_redirects=False)
        assert "Quadro Zed" not in other.get("/hosts").text and "Quadro Zed" not in other.get("/?model=x/Model-7B-Q4_K_M").text
        r = other.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
        assert r.headers["location"].startswith("/?model=")       # refused: not their machine
    with TestClient(app) as anyone:                                # signed out: a fit table, never a machine
        page = anyone.get("/?model=x/Model-7B-Q4_K_M").text
        assert "fit-strip" in page and "Quadro Zed" not in page


def test_an_old_database_with_prices_is_brought_up_to_date(tmp_path):
    import sqlite3
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, pw_hash BLOB NOT NULL, pw_salt BLOB NOT NULL, created_at TEXT);
        CREATE TABLE hosts (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, name TEXT NOT NULL, gpu TEXT NOT NULL, vram_gb REAL NOT NULL,
            price_cents_per_hour INTEGER NOT NULL, token TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'offline', last_seen TEXT, created_at TEXT);
        CREATE TABLE sessions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, host_id INTEGER NOT NULL, model TEXT NOT NULL,
            started_at TEXT, ended_at TEXT, minutes INTEGER, cost_cents INTEGER, ready_at TEXT, end_reason TEXT);
        CREATE TABLE ledger (id INTEGER PRIMARY KEY, txn_id TEXT, account TEXT, amount_cents INTEGER, memo TEXT, created_at TEXT);
        INSERT INTO users (email, pw_hash, pw_salt) VALUES ('a@b.co', X'00', X'00');
        INSERT INTO hosts (owner_id, name, gpu, vram_gb, price_cents_per_hour, token) VALUES (1, 'Box', 'G', 8, 60, 't');
        INSERT INTO sessions (user_id, host_id, model, minutes, cost_cents) VALUES (1, 1, 'm', 5, 5);
        INSERT INTO ledger (txn_id, account, amount_cents, memo) VALUES ('x', 'user:1', -5, 'session:1');
    """)
    old.commit(); old.close()
    db.init(path); db.init(path)
    conn = db.connect(path)
    assert "price_cents_per_hour" not in {r["name"] for r in conn.execute("PRAGMA table_info(hosts)")}
    assert "cost_cents" not in {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
    assert conn.execute("SELECT name, minutes FROM hosts JOIN sessions ON host_id = hosts.id").fetchone()["minutes"] == 5
    assert conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 1          # old money rows are history, left alone
    conn.execute("INSERT INTO hosts (owner_id, name, gpu, vram_gb, token) VALUES (1, 'New', 'G', 8, 'u')")
    conn.close()


def test_hugging_face_url_is_cleaned(client):
    from orbit.app import clean_model
    assert clean_model("https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF") == "bartowski/Qwen2.5-7B-Instruct-GGUF"
    assert clean_model("https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/tree/main") == "bartowski/Qwen2.5-7B-Instruct-GGUF"
    assert clean_model("  bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M ") == "bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M"


def test_remove_host(client):
    client.post("/signup", data={"email": "h@b.co", "password": "longenough"}, follow_redirects=False)
    client.post("/hosts", data={"name": "Old", "gpu": "RX 580", "vram_gb": 16})
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
    r = client.post("/hosts", data={"name": "Box", "gpu": "Quadro Zed", "vram_gb": 24})
    token = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()
    client.post("/api/hosts/heartbeat", data={"token": token})
    r = client.post("/sessions/start", data={"model": "x/Model-7B-Q4_K_M", "host_id": 1}, follow_redirects=False)
    assert r.headers["location"] == "/sessions/1"
    return token


def test_heartbeat_names_the_session_to_run(client):
    token = _start_session(client)
    # the host program learns the session id and the exact model name from the heartbeat
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {
        "session": {"id": 1, "model": "x/Model-7B-Q4_K_M"}}
    assert client.post("/api/hosts/heartbeat", data={"token": "nope"}).status_code == 401
    client.post("/sessions/1/stop", follow_redirects=False)
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {"session": None}


def test_the_clock_waits_for_the_machine(client):
    token = _start_session(client)
    assert "<strong>Waiting for the machine.</strong>" in client.get("/sessions/1").text
    assert client.post("/api/hosts/ready", data={"token": "nope"}).status_code == 404
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    conn = db.connect("test_app.db")
    assert conn.execute("SELECT ready_at FROM sessions WHERE id = 1").fetchone()["ready_at"] is not None
    conn.close()
    assert "<strong>Waiting for the machine.</strong>" not in client.get("/sessions/1").text


def test_stop_before_ready_counts_nothing(client):
    _start_session(client)
    client.post("/sessions/1/stop", follow_redirects=False)
    conn = db.connect("test_app.db")
    assert conn.execute("SELECT minutes FROM sessions WHERE id = 1").fetchone()["minutes"] == 0
    conn.close()
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


def _stamp(minutes_ago):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _ready_session(client):
    """A running, ready session."""
    token = _start_session(client)
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    return token


def _session_row(sid=1):
    conn = db.connect("test_app.db")
    s = conn.execute("SELECT minutes, end_reason FROM sessions WHERE id = ?", (sid,)).fetchone()
    host = conn.execute("SELECT status FROM hosts WHERE id = 1").fetchone()["status"]
    conn.close()
    return (s["minutes"], s["end_reason"]), host


def _set(sql, *args):
    conn = db.connect("test_app.db")
    conn.execute(sql, args)
    conn.close()


def test_a_session_runs_as_long_as_the_machine_does(client):
    token = _ready_session(client)
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(1200))  # twenty hours on your own machine: nothing cuts it off
    assert 'data-phase="running"' in client.get("/sessions/1").text
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json()["session"]["id"] == 1


def test_session_ends_when_the_host_stops_answering(client):
    _ready_session(client)
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(12))
    _set("UPDATE hosts SET last_seen = ? WHERE id = 1", _stamp(10))  # silent for 10 minutes
    page = client.get("/sessions/1").text
    assert ">ended<" in page and "The machine stopped answering" in page
    # counted from ready to the last heartbeat: 2 minutes, not the 12 since ready
    assert _session_row() == ((2, "host_lost"), "offline")


def test_lost_host_before_ready_counts_nothing(client):
    _start_session(client)
    _set("UPDATE hosts SET last_seen = ? WHERE id = 1", _stamp(10))
    assert ">ended<" in client.get("/sessions/1").text
    assert _session_row() == ((0, "host_lost"), "offline")


def test_chat_is_relayed_and_dropped_with_the_session(client):
    token = _start_session(client)
    # the machine is still loading: nothing can be sent yet
    assert client.post("/sessions/1/messages", data={"body": "hi"}).status_code == 409
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    r = client.post("/api/hosts/inbox", data={"token": token, "after": 0, "wait": 0}).json()
    assert r == {"session": {"id": 1, "model": "x/Model-7B-Q4_K_M"}, "messages": []}
    assert client.post("/sessions/1/messages", data={"body": "   "}).status_code == 400
    assert client.post("/sessions/1/messages", data={"body": "  hello there  "}).json() == {"id": 1}
    r = client.post("/api/hosts/inbox", data={"token": token, "after": 0, "wait": 0}).json()
    assert [(m["sender"], m["body"]) for m in r["messages"]] == [("user", "hello there")]
    assert client.post("/api/hosts/reply", data={"token": "nope", "session_id": 1, "body": "x"}).status_code == 404
    assert client.post("/api/hosts/reply", data={"token": token, "session_id": 1, "body": "Hi!"}).json() == {"id": 2}
    r = client.get("/sessions/1/messages?after=0&wait=0").json()
    assert [(m["sender"], m["body"]) for m in r["messages"]] == [("user", "hello there"), ("host", "Hi!")]
    assert r["ended"] is False and r["ready"] is True
    assert [m["id"] for m in client.get("/sessions/1/messages?after=1&wait=0").json()["messages"]] == [2]
    # the host program fetches only what it has not seen
    assert client.post("/api/hosts/inbox", data={"token": token, "after": 2, "wait": 0}).json()["messages"] == []
    # holding for news returns after the wait when nothing arrives
    import time
    t0 = time.monotonic()
    assert client.get("/sessions/1/messages?after=2&wait=0.6").json()["messages"] == []
    assert time.monotonic() - t0 >= 0.5
    # the session page shows the chat, honestly labelled
    page = client.get("/sessions/1").text
    assert 'id="chat"' in page and 'id="seal-state"' in page and "/static/seal.js" in page
    assert client.get("/static/seal.js").status_code == 200
    # Orbit stores whatever the ends send, byte for byte: an envelope is just a body to it
    envelope = '{"v":1,"t":"msg","from":"user","n":1,"ct":"AAECAwQ="}'
    mid = client.post("/sessions/1/messages", data={"body": envelope}).json()["id"]
    assert [m["body"] for m in client.get(f"/sessions/1/messages?after={mid - 1}&wait=0").json()["messages"]] == [envelope]
    # someone else cannot read it
    with TestClient(app) as other:
        other.post("/signup", data={"email": "o@b.co", "password": "longenough"}, follow_redirects=False)
        assert other.get("/sessions/1/messages?after=0&wait=0").status_code == 404
        assert other.post("/sessions/1/messages", data={"body": "hi"}).status_code == 409
    # stop: the conversation is gone, the host learns the session is over
    client.post("/sessions/1/stop", follow_redirects=False)
    assert client.post("/sessions/1/messages", data={"body": "hi"}).status_code == 409
    r = client.get("/sessions/1/messages?after=0&wait=0").json()
    assert r["ended"] is True and r["end_reason"] == "stopped" and r["messages"] == []
    assert client.post("/api/hosts/inbox", data={"token": token, "after": 0, "wait": 0}).json() == {"session": None, "messages": []}
    conn = db.connect("test_app.db")
    assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
    conn.close()
    assert "You stopped it" in client.get("/sessions/1").text


def test_old_database_gets_end_reason_and_messages(tmp_path):
    import sqlite3
    path = str(tmp_path / "old.db")
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY, user_id INTEGER, host_id INTEGER, model TEXT, "
                "started_at TEXT, ended_at TEXT, minutes INTEGER, cost_cents INTEGER, ready_at TEXT)")
    old.commit()
    old.close()
    db.init(path)
    conn = db.connect(path)
    assert "end_reason" in {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
    assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
    conn.close()


def test_a_held_inbox_request_counts_as_heartbeats(client, monkeypatch):
    """While the host program holds an inbox request it is alive, so last_seen must keep moving.
    Otherwise a host that vanishes is charged only up to the start of its last held request, and a
    host whose request is held longer than the timeout would be declared lost while connected."""
    import asyncio
    import types
    from orbit import app as app_module
    token = _ready_session(client)
    real_sleep = asyncio.sleep

    async def sleep(seconds):
        # between two polls the heartbeat row goes stale, as if ten minutes had passed
        _set("UPDATE hosts SET last_seen = ? WHERE id = 1", _stamp(10))
        await real_sleep(0)

    monkeypatch.setattr(app_module, "asyncio", types.SimpleNamespace(sleep=sleep))
    r = client.post("/api/hosts/inbox", data={"token": token, "after": 0, "wait": 0.2}).json()
    # without the refresh the sweep inside the loop would have ended the session as host_lost
    assert r["session"] == {"id": 1, "model": "x/Model-7B-Q4_K_M"} and r["messages"] == []
    conn = db.connect("test_app.db")
    last_seen = conn.execute("SELECT last_seen FROM hosts WHERE id = 1").fetchone()[0]
    conn.close()
    assert last_seen >= _stamp(1)
    assert _session_row()[0][1] is None  # still running
