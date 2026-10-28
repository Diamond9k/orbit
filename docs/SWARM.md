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

## Setup, once (Windows, AMD RX 580 or similar)

1. **Get llama.cpp.** From github.com/ggml-org/llama.cpp, Releases, download the Windows
   Vulkan zip (its name contains `win-vulkan-x64`). Unzip it to `C:\llama`.
2. **Get a coding model that fits 8 GB.** From Hugging Face, download
   `Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf` (about 4.7 GB) into `C:\llama\models`.
   Check Hugging Face for a newer 7B coding model at the time; any GGUF works.
3. **Start the model server** in its own PowerShell window and leave it running:
   ```
   C:\llama\llama-server.exe -m C:\llama\models\Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf -ngl 99 -c 16384 --port 8080
   ```
   `-ngl 99` puts every layer on the GPU. If it fails to load, lower it to 24 and the rest
   runs on the CPU, slower but fine overnight.
4. **Install the tools** in another PowerShell window:
   ```
   python -m pip install aider-chat
   python -m pip install -r requirements-dev.txt
   ```
5. **Make sure `git push` works** from this PC without a password prompt.
6. **Try one cycle** from Git Bash (comes with Git for Windows):
   ```
   BASE=claude/zen-ride-rbvl70 swarm/run.sh
   ```
   Once that branch is merged, drop the `BASE=` part and it builds from main.

A 7B model handles small, clear tasks and struggles with vague ones. Keep `docs/NEXT.md`
items tight. That matters more than any other setting.

## Run it nightly

Windows: open Task Scheduler, create a basic task, daily at 2 AM, action "Start a program":
program `C:\Program Files\Git\bin\bash.exe`, arguments `C:\path\to\orbit\swarm\run.sh`.
The model server from step 3 must be running.

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

## When to spend money

Use a paid model only for what open models are weakest at: breaking a big vague item into
small clear ones, and reviewing a branch the critic passed but you do not trust. Everything
else runs on your GPU.
