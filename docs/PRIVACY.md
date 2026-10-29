# Privacy: what Orbit protects, from whom, and how we know

Owner's goal, stated by Cooper on 2026-10-29: protect the user's prompts, answers and session
state from both Orbit and the hardware owner. Encryption between the browser and the host is one
necessary piece, not the finished solution.

This file is the honest map of that goal: who can see what today, what a verifiable protected
boundary would be, whether independent consumer hardware can offer one, and what has actually
been shown. Every claim on a page must trace back to a row here (rule 5). Research done
2026-10-29 by Keystone from public sources, listed at the end; where a source was not found that
is said rather than guessed.

## Who can see what

A session has four parties: the user's browser, Orbit (the relay and ledger), the host (the
person whose machine runs the model), and the network between them. Hugging Face sees which
model file a host downloaded, from the host's address.

| | Unsealed (main today) | Sealed, unverified host (this branch, "community") | Attested host ("verified", not built) | The user's own machine |
|---|---|---|---|---|
| Orbit sees the words | yes, in flight and in its database until the session ends | no: only envelope sizes and timing | no | nothing at all |
| Orbit can alter or inject words | yes | not without being noticed, once keys are exchanged; it could swap keys during the exchange (below) | no: the host's key is bound to an attestation Orbit cannot forge | no |
| Orbit knows who talked to which host, when, how long, which model | yes | yes | yes | no |
| The host sees the words | yes | yes, in plain text in RAM and VRAM; can log them; nothing stops or detects it | no: the owner's OS and hypervisor cannot read enclave memory; the browser checked what runs inside | the user is the host |
| The host knows who the user is | no: only a session number; the host program dials out to Orbit and never meets the browser | no | no | n/a |
| Session state (model context, KV cache) after the session | on the host's machine until the model server exits; not verifiable | same | inside the enclave, gone when it exits | n/a |

"Sealed from Orbit" is exactly what the page says in the second column. It does not say
"private", because the host can read everything.

### The key-swap gap in the community column

Both ends send their public key through Orbit. A relay that merely stores and forwards cannot
read what follows. A relay that actively replaces each key with its own could sit in the middle
unnoticed, because nothing in the community tier lets the browser check whose key it got. Two
things close the gap: an attestation report that binds the host's key to measured enclave
software (the verified tier), or a fingerprint the user compares with the host out of band
(impractical for strangers). Orbit's code is open and self-hostable, so anyone can check that the
relay as published does not do this; that is a software claim, not a cryptographic one, and the
page does not pretend otherwise.

## What a verifiable protected-compute boundary is

A protected-compute boundary means the model runs inside hardware-isolated memory that the
machine's owner cannot read, and the browser can verify before it sends a word that this is so
and that the software inside is the published one. The pieces, none of which Orbit has today:

1. **An enclave that can run inference.** CPU-side: AMD SEV-SNP confidential VMs or Intel TDX
   trust domains. GPU-side: NVIDIA's confidential-computing mode, which NVIDIA's own platform
   list limits to H100, H200, B200 and the RTX PRO 6000 Blackwell Server Edition, paired with a
   TDX or SEV-SNP host CPU (sources 1, 2). CPU-only inference inside a SEV-SNP VM is viable for
   small models: an independent February 2026 benchmark of llama.cpp on an EPYC 9005 confidential
   VM found little overhead (source 10).
2. **A key born inside the enclave.** The session key pair from `host/seal.py` is generated inside
   the enclave, and the attestation report's user-data field carries a hash of the public key
   and the session number, so the report vouches for exactly that key.
3. **A report the browser can check.** The report is signed by a chip key whose certificate
   chains to the vendor's root (AMD's VCEK to the ARK/ASK chain through AMD's key distribution
   service; Intel's equivalent through its provisioning certificates). The browser verifies the
   chain and the signature (source 7).
