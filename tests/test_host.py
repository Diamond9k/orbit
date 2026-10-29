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
