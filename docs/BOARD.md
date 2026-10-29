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

## Services on this PC (2026-10-29, verified by port)

| Port | What | Owner | Touch? |
|---|---|---|---|
| 8000 | Orbit app, pre-sealing code (worktree `main-ro` at 5eb4994) on Cooper's dev database | peer session | no |
| 5400 | Operator console (separate project) | peer session | no |
| 5500 | Launcher (separate project) | peer session | no |
| 8080 | llama.cpp serving Qwen2.5-Coder-14B Q4_K_M on the RX 580 (4.8 GB of 8 GB) | peer session's background job | no; may stop when that session ends |
| 9222 | Headless Chromium (REA capture) | peer session | no |
| 8020, 8030 | Fleet test instances, isolated databases | T1, T3 | theirs |

The swarm (`swarm/forever.sh`) is idle. Keystone does not start or stop it.

## Tasks

| Id | Task | Owner | Branch / worktree | Acceptance | Status | Evidence |
|---|---|---|---|---|---|---|
| T0 | Record, board, path map, pull requests, integration | Keystone | `keystone/fleet` in `orbit` | record entry pushed; this board true; PRs open with evidence | running | `docs/KEYSTONE.md` |
| T1 | Whole-product visual design: tokens, icon rail, purple accent, depth, motion, logo at 16/24/32, every page and state, explicit consent before sending unsealed | fleet agent (Claude) | `keystone/ui` in `keystone-ui` | tests green; screenshots at 320/390/1280 with measured zero overflow; contrast numbers; keyboard and reduced motion; no new deps; honest copy intact | running | `docs/evidence/2026-10-29-ui-overhaul.md`, `docs/evidence/ui/2026-10-29/` |
| T2 | Protected-compute research: authenticated transport and code delivery, attested CPU+GPU, Bifrost/Maverick/FHE; licenses, hardware, measured vs projected | fleet agent (Claude) | `keystone/privacy-boundary` in `keystone-privacy-boundary` | every claim sourced and dated; comparison table; proposal for Cooper; unknowns listed | running | `docs/evidence/2026-10-29-privacy-research.md` |
| T3 | Adversary tests against the real sealing code; host no longer answers plaintext after sealing | fleet agent (Claude) | `keystone/seal-adversary` in `keystone-seal-adversary` | tests for each adversary action, gaps named `known_gap`; host downgrade closed and tested; evidence table | running | `docs/evidence/2026-10-29-seal-adversary.md` |
| T4 | Open-source UI tooling evaluation (impeccable, frontend-design, Playwright, axe-core, alternatives) | fleet agent (Claude) | none (report only) | licenses from LICENSE files; local-first; smallest useful set in tiers | running | `docs/research/2026-10-29-ui-tools.md` once filed |
| T5 | Independent critic per gauntlet (T1, T3) | fleet agent (Claude), not the builder | reads the branch | reads diff and evidence; attempts the adversary actions; pass/fail against the written checks | waiting on T1, T3 | critic notes in the pull request |

## For Cooper

- Delete the merged and superseded branches (the classifier blocks Keystone from doing it):
  `git push origin --delete claude/epic-franklin-0a24a1 claude/project-thread-fppic6 claude/project-thread-raxl3o claude/zen-ride-rbvl70 review/2026-10-28-1717 review/2026-10-28-1735 review/2026-10-28-1856 review/2026-10-28-1923 escalate/2026-10-28-1856 escalate/2026-10-28-1947 keystone/first-session keystone/protected-compute keystone/swarm-guardrails`
  and locally `git -C C:\Users\cport\orbit\orbit worktree remove ..\keystone-swarm`.
- Port 8000 serves code from before the sealed chat. Restarting it on main is the peer session's
  call or yours; two app versions must not share `orbit.db`.
- Ruleset 26085278 on `main` still requires no status check and no review; a push from an
  account with write access could land on main. Keystone's question 3 in `docs/KEYSTONE.md`.
