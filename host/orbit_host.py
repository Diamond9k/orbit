"""Orbit host program: keep this machine online and run the model a user chose.

    python host/orbit_host.py

Put the token from the Hosts page in host/token.txt. Needs the cryptography package for
sealing (python -m pip install -r host/requirements.txt); the rest is the standard library.
It only dials out, so it works behind a home router with nothing to configure.

Every few seconds it sends a heartbeat. When Orbit's reply names a session, it starts
llama.cpp's server for that model (which downloads the GGUF from Hugging Face the first
time), waits until the server answers, then tells Orbit the machine is ready. Billing
starts only then. While the session runs it asks Orbit for the user's messages, puts each
one to the model, and posts the answer back. When the session ends, it stops the server.

Once the machine is ready it offers the browser a key, and from then on the conversation is
sealed: Orbit relays envelopes it cannot open (see host/seal.py and docs/PRIVACY.md). This
machine still sees the conversation in plain text, because the model runs here, and the page
tells the user so. If the cryptography package is missing, or the browser never answers the
offer, messages pass unsealed and the page says that instead.

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

try:
    import seal  # host/seal.py, beside this file; needs the cryptography package
except ImportError:  # run unsealed, and say so
    seal = None

ORBIT_URL =os.environ.get("ORBIT_URL", "http://localhost:8000").rstrip("/")
HEARTBEAT_URL = ORBIT_URL + "/api/hosts/heartbeat"
READY_URL = ORBIT_URL + "/api/hosts/ready"
INBOX_URL = ORBIT_URL + "/api/hosts/inbox"
REPLY_URL = ORBIT_URL + "/api/hosts/reply"
LLAMA_CMD = os.environ.get("ORBIT_LLAMA_CMD", "llama serve")
LLAMA_PORT = int(os.environ.get("ORBIT_LLAMA_PORT", "8081"))
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")
INTERVAL = 10  # seconds between heartbeats while no session is running
WAIT = 20  # seconds Orbit may hold an inbox request while nothing new is said
ANSWER_MAX_TOKENS = 1024

QUANT = re.compile(r"^(I?Q\d\w*|F16|BF16|F32)$", re.I)


def _post(url, token, **fields):
    data = urllib.parse.urlencode({"token": token, **fields}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    return urllib.request.urlopen(req, timeout=WAIT + 30)


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


def fetch_inbox(token, after, wait=WAIT, url=INBOX_URL):
    """Ask Orbit for the conversation after message `after`. Orbit holds the request up to
    `wait` seconds for something new. Returns the parsed reply, or None if Orbit did not answer."""
    try:
        with _post(url, token, after=after, wait=wait) as resp:
            return json.loads(resp.read() or b"{}")
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
        print(f"error: {e}")
        return None


def send_reply(token, session_id, body, url=REPLY_URL):
    """Post the model's answer. Returns the message id Orbit gave it, or None."""
    try:
        with _post(url, token, session_id=session_id, body=body) as resp:
            return json.loads(resp.read() or b"{}").get("id")
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
        print(f"error: {e}")
        return None


