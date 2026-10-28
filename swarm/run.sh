#!/usr/bin/env bash
# One swarm cycle: builder builds on a throwaway branch, tests run, critic reviews in ask
# mode. Green and clean goes to build/ and merges itself on GitHub. Anything else goes to
# review/ and waits. Nothing here touches main directly.
# Needs: git, python, aider, and llama-server running on this PC.
#
#   swarm/run.sh                 one cycle from main
#   BASE=some-branch swarm/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="${BASE:-main}"
STAMP="$(date +%Y-%m-%d-%H%M)"
BRANCH="build/$STAMP"
RUN="workspace/runs/$STAMP.md"
# The model server (llama.cpp) must already be running. See docs/SWARM.md.
if ! curl -s -o /dev/null http://127.0.0.1:8080/v1/models; then
  echo "No model server on port 8080. Start llama-server first (docs/SWARM.md)." >&2; exit 1
fi

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

# Files the builder must never change. Touching one sends the branch to review/.
PROTECTED='^(requirements.*\.txt|CLAUDE\.md|\.github/|swarm/|prompts/|\.aider\.conf\.yml|orbit/ledger\.py)'
if git diff --name-only "origin/$BASE"..HEAD | grep -Eq "$PROTECTED"; then
  GUARD=tripped; echo "Builder changed a protected file: $(git diff --name-only "origin/$BASE"..HEAD | grep -E "$PROTECTED" | tr '\n' ' ')" | tee -a "$RUN"
else
  GUARD=ok
fi

echo -e "\n## Tests\n" >> "$RUN"
if python -m pytest -q 2>&1 | tee -a "$RUN"; then TESTS=pass; else TESTS=fail; fi

echo -e "\n## Critic\n" >> "$RUN"
# The critic can run on a stronger paid model: set CRITIC_MODEL=claude-opus-5-5 and
# ANTHROPIC_API_KEY in your environment (never in the repo). Unset, it uses the local model.
CRITIC_ARGS=()
if [ -n "${CRITIC_MODEL:-}" ]; then CRITIC_ARGS=(--model "$CRITIC_MODEL"); fi
CRITIC_OUT="$(aider "${CRITIC_ARGS[@]}" --chat-mode ask --no-auto-commits --message-file prompts/critic.md --no-show-model-warnings 2>&1 | tee -a "$RUN")"
if echo "$CRITIC_OUT" | grep -qi "nothing found"; then CRITIC=clean; else CRITIC=flagged; fi

# Where the branch goes decides what happens to it:
#   build/   tests pass and critic clean  -> GitHub runs tests again and merges it
#   review/  anything else                -> waits for a fix, never merges on its own
if [ "$(git rev-parse HEAD)" = "$(git rev-parse "origin/$BASE")" ]; then
  echo "Builder made no commits. Nothing pushed." >> "$RUN"
elif [ "$TESTS" = pass ] && [ "$CRITIC" = clean ] && [ "$GUARD" = ok ]; then
  git push -q -u origin "$BRANCH" && echo "Pushed $BRANCH. It merges itself when GitHub tests are green." >> "$RUN"
else
  REVIEW="review/$STAMP"
  git branch -m "$BRANCH" "$REVIEW"; BRANCH="$REVIEW"
  git push -q -u origin "$BRANCH" && echo "Pushed $BRANCH for review. Tests: $TESTS. Critic: $CRITIC. Guard: $GUARD." >> "$RUN"
fi

{ echo -e "\n## Result"; echo "Tests: $TESTS"; echo "Critic: $CRITIC"; echo "Guard: $GUARD"; echo "Branch: $BRANCH"; } >> "$RUN"
echo "Run written to $RUN"
