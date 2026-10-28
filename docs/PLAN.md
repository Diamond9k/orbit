# Orbit build plan: a pyramid, V1 to V4, then done

Owner: Cooper. Runner: Claude Code on Cooper's Windows PC, Fable 5.1 with Ultracode.
Written 2026-10-26 from: the Orbit chat (2026-10-21 to 22), the Arc-OS repo on main, past design
gauntlet rounds, and a full scan of locallyuncensored.com (docs/SCAN-locallyuncensored.md).

## 0. What Orbit is (fixed, from Cooper)

One app to run any open model from Hugging Face, from an iPhone, on any size of compute. Two sides:
- **Use AI on private compute.** Your own PC runs it, free. No PC, or too small? Rent a GPU from a host.
- **Make money off your compute.** Install the helper, set your hours, earn a fixed hourly rate per tier.

Credits exactly as Cooper set them: users buy credits, Cooper sets every price, hosts get a fixed hourly
wage by GPU tier only while a rental runs, Orbit keeps the difference. Full spec: docs/MARKETPLACE.md.

From locallyuncensored.com we take the idea of the top bar (wordmark, short nav, GitHub and Discord
pills, one OS-aware Download), a public GitHub, a Discord, and a marketplace page. We beat it on the
weaknesses in SCAN section 6.

## 1. Why a pyramid

Each layer is everything the next layer stands on, built wide and all at once, then proven before
anything is stacked on it. Inside a layer, work runs in parallel lanes (Ultracode agents, one git worktree
each). Between layers, nothing moves until the layer's exit checks pass and Cooper merges.

```
                ┌──────────────────────┐
     V4  L4     │ Real money + launch  │
                ├──────────────────────┤
     V3  L3     │      Surfaces        │   site, app screens, helper UI, admin
                ├──────────────────────┤
     V2  L2     │       Engines        │   helper core, relay, marketplace engine, mobile core
                ├──────────────────────┤
     V1  L1     │     Foundation       │   repo, schema for everything, shared packages, protocol, test rigs
                ├──────────────────────┤
     V1  L0     │  Machine + accounts  │   tools on the PC, GitHub, Vercel, Supabase, Stripe test, Discord
                └──────────────────────┘
```

The rule that makes it a pyramid and not a staircase: **Layer 1 designs and migrates the data and the
protocol for every later feature at once**, the marketplace included, so Layers 2 and 3 never stop to
redesign the base. A later layer may add columns; it may not change what a lower layer promised.
Changing the base needs a new ADR and Cooper's yes.

## 2. How it is run: Arc's system, copied

Orbit runs on the Arc OS operating model in its own repo, with no Arc keys, memory or skills in it.

| Arc OS piece | Orbit copy |
|---|---|
| Root `CLAUDE.md` with numbered rules and a "where things live" table | `CLAUDE.md` in this repo |
| `.claude/settings.json` deny list (no .env reads, no push to main, no force push, no rm -rf) | same, in this repo |
| Branches only, `main` protected, PR per change; CI: lint, typecheck, test, build, gitleaks, Semgrep, npm audit | same CI, copied from Arc-OS |
| `docs/GATES.md` | in this repo |
| `docs/adr/` | ADRs 0001 to 0006 written in Layer 1 |
| `workspace/ARC-OS/` (router, skills, memory via `recall.mjs`, outputs, runs, `config/routines.json`) | `workspace/ORBIT/`, same layout |
| Studio gauntlet (bar, builder, blind critic, shuffler, swap-order check, ratchet) | `docs/GAUNTLET.md` |
| Under 60% sure, a person decides | Cooper decides, same rule |
| No sample data in a live panel | every number on the site and in the app is sourced or live |
| Nothing depends on Cooper's computer being on | Vercel, Supabase, cloud scheduled tasks |

## 3. Stack (ADR 0001)

- Monorepo, npm workspaces: `apps/web` (Next.js 16, Vercel), `apps/helper` (Tauri v2 + Rust, bundles
  llama.cpp server, detects Ollama and LM Studio), `apps/mobile` (Expo), `apps/relay` (the pairing and
  message relay, a small service on Vercel or Cloudflare, decided in ADR 0003), `packages/shared`
  (types from the schema, the fit calculator, the protocol, design tokens).
- Supabase for auth, Postgres and the ledger. RLS on every table from the first migration, explicit grants.
- Stripe for web credit purchases, Stripe Connect Express for host payouts, Apple in-app purchase for
  credits bought in the iPhone app.
