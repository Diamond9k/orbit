# Scan: Vast.ai

Read 2026-10-28, from Vast's own pages and docs through search snippets. Direct fetches were
blocked by the cloud session's network policy, so numbers below are what their pages state,
not independently verified. Where their pages contradict each other, both are shown.

## What it is
A marketplace where anyone with NVIDIA GPUs lists them and renters launch Docker containers.
Renters pick a template (image plus settings), filter offers by GPU, click Rent, get a Linux
container. Built for people comfortable with Docker and a terminal.

## Renter pricing
| Item | What Vast says |
|---|---|
| On-demand | fixed hourly rate, per-second billing, guaranteed uptime |
| Interruptible | bidding; highest bid runs, others pause; "50% or more" cheaper |
| Reserved | prepaid, up to 50% off |
| Minimum deposit | $5 before starting anything |
| Storage | billed while the instance exists, even stopped; rate set by host |
| Bandwidth | per GB up and down; rate set by host |
| Balance at zero | instances stop, card on file is charged |

## Host side
| Item | What Vast says |
|---|---|
| OS | Ubuntu Server 22.04 minimum, 24.04 recommended, server edition only |
| GPUs | NVIDIA Maxwell or newer, all the same model, over 7 GB each |
| CPU and RAM | 2 cores per GPU; RAM at least 95% of total GPU memory |
| Disk | SSD, 200 GB dedicated partition for Docker |
| Network | 500 Mbps both ways, public IPv4, no CGNAT, 5 to 100 open ports per GPU |
| Payout | weekly on Fridays via Wise, PayPal or Stripe; first payout up to two weeks |
| Fee | contradictory: a help FAQ says hosts keep 75%; a June 2024 update and the calculator say no fee |
| Minimum payout | contradictory: docs say $20, calculator says none |

## Security, in their words
- Tenants run in unprivileged Docker containers with separate namespaces and filesystems.
- Two tiers: "Verified Hosts" for general work, "Secure Cloud" for sensitive work, limited to
  datacenters with signed data agreements and ISO 27001 or Tier 3/4 facilities.
- Their FAQ says community hosts "may have less formal security measures" and argues hosts
  have little to gain from stealing data.
- Company-level SOC 2 Type II; HIPAA workloads only on Secure Cloud.

## What it means for Orbit
1. Vast is for people who already know Docker. Orbit's user types a model name and clicks
   Start. That gap is the whole opening.
2. Vast's host bar locks out the gaming PC behind a home router. Orbit's host program must
   install like an app and only dial out (rule 9).
3. Vast already labels hosts in two tiers. Orbit's community and verified split is the same
   honest shape.
4. Vast does not promise privacy on community hosts either. Orbit says nothing and builds the
   broker so it cannot look (rule 1).
5. Vast's fee is unclear on its own site. Orbit's one number, stated once, is a credibility win.
6. No bidding on Orbit (decision 2026-10-28). A session is never paused because someone outbid you.

## Sources
vast.ai/hosting, cloud.vast.ai/host/setup, docs.vast.ai/host/payment, vast.ai/hosting/calculator,
the June 2024 product update article, docs.vast.ai/guides/instances/pricing, the quickstart,
cdn.vast.ai/faq, docs.vast.ai/guides/reference/faq/security, vast.ai/compliance,
docs.vast.ai/creating-a-custom-template, docs.vast.ai/guides/instances/choosing/find-and-rent.

## Where the scan stopped, and what is next
- Direct reads of vast.ai were blocked. To read pages first-hand, allow `vast.ai` and
  `docs.vast.ai` in the session's network settings, then verify the fee and minimum payout.
- Not yet scanned, same questions each (renter flow, host bar, fee, tiers, what it means for
  Orbit): RunPod community cloud, Salad, io.net, Akash. Pick the one closest to home PCs
  first; Salad is the one that targets ordinary gaming rigs.
- The original reference scan (locallyuncensored, read 2026-10-26) was in the repo before it
  was cleared and is not restored here. Re-read it if that reference still matters.
