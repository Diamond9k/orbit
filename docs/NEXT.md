# What is next

Take the top item. Do only that. Move it to Done when the branch is pushed and tests pass.
Add anything else worth doing to Later, one line each. Do not reorder without Cooper.

## Now
The previous builder failed by widening scope, so keep each item to its named files, use stdlib and existing imports only, and never touch requirements.txt.


## Then
1. **Fingerprint check.** The browser and the host program each show a short code made from
   the two public keys. Same code on both: the relay did not swap keys. This closes the last
   privacy gap now that the machine is the person's own. `orbit/static/seal.js`, `host/seal.py`.
2. **Host program installs like an app** on Windows, Mac and Linux, with plain steps and a
   download link on the My machines page.
3. **Stream tokens** through the sealed relay: the machine seals partial replies, the page appends them.
4. **More than one model at a time**, one per machine. Today a person runs one session at a time.
5. **Direct browser-to-machine link**, with the relay as fallback, for speed.

## Later
- Decide what happens to the swarm and the marketplace documents (see the decision file).
- Fit check from the Hugging Face file list, and for Apple Silicon and CPU-only machines, not only GPU memory.
- Store host tokens hashed, not plain, so a copied database cannot impersonate a host.
- Limit sign-in attempts per email and per address.
- A second key for sign-in cookies so `ORBIT_SECRET` can be changed without signing everyone out.
- Continue the competitor scan in docs/SCAN-vastai.md: RunPod, Salad, io.net, Akash. Salad first.
- Branches review/2026-10-28-1717, -1735, -1856, -1923 and escalate/2026-10-28-1856 are
  swarm attempts at the host program, now merged by hand. Cooper can delete them.
- Direct browser-to-host link with the relay as fallback, for speed.
- Model fit read from the Hugging Face file list, not only the name.
- Host program: if a model server is already answering on its port when it starts (left over
  from a crash), adopt or stop it instead of failing to bind forever.
- Host program installs like an app (one file, no Python or llama.cpp to set up), and the
  Hosts page gives the plain steps and a download link (the stranger's number two complaint).
- Hosts page: plain steps to run the host program today (token file, `python host/orbit_host.py`,
  `ORBIT_URL`), until it installs like an app.
- Sessions end themselves on every request today; add a timer sweep in the app only if that
  proves too late in practice.
- The session page shows the conversation only while it runs; afterwards it says Orbit kept
  nothing. Let the user download their own transcript before stopping, from the browser.
- Decide whether a page that never receives the host's key may send unsealed (today: yes, after
  ten seconds, labelled) or must refuse. docs/PRIVACY.md, decision 3.
- A "measured" label for community hosts whose TPM attests they booted the unmodified host
  program. Integrity, not privacy; only worth it if the page can say that plainly.
- The session page's key exchange has no automated browser test (no browser driver in the repo).
  Add one before the verified tier, when the browser starts checking attestations.

## Done
- 2026-11-20, decided by Cooper: self-hosting only, no money (decision file of the same date).
  Removed the ledger, the store, Stripe, prices and Orbit's cut. A machine is seen and used
  only by its owner. The sandbox gives each guest simulated machines. CLAUDE.md goal and rules
  rewritten to match. 89 tests pass.
- 2026-11-20, asked for by Cooper: public sandbox on Vercel (`ORBIT_SANDBOX=1`, decision file of
  the same date), new look, About page. Closed along the way: the Stripe hook accepted events
  signed with an empty secret; test funds took any amount; a machine name could run script on the
  account page; NaN passed as a price or memory size; `/login` crashed for a signed-in person;
  sign-in cookies never expired and were not marked secure. Added: a content security policy with
  no inline script or style, a cross-site form check, model names limited to Hugging Face
  characters. Tests: tests/test_sandbox.py, tests/test_security.py.
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
- Swarm escalations merge themselves (a `build/` branch), so the builder stops repeating an
  item main never learned was stuck. The critic's reasons now show in the swarm window.
- Swarm builder uses Aider's diff edit format, so editing `orbit/app.py` fits the local model's
  16k context. The whole format overflowed it and the builder changed nothing.
- Host program runs the model: when the heartbeat names a session it starts `llama serve -hf`
  on port 8081, posts `/api/hosts/ready` once it answers, and stops it when the session ends.
  It reads the session from the heartbeat reply, so it waits on Now item 1 to do anything.
- Heartbeat reply names the session the host should run: `{"session": {"id", "model"}}` or
  `{"session": null}`. Built by Keystone after the local builder overflowed its context on it twice.
- Sessions end on their own: when the hardware time runs out (charged exactly the minutes the
  balance covered, never below zero) or when the host has not been heard from for three minutes
  (charged only up to its last heartbeat). Stopping late charges only the covered time. The ended
  page says why. A charge lost to a crash between closing the session and posting it is posted by
  the next sweep, once; a retry never bills twice.
- The chat is relayed. The user's words reach the model on the host and the answer comes back:
  browser to `/sessions/{id}/messages`, host program long-polls `/api/hosts/inbox`, asks llama.cpp,
  posts `/api/hosts/reply`. Orbit keeps bodies only while the session runs, never reads them,
  deletes them when it ends. Built by Keystone.
- The chat is sealed. The host program offers a key when the model is ready, the browser answers
  with its own, and from then on Orbit relays AES-GCM envelopes it cannot open (`host/seal.py`,
  `orbit/static/seal.js`, checked against each other under Node). The page says "Sealed from
  Orbit" and, in the same breath, that the host's machine can read the conversation. The research
  on protecting it from the host too is `docs/PRIVACY.md`. Built by Keystone at Cooper's direction.
