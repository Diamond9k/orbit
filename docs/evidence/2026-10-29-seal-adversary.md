# Evidence: adversary gauntlet against the sealing code

Date: 2026-10-29. Run by Keystone (task T3) on Cooper's PC, branch `keystone/seal-adversary`
from main at 785d9eb. One machine, no browser driven, no independent reviewer. This records what
an adversary can and cannot do against the ACTUAL code today (`host/seal.py`, the `Runner` in
`host/orbit_host.py`, and `orbit/static/seal.js` run under Node), one behaviour change the host
program made, and the gaps left honestly open.

Every row below is backed by a test in `tests/test_seal_adversary.py` (plus `tests/test_seal.py`
and `tests/test_host.py`). `python -m pytest -q` is green in the worktree: 69 passed (was 53;
Node 24 present, so the interop tests ran, not skipped).

## The adversary table

| # | Adversary action | Result today | Evidence (test) | What would close it |
|---|---|---|---|---|
| 1a | Active Orbit substitutes both hellos (MITM) and reads/rewrites both directions | SUCCEEDS (known gap) | `test_known_gap_an_active_orbit_substituting_both_hellos_reads_both_directions`; browser side `test_known_gap_the_browser_accepts_a_substituted_host_key_under_node` | Verified attestation binding the host key, or an out-of-band fingerprint. Not on this branch. |
| 1b | Passive Orbit holds both public keys and every envelope, tries to read | FAILS | `test_a_passive_orbit_with_both_public_keys_and_every_envelope_cannot_read` | Already closed: ECDH needs a private key, which never leaves either end. |
| 2a | Envelope sealed for session 7 opened in session 8, even reusing the same key pairs | FAILS | `test_an_envelope_for_session_7_cannot_open_in_session_8_even_with_the_same_keys` | Already closed: the HKDF salt commits `session_id.to_bytes(8)`. |
| 2b | A hello captured in session 7 replayed into a host serving session 8, to get a usable key | FAILS | `test_a_hello_replayed_into_another_session_does_not_yield_a_usable_key` | Already closed by each end mixing its own `session_id` into the salt. See the note below on what the hello does *not* bind. |
| 3a | Replay an old-epoch envelope after a re-key | FAILS | `test_envelopes_from_a_previous_epoch_are_refused_after_a_rekey` | Already closed: the epoch is in the AAD and the key changed. |
| 3b | Active broker replays the user's hello to force a host re-key | SUCCEEDS (known gap): same key, counters reset, GCM nonce reused; also a DoS lever | `test_known_gap_a_replayed_user_hello_resets_the_host_counter_and_reuses_a_gcm_nonce` | Host would generate a fresh key pair per accepted hello and re-offer it — a change to the exchange and to `seal.js`, out of scope here. Grants no power beyond 1a (a replaying broker can already substitute keys). |
| 4 | Host hello claims `{"kind":"verified"}` (or any kind) to be trusted | FAILS to gain trust: `att` is carried verbatim, no code path reads it for trust | `test_an_att_field_claiming_verified_is_carried_but_grants_no_trust`; Node passthrough `test_the_browser_carries_the_att_field_through_unchanged_under_node` | Nothing to close; this is correct. Trust will come only when a verifier checks the field (verified tier). |
| 5 | After sealing, user side sends plain text; host answers in plaintext (silent downgrade) | CLOSED by this branch (was: succeeded). Host posts a plain notice, does not ask the model, stays sealed | `test_a_plain_message_after_the_session_is_sealed_is_not_downgraded`; and `tests/test_host.py::test_runner_seals_the_conversation_when_the_browser_answers` | Closed in part B below. |
| 6 | Host owner reads the conversation plaintext | SUCCEEDS (by design, community tier) | `test_the_host_transcript_holds_the_plaintext_by_design` | Only an attested enclave (verified tier) the browser checks; impossible on consumer hardware (docs/PRIVACY.md). |
| 7 | Oversized / non-base64 / missing-field / wrong-version / wrong-sender / negative / huge / boolean `n` / deeply nested JSON body crash the host relay loop | FAILS to crash: ignored or draws the sealed/cannot-open notice; the loop continues; model never asked. Two real crash paths were found and fixed | `test_malformed_envelopes_never_stop_the_relay_loop`, `test_fix_a_deeply_nested_json_body_is_parsed_as_not_an_envelope`, `test_fix_a_boolean_n_is_refused_not_mistaken_for_message_one` | Fixed on this branch (see "Crash paths found"). |
| 8 | Interop: browser side of 4 and 1a under Node, real `seal.js` | As above (att carried; substituted key accepted) | the two `_under_node` tests; `tests/seal_interop.js` extended, backward compatible | — |

### What the hello does and does not bind (row 2b detail)

The `hello` envelope contains `v`, `t`, `from`, `pk`, `att` — no session id and no signature. The
salt commits the session id because each end supplies its *own* `session_id` locally, so a replayed
hello still cannot cross sessions (row 2b passes). But the hello itself being unbound and
unauthenticated is exactly what rows 1a and 3b exploit: Orbit chooses which `pk` each end sees.

