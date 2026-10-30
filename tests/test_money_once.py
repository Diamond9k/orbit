"""Money that must move exactly once: a card payment and a session's charge.

From the recon on ARC's billing: a retried Stripe event credited twice because event ids were
not kept; a webhook compared against an unset secret let anyone in; a "completed" checkout was
credited before the money arrived. Each test below is one of those, closed.
"""
import hashlib
import hmac
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from orbit import app as app_module
from orbit import db, ledger
from orbit.app import app

DB = os.environ["ORBIT_DB"]
SECRET = "whsec_test_only"


def _clean():
    for f in (DB, DB + "-wal", DB + "-shm"):
        if os.path.exists(f):
            os.remove(f)


@pytest.fixture
def conn():
    _clean()
    db.init(DB)
    c = db.connect(DB)
    yield c
    c.close()
    _clean()


@pytest.fixture
def client(monkeypatch):
    _clean()
    db.init(DB)
    monkeypatch.setattr(app_module, "STRIPE_WEBHOOK_SECRET", SECRET)
    with TestClient(app) as c:
        c.post("/signup", data={"email": "pay@b.co", "password": "longenough"}, follow_redirects=False)
        yield c
    _clean()


def _event(kind="checkout.session.completed", status="paid", cs="cs_test_1", cents=1000):
    return json.dumps({"id": "evt_1", "object": "event", "type": kind, "data": {"object": {
        "id": cs, "object": "checkout.session", "payment_status": status, "amount_total": cents,
        "metadata": {"user_id": "1"}}}})


def _send(client, payload, secret=SECRET):
    t = int(time.time())
    sig = hmac.new(secret.encode(), f"{t}.{payload}".encode(), hashlib.sha256).hexdigest()
    return client.post("/stripe/webhook", content=payload,
                       headers={"stripe-signature": f"t={t},v1={sig}", "content-type": "application/json"})


def _balance():
    c = db.connect(DB)
    try:
        return ledger.balance(c, "user:1")
    finally:
        c.close()


def test_a_keyed_posting_happens_once(conn):
    rows = [("stripe:clearing", -500), ("user:1", 500)]
    assert ledger.post(conn, rows, memo="stripe:cs_a", once="stripe:cs_a") is not None
    assert ledger.post(conn, rows, memo="stripe:cs_a", once="stripe:cs_a") is None
    assert ledger.balance(conn, "user:1") == 500
    assert ledger.posted(conn, "stripe:cs_a")


def test_postings_from_before_the_upgrade_count_as_posted(conn):
    ledger.post(conn, [("stripe:clearing", -500), ("user:1", 500)], memo="stripe:cs_old")
    conn.execute("DELETE FROM ledger_once")
    db.migrate(conn)
    assert ledger.post(conn, [("stripe:clearing", -500), ("user:1", 500)], once="stripe:cs_old") is None
    assert ledger.balance(conn, "user:1") == 500


def test_webhook_refuses_when_its_secret_is_not_set(client, monkeypatch):
    monkeypatch.setattr(app_module, "STRIPE_WEBHOOK_SECRET", "")
    r = _send(client, _event(), secret="")
    assert r.status_code == 503
    assert "STRIPE_WEBHOOK_SECRET" in r.text
    assert _balance() == 0


def test_webhook_refuses_a_bad_signature(client):
    assert _send(client, _event(), secret="whsec_wrong").status_code == 400
    assert _balance() == 0


def test_a_retried_payment_event_credits_once(client):
    assert _send(client, _event()).status_code == 200
    assert _send(client, _event()).status_code == 200
    assert _balance() == 1000


def test_an_unpaid_checkout_credits_nothing_until_the_money_arrives(client):
    assert _send(client, _event(status="unpaid")).status_code == 200
    assert _balance() == 0
    assert _send(client, _event(kind="checkout.session.async_payment_succeeded")).status_code == 200
    assert _balance() == 1000
    # Stripe may still deliver the late "completed" afterwards; it changes nothing.
    assert _send(client, _event()).status_code == 200
    assert _balance() == 1000
