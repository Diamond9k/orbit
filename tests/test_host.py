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
