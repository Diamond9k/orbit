# Orbit is a broker, not a middleman

Date: 2026-10-28

Conversations go from the user's browser to the host's machine. Orbit relays sealed
envelopes encrypted end to end with a key only the browser and the host program hold.
Orbit cannot read them even if it wanted to.

Why: it lets Orbit say nothing about privacy and still be believed. The host program only
dials out, so this also solves the home router problem with nothing for the host to
configure.

Rejected: Orbit as a plain relay that can see traffic (breaks the thesis), fully
peer-to-peer with no broker (years of work, no referee for payments), third-party tunnels
like Cloudflare or Tailscale (a datacenter dependency).
