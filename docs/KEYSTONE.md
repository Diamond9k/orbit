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
2. **Sealing the chat.** Rule 1 needs a cipher in the host program. The host program is
   standard library only, and the standard library has no authenticated cipher or key
   exchange. Options: add one proven library (PyNaCl or cryptography) to the host program and
   package it with the app, or keep the relay unsealed and say so. Keystone's recommendation:
   add the library. Until decided, the relay carries plain text and the page says so.
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

## Continuity log

Newest first. Each entry: date, what changed, evidence, what is next.

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
