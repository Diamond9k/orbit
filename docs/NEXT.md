# What is next

Take the top item. Do only that. Move it to Done when the branch is pushed and tests pass.
Add anything else worth doing to Later, one line each. Do not reorder without Cooper.

## Now
The previous builder failed by widening scope, so keep each item to its named files, use stdlib and existing imports only, and never touch requirements.txt.

1. **Heartbeat tells the host what to run.** Files: `orbit/app.py`, `tests/test_app.py`.
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
- Host program: once the model is loaded, POST `token` to `/api/hosts/ready`. Until it does, no
  session is ever charged. To test by hand: `curl -X POST -d token=<token> localhost:8000/api/hosts/ready`.
- Continue the competitor scan in docs/SCAN-vastai.md: RunPod, Salad, io.net, Akash. Salad first.
- Cycle 1 (review/2026-10-28-1717) went to review: GET instead of POST, tests read a real
  file, requirements.txt wiped. Branch can be deleted; item 1 stays on top.
- Edit a listed machine's price without removing it.
- Hosts page earnings, real numbers only (rule 5): "most you can earn: $X/hr with every machine
  busy" from host prices; optional "what you paid" next to earned-so-far from the ledger; after
  30 days online, measured hours rented and payback at that measured rate. No predicted return.
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
- Host program step 1: `host/orbit_host.py` sends the heartbeat every minute from the token in
  `host/token.txt` (gitignored). Built by Claude after the swarm escalated it.
- Billing starts when the host says the model is ready (`/api/hosts/ready`), not when the user
  clicks start. Stopping before that charges nothing. Existing `orbit.db` files get `ready_at` on start.
