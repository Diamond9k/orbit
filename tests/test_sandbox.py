"""Sandbox mode: guests, test funds, simulated machines, and nothing real behind them."""
import os
import re

import pytest
from fastapi.testclient import TestClient

import orbit.app as appmod
from orbit import db, sandbox
from orbit.app import app

MODEL = "x/Model-7B-Q4_K_M"


@pytest.fixture
def box(monkeypatch):
    for f in ("test_app.db", "test_app.db-wal", "test_app.db-shm"):
        if os.path.exists(f):
            os.remove(f)
    db.init("test_app.db")
    monkeypatch.setattr(appmod, "SANDBOX", True)
    monkeypatch.setattr(appmod, "DEV", False)
    monkeypatch.setitem(appmod.templates.env.globals, "sandbox", True)
    monkeypatch.setattr(sandbox, "_system_id", None)
    monkeypatch.setattr(sandbox, "_last_tick", 0.0)
    monkeypatch.setattr(sandbox, "LOAD_SECONDS", 0)
    sandbox._hosts.clear()
    with TestClient(app) as c:
        yield c
    sandbox._hosts.clear()
    for f in ("test_app.db", "test_app.db-wal", "test_app.db-shm"):
        if os.path.exists(f):
            os.remove(f)


def _enter(c):
    r = c.post("/sandbox/enter", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/?model=")


def _start(c):
    _enter(c)
    host_id = int(re.search(r'name="host_id" value="(\d+)"', c.get("/", params={"model": MODEL}).text).group(1))
    r = c.post("/sessions/start", data={"model": MODEL, "host_id": host_id}, follow_redirects=False)
    assert r.status_code == 303
    return int(r.headers["location"].rsplit("/", 1)[1])


def test_the_door_exists_only_in_the_sandbox(client_plain):
    assert client_plain.post("/sandbox/enter", follow_redirects=False).status_code == 404


@pytest.fixture
def client_plain():
    db.init("test_app.db")
    with TestClient(app) as c:
        yield c


def test_a_guest_enters_with_test_funds_and_no_details(box):
    page = box.get("/").text
    assert "Enter the sandbox" in page and "Sandbox" in page
    _enter(box)
    acct = box.get("/account").text
    assert "$10.00" in acct and "Guest " in acct and "sandbox test funds" in acct
    assert "@sandbox.invalid" not in acct


def test_email_accounts_are_closed(box):
    assert box.get("/signup", follow_redirects=False).status_code == 303
    r = box.post("/signup", data={"email": "a@b.co", "password": "longenough"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/" and "orbit_session" not in r.headers.get("set-cookie", "")
    assert box.post("/login", data={"email": "a@b.co", "password": "longenough"}, follow_redirects=False).headers["location"] == "/"


def test_no_host_program_and_no_card(box):
    for path in ("heartbeat", "ready", "inbox", "offline"):
        assert box.post(f"/api/hosts/{path}", data={"token": "x"}).status_code == 403
    assert box.post("/stripe/webhook", content=b"{}").status_code == 503
    _enter(box)
    assert box.post("/store/checkout", data={"amount_cents": 500}, follow_redirects=False).status_code == 503


def test_the_simulated_host_seals_and_answers(box):
    sid = _start(box)
    seal = sandbox.seal()
    d = box.get(f"/sessions/{sid}/messages", params={"after": 0}).json()
    assert d["ready"] is True
    hello = seal.parse(d["messages"][0]["body"])
    assert d["messages"][0]["sender"] == "host" and hello["t"] == "hello"
    me = seal.Sealer(sid, "user")
    me.accept(hello)
    box.post(f"/sessions/{sid}/messages", data={"body": me.hello()})
    box.post(f"/sessions/{sid}/messages", data={"body": me.seal("hello there friend")})
    d = box.get(f"/sessions/{sid}/messages", params={"after": 0}).json()
    answer = [m for m in d["messages"] if m["sender"] == "host"][-1]
    assert seal.parse(answer["body"])["t"] == "msg"          # what Orbit stored is an envelope
    text = me.unseal(answer["body"])
    assert "scripted" in text and "3 words" in text and MODEL in text
    # stop: charged like any session, and the envelopes are gone
    box.post(f"/sessions/{sid}/stop", follow_redirects=False)
    assert ">ended<" in box.get(f"/sessions/{sid}").text
    assert box.get("/health").json() == {"ok": True, "unbalanced_txns": 0, "sandbox": True}
    conn = db.connect("test_app.db")
    assert conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"] == 0
    conn.close()


def test_a_plain_message_gets_a_plain_scripted_reply(box):
    sid = _start(box)
    box.get(f"/sessions/{sid}/messages", params={"after": 0})
    box.post(f"/sessions/{sid}/messages", data={"body": "no seal"})
    d = box.get(f"/sessions/{sid}/messages", params={"after": 0}).json()
    assert "arrived unsealed" in d["messages"][-1]["body"]


def test_a_closed_page_ends_the_session(box):
    sid = _start(box)
    box.get(f"/sessions/{sid}/messages", params={"after": 0})
    conn = db.connect("test_app.db")
    conn.execute("UPDATE hosts SET last_seen = datetime('now', '-10 minutes') WHERE status = 'busy'")
    conn.execute("UPDATE sessions SET ready_at = datetime('now', '-12 minutes'), started_at = datetime('now', '-12 minutes')")
    conn.close()
    sandbox._last_tick = 0.0
    page = box.get("/account").text
    row = db.connect("test_app.db").execute("SELECT end_reason, minutes FROM sessions WHERE id = ?", (sid,)).fetchone()
    assert row["end_reason"] == "sandbox_idle" and row["minutes"] == 2   # paid to the last time the page was there
    assert "running" not in page


def test_guests_do_not_see_each_others_machines(box):
    _enter(box)
    r = box.post("/hosts", data={"name": "Mine Only", "gpu": "RTX 4090", "vram_gb": 24, "price_dollars_per_hour": 0.5})
    assert "Mine Only" in r.text
    assert "Mine Only" in box.get("/hosts").text and "online" in box.get("/hosts").text
    with TestClient(app) as other:
        assert "Mine Only" not in other.get("/hosts").text
        other.post("/sandbox/enter", follow_redirects=False)
        assert "Mine Only" not in other.get("/hosts").text
        assert "Mine Only" not in other.get("/", params={"model": MODEL}).text
        mine = db.connect("test_app.db").execute("SELECT id FROM hosts WHERE name = 'Mine Only'").fetchone()["id"]
        r = other.post("/sessions/start", data={"model": MODEL, "host_id": mine}, follow_redirects=False)
        assert r.headers["location"].startswith("/?model=")   # refused: not a machine this guest can see


def test_test_funds_are_fixed_and_capped(box):
    _enter(box)
    assert box.post("/store/dev-funds", data={"amount_cents": 99999999}, follow_redirects=False).status_code == 400
    assert box.post("/store/dev-funds", data={"amount_cents": -1000}, follow_redirects=False).status_code == 400
    for _ in range(4):
        assert box.post("/store/dev-funds", data={"amount_cents": 1000}, follow_redirects=False).headers["location"] == "/account"
    assert box.post("/store/dev-funds", data={"amount_cents": 1000}, follow_redirects=False).headers["location"] == "/store"


def test_the_sandbox_wipes_itself_when_it_is_full(box, monkeypatch):
    _enter(box)
    monkeypatch.setattr(sandbox, "MAX_GUESTS", 1)
    sandbox._last_tick = 0.0
    page = box.get("/").text
    assert "started again" in page
    conn = db.connect("test_app.db")
    assert conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 1      # only the machines' owner
    assert conn.execute("SELECT COUNT(*) AS n FROM hosts").fetchone()["n"] == len(sandbox.MACHINES)
    conn.close()
