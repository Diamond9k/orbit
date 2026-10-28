# What is next

Take the top item. Do only that. Move it to Done when the branch is pushed and tests pass.
Add anything else worth doing to Later, one line each. Do not reorder without Cooper.

## Now
1. **Host program.** A Python program a host runs with their token. Installs like an app on
   Windows, Mac and Linux. Only dials out, so it works behind a home router with nothing to
   configure. Detects the GPU and memory, sends a heartbeat, and when a session starts it
   downloads the GGUF model from Hugging Face, runs it with llama.cpp or Ollama, and reports
   minutes. First target machine: Cooper's gaming PC.

## Then
2. **Chat screen** inside the session page. Encrypted end to end between the browser and the
   host program. Orbit relays sealed envelopes it cannot open. Streams tokens.
3. **The guide.** Reacts to session events, not timers: model loaded, first answer sent, user
   idle, time running low, session ended. One tip per event, shown once. Answers questions
   from session data. Never sees the chat.
4. **Hosts paid, live on the site.** One number from the ledger. The scoreboard.
5. **Host tiers.** Verified for machines with enclave hardware that pass attestation,
   community for everyone else. Labels earned by the hardware.
6. **Host payouts.** Move earned balances to hosts through Stripe. Weekly.

## Later
- Direct browser-to-host link with the relay as fallback, for speed.
- Model fit read from the Hugging Face file list, not only the name.
- A real domain and a small rented box for Orbit once strangers are paying strangers.

## Done
- v0.1 web app: sign-in, hardware-time store, double-entry ledger, model fit from the name,
  exclusive sessions charged by the minute, host listing with token, heartbeat API.
- Site rebuilt on self-hosted Bootstrap. Home is the workbench. Friendly errors. Live session
  counter. Quantization chips. Busy machines shown.
- README and CLAUDE.md.
