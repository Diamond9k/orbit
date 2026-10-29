# The board

Durable task state for Keystone's fleet. Lives in the repository so that it survives a crashed
session, a closed window and a model that forgets. Conversation memory is not state; this file,
`docs/KEYSTONE.md`, the branches on origin and the pull request pages are.

## How it works

- A task gets one owner, one branch, one worktree, acceptance checks written before the build,
  and a budget. The owner commits as it goes and pushes the branch when done. Branches only.
- Done means: the branch's pull request merged under the repository's rules, with the checks run
  on the exact merged revision. A branch name proves nothing; the pull request page and the
  workflow run do.
- A critic who did not build it reads the actual diff and evidence before anything merges.
  "Nothing found" from a model is not evidence. Revalidate after any repair.
- Retries are bounded: two failed gauntlets on one task and it is escalated to Cooper here, with
  the reasons, instead of a third attempt.
- Nothing unmerged is deleted on a timer. A stale branch is listed under "For Cooper" with the
  command; Cooper deletes.
- Model choice, Cooper's rule (2026-10-29): first ask whether the work needs a model at all
  (tests, screenshots, overflow and contrast checks are scripts); then whether an open model on
  Cooper's own PC can do it for nothing (the local llama.cpp, the swarm); then a cheaper Claude
  model; Fable last, for judgement-critical work, one at a time and announced with its cost. Every
  Claude agent draws on the same plan limits as Cooper's own sessions.
- Stop: Cooper's word, or a file named `workspace/STOP`, means no new task is assigned; running
  owners finish the step they are on, commit, push, and report.
- Recovery after a crash: read this file, `docs/KEYSTONE.md`, `git worktree list`,
  `git branch -r`, the open pull requests and the listening ports. A task whose branch has
  commits and whose owner is gone is orphaned: a new owner resumes from the branch; nobody starts
  it again from scratch. Never run two app versions against one database; test data is isolated
  (`ORBIT_DB` under a scratch folder, dev funds, a port nobody else holds).
- Duplicate work, billing and payouts after a retry are prevented by the code, not the board:
  session charges are idempotent (`post_session_charge`, `sweep`), Stripe credits key on the
  event id, and the payout path, when built, must key on a `payout:<id>` memo the same way.

## Services on this PC (2026-10-29 16:35, verified by port)

| Port | What | Owner | State at 16:35 |
|---|---|---|---|
| 8000 | Orbit app, pre-sealing code (worktree `main-ro` at 5eb4994) on Cooper's dev database | peer session | not listening; the peer session is gone |
| 5400 | Operator console (separate project) | peer session | not listening |
| 5500 | Launcher (separate project) | peer session | not listening |
| 8080 | llama.cpp serving Qwen2.5-Coder-14B Q4_K_M on the RX 580 | whoever starts it | not listening; Keystone asks Cooper before starting it (`docs/FLEET.md`); command in `docs/SWARM.md` |
| 9222 | Headless Chromium (REA capture) | peer session | not listening |
| 8020, 8030 | Fleet test instances, isolated databases | T1, T3 | free |

The swarm (`swarm/forever.sh`) is idle. Keystone does not start or stop it. The GPU held about
1 GB of its 8 at 16:35 (desktop), 20.7 GB of RAM free.

## Tasks

