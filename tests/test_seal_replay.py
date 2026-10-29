"""A repeated or replayed hello must never reset the counters: that would reuse AES-GCM nonces.

Found in Keystone's review of the adversary gauntlet (2026-10-29). Two paths hit it: an active
broker replaying a hello on purpose, and the ordinary page reload, where the page restores its key
pair from sessionStorage and re-sends the same hello. Both ends now treat a hello carrying the
current peer key as a no-op and refuse a key from an earlier epoch of the session.
"""
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
    host_hello, user_hello = host.hello(), None
    user.accept(host_hello)
    user_hello = user.hello()
    host.accept(user_hello)
    return host, user, host_hello, user_hello


def test_the_same_hello_again_is_a_no_op_on_both_ends():
    host, user, host_hello, user_hello = _pair()
    assert host.unseal(user.seal("one")) == "one"
    assert user.unseal(host.seal("two")) == "two"
    state = (host.epoch, host.sent, host.received, user.epoch, user.sent, user.received)
    assert host.accept(user_hello) == {"kind": "none"}  # the hello the host already holds
    assert user.accept(host_hello) == {"kind": "none"}
    assert (host.epoch, host.sent, host.received, user.epoch, user.sent, user.received) == state
    assert json.loads(user.seal("three"))["n"] == 2  # the counters simply go on
    assert json.loads(host.seal("four"))["n"] == 2


def test_a_key_from_an_earlier_epoch_is_refused():
    host, tab1, host_hello, tab1_hello = _pair()
    host.unseal(tab1.seal("from tab one"))
    tab2 = seal.Sealer(7, "user")
    tab2.accept(host_hello)
    host.accept(tab2.hello())  # a second tab re-keys, as designed
    assert host.unseal(tab2.seal("from tab two")) == "from tab two"
    with pytest.raises(seal.SealError):  # the broker replays tab one's hello to bring its epoch back
        host.accept(tab1_hello)
    assert host.unseal(tab2.seal("still tab two")) == "still tab two"  # nothing changed for the live tab
    # the browser side of the same rule: a host that re-keyed, then its old hello replayed
    user = seal.Sealer(8, "user")
    host_a, host_b = seal.Sealer(8, "host"), seal.Sealer(8, "host")
    user.accept(host_a.hello())
    user.accept(host_b.hello())
    with pytest.raises(seal.SealError):
        user.accept(host_a.hello())


def test_the_host_program_survives_a_refused_replay():
    """A refused hello must not stop the relay loop: the host notices and goes on."""
    import orbit_host  # noqa: F401  (imported from host/ through the path above)
    from test_host import FakeProc, _odd_ids
    inbox_q, asked, posted = [], [], []
    running = {"session": {"id": 1, "model": "m"}}
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: inbox_q.pop(0), reply=_odd_ids(posted),
                          ask=lambda transcript: asked.append(1) or "Pong")
    r.step({"id": 1, "model": "m"})
    tab1 = seal.Sealer(1, "user")
    tab1.accept(posted[0])
    tab1_hello = tab1.hello()
    inbox_q.append(dict(running, messages=[{"id": 4, "sender": "user", "body": tab1_hello}]))
    r.relay()
    tab2 = seal.Sealer(1, "user")
    tab2.accept(posted[0])
    inbox_q.append(dict(running, messages=[{"id": 6, "sender": "user", "body": tab2.hello()}]))
    r.relay()
    inbox_q.append(dict(running, messages=[{"id": 8, "sender": "user", "body": tab1_hello}]))  # replayed
    r.relay()  # must not raise
    inbox_q.append(dict(running, messages=[{"id": 10, "sender": "user", "body": tab2.seal("still here?")}]))
    r.relay()
    assert tab2.unseal(posted[-1]) == "Pong"


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node to run the browser's seal.js")
def test_a_page_reload_continues_the_conversation_without_reusing_a_nonce():
    """The real seal.js under Node plays a reload: restore the key pair, replay the log, re-send the
    same hello (which the host now ignores), and go on. Before the fix the host reset its counters
    on that re-sent hello and the next message failed, after a nonce had been reused."""
    host = seal.Sealer(42, "host")
    proc = subprocess.Popen([shutil.which("node"), os.path.join(HERE, "seal_interop.js")], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def ask(obj, expect_error=False):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        assert line, proc.stderr.read()
        out = json.loads(line)
        assert ("error" in out) == expect_error, out
        return out

    try:
        host_hello = host.hello({"kind": "none"})
        first = ask({"session_id": 42, "host_hello": host_hello, "text": "q1"})
        assert host.accept(first["user_hello"]) == {"kind": "none"}
        assert host.unseal(first["sealed"]) == "q1"
        a1 = host.seal("a1")
        assert ask({"open": a1})["text"] == "a1"
        q2 = ask({"seal": "q2"})["sealed"]
        assert host.unseal(q2) == "q2"
        saved = ask({"export": True})
        # the reload: same key pair, no counters, the log replayed in order
        restored = ask({"restore": saved["saved"], "session_id": 42})
        assert restored["pk"] == saved["pk"] and restored["ready"] is False
        again = ask({"accept": host_hello})
        assert again["sent"] == 0 and again["received"] == 0 and again["epoch"] == host.epoch
        assert ask({"open": first["sealed"]})["text"] == "q1"  # its own message, from the log
        assert ask({"open": a1})["text"] == "a1"
        assert ask({"open": q2})["text"] == "q2"
        assert host.accept(again["user_hello"]) == {"kind": "none"}  # the page re-sends its hello: a no-op now
        assert host.sent == 1 and host.received == 2
        q3 = ask({"seal": "q3 after reload"})["sealed"]
        assert json.loads(q3)["n"] == 3 and host.unseal(q3) == "q3 after reload"
        a2 = host.seal("a2")
        assert json.loads(a2)["n"] == 2 and ask({"open": a2})["text"] == "a2"
        # the browser refuses a host key from an earlier epoch too
        other = seal.Sealer(42, "host")
        ask({"accept": other.hello()})
        ask({"accept": host_hello}, expect_error=True)
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
