# Evidence: a complete session on one PC, real app, real host program, real model

Date: 2026-10-29, 01:03 Central (06:03 UTC). Run by Keystone on Cooper's PC (Radeon RX 580, 8 GB).
Branch `keystone/first-session` at the commit that adds this file. Controlled test, not a real
user: Cooper's machine was both the host and the user's browser, the user was a script, the
money was dev test funds. It proves the mechanism, not the milestone.

## What ran

- Orbit (`python -m orbit`) on port 8020, scratch database, `ORBIT_DEV=1`, `ORBIT_HOST_TIMEOUT=30`.
- The host program (`host/orbit_host.py`) with `ORBIT_URL=http://127.0.0.1:8020` and
  `ORBIT_LLAMA_PORT=8091`, started through a wrapper that can stop it cleanly.
- llama.cpp 0.7.0-dev (build 11941), started by the host program:
  `llama serve -hf bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M --host 127.0.0.1 --port 8091`.
  The model was already in llama.cpp's cache.
- The script `e2e_local_session.py` in this folder played the user.

## What happened, from the script's log

```
[   1.1s] Orbit is up on 8020
[   1.5s] signed up as the user
[   1.5s] listed this PC as host 1 at $0.60 an hour; token written to host/token.txt (temporary)
[   1.5s] added $10.00 of dev test funds
[   2.5s] host program heartbeat received: machine online
[   2.5s] session 1 started with bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M; waiting for the host to load the model
[  23.2s] host said ready after 20.7s (ready_at 2026-10-29 06:03:00 UTC); billing starts here
[  23.2s] user sent message 1: 'Reply with exactly one word: pong'
[  24.2s] model answered in 1.0s: 'Pong'
[  24.2s] user sent message 3: 'Which word did you just reply with? Answer in one short sentence.'
[  25.2s] model answered in 1.0s: 'Pong'
[  25.2s] session 1 stopped: {'minutes': 1, 'cost_cents': 1, 'end_reason': 'stopped', 'ready_at': '2026-10-29 06:03:00', 'ended_at': '2026-10-29 06:03:03'}; ledger rows [('user:1', -1), ('host:1', 1), ('orbit:revenue', 0)]
[  25.2s] messages deleted with the session
[  26.3s] host program stopped the model server after the session ended
[  26.3s] /health: {'ok': True, 'unbalanced_txns': []}
[  26.3s] session 2 started; waiting for ready
[  46.9s] ready after 20.6s
[  67.6s] host program gone, model server stopped (the machine 'vanished'); host last_seen 2026-10-29 06:03:24 UTC
[  67.6s] waiting 40s for Orbit to notice
[ 107.6s] session 2 after the sweep: {'minutes': 1, 'cost_cents': 1, 'end_reason': 'host_lost', 'ready_at': '2026-10-29 06:03:24', 'ended_at': '2026-10-29 06:03:24'}; host status offline
[ 107.6s] user balance 999 -> 998 cents; charged 1 for 1 minute(s)
[ 108.6s] host program restarted: heartbeat says no session, machine online again
[ 111.7s] ALL CHECKS PASSED
```

## What this proves

- The heartbeat tells the host what to run; the host program starts the model and says ready;
  billing starts at ready, 20.7 s after the user clicked start.
- A user's words reach the model and the answer comes back through the relay: two turns, one
  second each, with the model keeping the conversation (second answer refers to the first).
- Stopping settles the ledger: one minute minimum, one cent at $0.60 an hour, host row plus
  Orbit row sum to the user's row, `/health` balanced. Messages are gone afterwards.
- The host program stops the model server when the session ends, and starts it again for the
  next session.
- When the host stops answering mid-session, Orbit ends the session by itself (within the
  timeout), marks the host offline, charges only up to the host's last heartbeat, and the host
  program coming back finds nothing to run.

## What this does not prove

- No stranger, no second machine, no real money, no real payout, no public address.
- The relay is unsealed: Orbit saw the bodies in flight.
- The host's `last_seen` lagged its real last moment by the length of one held inbox request
  (about 20 s) in this run; the user was charged less, not more. The code now refreshes
  `last_seen` every half second while a request is held. That change came after this run; a
  unit test covers it, this end-to-end run does not.
- Run once. Not repeated.

## Rerun it

From the repo root, with llama.cpp installed and ports 8020 and 8091 free:

```
python -m pip install -r requirements-dev.txt
python docs/evidence/e2e_local_session.py
```

It writes its log to `workspace/runs/e2e/`. It only stops processes it started.