| Id | Task | Owner | Branch / worktree | Acceptance | Status | Evidence |
|---|---|---|---|---|---|---|
| T0 | Record, board, path map, pull requests, integration | Keystone | `keystone/fourth-run` in `orbit` | record entry pushed; this board true; PRs open with evidence | running; fourth run woken by Cooper 16:35; `docs/FLEET.md` merged (PR 25) | `docs/KEYSTONE.md` |
| T6 | The fleet ledger tool, `swarm/ledger.py`, from tests written first | local 14B via aider | `local/ledger` in `local-ledger` | `tests/test_ledger.py` green; only the named file changed; under 80 lines | done 04:18, accepted; PR 27 | `docs/evidence/fleet-ledger.md` |
| T7 | The host program adopts or stops a model server left by a crash: `host/adopt.py` (worker) and the `Runner` wiring (director) | local 14B via `swarm/local_task.py`; Keystone wires | `local/host-adopt` in `local-host-adopt` | `tests/test_adopt.py` (13) and the five T7 tests in `tests/test_host.py` green; only the named files changed; module under 130 lines; two attempts at most | spec committed 16:48 (b2d4a9d); waits for the model server on 8080 | `docs/evidence/2026-10-29-T7-host-adopt.md` |
| T1 | Whole-product visual design: tokens, icon rail, purple accent, depth, motion, logo at 16/24/32, every page and state, explicit consent before sending unsealed | fleet agent (Claude) | `keystone/ui` in `keystone-ui` | tests green; screenshots at 320/390/1280 with measured zero overflow; contrast numbers; keyboard and reduced motion; no new deps; honest copy intact | paused by Cooper 04:05; WIP f9b423a pushed, not reviewed | `docs/evidence/2026-10-29-ui-overhaul.md`, `docs/evidence/ui/2026-10-29/` |
| T2 | Protected-compute research: authenticated transport and code delivery, attested CPU+GPU, Bifrost/Maverick/FHE; licenses, hardware, measured vs projected | fleet agent (Claude) | `keystone/privacy-boundary` in `keystone-privacy-boundary` | every claim sourced and dated; comparison table; proposal for Cooper; unknowns listed | not started: stopped 04:03 (Fable) and 04:05 (Sonnet, at the pause) | `docs/evidence/2026-10-29-privacy-research.md` |
| T3 | Adversary tests against the real sealing code; host no longer answers plaintext after sealing | fleet agent (Claude) | `keystone/seal-adversary` in `keystone-seal-adversary` | tests for each adversary action, gaps named `known_gap`; host downgrade closed and tested; evidence table | done 04:04, 69 tests; Keystone's review pending | `docs/evidence/2026-10-29-seal-adversary.md` |
| T4 | Open-source UI tooling evaluation (impeccable, frontend-design, Playwright, axe-core, alternatives) | fleet agent (Claude) | none (report only) | licenses from LICENSE files; local-first; smallest useful set in tiers | done 04:15; Cooper decides on tier (b) | `docs/research/2026-10-29-ui-tools.md` |
| T5 | Independent critic per gauntlet (T1, T3) | Keystone in-context (no agent, Cooper's rule) | reads the branch | reads diff and evidence; attempts the adversary actions; pass/fail against the written checks | T3 first | critic notes in the pull request |

## For Cooper

- Delete the merged and superseded branches (the classifier blocks Keystone from doing it):
  `git push origin --delete claude/epic-franklin-0a24a1 claude/project-thread-fppic6 claude/project-thread-raxl3o claude/zen-ride-rbvl70 review/2026-10-28-1717 review/2026-10-28-1735 review/2026-10-28-1856 review/2026-10-28-1923 escalate/2026-10-28-1856 escalate/2026-10-28-1947 keystone/first-session keystone/protected-compute keystone/swarm-guardrails`
  and locally `git -C C:\Users\cport\orbit\orbit worktree remove ..\keystone-swarm`.
- Port 8000 serves code from before the sealed chat. Restarting it on main is the peer session's
  call or yours; two app versions must not share `orbit.db`.
- Ruleset 26085278 on `main` still requires no status check and no review; a push from an
  account with write access could land on main. Keystone's question 3 in `docs/KEYSTONE.md`.
- The model server on 8080 is down (16:35). T7 and every later local task need it. Say yes and
  Keystone starts it in its own window with the `docs/SWARM.md` command; or start it yourself.
- Pull request 26 (sealing: adversary tests, no silent downgrade, nonce-reuse fix) was merged
  without the independent second review its description asked for. Choose: Codex, one announced
  Claude agent (Opus or Fable, as a security judgement), or none.