- Phone to PC is end to end encrypted; keys are exchanged in the pairing QR; the relay forwards ciphertext only.
- Hugging Face Hub API for model search and file sizes.
- Licence: gate G1. We copy no code from LU, so its AGPL never reaches us.

## 4. The layers

Every layer ends the same way: exit checks pass, whole-layer audit by a fresh critic,
PR, Cooper merges, a handoff file. Within a layer, lanes run in parallel; the lead session merges lanes
and runs the exit checks.

### L0: Machine and accounts (V1, part 1). Interactive, Cooper at the keyboard, about 1 to 2 hours.

Goal: nothing later is blocked on a missing tool or account.

1. Inventory the PC and write `workspace/ORBIT/shared/outputs/<date>-machine.md`: Windows version, GPU and
   memory, NVIDIA driver and CUDA, Node, npm, Git, GitHub CLI and login, Rust and cargo, Visual Studio
   Build Tools (needed by Tauri), WebView2, Docker Desktop or WSL2 (needed for the host container), Vercel
   CLI, Supabase CLI, Stripe CLI, Expo/EAS CLI, Playwright browsers, Python, Ollama or LM Studio, free disk.
2. Install what is missing, asking before each install.
3. With Cooper: public repo `Diamond9k/orbit` (G1 licence), branch protection on `main`, Discussions on;
   Vercel project `orbit` on Cooper's own account, linked; Supabase project `orbit`; Stripe test mode
   account (G4); Discord server from the channel list (G3). Cooper adds every key himself in the dashboards.
4. Done: the plan is on `main` in the public repo `Diamond9k/orbit`.

Exit: every tool in the inventory runs `--version`; the repo, Vercel project and Supabase project exist and
a hello-world deploy succeeds from a PR preview.

### L1: Foundation (V1, part 2). One long Ultracode run, 5 parallel lanes.

Goal: the base for the whole product, including the marketplace, built and tested with no product UI.

- **Lane A, repo and ops.** Monorepo skeleton; copy from Arc-OS the CI workflow, biome, tsconfig, `recall.mjs`
  and its lib, `run-record.mjs`, PR template, CODEOWNERS (Cooper); rename to ORBIT. Community files:
  README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG, issue templates. Port the existing Orbit
  landing page as-is to `apps/web` so the waitlist keeps working while the real site waits for L3.
- **Lane B, data.** One migration set for every table in MARKETPLACE.md plus `waitlist`. RLS policies,
  explicit grants, the ledger as append-only double-entry with database functions for each posting type,
  and a constraint that every transaction sums to zero. Seed only the `price_book` with values marked `test`.
  Tests run against a local Postgres (PGlite, as Arc-OS does) for every policy and every posting.
- **Lane C, shared packages.** Types generated from the schema; the fit calculator (model files, quant and
  context in, memory needed and tier out) checked against at least 10 real Hugging Face models; `facts.json`
  and its checker; design tokens.
- **Lane D, protocol.** The wire spec between phone, relay and helper: pairing (QR carries the PC's public key
  and a one-time secret), session keys, message types (chat, model list, model load, rental start, heartbeat,
  rental end), versioning. Reference implementation in `packages/shared` with test vectors both sides must pass.
- **Lane E, test rigs.** `npm run floor` (Lighthouse, axe, links, console, facts check), Playwright screenshot
  rig, `scripts/gauntlet-shuffle.mjs`, a simulated host (a script that speaks the protocol and sends signed
  heartbeats) so L2 can test the whole marketplace without real GPUs.

ADRs written here: 0001 stack, 0002 ledger, 0003 E2E link and relay host, 0004 marketplace trust model,
0005 licence, 0006 pyramid rule (lower layers are frozen once merged).

Exit: CI green; every table has RLS tests; a scripted transaction that does not sum to zero is rejected;
protocol test vectors pass in TypeScript; the simulated host connects; the ported landing page and waitlist
still work on the preview.

### L2: Engines (V2). One long Ultracode run, 4 parallel lanes, all standing only on L1.

Goal: everything works end to end with test money and minimal screens.

- **Lane A, helper core (Rust).** GPU and memory detection, tier assignment, a measured tokens-per-second
  benchmark, llama.cpp server management, model download from Hugging Face with resume, own-PC mode over the
  L1 protocol, host mode with hours and pause, the rental container runner (only the model folder and GPU
  passed in), signed heartbeats. Windows installer built by GitHub Actions.
- **Lane B, relay and pairing.** The relay per ADR 0003; pairing; reconnect; rate limits; it never sees plaintext.
- **Lane C, marketplace engine.** The full rental state machine, matching (tier, hours, cached model,
  reliability floor), holds, per-minute metering from heartbeats, automatic refunds, disputes, weekly payout
  batching in Stripe Connect test mode, Stripe test-mode credit purchase and webhooks, nightly reconciliation
  job. Admin API for the price book. Every edge has a test, driven by the simulated host.
