# What is next

Take the top item. Do only that. Move it to Done when the branch is pushed and tests pass.
Add anything else worth doing to Later, one line each. Do not reorder without Cooper.

## Now
The previous builder failed by widening scope, so keep each item to its named files, use stdlib and existing imports only, and never touch requirements.txt.


## Then
5. **Verified hosts.** The protected-compute boundary designed in docs/PRIVACY.md: the model runs
   inside enclave hardware (AMD SEV-SNP or Intel TDX, with NVIDIA confidential computing for the
   GPU), the host program's session key is born inside it, and the browser checks the attestation
   and the published measurement before it sends a word. Waits on Cooper: whether to pursue it and
   who provides the first attested machine. Consumer hardware cannot do this; it stays community.
6. **The guide.** Reacts to session events, not timers: model loaded, first answer sent, user
   idle, time running low, session ended. One tip per event, shown once. Answers questions
   from session data. Never sees the chat.
7. **Hosts paid, live on the site.** One number from the ledger. The scoreboard.
8. **Host tiers on the pages.** "Verified" for machines that pass item 5, "community" for everyone
   else, with the exact wording from docs/PRIVACY.md next to every machine and in every session.
9. **Host payouts.** Move earned balances to hosts through Stripe. Weekly.
10. **Stream tokens** through the sealed relay: the host seals partial replies, the page appends them.

## Later
- Continue the competitor scan in docs/SCAN-vastai.md: RunPod, Salad, io.net, Akash. Salad first.
- Branches review/2026-10-28-1717, -1735, -1856, -1923 and escalate/2026-10-28-1856 are
  swarm attempts at the host program, now merged by hand. Cooper can delete them.
- Edit a listed machine's price without removing it.
- Hosts page earnings, real numbers only (rule 5): "most you can earn: $X/hr with every machine
  busy" from host prices; optional "what you paid" next to earned-so-far from the ledger; after
  30 days online, measured hours rented and payback at that measured rate. No predicted return.
- Direct browser-to-host link with the relay as fallback, for speed.
- Model fit read from the Hugging Face file list, not only the name.
- A real domain and a small rented box for Orbit once strangers are paying strangers.
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
