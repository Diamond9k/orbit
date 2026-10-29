# The path, as it is

From a user's browser to a host being paid, step by step, at main `785d9eb` on 2026-10-29.
Three grades of evidence: **code** (it is in the repository with tests), **controlled** (it ran
on Cooper's PC playing both roles, scripted, with dev funds), **real** (an independent person,
real money). Nothing on this path has the third grade yet.

| Step | What happens | Where | Evidence | Gap |
|---|---|---|---|---|
| 1. Sign in | Email and password, signed cookie | `orbit/app.py`, `login.html`, `signup.html` | code | Only Cooper has an account |
| 2. Hardware time | Dollars in, through Stripe Checkout in test mode; the webhook credits the ledger once per checkout session (memo `stripe:<id>`); dev mode adds test funds | `orbit/app.py`, `orbit/ledger.py`, `store.html` | code; controlled with dev funds | No live Stripe key; no real dollar has entered |
| 3. Find a model and a machine | Model fit judged from the model's name and the machine's VRAM; machines listed by hosts with a price per hour | `run.html`, `orbit/app.py` | code; controlled | Fit from the name only; one host, Cooper's RX 580 |
| 4. Start | One user, one machine, exclusive; the host program hears the session in its heartbeat reply, starts `llama serve`, posts ready; billing starts at ready | `host/orbit_host.py`, `/api/hosts/*` | code; controlled (`docs/evidence/2026-10-29-first-session-e2e.md`) | The host program needs Python, the `cryptography` package and llama.cpp installed by hand; it does not install like an app |
| 5. Chat | Browser and host exchange keys through Orbit, then AES-GCM envelopes Orbit cannot open; Orbit keeps them only while the session runs | `host/seal.py`, `orbit/static/seal.js`, `session.html` | code (unit and Node interop); controlled (`docs/evidence/2026-10-29-sealed-session-e2e.md`) | The host's machine reads everything; an active Orbit could swap keys in the hello; Orbit serves the JavaScript; no browser-driven automated test |
| 6. End | Stopped by the user, out of time, or host lost; charged by the minute from ready; charge posted once, retries never bill twice | `orbit/app.py` (`end_session`, `post_session_charge`, `sweep`) | code; controlled | Sweeps run on requests, not a timer |
| 7. Host earns | The session charge splits into the host's balance and Orbit's cut (`ORBIT_CUT_PERCENT`, default 20) as ledger rows summing to zero | `post_session_charge` in `orbit/app.py`, rows posted by `orbit/ledger.py` | code | A balance in a table, not money |
| 8. Payout | Move a host's earned balance to the host | not built | none | Needs Stripe Connect or an equivalent, Cooper's account, a `payout:<id>` memo, weekly run; `docs/NEXT.md` item 9 |
| 9. Reach | A stranger types an address and gets Orbit | not built | none | Localhost only; no domain, no box, no TLS (and without https the browser cannot seal) |
| 10. Strangers | An independent user on an independent host's machine, unassisted | none | none | The milestone |

## The obstacles that matter most, ranked by what they block

1. **The host program does not install like an app.** Without it no independent host exists, so
   no independent session exists. Steps 4 to 10 wait on it. (`docs/NEXT.md`, Later.)
2. **No public address.** Without one no independent user exists and the browser cannot seal
   (WebCrypto needs https). Needs Cooper: a domain and a small box, and the decision to be
   reachable at all.
3. **No payout.** Hosts can earn balances but nothing pays them. Needs Cooper's Stripe decisions.
4. **Privacy from the host needs hardware ordinary people do not own.** Consumer parts cannot
   attest; the honest label today is "the host's machine can read this". The verified tier needs
   SEV-SNP or TDX plus a confidential-computing GPU (`docs/PRIVACY.md`), and Cooper's go.
5. **An active Orbit could swap keys.** True of the community tier until the host's identity is
   bound to something the browser can verify, and the browser's own code is delivered
   verifiably. Documented, not solved.

## The swarm and the controller

`swarm/run.sh` is one cycle (scout, builder, fixer, critic on the local 14B model; a Claude
director only with an API key); `swarm/forever.sh` loops it; `swarm/state.py` keeps per-item
failure counts, escalation and begin/end stamps in `workspace/state.json`; a `build/` branch
merges itself when green. It is idle today. Keystone's fleet is separate: Claude agents in
worktrees, tracked on `docs/BOARD.md`, merged only through pull requests Cooper sees.
