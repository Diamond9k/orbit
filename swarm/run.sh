#!/usr/bin/env bash
# One swarm cycle. Five roles, one goal:
#   scoreboard  reads the ledger (hosts paid, sessions, hosts online)
#   stranger    walks Orbit like a first-time user and reports friction
#   director    reads the bible, scoreboard, stranger report, last result; rewrites docs/NEXT.md
#   builder     takes the director's top item on a throwaway branch (Aider, local model)
#   critic      reads the diff cold
# Then the guard checks protected files and the branch goes to build/ (merges itself on
# GitHub) or review/ (waits). Nothing here touches main directly.
#
# Models per role, all optional, default local (llama-server on port 8080):
#   DIRECTOR_MODEL=claude-opus-5-5  STRANGER_MODEL=claude-opus-5-5  CRITIC_MODEL=claude-opus-5-5
#   (needs ANTHROPIC_API_KEY in the environment, never in the repo)
#
#   swarm/run.sh                 one cycle from main
#   BASE=some-branch swarm/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="${BASE:-main}"
STAMP="$(date +%Y-%m-%d-%H%M)"
BRANCH="build/$STAMP"
RUN="workspace/runs/$STAMP.md"
PY="${PYTHON:-python}"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1

if ! curl -s -o /dev/null http://127.0.0.1:8080/v1/models; then
  echo "No model server on port 8080. Start llama-server first (docs/SWARM.md)." >&2; exit 1
fi
if [ "$BASE" = "main" ] && [ "$(git branch --show-current)" = "main" ] && [ -n "$(git status --porcelain)" ]; then
  echo "Uncommitted changes on main. Commit or stash them first." >&2; exit 1
fi

mkdir -p workspace/runs
{ echo "# Swarm run $STAMP"; echo "Base: $BASE  Branch: $BRANCH"; echo "Models: director=${DIRECTOR_MODEL:-local} stranger=${STRANGER_MODEL:-local} critic=${CRITIC_MODEL:-local} builder=local"; } > "$RUN"

git fetch -q origin "$BASE"
git checkout -q -B "$BRANCH" "origin/$BASE"

echo -e "\n## Scoreboard\n" >> "$RUN"
"$PY" swarm/scoreboard.py 2>&1 | tee -a "$RUN"

echo -e "\n## Stranger\n" >> "$RUN"
"$PY" swarm/stranger.py 2>&1 | tee "workspace/runs/$STAMP-stranger.md" | tee -a "$RUN"

echo -e "\n## Director\n" >> "$RUN"
"$PY" swarm/director.py 2>&1 | tee -a "$RUN"
if [ -n "$(git status --porcelain docs/NEXT.md)" ]; then
  git add docs/NEXT.md && git commit -q -m "director: build order for $STAMP"
fi

echo -e "\n## Builder\n" >> "$RUN"
aider --yes-always --message-file prompts/builder.md --no-show-model-warnings 2>&1 | tee -a "$RUN"

if [ -n "$(git status --porcelain)" ]; then
  git add -A && git commit -q -m "swarm: leftover changes from $STAMP"
fi

# Files the builder must never change. Touching one sends the branch to review/.
PROTECTED='^(requirements.*\.txt|CLAUDE\.md|\.github/|swarm/|prompts/|\.aider\.conf\.yml|orbit/ledger\.py)'
if git diff --name-only "origin/$BASE"..HEAD | grep -Eq "$PROTECTED"; then
  GUARD=tripped; echo "Builder changed a protected file: $(git diff --name-only "origin/$BASE"..HEAD | grep -E "$PROTECTED" | tr '\n' ' ')" | tee -a "$RUN"
else
  GUARD=ok
fi

echo -e "\n## Tests\n" >> "$RUN"
if "$PY" -m pytest -q 2>&1 | tee -a "$RUN"; then TESTS=pass; else TESTS=fail; fi

echo -e "\n## Critic\n" >> "$RUN"
CRITIC_ARGS=()
if [ -n "${CRITIC_MODEL:-}" ]; then CRITIC_ARGS=(--model "$CRITIC_MODEL"); fi
CRITIC_OUT="$(aider "${CRITIC_ARGS[@]}" --chat-mode ask --no-auto-commits --message-file prompts/critic.md --no-show-model-warnings 2>&1 | tee -a "$RUN")"
if echo "$CRITIC_OUT" | grep -qi "nothing found"; then CRITIC=clean; else CRITIC=flagged; fi

# Where the branch goes decides what happens to it:
#   build/   tests pass, critic clean, guard ok  -> GitHub runs tests again and merges it
#   review/  anything else                        -> waits for a fix, never merges on its own
if [ "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$BASE")" ]; then
  echo "Nothing changed. Nothing pushed." >> "$RUN"
elif [ "$TESTS" = pass ] && [ "$CRITIC" = clean ] && [ "$GUARD" = ok ]; then
  git push -q -u origin "$BRANCH" && echo "Pushed $BRANCH. It merges itself when GitHub tests are green." >> "$RUN"
else
  REVIEW="review/$STAMP"
  git branch -m "$BRANCH" "$REVIEW"; BRANCH="$REVIEW"
  git push -q -u origin "$BRANCH" && echo "Pushed $BRANCH for review. Tests: $TESTS. Critic: $CRITIC. Guard: $GUARD." >> "$RUN"
fi

{ echo -e "\n## Result"; echo "Tests: $TESTS"; echo "Critic: $CRITIC"; echo "Guard: $GUARD"; echo "Branch: $BRANCH"; } >> "$RUN"
echo "Run written to $RUN"
