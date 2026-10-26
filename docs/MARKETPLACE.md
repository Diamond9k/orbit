# The marketplace

Where renters get GPU time from hosts, paid in credits, with Orbit in the middle setting every price.
Built across the pyramid: data in Layer 1, engine in Layer 2, screens in Layer 3, real money in Layer 4.

## The money model (Cooper's, unchanged)

- A renter buys credits. Cooper sets what a credit costs.
- Each GPU tier has a rent price in credits per hour, set by Cooper.
- Each tier has a fixed host wage in dollars per hour, set by Cooper. Hosts never set prices.
- The host earns only for minutes a rental is actually running.
- Orbit keeps the difference between what the renter spent and what the host earned.
- Own-PC use never touches credits.

All three numbers live in one `price_book` table with an effective date, so a price change never
rewrites history and every past rental can be recomputed exactly. Until gate G6 closes the table holds
test values marked `test`, and the site shows "set at launch".

## Tiers

Set by GPU memory, detected by the helper, never typed by the host.

| Tier | GPU memory | Typical cards | What it runs |
|---|---|---|---|
| Basic | 8 to 12 GB | 3060, 4060, 4070 | up to about 8B to 14B at 4-bit |
| Pro | 16 to 24 GB | 4080, 3090, 4090 | up to about 32B at 4-bit |
| Max | 32 GB and up | 5090, workstation cards | about 70B at 4-bit |

## Data (Layer 1 migration, all tables with RLS and explicit grants)

| Table | Holds |
|---|---|
| `profiles` | user id, display name, roles (renter, host), country, created |
| `devices` | a user's PCs and phones, public keys, last seen |
| `hosts` | host profile, payout account status (Stripe Connect), verification level, hold until |
| `gpus` | per device: model, memory, tier, driver, measured tokens per second on the test model |
| `availability` | host-set hours per device, timezone, paused flag |
| `price_book` | tier, credit price, rent credits per hour, host wage per hour, effective from, test or live |
| `rentals` | renter, device, tier, model, state, started, ended, minutes billed |
| `rental_heartbeats` | one row per minute a rental runs, signed by the helper |
| `ledger_accounts` | one per user wallet, plus Orbit revenue, host payable, Stripe clearing, refunds |
| `ledger_entries` | double-entry rows; every transaction sums to zero; append-only |
| `payouts` | batch, host, amount, Stripe transfer id, state |
| `ratings` | renter rates a finished rental; host reliability is computed, not typed |
| `disputes` | rental, reason, state, outcome |
| `audit_log` | every admin action and every price change |

## The rental lifecycle (Layer 2 engine, a state machine with tests for every edge)

`requested` → `matched` → `loading` (host downloads or opens the model) → `running` → `ended` | `failed` | `cancelled`

- **Match**: cheapest host in the needed tier that is online, in its hours, has the model cached if possible
  (cached hosts preferred, which is the "popular models ready" idea), and has a reliability score above the floor.
- **Hold**: on match, one hour of credits moves from the renter's wallet to a hold account.
- **Meter**: the helper sends a signed heartbeat each minute. Each heartbeat posts: renter hold to Orbit
  revenue (the rent), Orbit revenue to host payable (the wage). Missing heartbeats stop billing.
- **End**: unused hold returns to the renter. The host payable stays until the payout batch.
- **Fail**: a rental that fails in `loading` or in its first 2 minutes refunds in full, automatically.
- **Payouts**: weekly batch through Stripe Connect; new hosts have a 14-day hold; disputes freeze that rental's amount.

A nightly reconciliation proves: credits sold = credits spent + credits held + credits in wallets, and
host payable = sum of billed heartbeat wages minus paid out. It alerts Cooper on any difference.

## Host side (helper)

- Host mode is off until switched on. The host picks hours and can pause any time; a pause during a rental
  ends it cleanly and the renter is refunded the unused part.
- Rentals run in an isolated container with only the model folder and the GPU passed in. No access to the
  host's files, network beyond the relay, or other processes.
- Host dashboard: online status, tier, current rental (model only, never the renter's messages), earnings
  today, this week, pending payout, and ratings.

## Renter side (app and web)

- Machines screen: "My PC" first, then available tiers with credits per hour and a live count of online hosts.
- The model picker marks what fits each tier. Picking a model that does not fit any tier says so plainly.
- Wallet: balance, buy credits, history of every rental with minutes and credits.

## Trust and honesty

- The site says exactly what rentals guarantee: an isolated container, no host login to it, no logs kept by
  Orbit. It does not say the host physically cannot read memory on a machine they own. Own-PC mode is the
  private one, end to end encrypted.
- Content policy (gate G7) is accepted by hosts and renters before their first rental.
- Hosts and renters can report; reports open a dispute and can pause a host.

## Where it shows up

| Surface | Layer | What |
|---|---|---|
| `/marketplace` on the site | 3 | live online host count per tier, prices, "become a host", host waitlist until launch |
| iPhone app | 3 | Machines, Wallet, rental flow, rating |
| Helper | 2 engine, 3 UI | host mode, container runner, heartbeats, dashboard |
| Admin page `/admin` (Cooper only) | 3 | price book, hosts, rentals, disputes, payouts, reconciliation status |
| Discord | 0 and 3 | `#marketplace` channel, host announcements |
