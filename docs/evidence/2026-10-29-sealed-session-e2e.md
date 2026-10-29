# Evidence: a sealed session on one PC, real app, real host program, real model

Date: 2026-10-29, 03:00 Central (08:00 UTC). Run by Keystone on Cooper's PC (Ryzen 5 3600,
Radeon RX 580, 8 GB), branch `keystone/protected-compute`. Same rig as the first run
(`2026-10-29-first-session-e2e.md`) plus the sealing: controlled test, scripted user, dev test
funds, Cooper's machine as both host and user. It shows the mechanism, not a private real-world
session.

## What ran

- Orbit on port 8020 with a scratch database, `ORBIT_DEV=1`, `ORBIT_HOST_TIMEOUT=30`.
- The host program (`host/orbit_host.py`, with `host/seal.py`) on llama port 8091, started through
  the wrapper in this folder.
- llama.cpp 0.7.0-dev, `bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M`, from cache.
- `e2e_local_session.py` as the user. It plays the browser's half of the sealing with
  `host/seal.py` (the Python side), not with `orbit/static/seal.js`; the JavaScript side is
  checked against the Python side separately, under Node, in `tests/test_seal.py`.

## What happened

```
[   1.0s] Orbit is up on 8020
[   1.4s] signed up as the user
[   1.4s] listed this PC as host 1 at $0.60 an hour; token written to host/token.txt (temporary)
[   1.4s] added $10.00 of dev test funds
[   2.4s] host program heartbeat received: machine online
[   2.4s] session 1 started with bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M; waiting for the host to load the model
[  22.7s] host said ready after 20.2s (ready_at 2026-10-29 08:00:51 UTC); billing starts here
[  22.7s] host offered its key (attestation: {'kind': 'none'}); browser answered with its own; conversation sealed
[  22.7s] user sent sealed message 3: 'Reply with exactly one word: pong'
[  24.2s] model answered in 1.5s: 'pong' (its envelope on the relay: 73 chars)
[  24.2s] user sent sealed message 5: 'Which word did you just reply with? Answer in one short sentence.'
[  24.7s] model answered in 0.5s: 'pong' (its envelope on the relay: 73 chars)
[  24.7s] Orbit's database holds 6 messages for the session: all envelopes, none containing the words
[  24.7s] session 1 stopped: {'minutes': 1, 'cost_cents': 1, 'end_reason': 'stopped', 'ready_at': '2026-10-29 08:00:51', 'ended_at': '2026-10-29 08:00:54'}; ledger rows [('user:1', -1), ('host:1', 1), ('orbit:revenue', 0)]
[  24.7s] messages deleted with the session
[  25.8s] host program stopped the model server after the session ended
[  25.8s] /health: {'ok': True, 'unbalanced_txns': []}
[  25.8s] session 2 started; waiting for ready
[  36.7s] ready after 10.9s
[  57.6s] host program gone, model server stopped (the machine 'vanished'); host last_seen 2026-10-29 08:01:26 UTC
[  57.6s] waiting 40s for Orbit to notice
[  97.7s] session 2 after the sweep: {'minutes': 1, 'cost_cents': 1, 'end_reason': 'host_lost', 'ready_at': '2026-10-29 08:01:06', 'ended_at': '2026-10-29 08:01:26'}; host status offline
[  97.7s] user balance 999 -> 998 cents; charged 1 for 1 minute(s)
[  98.7s] host program restarted: heartbeat says no session, machine online again
[ 101.7s] ALL CHECKS PASSED
```

## What this shows

- The host program offered a key the moment the model was ready, with `{"kind": "none"}` as its
  attestation, which is the truth: this machine has nothing to attest with.
- Two sealed questions reached the real model and two sealed answers came back, the second
  answer referring to the first. Round trips of 1.5 s and 0.5 s.
- While the session ran, Orbit's database held six messages for it: the two hellos, two sealed
  questions, two sealed answers. The script checked every stored body: each parsed as an
  envelope, none contained the words. Orbit saw envelope sizes (73 characters for a one-word
  answer) and timing, nothing else.
- Billing and cleanup unchanged by the sealing: one cent, rows that sum to zero, messages deleted,
  model server stopped.
- The `last_seen` fix from the previous run held: session 2 ended at 08:01:26, the host's last
  heartbeat, twenty seconds after ready, whereas the earlier run ended it at the `ready_at` second.

## What this does not show

- The browser. The user here was Python code using `host/seal.py`. The real page
  (`orbit/templates/session.html` with `orbit/static/seal.js`) was not driven by this run; its
  cryptography is proven to interoperate under Node, its page logic is not covered by automation.
- Protection from the host. The host program decrypted every message in plain text, as it must to
  run the model. The page says so.
- Protection from an Orbit that swaps keys during the hello exchange. Nothing here binds the
  host's key to anything the browser can check. That is the verified tier, in `docs/PRIVACY.md`.
- Anything about strangers, real money or payouts.

## Rerun it

```
python -m pip install -r requirements-dev.txt
python docs/evidence/e2e_local_session.py
```

Needs llama.cpp and free ports 8020 and 8091. It writes `workspace/runs/e2e/` and stops only the
processes it started.
