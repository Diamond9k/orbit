# Scan: WiCi

Read 2026-11-02 from search snippets of press coverage. Direct fetches (tomshardware.com,
gizmodo.com, calendar.hkust.edu.hk) were blocked by the cloud session's network policy, and
WiCi's own site was not read. Every number below is WiCi's claim as reported by the press, not
verified. Where reports contradict each other, both are shown.

## What it is
Not a marketplace and not a competitor in Orbit's sense. WiCi is a Palo Alto hardware startup
selling **WiCi One**: a box holding an NVIDIA GPU plus a small PC, which shares the GPU with
laptops, phones and other devices on the same Wi-Fi 7 network. Marketed for gaming and for
local AI. Reviewers call it "a local server by any other name".

## The product
| Item | What the press reports |
|---|---|
| Base model | RTX 5060 Ti 16 GB, Intel Core 3 100U, 1 TB NVMe |
| Top model | RTX 5090 32 GB, Core Ultra 7 (225H or 255H, reports differ), 4 TB; "in development" |
| Price | contradictory: base $1,999 or $2,599; RTX 5090 $2,599, $9,999, or "not announced" |
| Status | preorders open; first units Q4 2026 (one Japanese report: December) |
| Link | Wi-Fi 7, ~11.5 Gbps theoretical, far below a wired eGPU; WiCi says caching, compression, dedup, streaming and pipelining make up for it |

## Software, in their words
- Driver mode: a virtual GPU driver makes the remote card look local to a nearby computer.
- SDK mode: Python, JavaScript and Swift libraries.
- API mode: an OpenAI-compatible endpoint (one report; not confirmed by a second).
- "TurboStream": pages weights from the 4 TB SSD to run models larger than VRAM (one report).
- A scheduler shares GPU memory between several local devices and reuses shared weights.
  One reviewer called shared local inference the strongest case for the product.

## Performance, in their words
- 140 tokens/s on Gemma 4 26B (RTX 5060 Ti); over 500 tokens/s (RTX 5090). WiCi's numbers.
- A Gizmodo hands-on saw the RTX 5090 unit run DeepSeek-V3 and called the demo unremarkable.
- Latency figures are not public. Several outlets say the gaming claims outrun the evidence.

## Company
- Palo Alto. Founders, investors and funding: not found.
- An HKUST ECE seminar, "WiCi: Wireless GPU Computing Infrastructure" (speaker Prof. Zili
  Meng), describes mobile devices offloading GPU work to a nearby GPU over Wi-Fi. Same name and
  idea; a link to the startup is not confirmed.

## What it means for Orbit
1. WiCi sells the box; Orbit pays the box. A WiCi One owner has a GPU idle most of the day and
   is exactly the kind of host Orbit wants. If it ships with an ordinary OS and NVIDIA driver,
   the host program should run on it like any other PC.
2. WiCi is local only: one household or office, one Wi-Fi network. Orbit is the reach beyond
   the router. They do not overlap on the user side; the browser user never needs to buy $2k+
   of hardware.
3. Their pitch ("make a GPU usable from anything nearby, no cables, no setup") is the same
   simplicity bar as rules 8 and 9. Worth watching their onboarding when units ship.
4. Their OpenAI-compatible endpoint and weight paging, if real, are the same ideas Orbit will
   need for bigger models on small hosts. Nothing to copy until it is measured.
5. Their performance numbers are claims. Orbit shows only measured numbers (rule 5); if WiCi
   boxes become hosts, their tokens/s on the site come from sessions, not from WiCi's sheet.

## Sources
tomshardware.com (WiCi One unveil), gizmodo.com (hands-on), techradar.com, techspot.com,
notebookcheck.net, guru3d.com, tweaktown.com, digitalcitizen.life, remio.ai, club386.com,
letsdatascience.com, digitaltoday.co.kr, gizmodo.jp, calendar.hkust.edu.hk/node/46526.

## Where the scan stopped, and what is next
- Allow WiCi's own site and the outlets above in the session's network settings to read them
  first-hand: settle the price, the OS on the box, and whether the API mode exists.
- When units ship: does the host program run on a WiCi One unchanged? That is the only
  question that moves hosts paid.
