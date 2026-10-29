#!/usr/bin/env bash
# One swarm cycle. Local agents do the volume for free. Claude only touches what cannot be
# wrong. Anything the local agents cannot finish is escalated to Cooper or a Claude session.
#
#   scout     (local)  walks Orbit like a first-time user, reports friction
#   director  (Claude) decides what to build next. Runs only when Now is empty or its top
#                      item is escalated, and only if ANTHROPIC_API_KEY is set.
#   builder   (local)  takes the top item on a throwaway branch
#   fixer     (local)  if tests fail, one free retry that may not touch tests
#   critic    (local)  first pass. If it is clean and the diff touches money, sessions or
#                      the host program, a Claude critic gets the final say (if a key is set).
#   guard              protected files send the branch to review/ no matter what
#
# After two failed cycles on the same item it is marked escalated in docs/NEXT.md (pushed as
# a build/ branch so the mark merges itself) and described in workspace/ESCALATE.md.
#
#   swarm/run.sh                 one cycle from main
#   swarm/forever.sh             cycles without end
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="${BASE:-main}"
STAMP="$(date +%Y-%m-%d-%H%M)"
BRANCH="build/$STAMP"
RUN="workspace/runs/$STAMP.md"
PY="${PYTHON:-python}"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
DIRECTOR_MODEL="${DIRECTOR_MODEL:-claude-opus-5-5}"
CRITIC_MODEL="${CRITIC_MODEL:-claude-opus-5-5}"
STRANGER_MODEL="${STRANGER_MODEL:-local}"
SENSITIVE='^(orbit/app\.py|orbit/db\.py|host/|orbit/templates/session\.html)'
PROTECTED='^(requirements.*\.txt|CLAUDE\.md|\.github/|swarm/|prompts/|\.aider\.conf\.yml|orbit/ledger\.py|docs/KEYSTONE\.md|docs/decisions/|\.claude/)'
AIDER_TIMEOUT="${AIDER_TIMEOUT:-2400}"  # seconds one builder, fixer or critic call may take before the cycle moves on

if ! curl -s -o /dev/null http://127.0.0.1:8080/v1/models; then
  echo "No model server on port 8080. Start llama-server first (docs/SWARM.md)." >&2; exit 1
fi

mkdir -p workspace/runs
{ echo "# Swarm run $STAMP"; echo "Base: $BASE  Branch: $BRANCH"; } > "$RUN"
"$PY" swarm/state.py begin "$STAMP" | tee -a "$RUN"  # a cycle that begins and never ends is visible next time

git fetch -q origin "$BASE"
git checkout -q -B "$BRANCH" "origin/$BASE"

echo -e "\n## Scoreboard\n" >> "$RUN"
"$PY" swarm/scoreboard.py 2>&1 | tee -a "$RUN"

echo -e "\n## Scout ($STRANGER_MODEL)\n" >> "$RUN"
STRANGER_MODEL="$STRANGER_MODEL" "$PY" swarm/stranger.py 2>&1 | tee "workspace/runs/$STAMP-stranger.md" | tee -a "$RUN"

