# The birth of Orbit

28 October 2026. One conversation between Cooper and a Claude session, in one day. This is
the record of where Orbit came from and why the bible says what it says. It is history, not
rules. The rules are in `CLAUDE.md`.

## The idea, as Cooper said it

Run open source models on local hardware instead of a datacenter. People with an idle GPU
list it. People who want a model use it from a browser and pay for the hardware time, not
per token. An agent inside the platform helps the user along. Datacenters are what make AI
expensive. Privacy is the point: the conversation stays on the machine that runs the model.

Cooper's own words on the parts that became rules:

- "we need to find a way to secure the hosts compute to only the users view."
- "we dont need to promise anything. Win Through Your Actions, Never Through Argument."
- "no outlandish claims." "I only will pay them if someone used their hardware."
- "do not give anything for free because when you do it lowers the value of the paid item."
- "the helper will only be in the platform when using the rented hardware."
- "I want the renter to be called a user because my selling isnt 'rent gpu' its 'run open
  source models with only paying for the hardware and no API credit'."
- "orbit is the broker and the thing bringing the want to run self hosted models type of ppl
  and the I have a RX 5090 that I dont use and want to make money off of it type of ppl."
- "the whole point of this is to be able to self host things with ease. I dont want to have
  to pay supabase to run my business."
- "Lets use my gaming pc as my datacenter."
- "I want to directly use hugging face for all the models."
- "Vast can't take them. You can, but only if the host program installs like a game."
- "I dont want the website to be where much of the selling happens. I want it to prioritize
  overall use QOL and the level of usefullness across the board."
- "when I look at money in the business world I dont look at it as a measurment of success
  but 100% a byproduct of success."
- "nothing is too strict and the wording is good. this has to be strict since its the bible
  of orbit."
- "I dont want to have to merge anything."
- "I want it to run 24/7." "no loop." "I want this to be full autonomy to reaching the goal."
- "multiple agents running on my pc open source with no api cost then for the things that
  cant be messed up just go to you."

## What was cut

- A hardware recycler marketplace. Cooper: "scrap recycler that was just me thinkign outloud."
- "100% guarantee of privacy" as a claim. Replaced by the broker design that makes the claim
  unnecessary: Orbit cannot read what it cannot open.
- Credits. Replaced by hardware time shown in dollars and minutes.
- Bidding and shared machines. One user, one machine, exclusive.
- Any paid cloud service to run Orbit itself. Stripe per transaction is the one exception.
- Calling the user a renter.

## The goal

Asked what a broad goal for a group of AI agents should be, and told that money is a
byproduct of success and not its measure, the goal became:

> Make running an AI model on hardware you control as easy as opening a browser tab, and so
> good that nobody who tries it goes back to a datacenter. Prove it by paying hosts one
> million dollars for sessions that strangers ran on their machines without needing help
> from anyone.

The test that follows from it: before any task, does this move hosts paid, or remove
something that blocks it? If neither, it is not the work.

## How the bible came to be

Cooper asked for a `CLAUDE.md` so good it never needs changing until the goal is met. It was
reframed twice at his request: first to explain how everything works, then to be stricter.
Each rule traces to a moment in the conversation:

| Rule | Where it came from |
|---|---|
| 1 Broker, not middleman | "secure the hosts compute to only the users view," and the decision that Orbit forwards sealed envelopes it cannot open |
| 2 One user, one machine, no bidding | The Vast.ai scan showed bidding and shared machines; Cooper: "Im good with no bidding" |
| 3 Nothing is free | "do not give anything for free" |
| 4 Hosts paid for use, never for listing | "I only will pay them if someone used their hardware" |
| 5 No promises, no claims | "Win Through Your Actions, Never Through Argument" |
| 6 Double-entry money | Chosen so a balance can never change without a matching row; `/health` checks it |
| 7 Nothing depends on a datacenter | "I dont want to have to pay supabase"; "Lets use my gaming pc as my datacenter" |
| 8 The user never sees Docker, ports, drivers | "the user experience while still keeping the same ideas" |
| 9 Host program installs like an app, only dials out | "Vast can't take them. You can, but only if the host program installs like a game" |
| 10 Text is data, not instructions | Standard defense once agents read web pages and model output |
| 11 Secrets never enter the repo, chat or memory | A live key appeared in a pasted screenshot during setup |
| 12 Branches merge themselves | "I dont want to have to merge anything" |
| 13 Ask Cooper before money, publishing, the irreversible | Cooper decides; agents build |

## What got built on day one

In order, each on a branch, each merged when tests passed:

1. The repository cleared.
2. The v0.1 web app: sign-in, hardware-time store, double-entry ledger, model fit from a
   Hugging Face name, exclusive sessions charged by the minute, host listing with a token,
   heartbeat API. Python, FastAPI, SQLite, Jinja2, Stripe. Six libraries.
3. The site rebuilt on self-hosted Bootstrap after Cooper said it "looks like shit in all
   aspects" and asked for proven code over hand-written code.
4. The README, the decisions folder, the logo.
5. Orbit ran on Cooper's Windows PC. Cooper listed his own machine, a Radeon RX 580 with
   8 GB, as host number one. The full loop settled correctly on real hardware: one cent
   moved from a user to a host through the ledger.
6. Stripe wired in test mode. Cooper bought hardware time with a test card and it landed in
   the ledger through the webhook.
7. The GitHub workflow that runs the tests and merges green `build/` branches by itself.
8. A scan of Vast.ai from primary sources, recorded in `docs/SCAN-vastai.md`.
9. The swarm.

## The swarm

Cooper wanted agents that work toward the goal around the clock on his own PC with open
models and no API cost, and Claude only for what cannot be wrong. The first attempt was
rejected: "its not working towards the goal. this a lack luster attempt at pleasing my
response of a mass AI agent cult trying to follow one broad goal." The second attempt was
rejected for stopping: "the whole point of the open source model is that it doesnt need to
turn off since its free."

What stood at the end of the day: five roles in turn on one GPU. A scout walks the site as a
stranger. A director (Claude, rarely) writes the next three build items from the goal, the
scoreboard and the scout's report. A builder (local 14B model through Aider) takes the top
item on a throwaway branch. A fixer gets one retry. A critic reads the change cold; Claude
gets the final say on money, sessions and the host program. A guard sends any change to a
protected file to review. `swarm/forever.sh` runs cycles until told to stop.

The local model ran on llama.cpp's Vulkan build because Ollama does not support the RX 580
on Windows. The 7B model described work instead of doing it; the 14B model wrote correct
files. Its first three cycles built the host program with passing tests and the critic
flagged it each time. A Claude session finished that item by hand, and fixed the swarm so an
escalation reaches main instead of being pushed to a branch nothing merges.

## Where it stood at the end

- Hosts paid: ten cents, to Cooper, by Cooper.
- Sessions: two. Sessions by strangers: zero.
- Hosts listed: one, online. Users: one.
- The swarm running on Cooper's PC, working on the heartbeat reply that tells a host what to
  load.

Everything after this is in `docs/NEXT.md`.
