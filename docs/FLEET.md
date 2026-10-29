# The fleet, revised

Date: 2026-10-29. Status: proposed by Keystone after Cooper's correction; not restarted until
Cooper has seen it.

## Cooper's correction (2026-10-29, verbatim where it binds)

"Local open-source models on my own hardware are the default for daily work. Before launching
any Claude subagent, ask: can a local model do this task to an acceptable standard? If we don't
know, run a small, bounded test and measure the result. Do not launch parallel paid or
plan-usage Claude agents by default. Use one only when local work has failed, the task requires
capabilities we cannot reasonably verify locally, or independent review is needed for sensitive
work. Tell me what it will do and why it is worth the usage before starting it."

What went wrong before it: Keystone launched four Fable 5.1 agents at once, for up to two hours
each, on Cooper's shared plan limits, and said so only in the record, not in chat.

## The shape

- **One director.** Keystone, a Claude Code session Cooper opens. It observes, picks the
  obstacle, writes the task with its named files and its tests first, chooses the worker by the
  ladder below, reads every diff, records the outcome, and keeps `docs/KEYSTONE.md` and
  `docs/BOARD.md` true. It is not always on and never claims to be.
- **Local workers.** llama.cpp on port 8080 (today Qwen2.5-Coder-14B Q4_K_M, 16,384 tokens of
  context, one slot, 4.8 GB on the RX 580) driven by aider 0.86.2 with the repository's
  `.aider.conf.yml` (diff edits, tests run after every edit). These are the swarm's builder,
  fixer and critic roles, run one task at a time, by the director, on a `local/*` branch in its
  own worktree. Cost: nothing.
- **Scripts, no model.** Tests, the GitHub workflow, screenshots at three widths with headless
  Edge, overflow and contrast measurement, the ledger. Most checks are this kind.
- **A stronger model, last.** One Claude agent at a time, on the cheapest model that can do the
  job, after Cooper has been told what it will do and why, with its usage written in the ledger.

## The ladder: which worker

1. Does it need a model at all? If a script or a test answers it, run the script.
2. Can the local model do it to standard? Yes, when the task is a small change to named files
   with an exact specification and tests written first (a new module under 100 lines, a route
   with a form and a test, a text change, a mechanical refactor the tests pin down). No, when
   the task needs the web (licences, papers, prices), judgement about security or money, taste,
   or more than about 8,000 tokens of code in view at once. Unknown: run a bounded test (one
   build attempt, one fix attempt, twenty minutes each, tests first), record it, and the answer
   joins the lists in "What goes where" below.
3. A cheaper Claude model (Sonnet, Haiku) for routine agent work that needs tools the local
   model does not have here (web fetches, long context), one at a time.
4. Fable or Opus only for judgement-critical work: security conclusions, design taste, research
   synthesis, independent review of money or privacy code. One at a time. Cooper told first.

## A task's life

1. **Spec.** The director writes the item in `docs/NEXT.md` or `docs/BOARD.md` with the files it
   may touch and a test file that is the acceptance check, committed before any model runs.
2. **Build, bounded.** The worker gets one attempt; if the tests fail, the fixer gets one; each
   is time-boxed (`AIDER_TIMEOUT`, default forty minutes for the swarm, twenty for a director-run
   task). A third failure is not retried: the task is escalated to Cooper or moved one rung up
   the ladder, and the ledger says so.
3. **Checks the builder does not control.** The tests on this PC; the GitHub tests workflow on
   push; a scope check that only the named files changed and no protected file (the swarm's
   `PROTECTED` list); the local critic's read of the diff; the director's own read of the diff.
   Money, sessions and the host program get one stronger-model review before merging, as the
   swarm already requires.
4. **Integrate.** A pull request Cooper sees. Never silently into the `build/` auto-merge path;
   that path stays for the swarm's escalation marks only.
5. **Record.** One ledger row (worker, minutes, result, note), the board updated, and a line in
   `docs/KEYSTONE.md` when something was decided or learned.

## Tracking

`docs/evidence/fleet-ledger.md` is a Markdown table, one row per piece of work: date, task,
worker (`local`, `claude:sonnet`, `claude:fable`, `script`, `keystone`), minutes of wall time,
result (`accepted` or `failed`), note. `swarm/ledger.py` appends rows and sums them per worker,
so "is this saving resources" is one command. Claude usage is recorded as the token count the
harness reports when an agent finishes; a killed agent's usage is "unmeasured", never guessed.
"Accepted" means the tests passed and the director accepted the diff or Cooper merged it;
"failed" means the attempts ran out.

## What goes where today

- **Local by default:** the ledger tool (the first test); the host program adopting a leftover
  model server on its port; editing a listed machine's price; the Hosts page's plain install
  steps; moving the UI's tokens onto a page once the design is set; README and docs edits from
  a list; any new test from an exact description.
- **Scripts:** screenshots at 320/390/1280, overflow and contrast numbers, logo renders, test
  runs, CI.
- **Stronger model, with Cooper's go each time:** the second review of the sealing findings;
  the privacy research (web-verified); the UI design decisions; the payout code review.

## Operating limits

- One local worker at a time: the server has one slot. The server belongs to the peer session
  today and may stop with it; if it does, Keystone asks Cooper before starting one.
- The swarm's forever loop stays off until Cooper says so. The director runs single tasks by
  hand, with the exact command written in the ledger note, so the run is reproducible.
- Stop means Cooper's word or `swarm/STOP`: no new task; the running one finishes its attempt,
  commits, and is recorded.
- Never two app versions on one database; test data lives under the scratch folder.

## The first bounded test: T6, the ledger tool

Spec: `tests/test_ledger.py` (seven tests), committed first on `local/ledger`. Worker: the local
14B through one plain chat call per attempt (`swarm/local_task.py`; this session's permission classifier refuses to
launch aider with `--yes-always`, so the director plays aider's part: spec and tests in, one
complete file out, the director writes it and runs the tests), two attempts, twenty-five minutes
each at most, prompt saved with the run.

Result, 04:18: the first answer came in 196 s, a 72-line file that passed six of the seven
tests; the seventh failed because the director's own test was wrong (it counted an escaped pipe
as not a pipe), so the second attempt (236 s) returned the same file and could not help. With
the test corrected, seven of seven pass; the file is pull request 27, unchanged from the model's
answer. Tokens: 4,609 in, 1,344 out, about 3.4 a second, cost nothing. Verdict: accepted.

Lessons, now rules: the director reads the first failure before spending the fixer attempt;
when both attempts fail the same way, suspect the spec; a 70-line file costs about three
minutes of generation on this card, so a task that needs more than two such files in view at
once is not for this worker.
