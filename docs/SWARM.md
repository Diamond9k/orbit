# The swarm

Agents that build Orbit on your own PC with open source models. One builder, one critic,
one cycle at a time. The bible (CLAUDE.md), the tests and your merge are the locks.

## What runs where

| Piece | What |
|---|---|
| llama.cpp (Vulkan build) | Runs the coding model on the GPU and serves it locally. Works on AMD cards like the RX 580 |
| Aider | The agent. Reads the prompt, edits files, runs tests, commits |
| `prompts/builder.md` | What the builder is told |
| `prompts/critic.md` | What the critic is told |
| `.aider.conf.yml` | Model name, auto test, files always loaded |
| `swarm/run.sh` | One cycle: fresh branch, build, test, critique, push to build/ or review/ |
| `workspace/runs/` | One file per cycle. Read these in the morning |

## The locks

- The builder works on a throwaway branch. It never sees main.
- The critic runs in ask mode. It cannot edit a file.
- Only a branch with passing tests and a clean critic goes to `build/`, and GitHub runs the
  tests again before it merges. Everything else goes to `review/` and waits.
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

## Run it nightly

Windows: open Task Scheduler, create a basic task, daily at 2 AM, action "Start a program":
program `C:\Program Files\Git\bin\bash.exe`, arguments `C:\path\to\orbit\swarm\run.sh`.
The model server from step 2 must be running.

Mac or Linux: `crontab -e` and add
```
0 2 * * * /full/path/to/orbit/swarm/run.sh >> /full/path/to/orbit/workspace/runs/cron.log 2>&1
```

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

## A stronger critic

The critic is the best place to spend a little money: it reads one diff and writes a short
list, so a cycle costs a few cents, and it catches what a 7B builder misses. In PowerShell,
before running a cycle:
```
$env:ANTHROPIC_API_KEY = "your key"
$env:CRITIC_MODEL = "claude-opus-5-5"
```
The builder stays on your GPU. Leave both unset and the critic runs locally.

## When to spend money

Use a paid model only for what open models are weakest at: breaking a big vague item into
small clear ones, and reviewing a branch the critic passed but you do not trust. Everything
else runs on your GPU.