def ask_model(transcript, port=LLAMA_PORT):
    """Put the whole conversation to llama.cpp's OpenAI-style endpoint and return the answer."""
    msgs = [{"role": "user" if m["sender"] == "user" else "assistant", "content": m["body"]} for m in transcript]
    body = json.dumps({"messages": msgs, "max_tokens": ANSWER_MAX_TOKENS}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"]


def attestation():
    """What this machine can prove about itself to the browser. Nothing yet: consumer hardware has
    no enclave a browser could check (docs/PRIVACY.md), so the page says the host can read the chat."""
    return {"kind": "none"}


class Runner:
    """Keeps at most one model server running, for the session Orbit named, and relays its chat."""

    def __init__(self, token, popen=subprocess.Popen, server_up=model_server_up, ready=send_ready,
                 inbox=fetch_inbox, reply=send_reply, ask=ask_model):
        self.token, self.popen, self.server_up, self.ready = token, popen, server_up, ready
        self.inbox, self.reply, self.ask = inbox, reply, ask
        self.session_id = None
        self.proc = None
        self.ready_sent = False
        self.transcript = []  # the conversation in plain text, oldest first; lives only in memory
        self.after = 0  # the newest relay message id seen
        self.sealer = None  # this session's keys, once the browser has answered our hello
        self.sealed = False  # whether the user's latest message came sealed; answers go back the same way

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
                self.offer_seal()

    def offer_seal(self):
        """Post this machine's public key so the browser can seal the conversation."""
        if seal is None:
            print("sealing unavailable (python -m pip install -r host/requirements.txt); the conversation passes unsealed")
            return
        self.sealer = seal.Sealer(self.session_id, "host")
        self.post(self.sealer.hello(attestation()))

    def post(self, body):
        """Post one message to the relay. Returns its id, or None if Orbit did not take it."""
        mid = self.reply(self.token, self.session_id, body)
        if mid:
            self.after = max(self.after, mid)
        return mid

    def say(self, text):
        """Send text to the user, sealed when the conversation is sealed. Returns the message id or None."""
        if self.sealed and self.sealer is not None and self.sealer.ready:
            return self.post(self.sealer.seal(text))
        return self.post(text)

    def take(self, m):
        """One message from the user: the browser's hello, a sealed message, or plain text.

        Returns the plain text to answer, or None when there is nothing to answer.
        """
        env = seal.parse(m["body"]) if seal is not None else None
        if env is None:  # plain text: an older page, or a browser that never got our key
            self.sealed = False
            return m["body"]
        if env["t"] == "hello":
            if self.sealer is None:
                self.sealer = seal.Sealer(self.session_id, "host")
            try:
                self.sealer.accept(env)  # a new browser tab re-keys; its attestation is not checked here
                self.sealed = True
                print("conversation sealed")
            except seal.SealError as e:
                print(f"bad hello from the browser: {e}")
            return None
        if self.sealer is None or not self.sealer.ready:
            self.say("Your message arrived sealed, but this machine has no key for it. Reload the page.")
            return None
        try:
            text = self.sealer.unseal(env)
        except seal.SealError as e:
            print(f"could not open a sealed message: {e}")
            self.say("A sealed message could not be opened. Reload the page to start a new key.")
            return None
        self.sealed = True
        return text

    def relay(self):
        """One round of the conversation: fetch what the user said, answer it, post the answer.

        Holds up to WAIT seconds while nothing is said, so it also paces the main loop.
        If Orbit says the session is over, the model server is stopped at once.
        """
        got = self.inbox(self.token, self.after)
        if got is None:
            return
        session = got.get("session")
        if session is None or session.get("id") != self.session_id:
            self.stop()
            return
        for m in got.get("messages", []):
            if m["id"] <= self.after:
                continue
            self.after = m["id"]
            if m["sender"] != "user":
                continue  # our own hello or answer, echoed back by the relay
            text = self.take(m)
            if text is not None:
                self.transcript.append({"sender": "user", "body": text})
        if self.transcript and self.transcript[-1]["sender"] == "user":
            try:
                answer = self.ask(self.transcript)
            except Exception as e:  # the model server failed; say so plainly instead of going quiet
                answer = f"The model did not answer: {e}"
            if self.say(answer):
                self.transcript.append({"sender": "host", "body": answer})

    def stop(self):
        if self.proc is not None:
            print(f"session {self.session_id} ended, stopping the model server")
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc, self.session_id, self.ready_sent = None, None, False
        self.transcript, self.after = [], 0
        self.sealer, self.sealed = None, False


def main():
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    runner = Runner(token)
    try:
        while True:
            ok, session = check_in(token)
            if ok:
                runner.step(session)
            if runner.ready_sent:
                runner.relay()  # waits for the user, up to WAIT seconds
            else:
                time.sleep(INTERVAL)
    finally:
        runner.stop()


if __name__ == "__main__":
    main()
