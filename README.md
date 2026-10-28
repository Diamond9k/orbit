# Orbit

**Run any open AI model from your iPhone, on any size of computer.**

Use your own PC for free. Rent a GPU from someone else when you need more power. Or rent out your
own GPU and get paid by the hour.

> **Status: planning.** This repo holds the full build plan. There is no app code yet. The first
> build step (V1) creates it. See [Roadmap](#roadmap) below.

---

## What Orbit is, in one minute

Open AI models (the free ones you can download from Hugging Face) need a strong computer to run.
Most people either have a gaming PC sitting idle, or no PC strong enough at all. Orbit connects both:

| If you... | Orbit lets you... | Cost |
|---|---|---|
| have a gaming PC | chat with models running on **your own PC**, from your iPhone, anywhere | Free |
| have no PC, or one that's too small | **rent GPU time** from someone else's PC, paid with credits | Credits |
| have a GPU you aren't using | **host**: set your hours, and earn a fixed hourly rate while someone rents it | You get paid |

Two promises the whole project is built around:

- **Private when it's yours.** Chats between your iPhone and your own PC are end to end encrypted.
  The relay in the middle only ever sees scrambled data.
- **Honest numbers.** Every number on the site or in the app comes from a sourced facts file or from
  live code. If something isn't known yet, it says so instead of guessing.

## How it works

```
   iPhone app  ──encrypted──▶  Relay  ──encrypted──▶  Your PC  (helper app runs the model)
                                  │
                                  └──────────────▶  A host's PC  (rented, paid in credits)
```

There are four pieces, all planned in this repo:

| Piece | What it does | Built with |
|---|---|---|
| **iPhone app** | Chat, pick models, pair with your PC, rent a GPU, see your wallet | Expo (React Native) |
| **Desktop helper** | Runs on a Windows PC. Detects the GPU, downloads and runs models, hosts rentals | Tauri v2 + Rust, llama.cpp |
| **Website and API** | Public site, marketplace, pricing, accounts, payments | Next.js on Vercel |
| **Database** | Accounts, rentals, and a double-entry credit ledger | Supabase (Postgres) |

Payments run through Stripe (website), Stripe Connect (host payouts) and Apple in-app purchase (iPhone).

## The marketplace, briefly

- Renters buy credits. Orbit sets the price of a credit.
- GPUs are sorted into three tiers by memory: **Basic**, **Pro** and **Max**. The helper detects the tier;
  hosts never type it.
- Each tier has a set rent (credits per hour) and a set host wage (dollars per hour). Hosts don't set prices.
- Hosts only earn for minutes a rental is actually running. Failed rentals refund automatically.
- Every credit movement is recorded twice (double-entry), so the books always balance.

Prices are not decided yet. Until they are, the site shows "set at launch". Full details:
[docs/MARKETPLACE.md](docs/MARKETPLACE.md).

## Roadmap

Orbit is built as a **pyramid**: each layer is finished and proven before the next one starts.

| Version | Layer | What gets built | State |
|---|---|---|---|
| V1 | L0 + L1 | Tools and accounts, then the foundation: repo setup, full database schema, shared code, encryption protocol, test rigs | Next up |
| V2 | L2 | Engines: the desktop helper, the relay, the marketplace engine, the core iPhone app | Planned |
| V3 | L3 | Everything people see: website, app screens, helper screens, docs and blog | Planned |
| V4 | L4 | Real payments, security review, polish, App Store and launch | Planned |

Each layer has written exit checks in [docs/PLAN.md](docs/PLAN.md). A layer that misses them is fixed,
never waved through.

## Find your way around

| File | Read it to learn |
|---|---|
| [CLAUDE.md](CLAUDE.md) | The project rules (start here if you're contributing) |
| [docs/PLAN.md](docs/PLAN.md) | The full build plan, layer by layer, with exit checks |
| [docs/MARKETPLACE.md](docs/MARKETPLACE.md) | How renting, hosting, credits and payouts work |
| [docs/SCORECARD.md](docs/SCORECARD.md) | How the website's quality is scored (10 dimensions, 100 points) |
| [docs/GAUNTLET.md](docs/GAUNTLET.md) | The review loop: one builds, independent reviewers judge blind |
| [docs/GATES.md](docs/GATES.md) | Decisions and accounts the owner still has to provide |
| [docs/SCAN-locallyuncensored.md](docs/SCAN-locallyuncensored.md) | Notes on the competitor site used as the quality bar |
| [docs/ULTRA.md](docs/ULTRA.md) | The one-run version of the build plan (wins over PLAN.md where they differ) |
| [docs/PROMPTS.md](docs/PROMPTS.md) | The exact prompts used to run each layer |
| [KICKOFF.md](KICKOFF.md) | The first prompt that starts the V1 build |

### Planned folder layout

These folders are created during V1 and don't exist yet:

```
apps/web/          website and API (Next.js, Vercel)
apps/helper/       desktop helper (Tauri + Rust)
apps/mobile/       iPhone app (Expo)
apps/relay/        pairing and message relay
packages/shared/   shared types, protocol, fit calculator, design tokens
supabase/          database migrations
docs/adr/          architecture decision records
workspace/ORBIT/   agent workspace (memory, outputs, routines)
```

## How work happens here

- **`main` is protected.** All changes go through a branch and a pull request. The owner merges.
- **No secrets in the repo.** API keys live only in the Vercel, Supabase and GitHub dashboards.
- **No copying.** Other products are studied for ideas, never copied (text, code, images or layout).
- Once code exists, every PR must pass: `npm run lint`, `npm run typecheck`, `npm test`,
  `npm run build` and `npm run floor`.

## Licence

[Apache-2.0](LICENSE).
