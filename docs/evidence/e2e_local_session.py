"""Controlled end-to-end exercise of Orbit on one PC: real web app, real host program, real model.

    python docs/evidence/e2e_local_session.py      (from the repo root; needs llama.cpp installed)

Runs Orbit on port 8020 against a scratch database, lists this PC as a host, starts the host
program (which starts llama.cpp for the chosen model on port 8091), and then acts as the user:
starts a session, talks to the model, stops, and checks the ledger. Then starts a second
session and stops the host program (its heartbeats cease, as if the machine vanished) to check
that Orbit ends the session on its own and charges only up to the last heartbeat.

Isolated: scratch DB, ports 8020 and 8091 (the swarm uses 8080, the host default is 8081), a
temporary host/token.txt removed at the end. Only processes this script started are stopped,
through their own handles or the host program's stop file. Nothing touches orbit.db or the swarm.
"""
import os
import re
import sqlite3
import subprocess
import sys
import time

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCRATCH = os.path.join(REPO, "workspace", "runs", "e2e")  # gitignored
os.makedirs(SCRATCH, exist_ok=True)
DB = os.path.join(SCRATCH, "e2e.db")
ORBIT_PORT = 8020
LLAMA_PORT = 8091
ORBIT = f"http://127.0.0.1:{ORBIT_PORT}"
MODEL = "bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M"  # the model the run page suggests first; already in llama.cpp's cache
TOKEN_FILE = os.path.join(REPO, "host", "token.txt")
HOST_STOP = os.path.join(SCRATCH, "host-stop")
HOST_TIMEOUT = 30  # seconds before Orbit treats a silent host as gone (default is 180)

report = []
t0 = time.monotonic()


def say(msg):
    line = f"[{time.monotonic() - t0:6.1f}s] {msg}"
    print(line, flush=True)
    report.append(line)


def pids_on_port(port):
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    return {int(line.split()[-1]) for line in out.splitlines() if f":{port} " in line and "LISTENING" in line}


def wait_for(pred, timeout, what, every=1.0):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        v = pred()
        if v:
            return v
        time.sleep(every)
    raise TimeoutError(f"gave up waiting for {what} after {timeout}s")


def q(sql, *args):
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _ok(url):
    try:
        return httpx.get(url, timeout=3).status_code == 200
    except Exception:
        return False


