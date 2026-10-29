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
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {"session": None}
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


def test_heartbeat_names_the_session_to_run(client):
    token = _start_session(client)
    # the host program learns the session id and the exact model name from the heartbeat
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {
        "session": {"id": 1, "model": "x/Model-7B-Q4_K_M"}}
    assert client.post("/api/hosts/heartbeat", data={"token": "nope"}).status_code == 401
    client.post("/sessions/1/stop", follow_redirects=False)
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {"session": None}


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


def _stamp(minutes_ago):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _ready_session(client):
    """A running, ready session: $10.00 of time on a $0.60/h machine, so 1000 minutes are covered."""
    token = _start_session(client)
    assert client.post("/api/hosts/ready", data={"token": token}).status_code == 200
    return token


def _session_row(sid=1):
    conn = db.connect("test_app.db")
    s = conn.execute("SELECT minutes, cost_cents, end_reason FROM sessions WHERE id = ?", (sid,)).fetchone()
    host = conn.execute("SELECT status FROM hosts WHERE id = 1").fetchone()["status"]
    conn.close()
    return (s["minutes"], s["cost_cents"], s["end_reason"]), host


def _set(sql, *args):
    conn = db.connect("test_app.db")
    conn.execute(sql, args)
    conn.close()


def test_session_ends_on_its_own_when_time_runs_out(client):
    token = _ready_session(client)
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(1200))  # ran 20 hours, had 1000 minutes
    page = client.get("/sessions/1").text
    assert ">ended<" in page and "Your hardware time ran out" in page
    assert _session_row() == ((1000, 1000, "out_of_time"), "online")
    assert "$0.00" in client.get("/account").text  # charged exactly what was there, never below zero
    assert client.get("/health").json()["ok"] is True
    assert client.post("/api/hosts/heartbeat", data={"token": token}).json() == {"session": None}


def test_stopping_late_charges_only_the_time_that_was_covered(client):
    _ready_session(client)
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(1500))
    client.post("/sessions/1/stop", follow_redirects=False)
    assert _session_row() == ((1000, 1000, "out_of_time"), "online")


def test_session_ends_when_the_host_stops_answering(client):
    _ready_session(client)
    _set("UPDATE sessions SET ready_at = ? WHERE id = 1", _stamp(12))
    _set("UPDATE hosts SET last_seen = ? WHERE id = 1", _stamp(10))  # silent for 10 minutes
    page = client.get("/sessions/1").text
    assert ">ended<" in page and "The machine stopped answering" in page
    # charged from ready to the last heartbeat: 2 minutes at $0.60/h is 2 cents, not the 12 minutes since ready
    assert _session_row() == ((2, 2, "host_lost"), "offline")
    assert "$9.98" in client.get("/account").text


def test_lost_host_before_ready_costs_nothing(client):
    _start_session(client)
    _set("UPDATE hosts SET last_seen = ? WHERE id = 1", _stamp(10))
    assert ">ended<" in client.get("/sessions/1").text
    assert _session_row() == ((0, 0, "host_lost"), "offline")
    assert "$10.00" in client.get("/account").text


def test_a_lost_charge_is_posted_once(client):
    _ready_session(client)
    client.post("/sessions/1/stop", follow_redirects=False)
    conn = db.connect("test_app.db")
    assert conn.execute("SELECT COUNT(*) FROM ledger WHERE memo = 'session:1'").fetchone()[0] == 3
    conn.close()
    # pretend the process died between closing the session and posting the charge, two minutes ago
    _set("DELETE FROM ledger WHERE memo = 'session:1'")
    _set("UPDATE sessions SET ended_at = ? WHERE id = 1", _stamp(2))
    client.get("/account")  # any sweep repairs it
    client.get("/account")  # and a second sweep does not bill twice
    conn = db.connect("test_app.db")
    rows = conn.execute("SELECT account, amount_cents FROM ledger WHERE memo = 'session:1' ORDER BY id").fetchall()
    conn.close()
    assert [(r["account"], r["amount_cents"]) for r in rows] == [("user:1", -1), ("host:1", 1), ("orbit:revenue", 0)]
    assert client.get("/health").json()["ok"] is True


def test_affordable_minutes_rounds_like_the_bill():
    import math
    from orbit.app import affordable_minutes
    assert affordable_minutes(1000, 60) == 1000
    assert affordable_minutes(60, 60) == 60
    assert affordable_minutes(0, 60) == 0 and affordable_minutes(100, 0) == 0
    for balance, price in [(1000, 70), (999, 60), (1, 60), (5, 7), (250, 33)]:
        m = affordable_minutes(balance, price)
        assert math.ceil(price * m / 60) <= balance < math.ceil(price * (m + 1) / 60)


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
    assert 'id="chat"' in page and "unsealed for now" in page
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
