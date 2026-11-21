# A public sandbox on Vercel

> Later the same day Orbit dropped all money (2026-11-20-self-hosting-only.md). The sandbox stays.
> Read "test funds", "cards" and "Stripe" below as gone: each guest now gets simulated machines.

Date: 2026-11-20. Asked for by Cooper: put Orbit on a Vercel address, sandboxed, so a possible
co-founder can look at it.

## Decision
The public address runs the real web app in sandbox mode (`ORBIT_SANDBOX=1`, `orbit/sandbox.py`).
The booking, the minute clock, the ledger and the key exchange are the real code paths. The
machines are simulated, the money is test funds, and replies are scripted and say so.

## Why this does not break the rules
- Rule 7 (no paid cloud): the sandbox is a demo address, not where Orbit runs. The real broker
  still runs on one ordinary machine with `python -m orbit`. Nothing in the app depends on Vercel.
- Rule 5 (no claims): every page in the sandbox says it is a sandbox. The session page says the
  simulated host runs on Orbit's own server, so the sandbox shows how sealing works, not privacy.
- Rule 3 (nothing is free): test funds exist only in the sandbox and in dev mode.

## What the sandbox refuses
Email accounts, cards, the Stripe hook and the host API. A guest sees the sandbox machines and
their own, never another guest's text. Data is wiped when it grows past the limits in
`orbit/sandbox.py` or when the server restarts (Vercel keeps only `/tmp`).

## Not decided here
A real public network address. That still waits on docs/NEXT.md ("a real domain and a small
rented box").
