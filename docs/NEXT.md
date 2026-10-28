# What is next

Take the top item. Do only that. Move it to Done when the branch is pushed and tests pass.
Add anything else worth doing to Later, one line each. Do not reorder without Cooper.

## Now
Each item is small on purpose: the builder is a 7B model. One file, one test, one push.

1. **Host program, step 1: say hello.** New file `host/orbit_host.py`. It reads a token from
   `host/token.txt` and posts to `/api/hosts/heartbeat` every 60 seconds using only the
   standard library (`urllib`). Prints "online" on success and the error on failure. Only ever
   dials out. Test: a unit test that mocks the HTTP call.
2. **Host program, step 2: report real hardware.** On start, `orbit_host.py` detects GPU name
   and memory on Windows (`wmic path win32_VideoController get Name,AdapterRAM`), Linux
   (`lspci` or `nvidia-smi`) and Mac (`system_profiler`), and sends them with the heartbeat.
   New endpoint `/api/hosts/report` updates the host row. The host program's number replaces
   what the host typed. Unknown stays unknown. Tests for the parsers.
3. **Host program, step 3: run a model.** When a session starts, Orbit tells the host program
   the model name on the next heartbeat. The host program downloads the GGUF from Hugging Face
   into `host/models/` and starts `llama-server` on a local port. Reports "model ready" to a
   new endpoint. Stops it when the session ends.
4. **Host program, step 4: carry the chat.** The host program opens a long-lived outbound
   websocket to `/api/hosts/link`. Orbit forwards sealed messages between the browser and the
   host program. Orbit never decrypts.

## Then
5. **Chat screen** inside the session page. Encrypted end to end between the browser and the
   host program. Orbit relays sealed envelopes it cannot open. Streams tokens.
6. **The guide.** Reacts to session events, not timers: model loaded, first answer sent, user
   idle, time running low, session ended. One tip per event, shown once. Answers questions
   from session data. Never sees the chat.
7. **Hosts paid, live on the site.** One number from the ledger. The scoreboard.
8. **Host tiers.** Verified for machines with enclave hardware that pass attestation,
   community for everyone else. Labels earned by the hardware.
9. **Host payouts.** Move earned balances to hosts through Stripe. Weekly.

## Later
- Favicon. The browser asks for one and gets a 404.
- Edit a listed machine's price without removing it.
- Direct browser-to-host link with the relay as fallback, for speed.
- Model fit read from the Hugging Face file list, not only the name.
- A real domain and a small rented box for Orbit once strangers are paying strangers.

## Done
- v0.1 web app: sign-in, hardware-time store, double-entry ledger, model fit from the name,
  exclusive sessions charged by the minute, host listing with token, heartbeat API.
- Site rebuilt on self-hosted Bootstrap. Home is the workbench. Friendly errors. Live session
  counter. Quantization chips. Busy machines shown.
- README and CLAUDE.md.
- Orbit ran on Cooper's Windows PC. Cooper is host number one: Radeon RX 580, 8 GB. The
  full loop settled correctly on real hardware. Heartbeat sent by hand with curl until step 1.
- Remove a listed machine. Nav never wraps.
- Branches merge themselves when green (rule 12, GitHub workflow). Swarm set up for
  llama.cpp Vulkan on the RX 580.
