# Scan: locallyuncensored.com (read 2026-10-26)

The reference Orbit has to beat. Read from the live homepage, /pricing/, and the public repo
PurpleDoubleD/locally-uncensored. Text and structure only; the V1 run adds the visual pass
(screenshots at 390 / 768 / 1440 px, light and dark, Lighthouse, axe) before scores are final.

Licence for our use: comparison-only. The critic may see it. The builder never copies its text,
code (AGPL-3.0), images, video or layout files. Gap notes go to the builder in words.

## 1. What it is

One product with two halves:
- **Locally Uncensored (LU)**: a free, open-source desktop app (Tauri v2 + Rust, React 19, TypeScript,
  Tailwind 4, Vite 8). Chat, image and video (via a ComfyUI it installs), a coding agent, an agent mode
  with tools and MCP, voice, computer control, and remote access from a phone. Windows, Linux,
  Apple Silicon Mac (beta), Android APK. Version 3.0.7. Claims 170,000+ downloads.
- **LU Cloud** on lu-labs.ai: the same catalog on hosted GPUs, paid with credits. Plans EUR 19 / 49 / 99
  a month (900k / 2.35M / 5M credits) or one-time packs EUR 15 to 300 that never expire.

Positioning: "uncensored" (abliterated models that answer instead of refusing), private in local mode,
free locally, pay only for cloud.

## 2. The homepage, top to bottom

**Meta and share**: title "Uncensored AI Studio: Free, Open Source Chat, Image, Video". Full OG and Twitter
cards with a 2752x1536 social image, theme colour #0a0a0a (near-black dark theme), author PurpleDoubleD.

**Top bar** (the part Cooper likes):
- Left: wordmark "Locally Uncensored".
- Middle links: What, Models, Pricing, Cloud, Setup, Blog, FAQ (anchors plus two pages).
- Right: live-ish proof pills "2000+ ⭐" (GitHub) and "1200+ 🟢" (Discord), a "Cloud" button,
  then a single **Download** button that resolves per OS (three same-label links in the markup:
  .exe, .dmg, .AppImage).
- Under it, an announcement strip: "LU Cloud is live. No GPU? Run it in your browser".

**Hero**: H1 "Uncensored AI, on your PC or online". Line: "the plug-and-play AI studio · Chat · Code ·
Image · Video · Remote". One paragraph defining uncensored AI with a link to an explainer page.
Primary CTA "Try LU Cloud in this browser" (demo, no account). Fine print with pricing floor. A
"send the link to yourself" affordance for phone visitors.

**Two download cards side by side**:
1. Desktop: version 3.0.7, platforms, 170,000+ downloads, three OS buttons, Android APK line with size
   and min version, small print on OS support, .deb and .rpm links.
2. LU Cloud: "no GPU needed, Mac, phone, packs from 15 EUR", link to plans.
Under them a utility row: What's new, Join Discord, All releases, Source on GitHub, Discussions,
"Antivirus warning?" (links SECURITY.md).

**Demo reel**: "Generate Anything. Locally. Uncensored." A 16-second video with 5 tabs (Chat, Image,
Video, Edit, Code) showing one character carried through every tool. Captioned for accessibility.

**Proof marquee**: scrolling strip of 9 facts (downloads, stars, AGPL, local privacy, 12 backends,
75+ one-click models, 3 OSes, 2,200+ automated checks), repeated for the loop.

**No GPU section**: why the cloud exists, an explainer video (local vs cloud routing), four stat
blocks (47 chat models, 19/44 answer without refusal, 7 image + 14 video models, EUR 19), then four
cards (chat online, image generator online, video generator online, API) with per-unit prices
(image about 2 to 3 cents, 5-second clip about 21 to 33 cents) and an OpenAI-compatible API on port 8129.

**Current Hosted offer**: a dense paragraph block on Flash models, daily allowance, the shared
900,000-credit wallet expressed as alternatives (900 images OR 90 clips), and caveats. Links to a
Venice comparison and a machine-readable `cloud-facts.json`.

**The studio, 7 numbered features**, each with headline, paragraph, a 3 to 4 step mini-sequence, model or
tool chips, and its own captioned demo video:
01 Chat (no refusal demo), 02 Create (12 modes), 03 Code (diff first), 04 Agent Mode, 05 Remote
(phone, QR + 6-digit code), 06 Voice (beta), 07 Computer control (beta, asks before every action).

**What's new**: release notes promise and three links (latest notes, changelog, blog).

