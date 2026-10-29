#!/usr/bin/env bash
# The swarm never turns off. Cycle after cycle on the local model, which is free.
# Claude is called only when the plan runs dry or a sensitive change needs a final look.
#
#   swarm/forever.sh            start
#   New-Item swarm/STOP         (PowerShell, another window) stop after the current cycle
#
# Before each cycle it waits for the previous build/ branch to merge on GitHub, so the
# director never plans on top of work that has not landed, and deletes merged build/ branches.
# A build/ branch that has not merged after 30 minutes is deleted; the next cycle redoes it.
set -uo pipefail
cd "$(dirname "$0")/.."
BASE="${BASE:-main}"
PY="${PYTHON:-python}"
LOG="workspace/runs/forever.log"
mkdir -p workspace/runs
rm -f swarm/STOP
say() { echo "$(date '+%Y-%m-%d %H:%M') $*" | tee -a "$LOG"; }

pending_builds() {
  git fetch -q --prune origin
  for b in $(git branch -r --list 'origin/build/*' | sed 's|^ *origin/||'); do
    if git merge-base --is-ancestor "origin/$b" origin/main; then
      git push -q origin --delete "$b" 2>/dev/null && say "cleaned merged $b"
    else
      echo "$b"
    fi
  done
}

say "swarm started"
while [ ! -f swarm/STOP ]; do
  waited=0
  while [ -n "$(pending_builds)" ] && [ ! -f swarm/STOP ]; do
    [ "$waited" -eq 0 ] && say "waiting for $(pending_builds | tr '\n' ' ')to merge on GitHub"
    sleep 60; waited=$((waited + 60))
    if [ "$waited" -ge 1800 ]; then
      say "gave up after 30 min on $(pending_builds | tr '\n' ' '): deleted. Check that auto-merge is allowed and main requires the tests check."
      for b in $(pending_builds); do git push -q origin --delete "$b"; done
      waited=0
    fi
  done
  [ -f swarm/STOP ] && break
  # Read Now fresh from main. If it is empty or escalated and there is no key for the
  # director, there is nothing to build: wait instead of spending a cycle on the scout.
  git fetch -q origin "$BASE" && git checkout -q --detach "origin/$BASE"
  if [ "$("$PY" swarm/state.py needs_director)" = yes ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    say "nothing to build: Now is empty or escalated and no ANTHROPIC_API_KEY is set. Checking again in 10 minutes."
    sleep 600; continue
  fi
  say "cycle starting"
  if bash swarm/run.sh; then say "cycle finished"; else say "cycle failed, continuing"; fi
  if [ -f workspace/ESCALATE.md ] && [ -s workspace/ESCALATE.md ]; then say "escalations waiting in workspace/ESCALATE.md"; fi
done
say "swarm stopped"
rm -f swarm/STOP
