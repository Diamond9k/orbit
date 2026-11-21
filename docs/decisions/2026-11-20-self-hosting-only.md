# Self-hosting only. No money.

Date: 2026-11-20. Decided by Cooper.

## Decision
Orbit is for pure self-hosting of any open model. A person runs models on machines they own.
There is zero renting of other people's compute, in either direction. Orbit charges nothing.
It is a passion project, not a business.

Cooper's reason: charging a fee for this contradicts the moral standpoint of the project.

## What this replaces
- 2026-10-28-broker-not-middleman.md: there is no broker. The relay idea stays: it passes
  sealed envelopes between a person's browser and that person's machine.
- 2026-10-28-no-free-tier-no-bidding.md: everything is free. There is nothing to bid on.
- The goal "pay hosts one million dollars" in CLAUDE.md.
- The marketplace version stays in Git: branch `claude/orbit-sandbox` and `main` before this merge.

## What changed in the code
- Removed: `orbit/ledger.py`, the store, Stripe, test funds, prices, Orbit's cut, the
  out-of-time rule, the `stripe` requirement.
- A machine has no price. Only its owner sees it and starts models on it.
- An old database loses its price and cost columns on start. An old `ledger` table is left alone.
- Signed out, the start page answers "will it fit?" for common GPU memory sizes.
- The sandbox gives each guest simulated machines of their own.

## What got better because of it
The host is now the user. So the hard privacy problem of the old design (the host reads
everything, and only enclave hardware could stop a stranger) is gone. One gap is left: a
dishonest relay could swap keys. With a stranger's machine that needed attestation. With your
own machine a short fingerprint shown on both ends closes it. That is now item 1 in docs/NEXT.md.

## Loose ends, closed the same day
- The swarm stays. Its prompts now name the new goal, and its scoreboard counts use.
- The marketplace documents stay as history. Each one says so in its first lines.