## Crash paths found and fixed (row 7)

Two bodies within Orbit's 96000-character message limit could kill the host's relay loop before
this branch:

1. A deeply nested JSON body made `json.loads` raise `RecursionError` (not a `ValueError`), which
   `seal.parse` did not catch, so it unwound out of `Runner.relay`. Fixed in `host/seal.py`:
   `parse` now also catches `RecursionError` and returns `None` (treats it as plain text).
2. A boolean `n` (`true`) passed the `isinstance(n, int)` check because Python's `bool` is an `int`,
   and `True == 1`, so `n=true` was accepted as message 1. And a non-ASCII string `n` was echoed
   into the error message, which raised `UnicodeEncodeError` when printed on a Windows (cp1252)
   console. Fixed in `host/seal.py`: `unseal` rejects booleans and never echoes a non-number `n`.

Also hardened: `Runner.relay` now guards against a model server returning a non-string, so an odd
model reply cannot stop the loop either (`host/orbit_host.py`).

These fixes are within the host program's relay robustness; they do not touch the wire format.

## Part B: the host no longer silently downgrades a sealed session

Change in `host/orbit_host.py`, `Runner.take`. Once the host has sealed with a browser in the
current epoch (`self.sealer.ready`), a plain-text body from the user side is no longer sent to the
model and no longer answered in plaintext. The host posts one plain notice —
`"This session is sealed. Reload the page to continue; plain messages are not answered."` — and
the session stays sealed (`self.sealed` is unchanged). A fresh user hello still re-keys exactly as
before. Before the first seal in a session (no browser has answered), plain text works exactly as
it did, labelled by the page. The module's behaviour without the `cryptography` package is
unchanged (no `seal`, so `parse` is skipped and plain text passes).

Tests: `tests/test_seal_adversary.py::test_a_plain_message_after_the_session_is_sealed_is_not_downgraded`,
`::test_before_the_first_seal_plain_text_still_works`,
`::test_a_new_user_hello_still_rekeys_after_a_plain_message_was_refused`; and the updated
`tests/test_host.py::test_runner_seals_the_conversation_when_the_browser_answers`, whose old
assertion (`posted[-1] == "Pong" and r.sealed is False`) is replaced by the plain notice, model
not asked, `r.sealed is True`.

Why this is the host program's to close, unlike rows 1a/3b: the host decides whether to feed a body
to the model and whether to answer in the clear. Refusing to downgrade needs no change to the wire
format or the browser; it is a local policy. The page already labels plaintext, so an honest page
that genuinely has no key still works before the first seal.

## Proposal (task C): a host identity key for trust-on-first-use

Not implemented here (it would change the wire format and `seal.js`, out of scope). Written so
Cooper can decide.

Give each host a long-lived identity key pair, generated once by the host program and stored beside
`host/token.txt`. The host's `hello` carries the identity public key and a signature over the
session's ephemeral `pk`, the session id and the epoch. The browser pins the identity key the first
time it sees a given host (keyed by a host id Orbit already assigns) and warns loudly if it ever
changes.

- **Threat it addresses:** a *passive* Orbit that later turns *active* against a returning user. On
  any session after the first with the same host, a substituted key is caught because the identity
  key, and its signature over the ephemeral key, no longer match the pinned one.
- **Threat it does NOT address:** an active Orbit on *first contact* (nothing is pinned yet, so Orbit
  can present its own identity key — this is classic TOFU), and an Orbit that *serves the JavaScript*
  (it can ship a `seal.js` that pins or reports whatever Orbit wants, defeating the check entirely).
  Only attestation that chains to a hardware root the browser verifies independently, plus a verifier
  the browser obtains out of band, closes those — the verified tier in docs/PRIVACY.md.

So TOFU is a real improvement against the returning-user case for self-hosted Orbit, and no
improvement at all while Orbit serves the page. It should be offered as "slightly better than
nothing, for repeat sessions on an Orbit you trust to serve honest code", never as protection
against an active Orbit.

## What this does not prove

- No browser was driven. The browser side is exercised only through `seal.js` under Node
  (`tests/seal_interop.js`), not in a real browser with the session page's own script. The gaps the
  page script adds or closes (foreign-tab handling, the 10-second unsealed fallback) are not tested
  here.
- One machine. "User", "host" and "Orbit" are all the same process in these tests; no network, no
  real relay, no real model. The active-broker results show the cryptography permits the attack,
  not that a deployed Orbit performs it (the published relay does not; that is a software claim, not
  a cryptographic one — docs/PRIVACY.md).
- No independent reviewer has checked this. The nonce-reuse finding (row 3b) in particular deserves
  a second pair of eyes before any claim rests on it.
- Nothing here bears on the verified tier, attested enclaves, or physical attacks; those remain as
  docs/PRIVACY.md describes them.