- **Lane D, mobile core (Expo).** Sign in, pair by one QR scan, chat with your own PC, model list with fit
  labels, rent a test GPU, see the wallet. Plain screens; looks come in L3. TestFlight build once G5 closes.

Exit (measured on a clean Windows VM and a real iPhone): install to first answer under 2.5 minutes; one-scan
pairing; chat works off the home network and the relay logs only ciphertext; a renter buys test credits,
rents a simulated host and a real second PC, both bill per minute, a forced failure refunds automatically,
the payout batch computes the right amount, and reconciliation balances to the cent.

### L3: Surfaces (V3). One long Ultracode run, 4 parallel lanes, then the gauntlet.

Goal: every screen people see, 2x the bar.

- **Lane A, website.** Top bar (wordmark; Run, Earn, Marketplace, Models, Pricing, Docs, Blog; live GitHub
  stars and Discord member pills cached 1 hour, a dash when unreachable; one OS-aware Download). Pages: `/`
  with the split hero, `/marketplace` with live online hosts per tier from the engine, `/models` with the fit
  checker on real Hugging Face sizes, `/pricing` (one table; "set at launch" until G6), `/download`, `/earn`,
  `/docs`, `/blog` with 3 founding posts, `/security`, `/privacy`, `/terms`, and `/admin` for Cooper only.
- **Lane B, iPhone app screens.** Home, Chat, Models, Machines, Wallet, Host mode view, Settings, onboarding
  ("Do you have a gaming PC?" splits into the two paths).
- **Lane C, helper UI.** First-run wizard, host dashboard (status, tier, current rental's model, earnings,
  pending payout, ratings), settings.
- **Lane D, content and community.** README final, docs site, Discord channel copy and pinned guides, 3 blog
  posts, the first 2 versus pages. Every number through `facts.json`.

Then the gauntlet (docs/GAUNTLET.md) on the site: 64 by round 1 or 2, 72 by round 3, 80 and 10/10 blind wins
to exit. The app task table in GAUNTLET.md must stay green.

Exit: site 80+ and 10/10 blind; every screen in the app and helper reachable and tested by Playwright or
Detox; a stranger on TestFlight completes both paths without help.

### L4: Real money and launch (V4). Shorter run, mostly sequential, every money step asks Cooper.

1. Live Stripe and Connect, Apple in-app purchase, the price book's live values from G6.
2. Security review of helper, relay, ledger and admin by a fresh critic; fixes merged.
3. Routines as cloud scheduled tasks (Arc `routines.json` shape): morning signups, revenue and host
   numbers to Cooper; nightly reconciliation; failure alerts.
4. Cut pass: every section, feature and setting answers "would anyone notice it gone?" Cut what fails.
5. Polish to Lighthouse 95+ on every page, axe 0 serious, LCP under 1.8 s on a 4G phone.
6. Launch: App Store submission, signed helper release (G8), Discord opens, launch posts.
7. Final gauntlet holds 80+ and 10/10 after the cuts. Done report. Stop.

## 5. When a layer misses its exit

Do not lower the bar and do not start the next layer.
1. Write what is short, by how much, with evidence.
2. Name the cause: plan, build, or bar. Plan and bar causes go to Cooper.
3. Build causes: one targeted chunk on only the short items, then re-run the exit checks.
4. Still short: popup to Cooper with options (fix in this layer, carry as the first item of the next layer
   with a written risk, or change the target in a new ADR).

## 6. Rules for every run

1. Branches only; Cooper merges. Lanes use worktrees and merge into the layer branch.
2. No made-up numbers. Unknown is shown as unknown.
3. Privacy claims exactly true (see MARKETPLACE.md, Trust and honesty).
4. Never copy LU's text, code, images, video or layout files.
5. Ask before anything that costs money, publishes, or can't be undone, with a popup and one recommended option.
6. Secrets: Cooper adds them. Never read `.env*`.
7. Usage pacing: 60% finish the current lane step, 80% start nothing new, 95% commit and write the handoff.
8. No em dashes in anything written.

## 7. Gates (docs/GATES.md)

G1 licence (L0), G2 domain (by L3), G3 Discord (L0), G4 Stripe test (L0) and live (L4), G5 Apple Developer
(by L2 for TestFlight), G6 prices and wages (by L4), G7 content policy (by L3), G8 code-signing cert (by L4).