def start_orbit():
    env = dict(os.environ, ORBIT_DEV="1", ORBIT_DB=DB, ORBIT_PORT=str(ORBIT_PORT), ORBIT_SECRET="e2e-not-secret",
               ORBIT_HOST_TIMEOUT=str(HOST_TIMEOUT), PYTHONUTF8="1")
    log = open(os.path.join(SCRATCH, "orbit.log"), "w", encoding="utf-8")
    p = subprocess.Popen([sys.executable, "-m", "orbit"], cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
    wait_for(lambda: _ok(f"{ORBIT}/health"), 30, "Orbit to start")
    say(f"Orbit is up on {ORBIT_PORT}")
    return p


def start_host():
    if os.path.exists(HOST_STOP):
        os.remove(HOST_STOP)
    env = dict(os.environ, ORBIT_URL=ORBIT, ORBIT_LLAMA_PORT=str(LLAMA_PORT), PYTHONUTF8="1")
    log = open(os.path.join(SCRATCH, "host.log"), "a", encoding="utf-8")
    return subprocess.Popen([sys.executable, os.path.join(HERE, "e2e_host_wrapper.py"), HOST_STOP], cwd=REPO, env=env,
                            stdout=log, stderr=subprocess.STDOUT)


def stop_host(host_p):
    """Ask the host program to exit through its own finally-block, which stops its model server."""
    with open(HOST_STOP, "w") as f:
        f.write("stop")
    try:
        host_p.wait(timeout=90)
    except subprocess.TimeoutExpired:
        say("host program did not exit within 90s of the stop file")


def main():
    assert not pids_on_port(ORBIT_PORT) and not pids_on_port(LLAMA_PORT), "test ports must be free"
    for f in (DB, DB + "-wal", DB + "-shm"):
        if os.path.exists(f):
            os.remove(f)
    orbit_p = host_p = None
    try:
        orbit_p = start_orbit()
        c = httpx.Client(base_url=ORBIT, follow_redirects=False, timeout=60)
        r = c.post("/signup", data={"email": "e2e-user@example.com", "password": "longenough"})
        assert r.status_code == 303, r.text
        say("signed up as the user")
        r = c.post("/hosts", data={"name": "Cooper's PC (e2e)", "gpu": "Radeon RX 580", "vram_gb": 8, "price_dollars_per_hour": 0.60})
        token = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S).group(1).strip()
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        say("listed this PC as host 1 at $0.60 an hour; token written to host/token.txt (temporary)")
        c.post("/store/dev-funds", data={"amount_cents": 1000})
        say("added $10.00 of dev test funds")

        host_p = start_host()
        wait_for(lambda: q("SELECT status FROM hosts WHERE id = 1")[0]["status"] == "online", 30, "the host to come online")
        say("host program heartbeat received: machine online")

        # ---- session 1: start, ready, talk, stop ----
        r = c.post("/sessions/start", data={"model": MODEL, "host_id": 1})
        assert r.status_code == 303 and r.headers["location"] == "/sessions/1", (r.status_code, r.text[:200])
        t_start = time.monotonic()
        say(f"session 1 started with {MODEL}; waiting for the host to load the model")
        wait_for(lambda: c.get("/sessions/1/messages", params={"after": 0, "wait": 5}, timeout=30).json()["ready"],
                 900, "the model to be ready", every=0.1)
        ready_row = q("SELECT ready_at FROM sessions WHERE id = 1")[0]["ready_at"]
        say(f"host said ready after {time.monotonic() - t_start:.1f}s (ready_at {ready_row} UTC); billing starts here")

        after = 0
        for prompt in ["Reply with exactly one word: pong", "Which word did you just reply with? Answer in one short sentence."]:
            t_q = time.monotonic()
            r = c.post("/sessions/1/messages", data={"body": prompt})
            assert r.status_code == 200, r.text
            say(f"user sent message {r.json()['id']}: {prompt!r}")
            got = None
            deadline = time.monotonic() + 300
            while time.monotonic() < deadline and not got:
                d = c.get("/sessions/1/messages", params={"after": after, "wait": 20}, timeout=60).json()
                for m in d["messages"]:
                    after = max(after, m["id"])
                    if m["sender"] == "host":
                        got = m
            assert got, "no answer from the model"
            say(f"model answered in {time.monotonic() - t_q:.1f}s: {got['body']!r}")

        page = c.get("/sessions/1").text
        assert 'id="chat"' in page and "unsealed for now" in page
        r = c.post("/sessions/1/stop")
        assert r.status_code == 303
        s = q("SELECT minutes, cost_cents, end_reason, ready_at, ended_at FROM sessions WHERE id = 1")[0]
        rows = q("SELECT account, amount_cents FROM ledger WHERE memo = 'session:1' ORDER BY id")
        say(f"session 1 stopped: {dict(s)}; ledger rows {[tuple(r) for r in rows]}")
        assert s["end_reason"] == "stopped" and s["cost_cents"] == -rows[0]["amount_cents"]
        assert q("SELECT COUNT(*) AS n FROM messages")[0]["n"] == 0, "messages should be gone"
        say("messages deleted with the session")
        wait_for(lambda: not pids_on_port(LLAMA_PORT), 90, "the host to stop the model server")
        say("host program stopped the model server after the session ended")
        health = c.get("/health").json()
        say(f"/health: {health}")
        assert health["ok"]

        # ---- session 2: the host vanishes mid-session ----
        r = c.post("/sessions/start", data={"model": MODEL, "host_id": 1})
        assert r.status_code == 303 and r.headers["location"] == "/sessions/2", (r.status_code, r.text[:200])
        t_start = time.monotonic()
        say("session 2 started; waiting for ready")
        wait_for(lambda: c.get("/sessions/2/messages", params={"after": 0, "wait": 5}, timeout=30).json()["ready"],
                 900, "ready", every=0.1)
        say(f"ready after {time.monotonic() - t_start:.1f}s")
        time.sleep(5)
        stop_host(host_p)
        last_seen = q("SELECT last_seen FROM hosts WHERE id = 1")[0]["last_seen"]
        say(f"host program gone, model server stopped (the machine 'vanished'); host last_seen {last_seen} UTC")
        balance_before = q("SELECT COALESCE(SUM(amount_cents),0) AS b FROM ledger WHERE account = 'user:1'")[0]["b"]
        say(f"waiting {HOST_TIMEOUT + 10}s for Orbit to notice")
        time.sleep(HOST_TIMEOUT + 10)
        page = c.get("/sessions/2").text
        s = q("SELECT minutes, cost_cents, end_reason, ready_at, ended_at FROM sessions WHERE id = 2")[0]
        host = q("SELECT status FROM hosts WHERE id = 1")[0]["status"]
        say(f"session 2 after the sweep: {dict(s)}; host status {host}")
        assert s["end_reason"] == "host_lost", "the session should have ended as host_lost"
        assert "The machine stopped answering" in page
        assert s["ended_at"] <= last_seen, (s["ended_at"], last_seen)
        balance_after = q("SELECT COALESCE(SUM(amount_cents),0) AS b FROM ledger WHERE account = 'user:1'")[0]["b"]
        say(f"user balance {balance_before} -> {balance_after} cents; charged {balance_before - balance_after} for {s['minutes']} minute(s)")
        assert c.get("/health").json()["ok"]

        # ---- the host program comes back: nothing to run, machine online again ----
        host_p = start_host()
        wait_for(lambda: q("SELECT status FROM hosts WHERE id = 1")[0]["status"] == "online", 30, "host back online")
        say("host program restarted: heartbeat says no session, machine online again")
        time.sleep(3)
        assert not pids_on_port(LLAMA_PORT), "no model server should be running without a session"
        say("ALL CHECKS PASSED")
    finally:
        if host_p is not None and host_p.poll() is None:
            stop_host(host_p)
        if orbit_p is not None:
            orbit_p.terminate()
        time.sleep(2)
        for port in (LLAMA_PORT, ORBIT_PORT):
            left = pids_on_port(port)
            if left:
                say(f"NOTE: something still listens on {port}: pids {sorted(left)} (not killed by this script)")
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        with open(os.path.join(SCRATCH, "e2e-report.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
