# Orbit sells tokens from a model, not minutes on a machine

Date: 2026-11-02. Decided by: Cooper. Proposed in conversation with Claude, after the GPU
pooling idea (docs/SCAN-wici.md) was worked through.

## Decision

The unit Orbit sells changes from exclusive minutes on one machine to tokens produced by a
model on a host's machine. The user still pays only a host, and the host is still paid only
for use. The agent that picks the model, trims the request and runs any tool loop lives in
the user's browser. Hosts are token producers. Orbit stays a broker.

## What changes

- Hosts set a price per million tokens, per model, and keep a few models warm instead of
  downloading one at the start of every session.
- A request may go to any warm host that has the model. No exclusive session, no timer.
- The ledger counts tokens the host actually produced, confirmed by both ends (the host made
  them, the browser received them), and pays per request. Still double-entry (rule 6). Still
  paid for use only (rule 4).
- A small agent in the browser chooses the model, sends only what the request needs, runs the
  tool loop, and seals every message. The host never runs the agent.
- Rules 2 ("one user, one machine, exclusive") and 3 ("hardware time is the only way in") are
  superseded by this file. The new wording for CLAUDE.md and the README's first line is set when
  the first build item below ships, so the page never claims something the code does not do.

## What stays

- Rule 1. Orbit forwards sealed envelopes it cannot open. Nothing in this decision lets Orbit,
  or any coordinator, read a request. If an agent needs plaintext, it runs in the browser.
- Rules 4 to 13. Rule 7 in particular: no cloud scheduler, no queue service.
- The host program: one file, dials out, home router, llama.cpp, GGUF from Hugging Face.
- The two privacy tiers and their wording (docs/PRIVACY.md). A community host can read what
  it is sent, and the page says so.

## What is given up, on purpose

- Pricing by the hour, and the simplicity of one person on one machine.
- A host now sees many strangers' requests in a day instead of one person's session. Trimming
  in the browser reduces what each request carries; it does not change who can read it.
- The line "Pay only for the hardware. No API credits." The replacement says that the user pays
  the person whose GPU answered, per answer, at a price that person set.

## Why

People do not want to rent a machine for an hour to ask a question; they want an answer and
will pay per answer. Per-request routing also makes the only workable form of pooling natural:
many independent requests spread over many hosts, each paid for what it produced. Pooling a
single request across strangers' machines was rejected on latency and privacy grounds and is
not part of this decision.

## Rejected

- The agent on the host or on Orbit: either one reads the conversation (breaks rule 1).
- Reverse engineering the WiCi protocol: built for a one-room link, legal exposure, and nothing
  it does helps a request that already runs whole on the host.
- Splitting one model across strangers' machines over the internet: slower than one machine
  and every member can read the words.

## Order of work

1. Per-token billing on the existing one-host flow. Proves the ledger and the measurement.
2. Hosts keep models warm and list a price per model.
3. Requests routed to any warm host.
4. The browser agent: model choice, request trimming, tool loop.
