# ORBIT ULTRA RUN

One run, start to finish, for Claude Code with Fable 5.1 and Ultracode on Cooper's Windows PC.
This file wins wherever it differs from docs/PLAN.md or docs/PROMPTS.md.

## 0. Read first, in this order

CLAUDE.md, docs/PLAN.md, docs/MARKETPLACE.md, docs/SCORECARD.md, docs/GAUNTLET.md,
docs/SCAN-locallyuncensored.md, docs/GATES.md. Then start section 2 and section 3 at the same time.

## 1. Mission

Build Orbit as the pyramid in PLAN.md: L0 machine and accounts, L1 foundation, L2 engines (the
marketplace engine included), L3 surfaces, then L4 prepared in test mode. Prove it is better than
locallyuncensored.com on every dimension, then keep pushing past it.

- **Moon (required):** site 80+ on SCORECARD.md and 10/10 blind wins against LU; the app task table in
  GAUNTLET.md all green; every layer's exit checks pass.
- **Stars (push for it):** 95+. Once a dimension beats LU blind 3 rounds running, ratchet it: its bar becomes
  the best site in the world for that one dimension (propose 3, pick the hardest one that is fetchable, log
  why). Once a dimension scores 10 against its rubric, rewrite that dimension's 10 one level harder in
  SCORECARD.md and score again. That is how the cap gets beaten instead of touched. Measured stretch
  numbers: Lighthouse 100 in all four on every page, LCP under 1.2 s on a 4G phone, axe 0 issues of any
  level, install to first answer under 90 seconds.

Never lower a bar. Never call a number met that code or two blind critics did not prove.

## 2. The org chart

**Director** (this session). Owns the plan, the clock and the budget, merges lane branches, opens PRs, is
the only one who talks to Cooper (popups, short options, one recommended). Writes no product code.

**Managers**, one per layer (L1, L2, L3; the Director manages L0 itself). Managers write no product code.
Their job, like HR plus a foreman:
- split the layer into tasks and assign them to that layer's 10 workers, two or three per lane;
- check every worker every 20 minutes: progress, stuck, off-plan, or breaking a rule;
- reassign a stuck task after 2 failed tries; stop any worker that touches main, a secret, or LU's text or code;
- keep the lane task lists and `mission/status.json` current (section 3);
- run the layer's exit checks and hand the Director a signed-off summary, or a list of what is short.

**Workers**, 10 per layer, each in its own git worktree on `l<N>/<lane>-<n>`. They build only what their
manager assigned and report back. A worker never grades its own work.

**Critics**, a separate pool, never builders and never managers. Fresh context every time. They run every
gauntlet comparison and every layer audit. If Codex is available (section 5), every gauntlet round adds
one Codex critic as a second model family, and an audit only passes when a Claude critic and the Codex
critic both pass it.

**Side agent: Mission Control** (section 3). Runs the whole time beside everything else.

## 3. Mission Control (start this in minute one, in parallel with L0)

A side agent builds a small local status page and keeps it open for Cooper, so he can watch the run.

1. First, the login tabs. Open each in Cooper's default browser with `start <url>`, one at a time, and tell
   him in one line what each is for: github.com/login, vercel.com/login, supabase.com/dashboard,
   dashboard.stripe.com/login, discord.com/app, huggingface.co/settings/tokens, expo.dev/login,
   developer.apple.com/account. Then run the CLI logins that open the browser for him to approve:
   `gh auth login --web`, `vercel login`, `supabase login`, `stripe login`, `npx eas-cli login`. Never ask him
   to paste a password or key into the terminal or chat.
2. Then build `mission/` : a single-page dashboard served at http://localhost:4400 (a tiny Node server, no
   framework), reading `mission/status.json` every 5 seconds. It shows: the pyramid with each layer's state,
   the clock against the hard limit, usage against the budget, every manager and worker with its task and
   last check-in, the latest gauntlet scores per dimension against LU (moon and stars lines drawn), gates
   open and closed, and links to every PR and Vercel preview. Open it with `start http://localhost:4400`.
3. Keep it honest: a field with no data shows a dash and what it waits on. No sample data.
4. After L0 the Director has the side agent open the first Vercel preview (the ported landing page) in a
   tab. After every layer it opens that layer's PR and preview.

`mission/` is committed to the repo but never deployed.

## 4. Running the layers

- **L0** (Director plus the side agent, Cooper present): PLAN.md L0. Install missing tools with winget,
  asking before each. Create the repo, Vercel project, Supabase project, Stripe test mode, Discord server
  with Cooper. Cooper adds every key in the dashboards himself.
- **L1, L2, L3** (manager plus 10 workers each): exactly the lanes in PLAN.md section 4. Layers are
  sequential, lanes inside a layer are parallel. L1 designs the schema and protocol for everything,
  marketplace included (MARKETPLACE.md), and is frozen once merged; a change needs a new ADR and Cooper's yes.
- **L3** runs the gauntlet per GAUNTLET.md: blind, order swapped, fix only what failed. Max 4 rounds per
  target to reach the moon; after the moon, keep running stars rounds until the time or budget limit, a
  dimension stops moving for 3 rounds, or Cooper says stop.
- **L4 in this run:** build and test every L4 piece in test mode only. Stop before anything live: real
  charges, real payouts, App Store submission, public release. List those as Cooper's next steps.

**Branches and PRs.** Agents never push to `main`. Each layer is one PR to `main`, stacked: L2 branches from
L1's branch, L3 from L2's, so the run never waits on a merge. Cooper merges in order when he is ready.

**Layer gate.** The next layer starts only when the manager's exit checks pass AND an independent critic audit
passes. If either fails, follow PLAN.md section 5. A failing base is never built on.

## 5. Codex (optional second opinion)

At the start, run `codex --version`. If Codex is installed and logged in, use it only as a critic, never as a
builder: `codex exec "<critic prompt>"` with the screenshots or diff paths, read its JSON answer. If its help
lists an MCP server mode, you may register it instead. If Codex is not available, say so once and continue
with Claude critics only.

## 6. Hard limits (safe, but use them)

- **Wall clock:** 12 hours total. Budget per layer: L0 1.5 h, L1 3 h, L2 3 h, L3 4 h (gauntlet included),
  L4 prep 0.5 h. A layer that overruns by 50% stops and goes to Cooper.
- **Usage:** at 60% finish current tasks, at 80% start nothing new except closing the current layer, at 90%
  every worker commits, managers write handoffs, the Director writes
  `workspace/ORBIT/shared/outputs/<date>-handoff.md` and the resume line for the next session. Hard stop.
- **Circuit breaker:** the same failure 3 times in a row stops that lane and goes to Cooper.
- **Never, at any point:** push to main, read `.env*`, paste or print a secret, spend money, publish, submit to
  Apple, copy LU's text, code, images or layout, or put a made-up number on any page.

## 7. Talking to Cooper

Popups only for what is truly his: installs, accounts, money, anything public or irreversible, a bar or plan
change. One recommended option first. If he does not answer within 15 minutes, keep working on everything
that does not depend on the answer, and leave the question open in Mission Control. Short updates only at
layer boundaries: what passed, the scores, the PR link, what is waiting on him. No em dashes anywhere.

## 8. Done

Report: per layer, exit checks with evidence; the site's scores per dimension (LU, Orbit, the ratcheted
bars); the app task table with measured times; open gates; the stacked PR links; the L4 live steps waiting
on Cooper.
