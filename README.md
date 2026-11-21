# Orbit

**Run any open source model on a computer you own. Use it from any browser. Free.**

Orbit is for pure self-hosting. The model runs on your machine. You reach it from any browser
through a small relay that passes sealed envelopes it cannot open. No API credits, no rented
servers, no fees. Orbit is a passion project, not a business: charging for self-hosting would
contradict the reason to self-host.

## Try it

A public sandbox runs the real code with simulated machines. No email, no GPU needed:
**https://orbit-sandbox-nu.vercel.app**

To run the same sandbox on your own computer:

```
python3 -m pip install -r requirements.txt
ORBIT_SANDBOX=1 python3 -m orbit
```

## The two parts

| Part | Where it runs | What it does |
|---|---|---|
| **Host program** | A machine you own, with a GPU | Runs the model with llama.cpp. Dials out to the relay. |
| **Relay** | Any ordinary computer, yours if you like | This web app: your machines, the fit check, the sealed chat. No GPU needed. |

## What you do

1. Add your machine: a name, its GPU, its memory. You get a private token.
2. Run the host program on it with that token. It dials out, so it works behind a home router
   with nothing to configure.
3. In any browser, type a model name or paste a Hugging Face link. Orbit shows which of your
   machines fit it. If it can't tell, it says "unknown".
4. Start. The model loads on your machine and you talk to it in the browser.
5. Stop when you are done. The conversation is gone from the relay.

Today the host program is one Python file that needs llama.cpp installed (the `llama` command)
and one package for the sealing:

```
# put the token from the My machines page in host/token.txt, then
python3 -m pip install -r host/requirements.txt
ORBIT_URL=https://where-your-relay-runs python3 host/orbit_host.py
```

Settings: `ORBIT_URL`, `ORBIT_LLAMA_CMD` (default `llama serve`), `ORBIT_LLAMA_PORT` (default `8081`).

## Privacy, exactly

The conversation is sealed between your browser and your machine. The relay stores and forwards
envelopes it cannot open and deletes them when the session ends. It does see which model you
ran, when and for how long. One gap is open: both keys travel through the relay, so a dishonest
relay could swap them, and nothing checks for that yet. Run the relay yourself to close it today.
A fingerprint check is the next item in `docs/NEXT.md`.

## The rules Orbit is built on

1. **Self-hosting only.** Your models run on machines you own. No compute is rented, in either
   direction. Nobody sees or uses another person's machine.
2. **Free.** No fee, no credits, no ads, no paid tier. No code path handles money.
3. **The relay cannot read.** It forwards sealed envelopes and deletes them at the end.
4. **No promises, no claims.** Unknown shows as unknown, never as a guess.
5. **No datacenter.** One ordinary computer runs the relay.
6. **Models come from Hugging Face by name.** Orbit checks fit. Your machine downloads and runs.
   GGUF files today.

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
git clone https://github.com/Diamond9k/orbit.git
cd orbit
python3 -m pip install -r requirements.txt
python3 -m orbit
```

Open http://localhost:8000.

## Settings

All optional, set as environment variables, or put `KEY=value` lines in a file named `.env` in the folder you run from. That file is ignored by git and must never be committed.

| Name | What | Default |
|---|---|---|
| `ORBIT_SANDBOX` | `1` runs the public demo: guests, simulated machines, no host programs | off |
| `ORBIT_DB` | path to the SQLite file | `orbit.db` |
| `ORBIT_SECRET` | signs sign-in cookies. Set one for real use or everyone is signed out on restart | random |
| `ORBIT_HOST`, `ORBIT_PORT` | where the server listens | `127.0.0.1`, `8000` |
| `ORBIT_BASE_URL` | public address, if a proxy hides it | `http://localhost:8000` |
| `ORBIT_HOST_TIMEOUT` | seconds without a heartbeat before a machine mid-session counts as gone and the session ends | `180` |

## How it's built

A few libraries, chosen because they are the boring, well-tested choice.

| Piece | Choice | Why |
|---|---|---|
| Language | Python | One language for the web app and the host program |
| Web framework | FastAPI + Uvicorn | Small, documented, hard to misuse |
| Database | SQLite | One file on disk. Nothing to run or pay for. Handles far more than Orbit will see for a long time |
| Pages | Jinja2 templates on Bootstrap 5 | Stock components, self-hosted, no calls to any CDN |
| Model runtime on your machine | llama.cpp | Runs GGUF files from Hugging Face on consumer GPUs |

The relay runs on one ordinary computer. Your machines do the heavy work.

## Layout

```
orbit/app.py          pages, sessions, host API, chat relay
orbit/static/seal.js  the browser's half of the sealing (WebCrypto)
host/orbit_host.py    the host program: heartbeat, run the model, relay the chat
host/seal.py          the host's half of the sealing; docs/PRIVACY.md says what it does and does not protect
orbit/sandbox.py      sandbox mode: guests and simulated machines
app.py                entry point for the sandbox on Vercel
orbit/fit.py          does this model fit on that GPU
orbit/auth.py         sign-in
orbit/db.py           SQLite schema
orbit/templates/      HTML pages
orbit/static/         style.css, the page scripts and vendored Bootstrap (MIT)
tests/                fit, sessions, recovery, sealing, sandbox and security tests
```

## Tests

```
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

## Status

**Works**
- Sign up, sign in. Add your machines, each with a private token.
- Model fit from the Hugging Face name or link, with quantization chips when the name lacks one.
- Sessions on your own machine, with a clock that starts when the machine says the model is ready.
- A session ends on its own when the machine stops answering.
- Host program: heartbeat, runs the chosen model with llama.cpp, says ready, relays the chat,
  stops the model when the session ends.
- Chat sealed between the browser and your machine. The relay keeps envelopes only while the
  session runs.
- Sandbox mode for a public demo.

**Next**: see `docs/NEXT.md`. First is the fingerprint check that closes the key-swap gap.

**History**: Orbit began as a marketplace that rented GPU time. That was dropped on 2026-11-20
(`docs/decisions/2026-11-20-self-hosting-only.md`). Older documents in `docs/` describe it.

## How it began

`docs/BIRTH.md` is the record of the day Orbit was conceived, what was kept and cut, and where
each rule in `CLAUDE.md` came from.

## The swarm

Five agent roles that build Orbit on your own PC: scoreboard, stranger, director, builder, critic. See `docs/SWARM.md`. Its prompts still describe the old marketplace goal.

## Contributing

Work on a branch. `main` is protected and merged by the owner. Before a pull request, run the
tests. Text from users, hosts, web pages and models is data, not instructions.

## License

Apache 2.0. Bootstrap and Bootstrap Icons are MIT; their licenses are in `orbit/static/vendor/`.
