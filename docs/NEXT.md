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
   from session data. Never sees the chat. Its model gets counts and states only, never an
   email, a host name or a word of the conversation (recon: Arc OS put emails in a prompt).
7. **Hosts paid, live on the site.** One number from the ledger. The scoreboard. From the recon:
   the number is a ledger sum, never a counter; a count cut off by a limit shows "100+", never a
   false exact figure; every figure is a link that lists the rows behind it; a percentage shows
   only above a minimum Cooper sets; a failed read shows the error, never a stale number.
8. **Host tiers on the pages.** "Verified" for machines that pass item 5, "community" for everyone
   else, with the exact wording from docs/PRIVACY.md next to every machine and in every session.
   "Verified" shows only from an attestation that ran on this session; a check that did not run
   shows "not checked", never a pass. Tier is written only by the server, never by the host.
9. **Host payouts.** Move earned balances to hosts through Stripe. Weekly. The recipe from the
   ARC billing audit (recon batch 5): Stripe Connect Express, separate charges and transfers; the
   onboarding route returns a single-use link and a refresh route mints a new one; status is
   re-read from Stripe each time; no ready account answers 409 "needs connect", never a payout to
   the platform. The weekly job writes a proposed batch, `UNIQUE(week)`, that Cooper approves
   (rule 13); a second run that week does nothing. Each transfer posts through `ledger.post(...,
   once="payout:<id>")`. The week ends at local midnight computed in two passes so DST cannot
   shift it. The job records each run (ok or failed) and the scoreboard shows when it last ran.
   A fee that cannot be read is unknown, never 0; verify Connect fees on stripe.com before
   setting any host take. Done only when one real transfer has landed.
10. **Stream tokens** through the sealed relay: the host seals partial replies, the page appends them.
   Test it with a fake host program (no model, an injected clock, `[[slow]]` and `[[drop]]` in
   the prompt to make it stall or vanish mid-reply), so minute counting and a host dropping
   mid-session are covered without a GPU.

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

- Stripe refunds and disputes: post balancing reversal rows (`once="refund:<id>"`) when Stripe
  sends `charge.refunded` or `charge.dispute.created`. Today neither is handled. Before strangers pay.
- Daily reconciliation: hardware time sold in the ledger against Stripe charges, host credits
  against Stripe transfers; any mismatch goes to Cooper, never fixed by a guess. With item 9.
- Model list carries each model's licence and allowed regions, "unknown" when not known
  (several open-weight licences went research-only or region-fenced in 2026).
- Swarm, when the fleet resumes (Cooper's call): a stall alarm (no progress in N minutes) and a
  spend cap per run; fixed exit codes for the item runner (0 ok, 3 waiting, 4 refused, 5 error).
- UI blueprint loop (marketing-creatives/loop/) waits on Cooper's 3 to 5 reference screens.
  When a round is kept, its rules go into a docs/DESIGN.md that every page is built from.

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
- Recon applied (2026-10-30): a card payment and a session's charge each post exactly once, even
  when Stripe retries or two sweeps race (`ledger.post(..., once=key)`, `ledger_once` table). The
  webhook credits only paid checkouts and names `STRIPE_WEBHOOK_SECRET` when it is unset. Host
  tokens are stored as SHA-256. A test walks every host route with bad tokens and every
  signed-in route without a cookie. `.claude/settings.json` denies .env reads and pushes to main;
  the critic must show proof; auto-merge is bound to the tested commit. Money figures use tabular
  digits; Inter, the navbar blur and the all-caps label are gone; the home page no longer says
  the conversation never passes through Orbit.