NEEDS="$("$PY" swarm/state.py needs_director)"
if [ "$NEEDS" = yes ] && [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo -e "\n## Director ($DIRECTOR_MODEL)\n" >> "$RUN"
  DIRECTOR_MODEL="$DIRECTOR_MODEL" "$PY" swarm/director.py 2>&1 | tee -a "$RUN"
  if [ -n "$(git status --porcelain docs/NEXT.md)" ]; then
    git add docs/NEXT.md && git commit -q -m "director: build order for $STAMP"
  fi
elif [ "$NEEDS" = yes ]; then
  echo "Now is empty or escalated and no ANTHROPIC_API_KEY is set. Nothing to build this cycle." | tee -a "$RUN"
  exit 0
fi
ITEM="$("$PY" swarm/state.py top)"
echo -e "\nItem: $ITEM" >> "$RUN"

echo -e "\n## Builder (local)\n" >> "$RUN"
timeout "$AIDER_TIMEOUT" aider --yes-always --message-file prompts/builder.md --no-show-model-warnings 2>&1 | tee -a "$RUN"
if [ -n "$(git status --porcelain)" ]; then git add -A && git commit -q -m "swarm: leftover changes from $STAMP"; fi

echo -e "\n## Tests\n" >> "$RUN"
if "$PY" -m pytest -q 2>&1 | tee workspace/runs/last-tests.txt | tee -a "$RUN"; then TESTS=pass; else TESTS=fail; fi

if [ "$TESTS" = fail ]; then
  echo -e "\n## Fixer (local)\n" >> "$RUN"
  timeout "$AIDER_TIMEOUT" aider --yes-always --read workspace/runs/last-tests.txt --message-file prompts/fixer.md --no-show-model-warnings 2>&1 | tee -a "$RUN"
  if [ -n "$(git status --porcelain)" ]; then git add -A && git commit -q -m "swarm: fixer changes from $STAMP"; fi
  echo -e "\n## Tests after fixer\n" >> "$RUN"
  if "$PY" -m pytest -q 2>&1 | tee -a "$RUN"; then TESTS=pass; else TESTS=fail; fi
fi

if git diff --name-only "origin/$BASE"..HEAD | grep -Eq "$PROTECTED"; then
  GUARD=tripped; echo "Changed a protected file: $(git diff --name-only "origin/$BASE"..HEAD | grep -E "$PROTECTED" | tr '\n' ' ')" | tee -a "$RUN"
else
  GUARD=ok
fi

echo -e "\n## Critic (local)\n" >> "$RUN"
CRITIC_OUT="$(timeout "$AIDER_TIMEOUT" aider --chat-mode ask --no-auto-commits --message-file prompts/critic.md --no-show-model-warnings 2>&1 | tee -a "$RUN")"
echo "$CRITIC_OUT"
if echo "$CRITIC_OUT" | grep -qi "nothing found"; then CRITIC=clean; else CRITIC=flagged; fi
if [ -z "$(git diff --name-only "origin/$BASE"..HEAD)" ]; then
  CRITIC=empty; echo "Nothing to review: the diff is empty. 'Nothing found' on nothing is not a clean critic." | tee -a "$RUN"
fi

if [ "$CRITIC" = clean ] && [ "$TESTS" = pass ] && [ "$GUARD" = ok ] && [ -n "${ANTHROPIC_API_KEY:-}" ] \
   && git diff --name-only "origin/$BASE"..HEAD | grep -Eq "$SENSITIVE"; then
  echo -e "\n## Critic, final say ($CRITIC_MODEL): the change touches money, sessions or the host program\n" >> "$RUN"
  CRITIC_OUT="$(timeout "$AIDER_TIMEOUT" aider --model "$CRITIC_MODEL" --chat-mode ask --no-auto-commits --message-file prompts/critic.md --no-show-model-warnings 2>&1 | tee -a "$RUN")"
  echo "$CRITIC_OUT"
  if echo "$CRITIC_OUT" | grep -qi "nothing found"; then CRITIC=clean; else CRITIC=flagged; fi
fi

CHANGED="$(git diff --name-only "origin/$BASE"..HEAD | grep -v '^docs/NEXT.md$' || true)"
if [ -z "$CHANGED" ]; then
  echo "Builder changed no files. Nothing pushed." | tee -a "$RUN"
  FAILS="$("$PY" swarm/state.py failed)"
elif [ "$TESTS" = pass ] && [ "$CRITIC" = clean ] && [ "$GUARD" = ok ]; then
  git push -q -u origin "$BRANCH" && echo "Pushed $BRANCH. It merges itself when GitHub tests are green." | tee -a "$RUN"
  "$PY" swarm/state.py reset; FAILS=0
else
  REVIEW="review/$STAMP"
  git branch -m "$BRANCH" "$REVIEW"; BRANCH="$REVIEW"
  git push -q -u origin "$BRANCH" && echo "Pushed $BRANCH for review. Tests: $TESTS. Critic: $CRITIC. Guard: $GUARD." | tee -a "$RUN"
  FAILS="$("$PY" swarm/state.py failed)"
fi

if [ "${FAILS:-0}" -ge 2 ]; then
  # The mark goes on a build/ branch so it merges itself. Next cycle the director replans
  # the item smaller, or the swarm waits for someone to fill Now.
  ESCALATE="build/$STAMP-escalate"
  WHY="Failed $FAILS cycles locally. Last: tests=$TESTS critic=$CRITIC guard=$GUARD. Branch: $BRANCH."
  git checkout -q -B "$ESCALATE" "origin/$BASE"
  "$PY" swarm/state.py escalate "$WHY" | tee -a "$RUN"
  git add docs/NEXT.md && git commit -q -m "Escalate: $ITEM" -m "$WHY" && git push -q -u origin "$ESCALATE" \
    && echo "Escalation pushed as $ESCALATE. It merges itself. Details in workspace/ESCALATE.md." | tee -a "$RUN"
fi

{ echo -e "\n## Result"; echo "Item: $ITEM"; echo "Tests: $TESTS"; echo "Critic: $CRITIC"; echo "Guard: $GUARD"; echo "Fails on this item: ${FAILS:-0}"; echo "Branch: $BRANCH"; } >> "$RUN"
"$PY" swarm/state.py end "$STAMP" "tests=$TESTS critic=$CRITIC guard=$GUARD branch=$BRANCH"
echo "Run written to $RUN"
