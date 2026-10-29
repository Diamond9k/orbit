import unittest
from unittest.mock import patch
from host.orbit_host import send_heartbeat
import urllib.error

class TestHost(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_send_heartbeat_success(self, mock_urlopen):
        mock_response = unittest.mock.Mock()
        mock_response.status = 200
        mock_urlopen.return_value = mock_response
        result = send_heartbeat("abc")
        self.assertTrue(result)
        mock_urlopen.assert_called_once_with(unittest.mock.ANY)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "http://localhost:8000/api/hosts/heartbeat")
        self.assertEqual(req.data, b"token=abc")

    @patch('urllib.request.urlopen')
    def test_send_heartbeat_failure(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("down")
        result = send_heartbeat("abc")
        self.assertFalse(result)
        mock_urlopen.assert_called_once_with(unittest.mock.ANY)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "http://localhost:8000/api/hosts/heartbeat")
        self.assertEqual(req.data, b"token=abc")

if __name__ == "__main__":
    unittest.main()
