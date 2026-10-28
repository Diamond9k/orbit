import unittest
from unittest.mock import patch
import urllib.request
import host.orbit_host as orbit_host

class TestOrbitHost(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_heartbeat_success(self, mock_open):
        mock_open.return_value.getcode.return_value = 200
        orbit_host.heartbeat()
        mock_open.assert_called_once_with('http://localhost:8000/api/hosts/heartbeat?token=token')

    @patch('urllib.request.urlopen')
    def test_heartbeat_failure(self, mock_open):
        mock_open.side_effect = urllib.error.URLError('Failed to connect')
        orbit_host.heartbeat()
        mock_open.assert_called_once_with('http://localhost:8000/api/hosts/heartbeat?token=token')

if __name__ == "__main__":
    unittest.main()
