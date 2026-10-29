import json
import os
import sys
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "host"))
import orbit_host  # noqa: E402


def test_heartbeat_posts_token(capsys):
    resp = mock.MagicMock(status=200)
    resp.__enter__.return_value = resp
    with mock.patch("urllib.request.urlopen", return_value=resp) as urlopen:
        assert orbit_host.send_heartbeat("abc") is True
    req = urlopen.call_args[0][0]
    assert req.get_method() == "POST"
    assert req.full_url == "http://localhost:8000/api/hosts/heartbeat"
    assert req.data == b"token=abc"
    assert "online" in capsys.readouterr().out


def test_heartbeat_failure_prints_error(capsys):
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        assert orbit_host.send_heartbeat("abc") is False
    assert "down" in capsys.readouterr().out


def test_heartbeat_reads_session_from_reply():
    resp = mock.MagicMock(status=200)
    resp.__enter__.return_value = resp
    resp.read.return_value = b'{"session": {"id": 3, "model": "o/M-GGUF Q4_K_M"}}'
    with mock.patch("urllib.request.urlopen", return_value=resp):
        assert orbit_host.check_in("abc") == (True, {"id": 3, "model": "o/M-GGUF Q4_K_M"})
    resp.read.return_value = b'{"ok": true}'  # Orbit before the heartbeat names sessions
    with mock.patch("urllib.request.urlopen", return_value=resp):
        assert orbit_host.check_in("abc") == (True, None)


def test_hf_ref():
    assert orbit_host.hf_ref("bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M") == "bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M"
    assert orbit_host.hf_ref("bartowski/Qwen2.5-7B-Instruct-GGUF q5_k_m") == "bartowski/Qwen2.5-7B-Instruct-GGUF:Q5_K_M"
    assert orbit_host.hf_ref("bartowski/Qwen2.5-7B-Instruct-GGUF") == "bartowski/Qwen2.5-7B-Instruct-GGUF"
    args = orbit_host.llama_args("o/M-GGUF Q4_K_M", port=9000, cmd="llama-server")
    assert args[1:] == ["-hf", "o/M-GGUF:Q4_K_M", "--host", "127.0.0.1", "--port", "9000"]


class FakeProc:
    def __init__(self, args):
        self.args, self.returncode, self.stopped = args, None, False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.stopped = True

    def wait(self, timeout=None):
        return 0


def test_runner_starts_model_then_says_ready_once():
    procs, up, readies, posted = [], [False], [], []
    r = orbit_host.Runner("tok", popen=lambda a: procs.append(FakeProc(a)) or procs[-1],
                          server_up=lambda: up[0], ready=lambda t: readies.append(t) or True,
                          reply=lambda t, sid, body: posted.append((sid, body)) or len(posted))
    s = {"id": 1, "model": "o/M-GGUF Q4_K_M"}
    r.step(s)
    assert len(procs) == 1 and "o/M-GGUF:Q4_K_M" in procs[0].args and readies == [] and posted == []
    up[0] = True
    r.step(s)
    r.step(s)
    assert readies == ["tok"] and len(procs) == 1
    assert len(posted) == 1 and posted[0][0] == 1 and json.loads(posted[0][1])["t"] == "hello"  # the key offer, once
    # session ends: server stopped
    r.step(None)
    assert procs[0].stopped and r.proc is None and r.sealer is None
    # a new session gets a fresh server and a fresh key offer
    r.step({"id": 2, "model": "o/N-GGUF"})
    assert len(procs) == 2 and r.session_id == 2
    assert len(posted) == 2 and posted[1][0] == 2 and json.loads(posted[1][1])["pk"] != json.loads(posted[0][1])["pk"]


def test_runner_restarts_a_crashed_server():
    procs = []
    r = orbit_host.Runner("tok", popen=lambda a: procs.append(FakeProc(a)) or procs[-1],
                          server_up=lambda: False, ready=lambda t: True)
    s = {"id": 1, "model": "o/M-GGUF"}
    r.step(s)
    procs[0].returncode = 1
    r.step(s)
    assert r.proc is None
    r.step(s)
    assert len(procs) == 2


def _odd_ids(posted):
    """A fake reply(): the relay numbers the host's posts 3, 5, 7...; the tests give user messages even ids."""
    return lambda t, sid, body: posted.append(body) or len(posted) * 2 + 1


def test_runner_relays_the_conversation():
    replies = [
        {"session": {"id": 1, "model": "m"}, "messages": [{"id": 4, "sender": "user", "body": "hi"}]},
        {"session": {"id": 1, "model": "m"}, "messages": []},
        {"session": None, "messages": []},
    ]
    asked, posted, inboxes = [], [], []
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: inboxes.append(after) or replies.pop(0),
                          reply=_odd_ids(posted),
                          ask=lambda transcript: asked.append([m["body"] for m in transcript]) or "hello")
    r.step({"id": 1, "model": "m"})
    assert r.ready_sent and len(posted) == 1 and json.loads(posted[0])["t"] == "hello" and r.after == 3  # the key offer
    r.relay()  # a plain user message arrives: the model is asked with the whole transcript, the answer is posted plain
    assert asked == [["hi"]] and posted[1] == "hello"
    assert [m["body"] for m in r.transcript] == ["hi", "hello"] and r.after == 5
    r.relay()  # nothing new: the model is not asked again
    assert asked == [["hi"]] and inboxes == [3, 5]
    r.relay()  # Orbit says the session is over: the server stops, the transcript is dropped
    assert r.proc is None and r.transcript == [] and r.after == 0 and r.sealer is None


def _raise(exc):
    raise exc


