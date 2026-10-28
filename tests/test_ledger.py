import pytest
from orbit import db, ledger


@pytest.fixture
def conn(tmp_path):
    path = str(tmp_path / "t.db")
    db.init(path)
    c = db.connect(path)
    yield c
    c.close()


def test_post_and_balance(conn):
    ledger.post(conn, [("stripe:clearing", -1000), ("user:1", 1000)], memo="buy")
    assert ledger.balance(conn, "user:1") == 1000
    assert ledger.balance(conn, "stripe:clearing") == -1000
    assert ledger.verify(conn) == []


def test_rejects_unbalanced(conn):
    with pytest.raises(ledger.LedgerError):
        ledger.post(conn, [("user:1", 100), ("host:1", -99)])
    assert ledger.balance(conn, "user:1") == 0


def test_rejects_single_row(conn):
    with pytest.raises(ledger.LedgerError):
        ledger.post(conn, [("user:1", 0)])


def test_rejects_fractional_cents(conn):
    with pytest.raises(ledger.LedgerError):
        ledger.post(conn, [("user:1", 1.5), ("host:1", -1.5)])


def test_three_way_split(conn):
    ledger.post(conn, [("user:1", -500), ("host:2", 400), ("orbit:revenue", 100)], memo="session:1")
    assert ledger.balance(conn, "host:2") == 400
    assert ledger.balance(conn, "orbit:revenue") == 100
    assert ledger.verify(conn) == []
