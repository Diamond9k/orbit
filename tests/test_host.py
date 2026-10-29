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
    procs, up, readies = [], [False], []
    r = orbit_host.Runner("tok", popen=lambda a: procs.append(FakeProc(a)) or procs[-1],
                          server_up=lambda: up[0], ready=lambda t: readies.append(t) or True)
    s = {"id": 1, "model": "o/M-GGUF Q4_K_M"}
    r.step(s)
    assert len(procs) == 1 and "o/M-GGUF:Q4_K_M" in procs[0].args and readies == []
    up[0] = True
    r.step(s)
    r.step(s)
    assert readies == ["tok"] and len(procs) == 1
    # session ends: server stopped
    r.step(None)
    assert procs[0].stopped and r.proc is None
    # a new session gets a fresh server
    r.step({"id": 2, "model": "o/N-GGUF"})
    assert len(procs) == 2 and r.session_id == 2


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


def test_runner_relays_the_conversation():
    replies = [
        {"session": {"id": 1, "model": "m"}, "messages": [{"id": 1, "sender": "user", "body": "hi"}]},
        {"session": {"id": 1, "model": "m"}, "messages": []},
        {"session": None, "messages": []},
    ]
    asked, posted, inboxes = [], [], []
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: inboxes.append(after) or replies.pop(0),
                          reply=lambda t, sid, body: posted.append((sid, body)) or 2,
                          ask=lambda transcript: asked.append([m["body"] for m in transcript]) or "hello")
    r.step({"id": 1, "model": "m"})
    assert r.ready_sent
    r.relay()  # a user message arrives: the model is asked with the whole transcript, the answer is posted
    assert asked == [["hi"]] and posted == [(1, "hello")]
    assert [m["body"] for m in r.transcript] == ["hi", "hello"] and r.after == 2
    r.relay()  # nothing new: the model is not asked again
    assert asked == [["hi"]] and inboxes == [0, 2]
    r.relay()  # Orbit says the session is over: the server stops, the transcript is dropped
    assert r.proc is None and r.transcript == [] and r.after == 0


def _raise(exc):
    raise exc


def test_runner_tells_the_user_when_the_model_fails():
    posted = []
    r = orbit_host.Runner("tok", popen=lambda a: FakeProc(a), server_up=lambda: True, ready=lambda t: True,
                          inbox=lambda t, after: {"session": {"id": 1, "model": "m"},
                                                  "messages": [{"id": 1, "sender": "user", "body": "hi"}]},
                          reply=lambda t, sid, body: posted.append(body) or 2,
                          ask=lambda transcript: _raise(OSError("connection refused")))
    r.step({"id": 1, "model": "m"})
    r.relay()
    assert posted == ["The model did not answer: connection refused"]


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
