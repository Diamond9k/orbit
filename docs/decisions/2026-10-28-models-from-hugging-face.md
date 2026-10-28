# Models come from Hugging Face, by name

Date: 2026-10-28

Orbit keeps no model catalog. A user types a Hugging Face model name or pastes a link. Orbit
checks fit against each host's GPU memory. The host program downloads the model from Hugging
Face when the session starts. V1 supports GGUF files, which run on consumer GPUs.

Why: Hugging Face is where open models live. Orbit's value is the matching and the guide, not
a copy of the catalog.
