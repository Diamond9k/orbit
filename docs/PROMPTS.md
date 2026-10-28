# How to send this: one prompt per layer

Five prompts, one per layer, each in a **new** Claude Code session on the Windows PC, run from the
`orbit` folder, with Fable 5.1 and Ultracode on. A new session per layer keeps the context clean; the
repo (PLAN, ADRs, handoff files) is the memory between them.

Do not send the next prompt until the last layer's PR is merged. That merge is your "the foundation
works" check. Two extra prompts cover running out of usage mid-layer and reviewing a layer.

| Send | When | You need to be there? | Roughly |
|---|---|---|---|
| P0 Machine and accounts | first | yes, the whole time (installs and sign-ups) | 1 to 2 hours |
| P1 Foundation | after P0's PR is merged | only for popups | one long Ultracode run |
| P2 Engines | after P1 is merged | for popups and the iPhone test | one long run |
| P3 Surfaces | after P2 is merged, G2 and G7 closed | for popups and gauntlet overrules | one long run |
| P4 Real money and launch | after P3 is merged, G4 live, G5, G6, G8 closed | yes, every money step | several short sessions |

---

## P0: Machine and accounts

Before sending: clone the repo with `git clone https://github.com/Diamond9k/orbit`, open a terminal in the
`orbit` folder, start Claude Code.

```
You are starting Orbit. Read CLAUDE.md, then docs/PLAN.md, docs/MARKETPLACE.md and docs/GATES.md.

Run Layer L0 from PLAN.md section 4, and only L0.

1. Inventory this PC exactly as L0 step 1 lists and write the result to
   workspace/ORBIT/shared/outputs/<today>-machine.md. Run each tool's version command; mark missing ones.
2. For each missing tool, ask me with a popup before installing. Install with winget where possible.
3. Walk me through creating the public GitHub repo Diamond9k/orbit, branch protection on main,
   Discussions on, the Vercel project "orbit" on my own account (not the ARC team), the Supabase project
   "orbit", a Stripe account in test mode, and the Discord server with the channel list in PLAN.md.
   Do the parts the CLIs can do after I log in. Never ask me to paste a key into chat: tell me which
   dashboard and which setting name, and I will add it.
4. Commit the L0 outputs on a branch, open a PR, and check the Vercel preview builds.
5. Update docs/GATES.md with what closed and the evidence. Write the handoff file.

Stop when L0's exit checks pass. Do not start L1.
```

## P1: Foundation

```
Read CLAUDE.md, docs/PLAN.md, docs/MARKETPLACE.md, docs/GAUNTLET.md, docs/GATES.md, every ADR,
and the newest handoff in workspace/ORBIT/shared/outputs/.

Run Layer L1 from PLAN.md section 4, and only L1.

Use Ultracode: run lanes A to E in parallel, one agent per lane, each in its own git worktree on a
branch named l1/<lane>. You are the lead: hand each lane its section of PLAN.md and MARKETPLACE.md,
merge finished lanes into the branch l1/foundation, resolve conflicts, and keep a task list per lane.

Lane B (data) designs the schema for every later feature now, the whole marketplace included, so no
later layer has to change it. Lane A copies only the named operating pieces from github.com/Diamond9k/Arc-OS
and nothing else from Arc.

When all lanes are merged: run L1's exit checks, then a whole-layer audit by a fresh subagent that did
not build anything, fix what it finds, open the PR to main, update GATES.md, write the handoff.
Popups for any decision. Stop after L1.
```

## P2: Engines

```
Read CLAUDE.md, docs/PLAN.md, docs/MARKETPLACE.md, docs/GAUNTLET.md, docs/GATES.md, every ADR,
and the newest handoff.

Run Layer L2 from PLAN.md section 4, and only L2.

Ultracode: lanes A to D in parallel, one agent per lane, worktrees on l2/<lane>, you merge into
l2/engines. Every lane builds only on what L1 merged. If a lane believes the L1 schema or protocol must
change, it stops and you ask me; that needs a new ADR (pyramid rule, ADR 0006).

Lane C builds the whole marketplace engine from MARKETPLACE.md against the simulated host from L1,
with a test for every state change, every ledger posting, refunds, payouts and reconciliation.

Exit checks are measured, not assumed: use a clean Windows VM for the install timing and tell me when
you need me to run the iPhone test. Then the fresh-critic audit, PR, GATES.md, handoff. Stop after L2.
```

## P3: Surfaces

```
Read CLAUDE.md, docs/PLAN.md, docs/MARKETPLACE.md, docs/SCORECARD.md, docs/GAUNTLET.md,
docs/SCAN-locallyuncensored.md, docs/GATES.md, every ADR, and the newest handoff.

Run Layer L3 from PLAN.md section 4, and only L3.

First, before building: run the Playwright, Lighthouse and axe pass on locallyuncensored.com, replace
the two provisional scores in SCORECARD.md with measured ones, delete the captures, and lock your
predicted scores for our site in an outputs file.

Ultracode: lanes A to D in parallel, worktrees on l3/<lane>, merged into l3/surfaces. Load the
frontend-design skill for lanes A, B and C.

Then the gauntlet on the site exactly as GAUNTLET.md says: you build, fresh subagents judge blind,
order swapped, fix only what failed, max 4 rounds per target. Targets from SCORECARD.md: 64, then 72,
then 80 with 10/10 blind wins. If a target is missed, follow PLAN.md section 5. Never lower the bar.

Then the fresh-critic audit, PR, GATES.md, handoff with before and after scores per dimension.
Stop after L3.
```

## P4: Real money and launch

Send once per step, in order, so every money step gets your full attention.

```
Read CLAUDE.md, docs/PLAN.md, docs/MARKETPLACE.md, docs/GATES.md, every ADR, and the newest handoff.

Run Layer L4 step <N> from PLAN.md section 4, and only that step. Anything that moves real money,
publishes, or submits to Apple: show me exactly what will happen and wait for my yes. Then PR,
GATES.md, handoff.
```

---

## If a session runs out of usage mid-layer

```
Read CLAUDE.md, docs/PLAN.md and the newest handoff in workspace/ORBIT/shared/outputs/.
Resume Layer L<N> where the handoff says it stopped. Check each lane's worktree and branch state
before doing anything. Do not redo merged work.
```

## Optional: review a layer before you merge it

```
You did not build this. Read docs/PLAN.md and review the open PR for Layer L<N> against that layer's
exit checks and the pyramid rule. Run every check yourself. Report PASS or FAIL per exit check with the
evidence, and the single most important fix. Change nothing.
```
