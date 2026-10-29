# The privacy goal, and how Orbit gets there in tiers

Date: 2026-10-29. Decided by: Cooper (the goal). Proposed by: Keystone (the tiers, the wording).

## Decision

Cooper's words: "Orbit's privacy goal is to protect the user's prompts, answers, and session
state from both Orbit and the hardware owner. Treat encryption between the browser and host as
one necessary piece, not the finished solution."

Keystone's reading, recorded here so it can be corrected rather than relitigated:

1. **Two tiers, both labelled exactly.** A *community* host is any machine running the host
   program: sealed from Orbit, readable by the host, and the page says so. A *verified* host runs
   the model inside enclave hardware whose attestation the browser checks before it sends a word;
   the page says "protected from the owner's software", never "protected from the owner", because
   physical attacks on the machine remain possible (docs/PRIVACY.md).
2. **Sealing ships first, as the piece it is.** Browser and host program exchange keys through
   the relay and seal every message (host/seal.py, orbit/static/seal.js). Orbit's code does not
   change except for the message size limit, which is the point: Orbit never needed the words.
3. **Consumer hardware is community hardware.** No consumer CPU or GPU found offers an enclave
   a browser can check. Cooper's own PC (Ryzen 5 3600, Radeon RX 580) is a community host.
4. **The verified tier is designed, not built**, and waits on Cooper's answers in
   docs/PRIVACY.md: whether to pursue it and who provides the first attested machine.
5. **Library.** The host program uses the `cryptography` package; the browser uses WebCrypto
   P-256 and AES-256-GCM. Chosen for being boring and universal. Reversible.

## Why

Rule 1 promised sealed envelopes Orbit cannot open; until this branch that was a promise, not a
mechanism. Rule 5 forbids claiming more than the product does. The research in docs/PRIVACY.md
shows that "private from the host" needs hardware most independent hosts do not have and that
even that hardware does not resist its owner's screwdriver, so the honest product is a labelled
tier, not a blanket claim.

## What would change this

AMD or Intel shipping attestable enclaves on consumer parts; Arm CCA Realms reaching shipping
devices for third-party workloads; a vendor fix for interposer attacks on DDR4 and a clear DDR5
story. Any of these gets a new dated file, not an edit of this one.
