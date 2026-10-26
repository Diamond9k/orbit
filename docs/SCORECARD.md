# Scorecard: the cap, the bar, and 2x

## The cap

100 points = a site with nothing left to improve on any of ten dimensions. Each dimension is 0 to 10.
A 10 means a hostile critic, given a day, cannot name a change that would make it better for the
person it serves. Nobody sits at 100; the best product sites in the world land in the low 90s.

| # | Dimension | What a 10 looks like |
|---|---|---|
| D1 | 5-second clarity | A stranger says what it is, who it is for, and what to do next, after 5 seconds, unprompted |
| D2 | Visual craft | One clear idea, consistent type scale and spacing grid, measured contrast, motion that explains |
| D3 | Structure and scannability | Every section earns its place; headings alone tell the story; no section repeats another |
| D4 | Conversion path | One obvious next step per audience, reachable from every viewport and every page |
| D5 | Proof and trust | Every claim is sourced or demonstrated; security and privacy claims are exactly true |
| D6 | Pricing clarity | A visitor can predict their bill for their use in one look, in their currency |
| D7 | Content and search depth | Answers the questions people search, with pages that rank and help |
| D8 | Community and open source surface | Public repo, contribution path, live community, release notes, all one click away |
| D9 | Consistency and accuracy | No two pages, the README, or the app disagree on any number or claim |
| D10 | Performance and accessibility | Lighthouse 95+ in all four, axe 0 serious, LCP under 1.8 s on 4G phone, works keyboard-only |

## Where locallyuncensored.com sits (provisional)

Scored from text, structure, the pricing page and the repo on 2026-10-26. D2 and D10 are marked
provisional: V1's first job is the visual and Lighthouse pass, and those two scores get replaced by
measured ones. The other eight carry evidence from SCAN-locallyuncensored.md.

| # | Score | Evidence |
|---|---|---|
| D1 | 5 | H1 is clear, but the page sells three things (local app, cloud, uncensored) at equal volume |
| D2 | 6* | Dark theme, per-feature demo videos; dense text blocks; no visual measure yet |
| D3 | 4 | 7 feature sections plus cloud, offer, models, why, blog, FAQ, and the download block twice |
| D4 | 6 | One-click OS download and no-account demo are strong; duplicate labels and two "Cloud" links cost it |
| D5 | 8 | Open source, SECURITY.md, antivirus explainer, signed updates, captioned demos |
| D6 | 4 | Credits as "OR" alternatives, 125 SKUs, EUR only, checkout on another domain |
| D7 | 9 | 15+ guides and versus pages, model pages, machine-readable facts |
| D8 | 8 | Public repo with full hygiene, Discord, Discussions, release notes in app |
| D9 | 4 | At least 6 contradictions (stars, model counts, refusal rate, macOS, remote-access privacy) |
| D10 | 6* | Many autoplay videos and a marquee on one page; not measured yet |
| **Total** | **60 / 100** | **The bar** |

## 2x the bar

A literal 2x of 60 is 120, which the cap does not allow. So 2x is defined on what is left to fix:
LU is 40 points short of the cap. **2x as good means half the shortfall: 20 points short, so 80 / 100.**
On top of the number, Orbit must win the blind side-by-side against LU on every one of the ten
dimensions (see GAUNTLET.md). A higher total that loses a dimension blind is not done.

| Version | Website target | Blind wins vs LU (of 10) |
|---|---|---|
| V1 | 64 (beats the bar) | 5 |
| V2 | 72 | 8 |
| V3 | 80 (2x) | 10 |
| V4 | 80 held after cuts, measured, with real users on it | 10 |

## How a score is given

- Two fresh critics score independently. Each score cites one measurement or one quoted line.
- The lower of the two is recorded. Scores are never averaged (they drift up).
- If the critics differ by 3 or more on a dimension, or either says it is under 60% sure, Cooper decides.
- The scorer never sees which build is ours or how many rounds have run.
