#!/usr/bin/env bash
# One swarm cycle: builder builds on a throwaway branch, tests run, branch is pushed only if
# tests pass, critic reviews in ask mode. Nothing here touches main.
# Needs: git, python3, aider, and Ollama running on this PC.
#
#   swarm/run.sh                 one cycle from main
#   BASE=some-branch swarm/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="${BASE:-main}"
STAMP="$(date +%Y-%m-%d-%H%M)"
BRANCH="build/$STAMP"
RUN="workspace/runs/$STAMP.md"
export OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"

if [ "$BASE" = "main" ] && [ "$(git branch --show-current)" = "main" ] && [ -n "$(git status --porcelain)" ]; then
  echo "Uncommitted changes on main. Commit or stash them first." >&2; exit 1
fi

mkdir -p workspace/runs
{ echo "# Swarm run $STAMP"; echo "Base: $BASE  Branch: $BRANCH"; } > "$RUN"

git fetch -q origin "$BASE"
git checkout -q -B "$BRANCH" "origin/$BASE"

echo -e "\n## Builder\n" >> "$RUN"
aider --yes-always --message-file prompts/builder.md --no-show-model-warnings 2>&1 | tee -a "$RUN"

if [ -n "$(git status --porcelain)" ]; then
  git add -A && git commit -q -m "swarm: leftover changes from $STAMP"
fi

echo -e "\n## Tests\n" >> "$RUN"
if python3 -m pytest -q 2>&1 | tee -a "$RUN"; then TESTS=pass; else TESTS=fail; fi

if [ "$TESTS" = pass ] && [ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/$BASE")" ]; then
  git push -q -u origin "$BRANCH" && echo "Pushed $BRANCH" >> "$RUN"
elif [ "$TESTS" = fail ]; then
  echo "Tests failed. Branch kept locally, nothing pushed." >> "$RUN"
else
  echo "Builder made no commits. Nothing pushed." >> "$RUN"
fi

echo -e "\n## Critic\n" >> "$RUN"
aider --chat-mode ask --no-auto-commits --message-file prompts/critic.md --no-show-model-warnings 2>&1 | tee -a "$RUN"

{ echo -e "\n## Result"; echo "Tests: $TESTS"; echo "Branch: $BRANCH"; } >> "$RUN"
echo "Run written to $RUN"
