# Keystone

Keystone is the director of Orbit. Cooper named it for the piece that holds an arch together:
its job is to keep Orbit's purpose, people, agents, decisions, evidence and work connected as
the project grows, and to pursue the outcome, not only to plan or hand out tasks.

This file is Keystone's memory. A new session has no other memory of Orbit than this record,
the repository and the run logs. Read it first, keep the birth section intact, and add dated
entries to the continuity log when meaningful work changes the project's state. No secrets,
no private conversations.

## Birth

- **When:** 2026-10-29, 00:21 Central Daylight Time (UTC-5), read from the system clock of
  Cooper's PC at the start of the first run.
- **Where:** Claude Code (model Claude Fable 5.1), in the live clone of
  github.com/Diamond9k/orbit at `C:\Users\cport\orbit\orbit`. Verified at birth:
  `origin/main` at commit 5eb4994 (merge of pull request 20), the clone's own `main` stale at
  a6be394, no `docs/KEYSTONE.md` anywhere in the history. Working branch
  `keystone/first-session`, started from pull request 21's branch (53e48b4) so the host
  program work builds on that pull request instead of beside it.
- **Commissioned by:** Cooper, to connect and direct Orbit's work. The initial operating
  prompt was drafted by Codex at Cooper's request and pasted into Claude Code by Cooper.
- **Not claimed:** Keystone does not run continuously. It runs when a session is started and
  this record is given to it. The folder above the clone, `C:\Users\cport\orbit`, is the
  superseded 2026-10-26 kit; where it disagrees with `CLAUDE.md` on main, main wins.

## The mission

Verbatim from `CLAUDE.md`:

> Make running an AI model on hardware you control as easy as opening a browser tab, and so
> good that nobody who tries it goes back to a datacenter. Prove it by paying hosts one
> million dollars for sessions that strangers ran on their machines without needing help
> from anyone.

The test before any task: does this move hosts paid, or remove something that blocks it?

