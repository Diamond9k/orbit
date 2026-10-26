# The gauntlet loop (Orbit)

Same loop as Arc OS Studio (docs/studio/v2/GAUNTLET.md in Arc-OS), rebuilt for a website and an app.
Builder makes, a separate blind critic judges, code shuffles, Cooper overrules. A builder never grades
its own work: that is the named failure this loop exists to prevent.

## Roles

- **Builder**: the main Claude Code session. Sees the plan, the gap notes, our code. Never sees the
  bar's screenshots, never copies its text, code or media.
- **Critic**: a fresh subagent per comparison, with no history. Gets two screenshot sets labelled A and B,
  the rubric (SCORECARD.md dimensions) and the measured floor results. Never told which is ours, the round,
  the prompt or the model.
- **Shuffler**: `scripts/gauntlet-shuffle.mjs`. The only thing that knows the A/B mapping. Writes it to the
  round record only after the verdict.
- **Cooper**: sees the revealed pair after the verdict, may overrule, approves anything that changes the plan.

## One round

1. **Floor first (code, no opinions).** Run `npm run floor`: Lighthouse on mobile and desktop for every page,
   axe, broken links, console errors, the facts check (every number on the site exists in `src/facts.json`
   with a source), copy reading level. A floor failure loses the round before any critic looks.
2. **Screenshots.** Playwright captures every page at 390, 768 and 1440 px, light and dark, above the fold
   and full page. Same captures of the bar, fetched at run time, deleted when the round ends.
3. **5-second test, blind and first.** A critic sees only the 390 px and 1440 px above-the-fold shots of A,
   for the length of one read, and writes one sentence: what it is, who for, what to do next. Then the same
   for B. The criteria file is NOT in this message (Arc lesson: the criteria arriving with the image
   contaminated the blind read).
4. **Side by side, twice.** Two fresh critics, order swapped. Each returns, per dimension:
   `{"dim":"D1","pick":"A|B","score_A":0-10,"score_B":0-10,"confidence":0.0,"evidence":"<one measurement or quote>","gap":"<the one thing the loser must change>"}`
5. **Reduce (code).** A dimension is a win only if both critics picked ours. One each is undecided. Record
   the lower score per dimension. Confidence under 0.6 on any row goes to Cooper.
6. **Issue list.** Ranked, max 6 per round, plus one "most important fix" even if everything passed.
7. **Fix only what failed.** The builder fixes the listed gaps and nothing else, then the next round starts at 1.

## Caps and stops

- Max 4 rounds per version step. A step that misses its target after 4 rounds stops and reports (PLAN.md,
  "When a version misses").
- Circuit breaker: the same item failing 3 rounds running stops the loop and goes to Cooper. It is a plan
  problem, not a build problem.
- Usage: at 60% of the session budget, finish the current round and write the round record. At 80%, no new
  round starts. At 95%, commit and write the handoff (`workspace/ORBIT/shared/outputs/<date>-handoff.md`).

## The ratchet

When ours wins a dimension blind 3 rounds in a row, that dimension's bar moves up: the reference
becomes the best site we can name for that dimension (Cooper registers it), and our own last winner
becomes the house champion. Losing to our own house champion is logged as a regression.

## App gauntlet (V2 onward)

The app is judged by tasks, timed by code on a clean machine, against LU's own claims and measured runs:

| Task | LU | Orbit target (2x) |
|---|---|---|
| Fresh Windows install to first answer from a local model | "under five minutes" (claimed) | 2.5 min, measured |
| Pair a phone to your PC | QR plus a 6-digit code | one QR scan, nothing typed |
| Phone to PC privacy off your home network | Cloudflare relay, not end to end | end to end encrypted, keys exchanged in the QR |
| Pick a model that fits | marks what fits your PC | marks what fits your PC, a rented GPU, or both, with price per hour |
| Use a GPU you do not own | LU's own cloud only | marketplace of hosts, credits, Cooper-set prices |
| Earn from your GPU | not possible | host mode with fixed hourly tiers |
