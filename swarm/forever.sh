#!/usr/bin/env bash
# The swarm never turns off. Cycle after cycle on the local model, which is free.
# Claude is called only when the plan runs dry or a sensitive change needs a final look.
#
#   swarm/forever.sh            start
#   New-Item swarm/STOP         (PowerShell, another window) stop after the current cycle
#
# Before each cycle it waits for the previous build/ branch to merge on GitHub, so the
# director never plans on top of work that has not landed, and deletes merged build/ branches.
set -uo pipefail
cd "$(dirname "$0")/.."
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
    if [ "$waited" -ge 1800 ]; then say "still waiting after 30 min: check that auto-merge is allowed and main requires the tests check"; waited=0; fi
  done
  [ -f swarm/STOP ] && break
  say "cycle starting"
  if bash swarm/run.sh; then say "cycle finished"; else say "cycle failed, continuing"; fi
  if [ -f workspace/ESCALATE.md ] && [ -s workspace/ESCALATE.md ]; then say "escalations waiting in workspace/ESCALATE.md"; fi
done
say "swarm stopped"
rm -f swarm/STOP
