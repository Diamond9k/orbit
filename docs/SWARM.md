# The swarm

Agents that build Orbit on your own PC with open source models. One builder, one critic,
one cycle at a time. The bible (CLAUDE.md), the tests and your merge are the locks.

## What runs where

| Piece | What |
|---|---|
| Ollama | Runs the coding model on your GPU and serves it locally |
| Aider | The agent. Reads the prompt, edits files, runs tests, commits |
| `prompts/builder.md` | What the builder is told |
| `prompts/critic.md` | What the critic is told |
| `.aider.conf.yml` | Model name, auto test, files always loaded |
| `swarm/run.sh` | One cycle: fresh branch, build, test, push only if green, critique |
| `workspace/runs/` | One file per cycle. Read these in the morning |

## The locks

- The builder works on a throwaway branch named `build/<date>`. It never sees main.
- Nothing is pushed unless the tests pass.
- The critic runs in ask mode. It cannot edit a file.
- Nothing is merged by any agent. You open the pull request and you merge.

## Setup, once

1. Install Ollama from ollama.com. Then pull a coding model that fits your GPU memory:
   ```
   ollama pull qwen2.5-coder:32b      # needs about 20 GB of GPU memory
   ollama pull qwen2.5-coder:14b      # about 10 GB
   ```
   If you pull a different one, change `model:` in `.aider.conf.yml` to match.
   Check Hugging Face and the Ollama library for what is best at the time.
2. Install Python 3.11 or newer, then:
   ```
   python3 -m pip install aider-chat
   python3 -m pip install -r requirements-dev.txt
   ```
3. Clone the repo and make sure `git push` works from this PC without a password prompt.
4. Run one cycle by hand and watch it:
   ```
   BASE=claude/zen-ride-rbvl70 swarm/run.sh
   ```
   Once that branch is merged, drop the `BASE=` part and it builds from main.

## Running it on a schedule

Only after you have watched a few cycles by hand and trust them. On Mac or Linux, add one
line with `crontab -e`, using your real path:
```
0 2 * * * /full/path/to/orbit/swarm/run.sh >> /full/path/to/orbit/workspace/runs/cron.log 2>&1
```
On Windows, use Task Scheduler to run `swarm/run.sh` through Git Bash.

## Each morning

Open the newest file in `workspace/runs/`. Three outcomes:

- **Critic says "Nothing found".** Open a pull request from the branch, read the diff yourself,
  merge.
- **Critic lists problems.** Paste the list into the top of `docs/NEXT.md` as the next item.
  The next cycle fixes it.
- **Builder got stuck or wandered.** The item was too vague. Rewrite it in `docs/NEXT.md` in
  smaller, plainer words. That is the fix, not a bigger model.

## When to spend money

Use a paid model only for what open models are weakest at: breaking a big vague item into
small clear ones, and reviewing a branch the critic passed but you do not trust. Everything
else runs on your GPU.
