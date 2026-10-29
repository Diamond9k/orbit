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

### 2026-10-29 16:35 CDT (UTC-05:00) (fourth run: woken by Cooper's message)

**Wake.** Cooper's message in the terminal chat, "wake up keystone", read at 16:35 by this PC's
clock, twelve hours after the sign-off. A new session, as the record intends; nothing of
Keystone's ran in between.

**What Cooper decided while Keystone slept, read from GitHub.** Pull requests 25, 26 and 27 were
merged at 04:28 (33d6ee2, 7644de5, f7996dc; no comments and no reviews on their pages). So
`docs/FLEET.md` is on main (the revised setup, accepted by merge); pull request 26 is on main
without the independent second review its description asked for; the fleet ledger tool and its
driver are on main. Main is f7996dc and its 78 tests pass on this PC (16:40). Still open: who gives
the sealing changes their second review, now a review after the merge; the paused UI branch; the
privacy research; the thirteen stale branches, still on origin at 16:35.

**Ground truth at 16:35, by port and process.** Nothing listens on 8000, 5400, 5500, 8080 or 9222:
the peer session's app, console, launcher and headless browser and the model server are all gone
(no process; not a crash of Keystone's). The GPU holds about 1 GB of its 8 for the desktop and
20.7 GB of RAM is free, so the model server could run; `docs/FLEET.md` says Keystone asks Cooper
before starting one, so it has not been started. All seven worktrees are clean. Three node
processes belong to other tools (two `server.js`, one Codex runtime); not touched.

**What changed this run.** Worktree `local-host-adopt`, branch `local/host-adopt` from main: the
spec for T7, the host program adopting or stopping a model server left by a crash (`docs/NEXT.md`
Later; the first thing the host program must do before it ships as an app,
`docs/decisions/2026-10-29-host-program-as-an-app.md`). Tests first, committed at 16:48 (b2d4a9d):
thirteen in `tests/test_adopt.py` for the worker's new module `host/adopt.py`, five at the end of
`tests/test_host.py` for the director's wiring, `tests/conftest.py` keeping the pid file out of the
repository, the prompt saved with the run and verbatim in `docs/evidence/2026-10-29-T7-host-adopt.md`.
The worker is the local 14B through `swarm/local_task.py`, as in T6; the split (a new module under
130 lines for the worker, about twenty lines of wiring for the director) follows T6's measured rate
of about three minutes per seventy lines. The branch is red until the module exists (two test files
import it) and is not pushed. Branch `keystone/fourth-run` in the nested clone: this entry, the
board, the ledger.

**Found while writing the spec, not fixed.** `model_server_up` trusts any server that answers
health on the port, so a stranger's server there could mark the host ready for a model it does not
run. Written in the T7 evidence file; goes to `docs/NEXT.md` Later with the T7 pull request.

**Evidence, by kind.** Code-supported: 78 tests on main on this PC; the T7 tests exist, their
module does not yet. Controlled: nothing new. Real people: none.

**Decisions now Cooper's.** (1) Start the model server for the local worker, yes or no; Keystone
can start it in its own window with the `docs/SWARM.md` command so it outlives this session.
(2) The second review of pull request 26, now merged: Codex, one announced Claude agent (Opus or
Fable; it is a security judgement), or none. (3) The paused UI branch and the privacy research,
unchanged from the 04:50 entry. (4) The thirteen stale branches: the command in `docs/BOARD.md`.

**Next meaningful step.** On the first yes: run T7 on the local model, wire it, push, open the pull
request. Then the host program as an app (option A, Windows; needs decisions 1 and 4 of its proposal).

### 2026-10-29 04:50 CDT (UTC-05:00) (same session: the pause, Cooper's correction, the fleet revised)

**Cooper's correction, 04:05, verbatim where it binds.** "Pause the current fleet and preserve all
work already completed. Do not delete branches, reset worktrees, or stop the local model server."
"Local open-source models on my own hardware are the default for daily work. Before launching any
Claude subagent, ask: can a local model do this task to an acceptable standard? If we don't know,
run a small, bounded test and measure the result. Do not launch parallel paid or plan-usage Claude
agents by default. Use one only when local work has failed, the task requires capabilities we
cannot reasonably verify locally, or independent review is needed for sensitive work. Tell me what
it will do and why it is worth the usage before starting it." "Redesign the fleet around one
director, local workers, bounded attempts, and independent checks. Test one local task before
scaling up. Track useful work completed, failures, time, and Claude usage." "Do not restart the
fleet until you have shown me the revised setup." Minutes earlier: "I want to always first think
'can we run the ai model that needs to be ran for the desired outcome using open source models on
personal compute for zero cost'".

**What Keystone had done wrong.** Launched four Fable 5.1 agents in parallel at 03:50, each with a
budget of one to two hours, on Cooper's shared plan limits, and said which model only in the
record, not in chat. Measured usage before the pause: T3 154,524 tokens, T4 151,965; T1 and T2
unmeasured (killed).

**The pause, 04:05.** All agents stopped; nothing deleted; the model server untouched. T1's
unfinished UI work saved as a WIP commit (`f9b423a`, `keystone/ui`, 11 files, tests pass, not
reviewed). T2 had produced nothing on either model. T4's report filed on `keystone/fleet`. T3 done.

**T3 reviewed by the director, and widened.** The builder's nonce finding was correct and larger
than it said: `accept()` reset the counters on any repeated hello, so the ordinary page reload
(key pair restored, log replayed, hello re-sent) made the host reuse an AES-GCM nonce and refuse
the next message. Fixed on both ends with no wire change: a hello with the current peer key is a
no-op, a key from an earlier epoch is refused; a reload is now played end to end by the real
`seal.js` under Node. Pull request 26, 73 tests. It waits for an independent second review, as
Cooper's rule asks for security changes.

**The fleet, revised.** `docs/FLEET.md`: one director (this session, not always on); local workers
(the 14B through llama.cpp, one slot) for small tasks with named files and tests written first;
scripts for everything that needs no model; a stronger model last, one at a time, announced, with
its usage recorded. Bounded attempts: one build, one fix, time-boxed, then escalation. Checks the
builder does not control: tests here and on GitHub, a scope check, the local critic, the
director's read; a stronger-model review for money, sessions and the host program. Tracking:
`docs/evidence/fleet-ledger.md`, one row per piece of work, summed per worker by `swarm/ledger.py`.

**A limit met.** This session's permission classifier refuses to launch aider with `--yes-always`
("Create Unsafe Agents"), so the director cannot start the swarm's own loop. Instead the director
drives the local model through plain chat calls: spec and tests first, the model answers with one
complete file, the director writes it and runs the tests, two attempts at most. That is the first
bounded test (T6, the ledger tool). Result at 04:18: accepted; the 14B wrote the 72-line tool
from the tests in 196 s at no cost, and the one failing test was the director's own mistake,
corrected; pull request 27. Driver: `swarm/local_task.py`.

**Evidence, by kind.** Code-supported: 73 tests on `keystone/seal-adversary`, 56 on
`keystone/fleet`, 53 on the paused `keystone/ui`. Controlled: nothing new. Real people: none.

**Decisions now Cooper's.** Approve or amend the revised setup before anything restarts. Who gives
pull request 26 its second review. What becomes of the paused UI branch: resume page by page with
the local worker under the director's eye, or one announced Claude agent. Whether the privacy
research is done by the director in pieces. Merge or send back pull request 25.

**Next meaningful step.** After Cooper's go: local tasks one at a time through the ladder, the
host-as-an-app build first.

**Sign-off, 04:35.** Cooper: "save this going to sleep I will message Keystone in claude terminal chat
when the agent should arise". Everything above is pushed; the fleet stays paused; no process of
Keystone's runs. Keystone does nothing until Cooper's message, then starts from the decisions list.

### 2026-10-29 03:45 CDT (UTC-05:00) (third run: crash recovery, the merges, the fleet)

**What happened between runs.** Cooper merged pull requests 22, 23 and 24 himself; main is
`785d9eb` and its 53 tests pass on this PC. The session that wrote the previous entry then
died: Cooper's screenshot of 03:15 shows the Claude Code runtime (Bun 1.4.4) reporting a
segmentation fault. Nothing was mid-write, no agent was running, no work was lost. This entry is
written by a new session that recovered its context from this record, the repository and the
ports, as the record intends.

**Cooper's direction, received this run.** First: "Your previous session crashed. Before
continuing, inspect your saved session context, docs/KEYSTONE.md, the current branch and
worktrees, uncommitted changes, and any agent work already running. Tell me what was completed,
what was interrupted, and what you will resume. Preserve all existing work; do not start
duplicate agents or stop other services." Then an expanded operating prompt (prepared by Codex
for Cooper) that widens Keystone's charge to a coordinated fleet, a durable task board, the
privacy workstream and the whole product's visual design. Its binding lines, verbatim: "A sealed
relay does not by itself protect inference from the host. Do not redefine the goal as asking
users to trust an ordinary host." "Do not silently downgrade a requested protected session to
plaintext or an unverified mode." "Never state that an active broker or hardware owner cannot
read messages unless the required defenses are actually present and independently verified."
"Do not present prototype encryption as protection from the hardware owner." "Do not expose
secrets, perform unattended destructive cleanup, or silently push into an auto-merge path." "Do
not pretend this prompt alone creates an always-on agent fleet." On design: a compact vertical
icon rail like the Codex app, purposeful motion with honest indeterminate states and never a
fabricated percentage, subtle beveled depth, a configurable purple accent with a functional
role and contrast, a simple open orbital mark and node refined at 16, 24 and 32 px, tokens as
CSS custom properties, reduced-motion alternatives, every state designed, no fake values.