4. **A measurement the browser can recognise.** The report states the hash of the firmware,
   kernel and disk image that booted. Orbit publishes the expected hashes for each release of the
   host image, built reproducibly from the repository, and signs them into a public transparency
   log, so that a dishonest Orbit cannot quietly bless a different image. This is the pattern
   Tinfoil describes for its browser-side verifier (source 8); Edgeless Continuum does the same
   check in a client-side proxy (source 9). Orbit must build its own; copying is not allowed.
5. **The GPU inside the boundary.** With NVIDIA confidential computing on, the GPU's own
   attestation (through NVIDIA's attestation service or local verifier) is folded into the
   evidence, and traffic between CPU enclave and GPU is encrypted.
6. **Then, and only then, derive keys.** The browser accepts the host's hello only if the
   attestation verifies and the measurement is on the published list. The rest of the protocol is
   the sealing already built on this branch.

What this still does not give:

- **Trust in the chip vendor.** AMD, Intel and NVIDIA sign the reports; their keys are the
  root. There is no way around this with today's hardware.
- **Side channels.** Timing, cache and power channels against enclaves are a research field with
  a steady stream of results; a determined owner with root on the machine has every one of them
  available.
- **Physical attacks by the owner.** This is the decisive point for Orbit, because independent
  hosts own the box. In late 2025, two groups showed interposers on DDR4 memory that break both
  SGX and SEV-SNP: WireTap (passive, several hundred dollars) and Battering RAM (active, under
  fifty dollars), the latter bypassing the boot-time defences AMD and Intel had added. Intel's
  statement places physical attacks outside the protection boundary of its memory encryption.
  Neither paper covers DDR5, and no vendor fix for DDR4 was found (sources 4, 5, 6). So even the
  verified tier must be worded as "protected from the owner's software", never "protected from
  the owner".

## Can independent consumer hardware participate safely?

Short answer: as a community host, yes, with the page saying the host can read the conversation.
As a verified host, no. Nothing a consumer buys today offers a boundary the browser could check.

| Hardware | Attestable enclave for inference? | Finding |
|---|---|---|
| AMD Ryzen (Cooper's PC: Ryzen 5 3600) | no | Every SEV-SNP attestation guide found is for EPYC; no AMD document describing SEV-SNP on Ryzen was found (sources 3, 7). Treat as unavailable until AMD says otherwise. |
| Intel Core | no | SGX was removed from client processors from the 11th generation on; TDX is a Xeon feature. Intel is phasing SGX out of servers too, in favour of TDX (sources 11, 12). |
| NVIDIA GeForce / AMD Radeon (Cooper's RX 580) | no | NVIDIA's confidential-computing list has no GeForce part; AMD consumer GPUs have no equivalent (source 1). |
| Arm (phones, Snapdragon laptops) | not yet | Arm CCA Realms exist in the architecture; no shipping consumer device with Realms available to third-party workloads was found (source 13). |
| Apple silicon | no | The Secure Enclave is not a general enclave for third-party inference; Private Cloud Compute runs on Apple's servers only. |
| TPM 2.0 (every Windows 11 PC) | integrity, not confidentiality | A TPM can attest what booted (measured boot), so a host could prove it started an unmodified Orbit host image. The owner, with admin rights or a debugger, can still read every byte of RAM. This proves honesty of the install, not privacy of the conversation. Possible later as a "community, measured" label; not a protection claim. |

Hardware that does qualify is server or workstation class: an EPYC (Milan or later) or Xeon
(4th generation or later) system, optionally with an H100-class or RTX PRO 6000 Blackwell Server
Edition GPU. Independent people and small shops own such machines; "independent" is not the same
as "consumer". The verified tier is for them. The physical-attack caveat above applies to every
one of them.

### What consumer hosts can honestly offer

- The user's words are sealed from Orbit (built on this branch).
- The host never learns who the user is: no name, no email, no address. The host API hands over a
  session number and a model name, nothing else (`orbit/app.py`, `_host_session`).
- The conversation is not stored by Orbit after the session; it is deleted at the end (built).
  Whether the host's machine kept a copy cannot be checked.
- A measured-boot label later, if Cooper wants it: "this machine booted the unmodified host
  program", with the limits above spelled out.

## What has been shown, by kind

| Claim | Kind of evidence | Where |
|---|---|---|
| Browser and host derive the same keys; Orbit's stored body carries no plain text; tampering, replay and reordering are rejected; a new tab re-keys | unit tests, Python side | `tests/test_seal.py` |
| The real browser code (`orbit/static/seal.js`) interoperates with the host code | unit test running `seal.js` under Node against `host/seal.py` | `tests/test_seal.py`, `tests/seal_interop.js` |
| The host program offers a key at ready, answers sealed messages sealed, and falls back to plain text for a page that never answers | unit tests with fakes | `tests/test_host.py` |
| A real model answers through the sealed relay and Orbit's database holds only envelopes | controlled end-to-end run on one PC, scripted user | `docs/evidence/` (see the dated file for this run) |
| The session page's key exchange works in a real browser | not shown by automation; no browser driver in this repository | hand check only |
| A stranger had a private session on an independent host | not shown | nothing |

Proof of a private real-world session would be: a user who is not Cooper, on a host that is not
Cooper, where someone other than Orbit confirms that Orbit's database and logs held only
envelopes, the host was an attested enclave whose measurement the user's browser checked, and the
host's owner could not produce the plain text. Nothing here reaches the second or third part.

## Decisions this leaves with Cooper

1. The host program now depends on the `cryptography` package (PyCA, the standard choice in
   Python) for the sealing; the browser uses WebCrypto with P-256 and AES-GCM because every
   browser has had them for years, while X25519 only reached all three major browsers in 2025
   (source 14). Keystone made this call for the prototype; it is one line to change.
2. Whether to pursue the verified tier, and who buys or rents the first attested machine. Cooper
   has none. Rule 7 says no datacenter dependence; a verified host is still an independent host,
   but the first one will cost someone thousands of dollars.
3. Whether to keep the unsealed fallback for pages that never receive a key, or refuse to send.
4. Whether a "measured" label for TPM-attested consumer hosts is worth building, given it must be
   explained as integrity, not privacy.

## Sources (read 2026-10-29)

1. NVIDIA, Confidential Containers supported platforms: https://docs.nvidia.com/datacenter/cloud-native/confidential-containers/latest/supported-platforms.html
2. NVIDIA, Trusted Computing Solutions (nvtrust): https://docs.nvidia.com/nvtrust
3. AMD, SEV-SNP attestation overview (slides): https://www.amd.com/content/dam/amd/en/documents/developer/lss-snp-attestation.pdf
4. Battering RAM project page: https://batteringram.eu/
5. Intel, "More information on encrypted memory frameworks" (statement on WireTap and Battering RAM): https://www.intel.com/content/www/us/en/developer/articles/news/more-information-encrypted-memory-frameworks.html
6. Kaspersky summary of WireTap and Battering RAM: https://www.kaspersky.com/blog/wiretap-battering-ram-tee-attacks/54598/
7. SNPGuard, remote attestation of SEV-SNP VMs with open-source tools (arXiv 2406.01186): https://arxiv.org/html/2406.01186v1
8. Tinfoil, attestation architecture (browser-side verification, Sigstore-published measurements): https://docs.tinfoil.sh/verification/attestation-architecture
9. Edgeless Systems, Continuum architecture: https://docs.edgeless.systems/continuum/under-the-hood/architecture/overview
10. Phoronix, performance cost of AMD SEV-SNP on EPYC 9005 (includes llama.cpp): https://www.phoronix.com/review/amd-epyc-9005-sev-snp
11. OpenMetal, Intel TDX and SGX hardware requirements: https://openmetal.io/resources/blog/intel-tdx-and-sgx-requirements/
12. BleepingComputer, SGX removed from 11th-generation and later client chips: https://www.bleepingcomputer.com/news/security/new-intel-chips-wont-play-blu-ray-disks-due-to-sgx-deprecation/
13. Arm, Confidential Compute Architecture: https://www.arm.com/architecture/security-features/arm-confidential-compute-architecture
14. Igalia, secure curves in WebCrypto (X25519 shipping in Chrome 133): https://blogs.igalia.com/jfernandez/?p=1913
