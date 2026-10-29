# What is next

Take the top item. Do only that. Move it to Done when the branch is pushed and tests pass.
Add anything else worth doing to Later, one line each. Do not reorder without Cooper.

## Now
The previous builder failed by widening scope, so keep each item to its named files, use stdlib and existing imports only, and never touch requirements.txt.

1. **Host program, step 1: say hello (retry, smaller).** _(escalated: needs Claude or Cooper)_ New file `host/orbit_host.py`, standard library only.
   Write one function `send_heartbeat(token, url="http://localhost:8000/api/hosts/heartbeat")`.
   It builds `urllib.request.Request(url, data=urllib.parse.urlencode({"token": token}).encode(), method="POST")`
   and calls `urllib.request.urlopen` on it. On a 200 reply it prints "online" and returns True.
   On any `urllib.error.URLError` or `HTTPError` it prints the error and returns False.
   `main()` reads the token from `host/token.txt` (stripped), then calls `send_heartbeat` every 60 seconds.
   It only dials out.
   New file `tests/test_host.py`: call `send_heartbeat("abc")` directly with a literal token and never read a real file.
   Patch `urllib.request.urlopen`. Assert `req.get_method() == "POST"`, `req.full_url` is that URL, and `req.data == b"token=abc"`.
   Make the mock raise `URLError("down")` and assert it returns False and the printed output contains "down".
   Do not touch any other file except `docs/NEXT.md`.
   Why: without a host program no machine can stay online without hand-typed curl, so no stranger's session can ever be paid.
2. **Do not bill before the machine is ready (stranger friction).** Files: `orbit/db.py`, `orbit/app.py`, and a new test in `tests/test_app.py`.
   In `orbit/db.py`, add a nullable `ready_at` column to the sessions table. It must be added safely to an existing `orbit.db`.
   In `orbit/app.py`, add a route `POST /api/hosts/ready` that reads form field `token`, the same way the `heartbeat` route does.
   It sets `ready_at` to now on that host's running session and returns 200. It returns 404 if the token is unknown or there is no running session.
   Wherever `app.py` counts the session's minutes for the charge, count from `ready_at` instead of the start time. While `ready_at` is null the count is zero.
   While `ready_at` is null, the session page shows "Waiting for the machine. You are not being charged." instead of the running cost.
   Do not edit `orbit/ledger.py`.
   Test: start a session. Assert the charged minutes are 0 and the page shows the waiting text. Then POST `/api/hosts/ready` with the host's token, assert 200, and assert `ready_at` is set. Also assert an unknown token returns 404.
   Why: the stranger watched a cost clock run with no chat, and a user billed for a machine that is not ready leaves and never becomes a paid session.
3. **Heartbeat tells the host what to run.** Files: `orbit/app.py`, `tests/test_app.py`.
   Change the `POST /api/hosts/heartbeat` 200 reply to JSON. It is `{"session": null}` when the host has no running session.
   When it has one, it is `{"session": {"id": <session id>, "model": "<model name of that session>"}}`.
   Keep the existing behavior of marking the host online and the existing error replies.
   Test: a heartbeat with no session returns `{"session": null}`. After starting a session on that host, a heartbeat returns the session id and the exact model name.
   Why: the host program can only load the model a stranger chose if Orbit tells it on the heartbeat

## Then
5. **Chat screen** inside the session page. Encrypted end to end between the browser and the
   host program. Orbit relays sealed envelopes it cannot open. Streams tokens.
6. **The guide.** Reacts to session events, not timers: model loaded, first answer sent, user
   idle, time running low, session ended. One tip per event, shown once. Answers questions
   from session data. Never sees the chat.
7. **Hosts paid, live on the site.** One number from the ledger. The scoreboard.
8. **Host tiers.** Verified for machines with enclave hardware that pass attestation,
   community for everyone else. Labels earned by the hardware.
9. **Host payouts.** Move earned balances to hosts through Stripe. Weekly.

## Later
- Cycle 1 (review/2026-10-28-1717) went to review: GET instead of POST, tests read a real
  file, requirements.txt wiped. Branch can be deleted; item 1 stays on top.
- Edit a listed machine's price without removing it.
- Direct browser-to-host link with the relay as fallback, for speed.
- Model fit read from the Hugging Face file list, not only the name.
- A real domain and a small rented box for Orbit once strangers are paying strangers.

## Done
- v0.1 web app: sign-in, hardware-time store, double-entry ledger, model fit from the name,
  exclusive sessions charged by the minute, host listing with token, heartbeat API.
- Site rebuilt on self-hosted Bootstrap. Home is the workbench. Friendly errors. Live session
  counter. Quantization chips. Busy machines shown.
- README and CLAUDE.md.
- Orbit ran on Cooper's Windows PC. Cooper is host number one: Radeon RX 580, 8 GB. The
  full loop settled correctly on real hardware. Heartbeat sent by hand with curl until step 1.
- Remove a listed machine. Nav never wraps.
- Branches merge themselves when green (rule 12, GitHub workflow). Swarm set up for
  llama.cpp Vulkan on the RX 580.
- Starting a second session sends you to the running one and now says why on that page.
