import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "host"))
import seal  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _pair(sid=7):
    host, user = seal.Sealer(sid, "host"), seal.Sealer(sid, "user")
    att = user.accept(host.hello())
    host.accept(user.hello())
    return host, user, att


def test_both_ends_derive_the_same_keys_and_talk_both_ways():
    host, user, att = _pair()
    assert att == {"kind": "none"}
    assert host.epoch == user.epoch and len(host.epoch) == 16
    sealed = user.seal("Reply with one word: pong")
    env = json.loads(sealed)
    assert env["t"] == "msg" and env["from"] == "user" and env["n"] == 1
    assert "pong" not in sealed  # Orbit, which stores this string, cannot see the words
    assert host.unseal(sealed) == "Reply with one word: pong"
    back = host.seal("Pong")
    assert "Pong" not in back
    assert user.unseal(back) == "Pong"
    assert user.unseal(host.seal("Still here")) == "Still here"
    assert host.unseal(user.seal("")) == ""  # empty is legal


def test_hello_and_plain_text_are_told_apart():
    host = seal.Sealer(1, "host")
    assert seal.parse(host.hello())["t"] == "hello"
    assert seal.parse("just words") is None
    assert seal.parse('{"v": 1, "t": "other", "from": "host"}') is None
    assert seal.parse('{"v": 2, "t": "msg", "from": "host"}') is None
    assert seal.parse('{"v": 1, "t": "msg", "from": "orbit"}') is None
    assert seal.parse("{not json") is None


def test_a_tampered_or_replayed_envelope_is_refused():
    host, user, _ = _pair()
    sealed = user.seal("secret")
    env = json.loads(sealed)
    bad = dict(env, ct=env["ct"][:-4] + ("AAAA" if env["ct"][-4:] != "AAAA" else "BBBB"))
    with pytest.raises(seal.SealError):
        host.unseal(json.dumps(bad))
    assert host.unseal(sealed) == "secret"
    with pytest.raises(seal.SealError):  # the same envelope again
        host.unseal(sealed)
    first, second = user.seal("one"), user.seal("two")
    with pytest.raises(seal.SealError):  # out of order
        host.unseal(second)
    assert host.unseal(first) == "one" and host.unseal(second) == "two"
    with pytest.raises(seal.SealError):  # a message from the wrong direction
        host.unseal(host.seal("to myself"))


def test_wrong_session_or_a_third_key_cannot_open_it():
    host, user, _ = _pair(sid=7)
    other_host, other_user = seal.Sealer(8, "host"), seal.Sealer(8, "user")
    other_user.accept(other_host.hello())
    other_host.accept(other_user.hello())
    with pytest.raises(seal.SealError):
        other_host.unseal(user.seal("for session 7 only"))
    eavesdropper = seal.Sealer(7, "host")
    eavesdropper.accept(user.hello())  # knows the user's public key, not the host's private one
    with pytest.raises(seal.SealError):
        eavesdropper.unseal(user.seal("still sealed"))


def test_a_new_browser_tab_starts_a_new_epoch():
    host, user, _ = _pair()
    assert host.unseal(user.seal("from tab one")) == "from tab one"
    tab_two = seal.Sealer(7, "user")
    tab_two.accept(host.hello())
    host.accept(tab_two.hello())  # the host re-keys for the new tab
    assert host.epoch == tab_two.epoch != user.epoch
    assert host.sent == host.received == 0
    assert host.unseal(tab_two.seal("from tab two")) == "from tab two"
    with pytest.raises(seal.SealError):  # the old tab's envelopes are from another epoch
        host.unseal(user.seal("stale"))


def test_bad_hellos_are_refused():
    user = seal.Sealer(7, "user")
    with pytest.raises(seal.SealError):
        user.accept(seal.Sealer(7, "user").hello())  # same role
    with pytest.raises(seal.SealError):
        user.accept('{"v":1,"t":"hello","from":"host","pk":"AAAA"}')  # not a point on the curve
    with pytest.raises(seal.SealError):
        user.accept('{"v":1,"t":"hello","from":"host","pk":"!!"}')  # not base64
    with pytest.raises(seal.SealError):
        user.seal("too soon")
    with pytest.raises(seal.SealError):
        seal.Sealer(7, "orbit")


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the browser's seal.js")
def test_the_browser_code_interoperates_with_the_host_code():
    """The real orbit/static/seal.js, run under Node, exchanges hellos and messages with host/seal.py."""
    host = seal.Sealer(42, "host")
    proc = subprocess.Popen([shutil.which("node"), os.path.join(HERE, "seal_interop.js")], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def ask(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        assert line, proc.stderr.read()
        out = json.loads(line)
        assert "error" not in out, out
        return out

    try:
        first = ask({"session_id": 42, "host_hello": host.hello({"kind": "none"}), "text": "Reply with one word: pong"})
        assert first["att"] == {"kind": "none"}
        assert host.accept(first["user_hello"]) == {"kind": "none"}
        assert host.unseal(first["sealed"]) == "Reply with one word: pong"
        assert ask({"open": host.seal("Pong")})["text"] == "Pong"
        assert ask({"open": host.seal("Still pong. Unicode: naïve café ✓")})["text"] == "Still pong. Unicode: naïve café ✓"
        assert host.unseal(ask({"seal": "second from the browser"})["sealed"]) == "second from the browser"
        # the browser refuses a replay too
        proc.stdin.write(json.dumps({"open": host.seal("x")}) + "\n")
        proc.stdin.flush()
        proc.stdout.readline()
        replay = json.dumps({"v": 1, "t": "msg", "from": "host", "n": 1, "ct": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="})
        proc.stdin.write(json.dumps({"open": replay}) + "\n")
        proc.stdin.flush()
        assert "error" in json.loads(proc.stdout.readline())
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
