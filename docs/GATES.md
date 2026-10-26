# Gates: what each piece waits on

Same format as Arc OS docs/GATES.md. Update this file when a gate closes, with the evidence.

Last checked 2026-10-26.

| Gate | What is owed | Owner | Lights up | State |
| --- | --- | --- | --- | --- |
| G1 | Licence for the public repo (proposal: Apache-2.0) | Cooper | Public repo, ADR 0005 | Open |
| G2 | Domain bought and pointed at the Vercel project | Cooper | Live URL, email sender, Discord vanity link | Open. The landing page uses hello@orbit.app as a placeholder; not checked or owned |
| G3 | Discord server created, invite link set as `DISCORD_INVITE` | Cooper | Discord pill, community links | Open |
| G4 | Stripe account; test keys in Vercel (V2), live keys and Connect (V3) | Cooper | Credits purchase, host payouts | Open |
| G5 | Apple Developer account | Cooper | TestFlight (V2), App Store and in-app purchase (V3) | Open |
| G6 | Price of credits; credits per hour per GPU tier; host hourly rate per tier | Cooper | Pricing page numbers, marketplace, payouts | Open. Site shows "set at launch" until then |
| G7 | Content policy for rentals (what may run on a host's GPU) | Cooper | Host and renter terms, marketplace launch | Open |
| G8 | Windows code-signing certificate | Cooper | Installer without a SmartScreen warning | Open. Unsigned works for V2 test users |
