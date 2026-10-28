# Orbit

Run open source models. Pay only for the hardware. No API credits.

Orbit connects people who want to run an open model with people who have an idle GPU.
The user gets one whole machine to themselves for as long as they need. The host is paid
for every hour it is used. Orbit matches, counts the minutes and moves the money. It never
runs a model and never sees a conversation.

## Run it on your PC

Needs Python 3.11 or newer.

```
pip install -r requirements.txt
set ORBIT_DEV=1          # Windows.  On Mac or Linux:  export ORBIT_DEV=1
python -m orbit
```

Open http://localhost:8000 in your browser.

`ORBIT_DEV=1` turns on a "test funds" button in the store so you can try the whole loop
without a card. Leave it unset for real use.

## What is in v0.1

- Sign up and sign in.
- Store: buy hardware time by card through Stripe (needs keys, see below). Shown in dollars and minutes, never "credits".
- Ledger: every money movement is two or more rows that sum to zero. `/health` reports if the books ever stop balancing.
- Run a model: type a Hugging Face model name. Orbit reads the size and quantization from the name and says, for each machine online, whether it fits. When the name does not say, it says "unknown" rather than guess.
- Sessions: one user, one machine, exclusive. Start needs at least one hour of time on that machine. Stop charges by the minute, pays the host and takes Orbit's cut.
- Hosts: list a machine, get a token. The host program (step 2, not built yet) uses the token to say "I'm online".

Not built yet: the host program that actually runs the model, the chat screen, and the in-session guide.

## Settings

All optional, set as environment variables.

| Name | What | Default |
|---|---|---|
| `ORBIT_DEV` | `1` enables test funds | off |
| `ORBIT_DB` | path to the SQLite file | `orbit.db` |
| `ORBIT_SECRET` | signs sign-in cookies. Set one for real use or everyone is signed out on restart | random |
| `ORBIT_CUT_PERCENT` | Orbit's share of each session | `20` |
| `ORBIT_HOST`, `ORBIT_PORT` | where to listen | `127.0.0.1`, `8000` |
| `ORBIT_BASE_URL` | public address, used by Stripe redirects | `http://localhost:8000` |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | from the Stripe dashboard. Without them the store shows "not set up yet" | unset |

## Tests

```
python -m pytest
```

## Layout

```
orbit/app.py        pages, sessions, host API, Stripe hook
orbit/ledger.py     the only code that moves money
orbit/fit.py        does this model fit on that GPU
orbit/auth.py       sign-in
orbit/db.py         SQLite schema
orbit/templates/    HTML pages
tests/              ledger, fit and full-loop tests
```
