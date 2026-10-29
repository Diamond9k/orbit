"""Orbit host program: keep this machine online and run the model a user chose.

    python host/orbit_host.py

Put the token from the Hosts page in host/token.txt. Standard library only.
It only dials out, so it works behind a home router with nothing to configure.

Every few seconds it sends a heartbeat. When Orbit's reply names a session, it starts
llama.cpp's server for that model (which downloads the GGUF from Hugging Face the first
time), waits until the server answers, then tells Orbit the machine is ready. Billing
starts only then. When the session ends, it stops the server.

Settings, all optional, as environment variables:
    ORBIT_URL        where Orbit runs (default http://localhost:8000)
    ORBIT_LLAMA_CMD  how llama.cpp's server is started (default "llama serve")
    ORBIT_LLAMA_PORT local port for the model server (default 8081)
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ORBIT_URL = os.environ.get("ORBIT_URL", "http://localhost:8000").rstrip("/")
HEARTBEAT_URL = ORBIT_URL + "/api/hosts/heartbeat"
READY_URL = ORBIT_URL + "/api/hosts/ready"
LLAMA_CMD = os.environ.get("ORBIT_LLAMA_CMD", "llama serve")
LLAMA_PORT = int(os.environ.get("ORBIT_LLAMA_PORT", "8081"))
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")
INTERVAL = 10  # seconds between heartbeats

QUANT = re.compile(r"^(I?Q\d\w*|F16|BF16|F32)$", re.I)


def _post(url, token):
    req = urllib.request.Request(url, data=urllib.parse.urlencode({"token": token}).encode(), method="POST")
    return urllib.request.urlopen(req, timeout=30)


def check_in(token, url=HEARTBEAT_URL):
    """Send one heartbeat. Returns (ok, session) where session is {"id", "model"} or None."""
    try:
        with _post(url, token) as resp:
            if resp.status != 200:
                print(f"unexpected reply: {resp.status}")
                return False, None
            try:
                body = json.loads(resp.read() or b"{}")
            except (TypeError, ValueError):
                body = {}
            print("online")
            session = body.get("session") if isinstance(body, dict) else None
            return True, session if isinstance(session, dict) else None
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"error: {e}")
        return False, None


def send_heartbeat(token, url=HEARTBEAT_URL):
    return check_in(token, url)[0]


def hf_ref(model):
    """Orbit's model name to llama.cpp's -hf argument.

    "owner/Repo-GGUF Q4_K_M" -> "owner/Repo-GGUF:Q4_K_M"; "owner/Repo-GGUF" stays as is and
    llama.cpp picks its default file.
    """
    parts = model.split()
    repo = parts[0]
    quants = [p for p in parts[1:] if QUANT.match(p)]
    return f"{repo}:{quants[0].upper()}" if quants else repo


def llama_args(model, port=LLAMA_PORT, cmd=LLAMA_CMD):
    args = shlex.split(cmd, posix=(os.name != "nt"))
    args[0] = shutil.which(args[0]) or args[0]  # on Windows the installer may add a .cmd shim
    return args + ["-hf", hf_ref(model), "--host", "127.0.0.1", "--port", str(port)]


def model_server_up(port=LLAMA_PORT):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def send_ready(token, url=READY_URL):
    try:
        with _post(url, token) as resp:
            return resp.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"error: {e}")
        return False


class Runner:
    """Keeps at most one model server running, for the session Orbit named."""

    def __init__(self, token, popen=subprocess.Popen, server_up=model_server_up, ready=send_ready):
        self.token, self.popen, self.server_up, self.ready = token, popen, server_up, ready
        self.session_id = None
        self.proc = None
        self.ready_sent = False

    def step(self, session):
        if session is None or session.get("id") != self.session_id:
            self.stop()
        if session is None:
            return
        if self.proc is None:
            print(f"starting {session['model']} for session {session['id']}")
            self.session_id = session["id"]
            self.proc = self.popen(llama_args(session["model"]))
            self.ready_sent = False
        if self.proc.poll() is not None:
            print(f"the model server stopped (exit {self.proc.returncode}); trying again")
            self.proc = None
            return
        if not self.ready_sent and self.server_up():
            self.ready_sent = self.ready(self.token)
            if self.ready_sent:
                print("model ready")

    def stop(self):
        if self.proc is not None:
            print(f"session {self.session_id} ended, stopping the model server")
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc, self.session_id, self.ready_sent = None, None, False


def main():
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    runner = Runner(token)
    try:
        while True:
            ok, session = check_in(token)
            if ok:
                runner.step(session)
            time.sleep(INTERVAL)
    finally:
        runner.stop()


if __name__ == "__main__":
    main()