**Ground truth, verified by port and counter at 03:30.** Port 8000: the peer session's Orbit
app from worktree `main-ro` at `5eb4994`, code from before the sealed chat, on Cooper's dev
database; not touched. Ports 5400 and 5500: the peer's console and launcher, separate projects;
not touched. Port 8080: llama.cpp serving Qwen2.5-Coder-14B Q4_K_M, healthy, holding 4.8 GB of
the RX 580's 8 GB, a background job of the peer session that may stop when it does. Port 9222:
the peer's headless Chromium. The swarm is idle; Keystone neither starts nor stops it. Ruleset
26085278 on main still requires no status check and no review (question 3). REA is not
available to this session; the Codex desktop app is installed (Appx 26.1023.6123.0) and its
files were not opened (rule 8); Cooper's screenshot of 03:03 is the only evidence of the rail
he likes, and only its visible qualities were used.

**What changed this run, so far.** Branch `keystone/fleet`: this entry; `docs/BOARD.md`, the
durable task board (ownership, acceptance checks, bounded retries, stop, recovery after a
crash, what the code and not the board prevents); `docs/PATH.md`, the path from browser to
payout with the grade of evidence per step and the obstacles ranked. Four tasks assigned to
Claude agents in isolated worktrees branched from main, each with written acceptance checks and
a budget, none touching the running services: T1 the visual design on `keystone/ui` (including
explicit consent before a page sends unsealed), T2 protected-compute research on
`keystone/privacy-boundary` (transport binding and code delivery, attested CPU and GPU,
Bifrost, Maverick, FHE; licenses, hardware, measured versus projected), T3 adversary tests
against the real sealing code on `keystone/seal-adversary` (and the host program no longer
answering plaintext once sealed), T4 an evaluation of open-source UI tooling, report only. T5,
an independent critic for T1 and T3, waits on them. Local open models were not used for these:
the 14B coder is adequate for small scoped edits (the swarm's job) and not for design or
security judgement; no paid API call was made.

**Evidence, by kind.** Code-supported: main's tests, plus three interruption tests in
`tests/test_recovery.py` (a restarted host program does not restart the clock, a restarted Orbit
keeps the running session and its messages, a repeated stop bills once); 56 pass. A mistake,
repaired: that file run on its own used the default database, so a synthetic user and machine
landed in Cooper's dev `orbit.db` at 03:50 for a few minutes; both rows were listed and removed,
nothing else was touched, and `tests/conftest.py` now pins every test to the throwaway database.
`docs/decisions/2026-10-29-host-program-as-an-app.md` proposes how the host program ships
(llama.cpp is MIT; its Windows Vulkan build is 37 MB). Controlled: nothing new yet this run.
Real people: none. Everything above about the fleet is assignment, not result; results go in
the next entry with the pull request numbers.

**Decisions now Cooper's.** Delete the thirteen merged or superseded branches
(`docs/BOARD.md`, For Cooper). Whether port 8000 should move to main's code. Question 3, the
ruleset. The verified tier, a public address and payouts remain the three decisions that gate
steps 8 to 10 of `docs/PATH.md`.

**Lessons from Cooper's library opened for this run:** n52 (Impeccable), Module F3 (a design
system as reusable tokens and components), j6 (thirty single-file design systems, as taste
references), b24 (the official design skill); F4 (UI sniping) not used, rule 8.

**Next meaningful step.** Critique and integrate the four branches through pull requests; then
the host program that installs like an app, the first obstacle on `docs/PATH.md`.

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