def test_runner_tells_the_user_when_the_model_fails():
    posted = []
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: {"session": {"id": 1, "model": "m"},
                                                  "messages": [{"id": 4, "sender": "user", "body": "hi"}]},
                          reply=_odd_ids(posted),
                          ask=lambda transcript: _raise(OSError("connection refused")))
    r.step({"id": 1, "model": "m"})
    r.relay()
    assert posted[-1] == "The model did not answer: connection refused"


def test_runner_seals_the_conversation_when_the_browser_answers():
    import seal
    inbox_q, asked, posted = [], [], []
    running = {"session": {"id": 1, "model": "m"}}
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: inbox_q.pop(0), reply=_odd_ids(posted),
                          ask=lambda transcript: asked.append([(m["sender"], m["body"]) for m in transcript]) or "Pong")
    r.step({"id": 1, "model": "m"})
    browser = seal.Sealer(1, "user")
    assert browser.accept(posted[0]) == {"kind": "none"}  # the host's hello; nothing to attest with yet
    inbox_q.append(dict(running, messages=[{"id": 4, "sender": "user", "body": browser.hello()}]))
    r.relay()
    assert r.sealed and r.sealer.ready and asked == []  # a hello is not a question for the model
    inbox_q.append(dict(running, messages=[{"id": 6, "sender": "user", "body": browser.seal("ping?")}]))
    r.relay()
    assert asked == [[("user", "ping?")]]  # the model saw plain text
    assert "ping" not in posted[-1] and "Pong" not in posted[-1]  # the relay saw none of it
    assert browser.unseal(posted[-1]) == "Pong"
    # an envelope the host cannot open gets a sealed notice, not silence, and never reaches the model
    inbox_q.append(dict(running, messages=[{"id": 8, "sender": "user", "body": posted[-1]}]))  # its own envelope bounced back
    r.relay()
    assert "could not be opened" in browser.unseal(posted[-1]) and asked == [[("user", "ping?")]]
    # a new browser tab re-keys and the conversation goes on
    tab2 = seal.Sealer(1, "user")
    tab2.accept(posted[0])
    inbox_q.append(dict(running, messages=[{"id": 10, "sender": "user", "body": tab2.hello()},
                                           {"id": 12, "sender": "user", "body": tab2.seal("still there?")}]))
    r.relay()
    assert asked[-1][-1] == ("user", "still there?") and tab2.unseal(posted[-1]) == "Pong"
    # plain text once the session is sealed is NOT downgraded: a plain notice, the model is not asked,
    # and the session stays sealed (Cooper 2026-10-29: do not silently downgrade a protected session)
    before = len(asked)
    inbox_q.append(dict(running, messages=[{"id": 14, "sender": "user", "body": "plain"}]))
    r.relay()
    assert len(asked) == before
    assert posted[-1] == "This session is sealed. Reload the page to continue; plain messages are not answered."
    assert r.sealed is True


def test_runner_runs_unsealed_without_the_cryptography_package(monkeypatch):
    monkeypatch.setattr(orbit_host, "seal", None)
    posted, asked = [], []
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: {"session": {"id": 1, "model": "m"},
                                                  "messages": [{"id": 1, "sender": "user", "body": "hi"}]},
                          reply=lambda t, sid, body: posted.append(body) or 2,
                          ask=lambda transcript: asked.append(1) or "hello")
    r.step({"id": 1, "model": "m"})
    assert posted == [] and r.sealer is None  # no key to offer
    r.relay()
    assert posted == ["hello"]


def test_ask_model_sends_the_conversation_as_roles():
    import io
    import json
    payload = json.dumps({"choices": [{"message": {"role": "assistant", "content": "42"}}]}).encode()
    resp = mock.MagicMock(status=200)
    resp.__enter__.return_value = io.BytesIO(payload)
    with mock.patch("urllib.request.urlopen", return_value=resp) as urlopen:
        out = orbit_host.ask_model([{"id": 1, "sender": "user", "body": "q"}, {"id": 2, "sender": "host", "body": "a"},
                                    {"id": 3, "sender": "user", "body": "q2"}], port=9000)
    assert out == "42"
    req = urlopen.call_args[0][0]
    assert req.full_url == "http://127.0.0.1:9000/v1/chat/completions"
    sent = json.loads(req.data)
    assert [(m["role"], m["content"]) for m in sent["messages"]] == [("user", "q"), ("assistant", "a"), ("user", "q2")]


def test_inbox_and_reply_post_the_token_and_fields():
    resp = mock.MagicMock(status=200)
    resp.__enter__.return_value = resp
    resp.read.return_value = b'{"session": {"id": 1, "model": "m"}, "messages": []}'
    with mock.patch("urllib.request.urlopen", return_value=resp) as urlopen:
        assert orbit_host.fetch_inbox("abc", 5, wait=3) == {"session": {"id": 1, "model": "m"}, "messages": []}
    req = urlopen.call_args[0][0]
    assert req.full_url == "http://localhost:8000/api/hosts/inbox"
    assert b"token=abc" in req.data and b"after=5" in req.data and b"wait=3" in req.data
    resp.read.return_value = b'{"id": 9}'
    with mock.patch("urllib.request.urlopen", return_value=resp) as urlopen:
        assert orbit_host.send_reply("abc", 1, "hello there") == 9
    req = urlopen.call_args[0][0]
    assert req.full_url == "http://localhost:8000/api/hosts/reply"
    assert b"session_id=1" in req.data and b"body=hello+there" in req.data
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        assert orbit_host.fetch_inbox("abc", 0) is None and orbit_host.send_reply("abc", 1, "x") is None
