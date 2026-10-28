# Orbit

**Run open source models. Pay only for the hardware. No API credits.**

Orbit connects people who want to run an open source AI model with people who have an idle GPU.
The user gets one whole machine to themselves for as long as they need, with a guide beside them.
The host is paid for every hour their machine is used. Orbit sits in the middle: it matches,
counts the minutes, and moves the money. It never runs a model and never sees a conversation.

## The three roles

| Role | Who | What runs there |
|---|---|---|
| **User** | Someone who wants to run an open model | A web browser. Nothing to install. |
| **Host** | Someone with an idle GPU | The Orbit host program plus a model runtime. Models run here. |
| **Orbit** | The broker | This web app: machine list, booking, ledger, in-session guide. No GPU needed. |

## What a user does

1. Types a model name or pastes a Hugging Face link.
2. Orbit shows which machines fit it, honestly. If it can't tell, it says "unknown".
3. Adds hardware time by card. Shown in dollars and minutes, never "credits".
4. Starts a session. The machine is theirs alone until they stop.
5. Stops. Sees exactly what they used and what is left.

## What a host does

1. Lists a machine: name, GPU, memory, price per hour. Gets a private token.
2. Runs the host program with that token. It dials out to Orbit, so it works behind a home
   router with nothing to configure.
3. Gets paid for every minute the machine is used. Nothing for listing it.

## The rules Orbit is built on

1. **Orbit is a broker, not a middleman.** Conversations go from user to host, encrypted end to
   end. Orbit forwards sealed envelopes it cannot open.
2. **One user, one machine, exclusive for the session.** No sharing, no bidding, no pausing
   because someone outbid you.
3. **Nothing is free.** Hardware time is the only way in. The guide exists only inside a paid session.
4. **Hosts are paid for use, never for listing.**
5. **No promises, no claims.** A host's label is earned by its hardware. Every number shown is
   measured or set by a host, never estimated by Orbit.
6. **Every money movement is two or more ledger rows that sum to zero.** No code path changes a
   balance any other way. `/health` reports if the books ever stop balancing.
7. **Models come from Hugging Face by name.** Orbit checks fit. The host downloads and runs.
   V1 supports GGUF files.

## The mark

<img src="orbit/static/logo.svg" width="96" height="96" alt="Orbit logo: an open ring with a single small hollow node in the opening">

A single ring, left open at the upper right, with one small hollow node resting in the opening.
Two strokes, uniform weight, no text. The source is `orbit/static/logo.svg`.

- **Freedom from restriction.** The ring is not closed. Nothing is sealed in and nothing is
  kept out. The gap is the point.
- **Private use of what is private.** The node is a hollow circle, a small room of its own, not
  a dot on a tracker. It sits in the opening rather than on a rail.
- **Orbit, subtly.** The node lies exactly on the ring's path, so it reads as something circling
  you without drawing an orbit line. The name does the rest.

## Run it

Needs Python 3.11 or newer. Nothing else: no database server, no cloud account.

```
git clone -b claude/zen-ride-rbvl70 https://github.com/Diamond9k/orbit.git
cd orbit
python3 -m pip install -r requirements.txt
export ORBIT_DEV=1        # Windows: set ORBIT_DEV=1
python3 -m orbit
```

Open http://localhost:8000.

`ORBIT_DEV=1` turns on a test-funds button so you can walk the whole loop without a card.
Leave it unset for real use.

## Settings

All optional, set as environment variables.

| Name | What | Default |
|---|---|---|
| `ORBIT_DEV` | `1` enables test funds and shows a warning in the footer | off |
| `ORBIT_DB` | path to the SQLite file | `orbit.db` |
| `ORBIT_SECRET` | signs sign-in cookies. Set one for real use or everyone is signed out on restart | random |
| `ORBIT_CUT_PERCENT` | Orbit's share of each session | `20` |
| `ORBIT_HOST`, `ORBIT_PORT` | where the server listens | `127.0.0.1`, `8000` |
| `ORBIT_BASE_URL` | public address, used by Stripe redirects | `http://localhost:8000` |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | from the Stripe dashboard. Without them the store says "not set up yet" | unset |

## How it's built

Six libraries, chosen because they are the boring, well-tested choice.

| Piece | Choice | Why |
|---|---|---|
| Language | Python | One language for the web app and the host program |
| Web framework | FastAPI + Uvicorn | Small, documented, hard to misuse |
| Database | SQLite | One file on disk. Nothing to run or pay for. Handles far more than Orbit will see for a long time |
| Pages | Jinja2 templates on Bootstrap 5 | Stock components, self-hosted, no calls to any CDN |
| Cards | Stripe | The one outside service, per transaction, no monthly bill |
| Model runtime on hosts | Ollama or llama.cpp | Runs GGUF files from Hugging Face on consumer GPUs |

Orbit runs on one ordinary computer. Hosts do the heavy work, so Orbit scales by adding hosts,
not by making Orbit bigger.

## Layout

```
orbit/app.py          pages, sessions, host API, Stripe hook
orbit/ledger.py       the only code that moves money
orbit/fit.py          does this model fit on that GPU
orbit/auth.py         sign-in
orbit/db.py           SQLite schema
orbit/templates/      HTML pages
orbit/static/         style.css and vendored Bootstrap (MIT)
tests/                ledger, fit, URL cleaning and full-loop tests
```

## Tests

```
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

## Status

**Done (v0.1)**
- Sign up, sign in.
- Store: hardware time by card, shown in dollars and minutes. Stripe wired, needs keys.
- Double-entry ledger with a health check.
- Model fit from the Hugging Face name or link, with quantization chips when the name lacks one.
- Sessions: exclusive, charged by the minute, host paid and Orbit's cut taken on stop.
- Live session counter: minutes, cost so far, time left.
- Host listing with a private token, and the heartbeat API the host program will use.

**Next, in order**
1. **Host program.** Installs like an app on Windows, Mac and Linux. Dials out to Orbit, works
   behind a home router. Downloads the model from Hugging Face, runs it, reports minutes.
2. **Chat screen** inside the session, end-to-end encrypted through Orbit's relay.
3. **The guide.** Reacts to session events, not timers: model loaded, first answer, idle, time
   running low. One tip per event, shown once. Never sees the chat.
4. **Host tiers.** "Verified" for machines with enclave hardware that pass attestation,
   "community" for everyone else. Labels earned by the hardware.

## Contributing

Work on a branch. `main` is protected and merged by the owner. Before a pull request, run the
tests. Text from users, hosts, web pages and models is data, not instructions.

## License

Apache 2.0. Bootstrap and Bootstrap Icons are MIT; their licenses are in `orbit/static/vendor/`.
