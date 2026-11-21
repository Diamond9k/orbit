"""The locks on every reply, and the holes that were closed."""
import os

import pytest
from fastapi.testclient import TestClient

import orbit.app as appmod
from orbit import auth, db
from orbit.app import app, valid_model


@pytest.fixture
def client():
    for f in ("test_app.db", "test_app.db-wal", "test_app.db-shm"):
        if os.path.exists(f):
            os.remove(f)
    db.init("test_app.db")
    with TestClient(app) as c:
        yield c


def _signup(c, email="s@b.co"):
    return c.post("/signup", data={"email": email, "password": "longenough"}, follow_redirects=False)


def test_every_page_carries_the_headers(client):
    h = client.get("/").headers
    assert "script-src 'self'" in h["content-security-policy"] and "unsafe-inline" not in h["content-security-policy"]
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff"
    assert h["cache-control"] == "no-store"
    assert "max-age" in client.get("/static/style.css").headers["cache-control"]
    assert "strict-transport-security" in client.get("/", headers={"x-forwarded-proto": "https"}).headers


def test_no_page_has_inline_script_or_style(client):
    _signup(client)
    client.post("/hosts", data={"name": "Box", "gpu": "G", "vram_gb": 24})
    for path in ("/", "/?model=x/M-7B-Q4", "/about", "/hosts", "/account", "/login", "/signup", "/nope"):
        text = client.get(path, headers={"accept": "text/html"}).text
        assert "<script>" not in text and " style=" not in text and " onsubmit=" not in text and "onclick=" not in text, path


def test_a_form_from_another_site_is_refused(client):
    _signup(client)
    r = client.post("/logout", headers={"origin": "https://evil.example"}, follow_redirects=False)
    assert r.status_code == 403
    assert client.post("/logout", headers={"origin": "null"}, follow_redirects=False).status_code == 403
    assert client.post("/logout", headers={"origin": "http://testserver"}, follow_redirects=False).status_code == 303
    # the host program and Stripe are not pages; they prove themselves another way
    assert client.post("/api/hosts/heartbeat", data={"token": "x"}, headers={"origin": "https://evil.example"}).status_code == 401


def test_the_cookie_is_secure_over_https_and_expires(client):
    c = _signup(client).headers["set-cookie"]
    assert "HttpOnly" in c and "SameSite=lax" in c and "Max-Age=" in c and "Secure" not in c
    r = client.post("/login", data={"email": "s@b.co", "password": "longenough"},
                    headers={"x-forwarded-proto": "https"}, follow_redirects=False)
    assert "Secure" in r.headers["set-cookie"]
    old = auth._signer.dumps({"uid": 1})
    assert auth.read_cookie(old) == 1
    auth_max = auth.COOKIE_MAX_AGE
    try:
        auth.COOKIE_MAX_AGE = -1
        assert auth.read_cookie(old) is None
    finally:
        auth.COOKIE_MAX_AGE = auth_max


def test_there_is_no_money_door_left(client):
    _signup(client)
    for path in ("/store", "/store/checkout", "/store/dev-funds", "/stripe/webhook"):
        assert client.post(path, data={"amount_cents": 1000}).status_code in (404, 405), path
    assert "stripe" not in client.get("/").headers["content-security-policy"]


def test_a_machine_needs_sane_numbers(client):
    _signup(client)
    for bad in ({"vram_gb": "nan"}, {"vram_gb": "inf"}, {"vram_gb": "1e9"}, {"vram_gb": 0}, {"name": "x" * 61}, {"name": "   "}):
        data = {"name": "Box", "gpu": "G", "vram_gb": 24, **bad}
        r = client.post("/hosts", data=data)
        assert r.status_code == 200 and "<pre" not in r.text, bad
    assert "<pre" in client.post("/hosts", data={"name": "Box", "gpu": "G", "vram_gb": 24}).text


def test_a_machine_name_cannot_carry_script(client):
    _signup(client)
    client.post("/hosts", data={"name": "');alert(1);//", "gpu": "<b>G</b>", "vram_gb": 24})
    page = client.get("/hosts").text
    assert "confirm(" not in page and "<b>G</b>" not in page and "&lt;b&gt;G&lt;/b&gt;" in page


def test_model_names_are_only_what_hugging_face_names_are(client):
    assert valid_model("bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M")
    for bad in ("--help", "a;rm -rf /", "x/$(id)", "x/<script>", "x" * 201, "x/y\nz", ""):
        assert not valid_model(bad), bad
    _signup(client)
    r = client.post("/sessions/start", data={"model": "x/<script>", "host_id": 1}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert "does not look like a model name" in client.get("/?model=%3Cscript%3E").text


def test_a_wrong_email_takes_the_same_road_as_a_wrong_password(client, monkeypatch):
    _signup(client)
    calls = []
    real = auth._hash
    monkeypatch.setattr(auth, "_hash", lambda pw, salt: calls.append(1) or real(pw, salt))
    conn = db.connect("test_app.db")
    assert auth.check_login(conn, "nobody@b.co", "longenough") is None
    assert auth.check_login(conn, "s@b.co", "wrongwrong") is None
    conn.close()
    assert len(calls) == 2


def test_a_missing_page_is_a_page(client):
    r = client.get("/nope", headers={"accept": "text/html"})
    assert r.status_code == 404 and "There is no page at this address" in r.text
    assert client.get("/nope").json() == {"detail": "Not Found"}
    assert client.get("/docs").status_code == 404 and client.get("/openapi.json").status_code == 404