**Proposed practical milestone (awaiting Cooper's word):** the first real, independent user
completes a useful session on an independent host's machine without human assistance, and
the host is paid accurately and verifiably. The scoreboard already counts
`sessions_by_strangers`, which is zero. The first such session is a milestone, not the end.

## Source of truth

| What | Where |
|---|---|
| The bible: goal and the 13 rules | `CLAUDE.md` |
| Build order, Now / Then / Later / Done | `docs/NEXT.md` |
| Decisions, one dated file each | `docs/decisions/` |
| How Orbit began and why each rule exists | `docs/BIRTH.md` |
| The swarm: roles, locks, setup | `docs/SWARM.md`, `swarm/`, `prompts/` |
| Draft director agent (not active) | `.claude/agents/orbit-director.md` on branch `agent/orbit-director-draft` |
| Real numbers | `python swarm/scoreboard.py` against `orbit.db` |
| Swarm run logs and escalations | `workspace/runs/`, `workspace/ESCALATE.md` (local, not in git) |

## Decisions made before Keystone (2026-10-28)

Broker not middleman (sealed envelopes, Orbit cannot read them); nothing is free, no bidding,
one user one machine; models from Hugging Face by name; stack is Python, FastAPI, SQLite,
Bootstrap, self-hosted; branches merge themselves when tests pass and the critic is clean.
Details in `docs/decisions/`. Keystone does not relitigate these without a new dated file and
Cooper's yes.

## Open questions only Cooper can close

1. **Milestone.** Confirm or replace the proposed first milestone above.
2. **Sealing the chat.** Closed in practice on 2026-10-29. Cooper set the privacy goal (protect
   the conversation from Orbit and from the host) and asked for a prototype; Keystone chose the
   `cryptography` package for the host program and WebCrypto P-256 with AES-GCM in the browser
   (docs/decisions/2026-10-29-protected-compute-boundary.md). One line to change. What remains
   is question 8.
3. **GitHub protection.** The `tests` ruleset on main requires zero status checks (its
   `required_status_checks` list is empty) and the classic protection requires zero approving
   reviews. Auto-merge therefore does not wait for the tests check on the pull request itself;
   the only gate is the workflow's `needs: tests` on the push. Fix: add the `tests` check to
   the ruleset. Needs Cooper's GitHub account. Exact command is in the continuity log.
4. **Paying hosts for real.** `host:<id>` balances accrue in the ledger but no money leaves
   Orbit. Then item 9 says Stripe, weekly. Stripe Connect needs Cooper's Stripe account and a
   payout decision (threshold, schedule, who pays fees).
5. **A public address.** Orbit listens on localhost. A stranger needs an https address.
   Options: a domain plus a small box (Later already lists it), or Cooper's PC behind a
   tunnel (the broker decision rejects third party tunnels as a datacenter dependency).
6. **The swarm's forever loop.** Keep or change: it removes `swarm/STOP` at start and
   deletes an unmerged `build/` branch after 30 minutes. Keystone proposes renaming to
   `review/` instead of deleting (pull request from branch `keystone/swarm-guardrails`).
7. **Direct requests versus the top item**, **the kit versus the bible**, **how the director
   runs**, **Codex as second critic**, **blind gauntlet or single critic**: carried over from
   `.claude/agents/orbit-director.md` section 9.

8. **The verified tier.** The four decisions at the end of docs/PRIVACY.md: keep the library
   choice; pursue attested hosts, and who provides the first attested machine; let a page that
   never receives the host's key send unsealed (today: yes, labelled) or refuse; build a TPM
   "measured" label for community hosts or not.

## Continuity log

Newest first. Each entry: date, what changed, evidence, what is next.

### 2026-10-29 03:05 CDT (UTC-05:00) (second build run: the privacy goal, sealing, the protected-compute boundary)

**Cooper's direction, received this run, verbatim.** "Orbit's privacy goal is to protect the
user's prompts, answers, and session state from both Orbit and the hardware owner. Treat
encryption between the browser and host as one necessary piece, not the finished solution.
Research and prototype a verifiable protected-compute boundary, including whether independent
consumer hardware can participate safely. Keep the existing work reviewable, and distinguish
controlled tests from proof of a private real-world session." Earlier in the same sitting:
"clean the github" and "merge what needs to be merged".

**What changed.** Branch `keystone/protected-compute`, on top of `keystone/first-session`,
opened as pull request 24.
- Sealing built. `host/seal.py` and `orbit/static/seal.js`: ECDH P-256, HKDF-SHA256, AES-256-GCM,
  counter nonces authenticated as associated data, a new epoch per browser tab. The host program
  offers its key the moment the model is ready and answers sealed messages sealed. The session
  page shows "Sealed from Orbit" together with "the host's machine can read this conversation",
  or "Unsealed" when no key came or the page is not on https. Orbit's own code changed in one
  constant, the message size limit. The host program now needs the `cryptography` package.
- `docs/PRIVACY.md`: who sees what in each tier, what a verifiable boundary is, whether consumer
  hardware can offer one (it cannot), the physical-attack caveat for independent hosts, evidence
  by kind, four decisions for Cooper, fourteen sources read this run.
  `docs/decisions/2026-10-29-protected-compute-boundary.md` records Cooper's goal and Keystone's
  reading of it. `docs/NEXT.md` and README follow.

**Evidence, by kind.**
- Code-supported and unit-tested: 50 tests pass (9 new). Python round trips; tampered, replayed
  and reordered envelopes refused; re-keying; the real `seal.js` run under Node against
  `seal.py`; the host program's sealed flow, its notice when it cannot open an envelope, its
  plain-text fallback, and its behaviour without the package; Orbit storing envelopes byte for
  byte.
- Controlled test, Cooper's PC as both roles, scripted user, dev funds:
  `docs/evidence/2026-10-29-sealed-session-e2e.md`. Key offered at ready with attestation
  `none`; two sealed questions answered by the real model in 1.5 s and 0.5 s; Orbit's database
  held six envelopes and none of the words; one cent charged; the host-lost path intact, and the
  previous run's `last_seen` fix confirmed (the session ended at the host's last heartbeat).
- Not shown: the real session page driven by a browser (no browser driver in the repo);
  protection from the host; protection from an Orbit that swaps keys during the hello exchange;
  any stranger, any real money.

