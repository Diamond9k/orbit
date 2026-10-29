"""Orbit host program, step 1: tell Orbit this machine is online.

    python host/orbit_host.py

Put the token from the Hosts page in host/token.txt. Standard library only.
It only dials out, so it works behind a home router with nothing to configure.
"""
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HEARTBEAT_URL = "http://localhost:8000/api/hosts/heartbeat"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")


def send_heartbeat(token, url=HEARTBEAT_URL):
    req = urllib.request.Request(url, data=urllib.parse.urlencode({"token": token}).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                print("online")
                return True
            print(f"unexpected reply: {resp.status}")
            return False
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"error: {e}")
        return False


def main():
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    while True:
        send_heartbeat(token)
        time.sleep(60)


if __name__ == "__main__":
    main()
