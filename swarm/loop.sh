#!/usr/bin/env bash
# Run the swarm forever: one cycle after another, until a file named swarm/STOP exists.
#
#   swarm/loop.sh                   cycles back to back
#   PAUSE=1800 swarm/loop.sh        wait 30 minutes between cycles (caps cost)
#   touch swarm/STOP                stops after the current cycle
#
# Before each cycle it waits for the previous build/ branch to merge, so the director never
# plans on top of work that has not landed, and deletes build/ branches that have merged.
set -uo pipefail
cd "$(dirname "$0")/.."
PAUSE="${PAUSE:-0}"
LOG="workspace/runs/loop.log"
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

say "loop started (pause between cycles: ${PAUSE}s)"
while [ ! -f swarm/STOP ]; do
  waited=0
  while [ -n "$(pending_builds)" ] && [ ! -f swarm/STOP ]; do
    [ "$waited" -eq 0 ] && say "waiting for $(pending_builds | tr '\n' ' ')to merge on GitHub"
    sleep 60; waited=$((waited + 60))
    if [ "$waited" -ge 1800 ]; then say "still waiting after 30 min; check GitHub auto-merge settings"; waited=0; fi
  done
  [ -f swarm/STOP ] && break
  say "cycle starting"
  if bash swarm/run.sh; then say "cycle finished"; else say "cycle failed (exit $?), continuing"; fi
  [ -f swarm/STOP ] && break
  [ "$PAUSE" -gt 0 ] && { say "pausing ${PAUSE}s"; sleep "$PAUSE"; }
done
say "loop stopped"
rm -f swarm/STOP