**Setup in 3 steps** ("Running in under five minutes"): Install, Wizard finds everything, Run, plus a
first-start demo video and a link to the handbook.

**Models**: six model cards (Gemma 4, Qwen 3.8 / GPT-OSS / GLM, Juggernaut XL, Z-Image Turbo, LTX 2.3,
FramePack F1) each tagged with a hardware fit line.

**Why**: two paragraphs on privacy, free, open source, 2,200+ checks.

**Writing**: 15 blog cards (guides, comparisons, versus pages). This is a large SEO engine.

**FAQ**: 10 questions (what is it, model support, ChatGPT alternative, free and offline, vs Open WebUI and
LM Studio, hardware, what uncensored means, remote access leaks, voice, computer control, macOS).

**End CTA**: repeats the hero CTA and both download cards.

**Footer**: about 21 links (guide, pricing, cloud, three "online" landing pages, alternatives, is it safe,
remote access, Discord, GitHub, Discussions, Issues, Reddit, LinkedIn, Privacy, Terms, Impressum).

## 3. Pricing page

Own slimmer nav (Home, Chat, Images, Video, Pricing, proof pills, Download). Dated "October 5, 2026".
Three plan cards (Hosted EUR 19, Pro EUR 49 "most popular", Max EUR 99) with monthly or annual. Full tables:
9 image models and 17 video models with credits per run and max runs per plan, a 64-row Create Studio
table, five credit packs, the full 125-model catalog, three policy notes, and a machine-readable data link.
Checkout happens on lu-labs.ai with "neutral product language" on the payment page.

## 4. The GitHub repo (what makes it feel real)

Public, AGPL-3.0, 1.8k stars, 289 forks, 2,611 commits, 13 open issues. README: logo, 6 badges
(licence, stars, last commit, discussions, Discord, website), demo GIF, 2x2 screenshot grid, anchor nav,
download table by platform, "what is new", three steps, build-from-source, "what is in the box",
a 14-row comparison table vs Open WebUI / LM Studio / Jan / SillyTavern, model tables by VRAM,
bring-your-own-engine list (14 engines), FAQ, roadmap checklist, tech stack, community, licence.
Repo hygiene: CODE_OF_CONDUCT, CONTRIBUTING, SECURITY (antivirus false positive explained, signed
update channel with a public minisign key), CHANGELOG, issue templates, Playwright e2e, Vitest,
ESLint, GitHub Actions builds the installers.

## 5. What works (keep the idea, never the expression)

1. Download is one click from the top bar on every page, resolved to your OS.
2. Proof lives in the nav: star count and Discord count as small pills.
3. Every feature has a short captioned demo video, not a screenshot.
4. Hardware honesty: "what fits your PC" is everywhere.
5. Trust surfaces: open source, SECURITY.md, antivirus explainer, signed updates.
6. A no-account demo as the primary CTA.
7. Machine-readable facts file behind the public numbers.
8. A content engine (guides, versus pages, model pages) for search.
9. Community loop: Discord, Discussions, Issues, release notes shown in-app.

## 6. Where it is weak (where Orbit wins)

1. **Contradictions in its own numbers.** Nav says 2000+ stars, the repo shows 1.8k. Chat models: 47 in a
   stat, 48 in the card and on pricing. No-refusal: 19/44 on the site, 24/46 in the README. Image and video
   models: 7 + 14 on the home stat, 9 + 17 on the cloud note, 18 image models in the catalog. macOS: the site
   says Apple Silicon beta since 3.0.6, the README says there is no macOS desktop build and lists v3.0.2.
2. **Contradictory trust message.** The site FAQ says remote access over the internet is relayed by
   Cloudflare and not end to end, so Cloudflare could read it. The README answers the same question "No."
3. **Wall of words.** The cloud offer is paragraphs of caveats. The 5-second read of the page is unclear:
   local app, cloud service, or uncensored chatbot.
4. **Pricing needs a calculator.** Credits as "900 images OR 90 clips" alternatives, 125 SKUs, EUR only,
   checkout on a second domain.
5. **Nav noise.** "Cloud" appears twice pointing to different pages; three Download links share one label.
6. **No second side.** Nobody can earn. Compute is LU's own cloud or yours, nothing in between.
7. **Phone is a remote, not a product.** Pairing is QR plus a 6-digit code, and off-LAN traffic is not
   end-to-end encrypted.
8. **Uncensored is the brand.** That limits who will share it, pay for it, and which payment and app stores
   will carry it.