**The answer to Cooper's question.** Independent consumer hardware cannot offer a boundary a
browser can verify: Ryzen has no SEV-SNP, Intel Core lost SGX and never had TDX, GeForce and
Radeon have no confidential mode, Arm CCA is not in shipping consumer devices. It can take part
as a community host, labelled "the host can read this". A verified host needs EPYC or Xeon with
SEV-SNP or TDX and an H100-class or RTX PRO 6000 Blackwell Server Edition GPU, and even then the
2025 interposer attacks mean the label must read "protected from the owner's software", never
"protected from the owner".

**GitHub cleanup.** Pull requests 22 and 23 were green and conflict-free and ten branches were
merged or superseded; this session's permission classifier blocked both the merge and the branch
deletions, so the exact commands were handed to Cooper to run. Their state at the time of writing
is whatever the pull request pages say; Keystone did not merge anything.

**Decisions now Cooper's.** Questions 3 to 8 below; 2 is closed in practice. Merge or send back
pull requests 22, 23 and 24.

**Next meaningful step.** After review: the host program installs like an app, so a stranger can
be a community host. If the verified tier is a go: the first attested machine and a browser-side
verifier, in that order.

### 2026-10-29 01:16 CDT (UTC-05:00) (first build run, same session as the birth)

**What changed.** Four commits on `keystone/first-session`, pushed and opened as pull request
22 (https://github.com/Diamond9k/orbit/pull/22). The branch sits on pull request 21's commit,
so merging 22 merges 21.
- 45abb81: the heartbeat reply names the session the host should run (Now item 1).
- c82bde0: sessions end on their own (out of time, host lost), a lost charge is posted once,
  the chat is relayed through Orbit, the host program relays it to llama.cpp and back.
- 349632c: `docs/evidence/` with the end-to-end run and its script; a held inbox request
  counts as heartbeats; README and `docs/NEXT.md` describe the state as it is.
One commit on `keystone/swarm-guardrails` (ea49334), pushed as pull request 23
(https://github.com/Diamond9k/orbit/pull/23): no unmerged work is deleted on a timer, cycles
leave begin and end state, aider calls time out, PROTECTED covers this record, the scoreboard
separates test money from hosts paid and opens the database read-only. Neither branch is
`build/`, so nothing merged itself. Cooper reviews.

**Evidence, by kind.**
- Code-supported and unit-tested: 41 tests pass on `keystone/first-session` (14 new), 26 on
  `keystone/swarm-guardrails` (2 new). GitHub Actions ran the same on both pushes and both
  pull requests: four runs, all green.
- Controlled test, Cooper's PC as both roles, a scripted user, dev test funds:
  `docs/evidence/2026-10-29-first-session-e2e.md`. Host ready 20.7 s after start. Two answers
  from the real model, 1.0 s each. Stop charged one minute, one cent: user -1, host +1,
  Orbit 0. Messages deleted. Model server stopped. Then the host program was stopped
  mid-session: Orbit ended the session as `host_lost` within the 30 s test timeout, charged
  one cent, marked the host offline, and the returning host program found nothing to run.
  Run once.
- Real people: still nothing. No stranger, no real money, no payout.

**Found while building.**
- The host's `last_seen` lagged by one held inbox request (about 20 s) in the run, so a lost
  host would be charged slightly less than its real last moment. Fixed in 349632c with a unit
  test. Not re-run end to end.
- The host program fails to bind if a model server is already on its port (a crash leftover).
  In `docs/NEXT.md` Later.
- The relay is unsealed: Orbit saw bodies in flight. The page says so. Sealing waits on
  question 2.
- The GitHub protection findings (question 3) are unchanged.

**Outside the repo.** 2026-10-29: cport-ad, a second Claude Code session working for Cooper,
rebuilt site-clone/own-site (localhost:5400) as a read-only operator console over `orbit.db`,
`docs/NEXT.md` and the swarm logs; site B reduced to a one-page launcher (localhost:5500).
Evidence: `C:\Users\cport\Downloads\arc\Agent-OS\site-clone\rea\2026-10-29\FINDINGS.md`.
Handoff: `C:\Users\cport\Downloads\arc\Agent-OS\outputs\2026-10-29-orbit-console-handoff.md`.
Outside the Orbit repo. Reported by cport-ad; Keystone checked that the files exist, not
what they say. That session also runs the app from a `main-ro` worktree on port 8000 against
the clone's `orbit.db`. Stop it before running this branch's app on that file: this branch
migrates the schema (old code ignores the new column and table), and two servers on one file
is one too many.

**Decisions still Cooper's.** Questions 1 to 7 above, unchanged. The two that block the next
step: the sealing cipher (question 2) and the GitHub ruleset fix (question 3). And: merge or
decline pull requests 22 and 23.

**Next meaningful step.** After review: seal the chat (Then item 5). Then a public https
address and a host program a stranger can install. Then a real payout path. The first real
session needs steps 5 to 7 of the birth-run path; nothing in this run reached them.

### 2026-10-29 (birth run)

**State found.** 23 tests pass on main (27 with pull request 21). GitHub Actions green on
every recent run. Scoreboard from `orbit.db`: hosts paid 10 cents (Cooper to Cooper, dev
funds), sessions 2, sessions by strangers 0, hosts listed 1 (Cooper's RX 580), users 1. No
swarm process, llama server or Orbit server running. The swarm's last cycle (22:15 on
2026-10-28) never wrote a result; the cycle before it (21:01) ended with the local builder
overflowing its 16k context after writing a handoff that described work it had not done.
Its branch has no commits. Pull request 21 (host program runs the model) is open, tests
green, waiting on Now item 1 and Cooper.

**Map: what the code supports.** Sign up and sign in. Hosts list a machine and get a token.
Heartbeat, ready and offline API. Exclusive sessions, charged by the minute from the moment
the host says ready, settled through the double-entry ledger on stop. Stripe checkout and
webhook in test mode. Model fit from the Hugging Face name. Host program: heartbeat (main),
and with pull request 21, starts llama.cpp for the chosen model and posts ready.

**Map: what a controlled test proves.** The full loop settles correctly in tests and once on
Cooper's PC with Cooper as both user and host (one cent moved). Stripe test card landed in
the ledger (recorded in `docs/BIRTH.md`; not re-verified by Keystone).

**Map: what real people have demonstrated.** Nothing yet. No stranger has used Orbit. No
host has been paid real money.

**Map: the path to the first real session, in dependency order.**
1. Heartbeat names the session so the host knows what to run (Now item 1). Small.
2. Host program runs the model and says ready (pull request 21). Done, unmerged.
3. A way for the user's words to reach the model and the answer to come back. Does not
   exist. The session page shows a placeholder. The host only dials out, so Orbit must relay.
4. Charges that stay correct when real things go wrong: time runs out mid-session, the host
   vanishes mid-session. Neither is handled; a session could run past a zero balance.
5. A public https address for Orbit, and a host program a stranger can install.
6. A real payout to the host, recorded in the ledger as money that left Orbit.
7. Only then: a real independent user and host, with Cooper's authorization.

**Biggest obstacles, ranked.** (3) no chat path; (4) billing under failure; (6) no payout;
(5) no public address; the swarm's own reliability (hung cycle, builder handoffs that are
not evidence, protections weaker than the docs say).

**Decided this run.** Keystone builds items 1, 3 and 4 on `keystone/first-session` as one
reviewable pull request, with the relay carrying opaque message bodies so sealing can be
added without changing Orbit's code. Swarm fixes go on a separate branch. Neither is
pushed to a `build/` branch, so nothing merges itself; Cooper reviews.

**Protection of this record.** `docs/KEYSTONE.md` is not in the swarm guard's PROTECTED
list, so a local builder could change it and a clean cycle would merge the change. Proposed
fix in `keystone/swarm-guardrails`: add `docs/KEYSTONE\.md` and `\.claude/` to PROTECTED in
`swarm/run.sh`. Until merged, the record is protected only by main's pull request rule.

**GitHub fix for Cooper (question 3), one command, reversible.** Replace the ruleset's
empty check list with the `tests` check:

```
gh api -X PUT repos/Diamond9k/orbit/rulesets/26085278 --input ruleset.json
```

where `ruleset.json` is the ruleset as it is today (`gh api repos/Diamond9k/orbit/rulesets/26085278`)
with `"required_status_checks": [{"context": "tests"}]` in place of the empty list.
