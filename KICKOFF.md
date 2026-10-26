# Kickoff: paste this into Claude Code on the Windows PC

Before pasting: unzip this kit into an empty folder named `orbit` in your projects folder, open a
terminal there, and start Claude Code with Fable 5.1 and Ultracode on.

---

You are building Orbit from an empty repo. Everything you need is in this folder.

Read, in this order, before doing anything: `CLAUDE.md`, `docs/PLAN.md`, `docs/SCORECARD.md`,
`docs/GAUNTLET.md`, `docs/SCAN-locallyuncensored.md`, `docs/GATES.md`.

Then run **V1 only**, chunk by chunk, exactly as PLAN.md section 4 describes. Do not start V2.

How to run it:
- Make a task list from V1's 14 steps and keep it current.
- Copy the operating pieces PLAN.md section 1 names from the Arc-OS repo (github.com/Diamond9k/Arc-OS):
  CI workflow, biome.json, tsconfig.json, recall.mjs and its lib, run-record.mjs, the PR template.
  Rename ARC to ORBIT. Copy nothing else from Arc: no keys, memory, skills or data.
- Anything that needs my account (creating the GitHub repo, the Vercel project, the Supabase project,
  branch protection, the Discord server, buying anything): stop, ask me with a popup, and wait.
- Step 8 before step 9: lock your V1 score predictions in a file before you build.
- Run the gauntlet in docs/GAUNTLET.md with fresh subagents as critics. You build; you never grade
  your own work. Max 4 rounds. Fix only what failed each round.
- If V1 misses 64 / 100 or 5 blind wins after 4 rounds, follow PLAN.md section 5. Do not lower the bar.
- Pace usage: at 60% finish the round, at 80% start nothing new, at 95% commit and write the handoff.
- No em dashes in anything you write (site copy, docs, commits).

When V1's exit checks all pass: run a whole-repo audit, open the PR, and give me a short summary with
the before and after scores per dimension, the blind wins, and what is waiting on me in GATES.md.
