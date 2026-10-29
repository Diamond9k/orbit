# The swarm

Agents that build Orbit toward the goal in CLAUDE.md, on your own PC, without turning off.
Local open models do the volume for free. Claude touches only what cannot be wrong. What the
local agents cannot finish is escalated to Cooper or a Claude session.

## The roles

| Role | Model | What it does |
|---|---|---|
| Scout | local | Walks Orbit like a first-time user, every screen, reports where it got stuck |
| Director | Claude, rarely | Decides what to build next from the goal, the scoreboard and the scout's report. Runs only when the Now list is empty or its top item is escalated |
| Builder | local | Takes the top item on a throwaway branch |
| Fixer | local | If tests fail, one free retry that may fix code but never tests |
| Critic | local, then Claude for sensitive changes | First pass locally. If clean and the change touches money, sessions or the host program, Claude gets the final say |
| Guard | none | Protected files send the branch to review no matter what |

`swarm/run.sh` is one cycle. `swarm/forever.sh` runs cycles without end. After two failed
cycles on one item it is marked escalated in `docs/NEXT.md` and described in
`workspace/ESCALATE.md`. The mark is pushed as a `build/` branch so it merges itself. On the
next cycle the director replans the item smaller. Paste `workspace/ESCALATE.md` or the run
file into a Claude session to get it unstuck by hand.

Each cycle records that it began and how it ended in `workspace/state.json`. A cycle that
began and never ended (the machine slept, the window was closed) is named in `forever.log`
at the next start instead of vanishing. Every builder, fixer and critic call is bounded by
`AIDER_TIMEOUT` (default 40 minutes); when it fires, the cycle moves on and records it.
A critic that says "Nothing found" about an empty diff is recorded as `empty`, not clean.

Without `ANTHROPIC_API_KEY` set, everything runs local: the director never runs, so the
swarm works through the existing Now list and then checks every ten minutes until someone
fills it.

## The local model

A 7B model writes a small file when told exactly what to write, and nothing more. In cycle
two it described the work instead of doing it. A 14B model follows Aider's edit format far
better. On an 8 GB card it splits between the GPU and system RAM: slower per token, but the
swarm never stops, so speed matters less than getting it right.
```
llama serve -hf bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M --port 8080 -c 16384 -np 1 -ngl 20
```
Aider uses the diff edit format: the model writes only the lines it changes. With the whole
format it had to rewrite every file it touched, and `orbit/app.py` alone is about 5k tokens,
so input plus output passed the 16k context and the builder hit a token limit, changing nothing.

`-ngl 20` puts 20 layers on the GPU and the rest on the CPU. If it runs out of GPU memory,
lower it. Check Hugging Face for a newer 14B coding model at the time.

## The locks

- The builder works on a throwaway branch. It never sees main.
- The critic runs in ask mode. It cannot edit a file. The fixer cannot edit tests.
- The guard: if the builder touches requirements, the bible, the workflow, the swarm, the
  prompts, the ledger, the decisions, Keystone's record (`docs/KEYSTONE.md`) or `.claude/`,
  the branch goes to review no matter what.
- Only a branch with passing tests, a clean critic and a clean guard goes to `build/`, and
  GitHub runs the tests again before it merges. Everything else goes to `review/`.
- Cooper can revert anything.

## Setup, once (Windows, tested on an AMD RX 580)

1. **Install llama.cpp** with its own installer. In PowerShell:
   ```
   irm https://llama.app/install.ps1 | iex
   ```
   It probes for CUDA, ROCm and Vulkan and picks the right build for your GPU.
2. **Start the model server** in its own PowerShell window and leave it running. It downloads
   the model from Hugging Face the first time (about 9 GB):
   ```
   llama serve -hf bartowski/Qwen2.5-Coder-14B-Instruct-GGUF:Q4_K_M --port 8080 -c 16384 -np 1 -ngl 20
   ```
   Open http://127.0.0.1:8080 and send a message. If Task Manager's GPU graph jumps, the GPU
   is doing the work. Check Hugging Face for a newer 7B coding model at the time; any GGUF
   with a Q4_K_M file works.
3. **Install Aider in its own environment**, so it never changes your other Python packages:
   ```
   python -m pip install aider-install
   aider-install
   ```
   Close and reopen PowerShell, then `aider --version` should print a version.
4. **Install the test tools** in the repo folder: `python -m pip install -r requirements-dev.txt`.
5. **Make sure `git push` works** from this PC without a password prompt.
6. **Set the key** for the rare Claude calls, in the same PowerShell window:
   ```
   $env:ANTHROPIC_API_KEY = "your key"
   ```
7. **Start the swarm** from PowerShell in the repo folder (Git for Windows provides bash):
   ```
   & "C:\Program Files\Git\bin\bash.exe" swarm/forever.sh
   ```
   It runs until you create a file named `swarm/STOP` (from another window: `New-Item swarm/STOP`).
   The file stays after the swarm stops; delete it before starting the swarm again, so a stop
   is never undone by a restart you did not mean.
   Its log is `workspace/runs/forever.log`, one file per cycle beside it. Warnings about the
   console or prompt toolkit are harmless. For a single cycle, run `swarm/run.sh` instead.

## What happens to a branch

- Tests pass and critic says "Nothing found": pushed as `build/<date>`. GitHub runs the tests
  again, opens a pull request, and merges it. Nobody clicks anything.
- Anything else: pushed as `review/<date>`. It waits. Nothing merges on its own.
- A `build/` branch that has not merged after 30 minutes is kept as `review/<date>-stuck` and
  noted in `workspace/ESCALATE.md`, and the swarm moves on. Nothing unmerged is ever deleted.

## Once in GitHub settings

Settings, General: tick "Allow auto-merge". Settings, Branches: protect `main` and require
the "tests" check. That is what makes `build/` branches merge themselves.

## Each morning

Open the newest file in `workspace/runs/`. Three outcomes:

- **Merged itself.** Nothing to do. Glance at the diff on GitHub if you like. Revert if it
  smells wrong.
- **Went to review/.** The critic's list is in the swarm window and in the run file. Paste
  it into the top of `docs/NEXT.md` as the next item. The next cycle fixes it.
- **Builder got stuck or wandered.** The item was too vague. Rewrite it in `docs/NEXT.md` in
  smaller, plainer words. That is the fix, not a bigger model.

## When to spend money

Use a paid model only for what open models are weakest at: breaking a big vague item into
small clear ones, and reviewing a branch the critic passed but you do not trust. Everything
else runs on your GPU.
