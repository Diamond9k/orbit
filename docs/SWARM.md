# The swarm

Agents that build Orbit toward the goal in CLAUDE.md, on your own PC. Five roles, one cycle.
The bible, the tests, the guard and your revert are the locks.

## The roles

| Role | What it does | File | Model |
|---|---|---|---|
| Scoreboard | Reads the ledger: hosts paid, sessions by strangers, hosts online | `swarm/scoreboard.py` | none |
| Stranger | Walks Orbit like a first-time user, every screen, and reports where it got stuck | `swarm/stranger.py`, `prompts/stranger.md` | `STRANGER_MODEL` |
| Director | Owns the goal. Reads the bible, scoreboard, stranger report and last result, then rewrites the Now section of `docs/NEXT.md` | `swarm/director.py`, `prompts/director.md` | `DIRECTOR_MODEL` |
| Builder | Takes the director's top item on a throwaway branch | Aider, `prompts/builder.md`, `.aider.conf.yml` | local |
| Critic | Reads the diff cold and lists what a stranger would hit | Aider in ask mode, `prompts/critic.md` | `CRITIC_MODEL` |

`swarm/run.sh` runs them in that order, then the guard checks protected files and the branch
goes to `build/` (merges itself on GitHub) or `review/` (waits). Logs land in `workspace/runs/`.

## Which roles need a strong model

Honest answer: the director, the stranger and the critic. A 7B model can write a small file
when told exactly what to write. It cannot read a goal and decide what matters, and it cannot
notice what a builder got wrong. Cycle one proved it. Set these before a cycle:
```
$env:ANTHROPIC_API_KEY = "your key"
$env:DIRECTOR_MODEL = "claude-opus-5-5"
$env:STRANGER_MODEL = "claude-opus-5-5"
$env:CRITIC_MODEL = "claude-opus-5-5"
```
Each of those roles makes one call per cycle, so a cycle costs well under a dollar. The
builder stays on your GPU and does the long work for free. Leave the variables unset and
every role runs on the local model.

## The locks

- The builder works on a throwaway branch. It never sees main.
- The critic runs in ask mode. It cannot edit a file.
- The guard: if the builder touches requirements, the bible, the workflow, the swarm, the
  prompts or the ledger, the branch goes to review no matter what.
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
   the model from Hugging Face the first time (about 4.7 GB):
   ```
   llama serve -hf bartowski/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M --port 8080
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
6. **Run one cycle** from PowerShell in the repo folder (Git for Windows provides bash):
   ```
   & "C:\Program Files\Git\bin\bash.exe" swarm/run.sh
   ```
   Warnings about the console or prompt toolkit are harmless.

A 7B model handles small, clear tasks and struggles with vague ones. Keep `docs/NEXT.md`
items tight. That matters more than any other setting.

## Run it all the time

`swarm/loop.sh` runs cycle after cycle until you stop it. Before each cycle it waits for the
previous `build/` branch to merge on GitHub, so the director never plans on top of work that
has not landed. From PowerShell in the repo folder, with the key and model variables set:
```
& "C:\Program Files\Git\bin\bash.exe" swarm/loop.sh
```
To cap cost, pause between cycles: `$env:PAUSE = "1800"` (30 minutes) before the line above.
To stop after the current cycle, create an empty file named `swarm/STOP` (from another
window: `New-Item swarm/STOP`). The loop's own log is `workspace/runs/loop.log`.

To start it with Windows: Task Scheduler, create a basic task, trigger "When I log on",
action "Start a program", program `C:\Program Files\Git\bin\bash.exe`, arguments
`C:\path\to\orbit\swarm\loop.sh`. The model server must also be running; add a second
task for it with program `llama` and arguments
`serve -hf bartowski/Qwen2.5-Coder-7B-Instruct-GGUF:Q4_K_M --port 8080`.
Put the key and model variables in the user's environment variables (Windows settings,
"Edit environment variables for your account") so scheduled tasks can see them.

While the loop runs, the builder uses the same GPU that is listed as host number one. With
no strangers yet that is fine. When strangers arrive, run the loop off-hours or on a second
machine.

## What happens to a branch

- Tests pass and critic says "Nothing found": pushed as `build/<date>`. GitHub runs the tests
  again, opens a pull request, and merges it. Nobody clicks anything.
- Anything else: pushed as `review/<date>`. It waits. Nothing merges on its own.

## Once in GitHub settings

Settings, General: tick "Allow auto-merge". Settings, Branches: protect `main` and require
the "tests" check. That is what makes `build/` branches merge themselves.

## Each morning

Open the newest file in `workspace/runs/`. Three outcomes:

- **Merged itself.** Nothing to do. Glance at the diff on GitHub if you like. Revert if it
  smells wrong.
- **Went to review/.** The critic's list is in the run file. Paste it into the top of
  `docs/NEXT.md` as the next item. The next cycle fixes it.
- **Builder got stuck or wandered.** The item was too vague. Rewrite it in `docs/NEXT.md` in
  smaller, plainer words. That is the fix, not a bigger model.

## When to spend money

Use a paid model only for what open models are weakest at: breaking a big vague item into
small clear ones, and reviewing a branch the critic passed but you do not trust. Everything
else runs on your GPU.
