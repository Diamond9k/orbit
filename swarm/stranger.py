"""The stranger: uses Orbit the way a person who knows nothing would, and reports friction.

It runs the real app in memory, walks the whole path (land, sign up, find a model, list a
machine, add time, start, stop, account), records every screen as plain text, then asks a
model to read the walk as a first-time user and list where it got stuck.

    STRANGER_MODEL=claude-opus-5-5 python swarm/stranger.py > workspace/runs/<stamp>-stranger.md
"""
import html
import os
import re
import sys
import tempfile

os.environ.setdefault("ORBIT_DEV", "1")
_tmp = tempfile.mkdtemp()
os.environ["ORBIT_DB"] = os.path.join(_tmp, "stranger.db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient  # noqa: E402

from orbit import db  # noqa: E402
from orbit.app import app  # noqa: E402
from swarm.llm import ask  # noqa: E402

PROMPT = open(os.path.join(os.path.dirname(__file__), "..", "prompts", "stranger.md")).read()


def text_of(page: str) -> str:
    page = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S)
    page = re.sub(r"<[^>]+>", " ", page)
    page = html.unescape(page)
    return re.sub(r"\s+", " ", page).strip()


def walk() -> list[tuple[str, str]]:
    """Return (step, screen text) for each screen a first-time user sees."""
    db.init()
    c = TestClient(app)
    steps = []
    steps.append(("Open the site", text_of(c.get("/").text)))
    steps.append(("Search a model before signing up", text_of(c.get("/?model=bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M").text)))
    c.post("/signup", data={"email": "stranger@example.com", "password": "longenough"})
    steps.append(("After sign up", text_of(c.get("/account").text)))
    steps.append(("Search a model, no machines yet", text_of(c.get("/?model=bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M").text)))
    r = c.post("/hosts", data={"name": "My PC", "gpu": "Radeon RX 580", "vram_gb": 8, "price_dollars_per_hour": 0.25})
    steps.append(("List my own machine", text_of(r.text)))
    m = re.search(r"<pre[^>]*>(.*?)</pre>", r.text, re.S)
    token = m.group(1).strip() if m else ""
    c.post("/api/hosts/heartbeat", data={"token": token})
    steps.append(("Search again, machine online, no money", text_of(c.get("/?model=bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M").text)))
    steps.append(("Store", text_of(c.get("/store").text)))
    c.post("/store/dev-funds", data={"amount_cents": 1000})
    steps.append(("Search with money", text_of(c.get("/?model=bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M").text)))
    r = c.post("/sessions/start", data={"model": "bartowski/Qwen2.5-7B-Instruct-GGUF Q4_K_M", "host_id": 1}, follow_redirects=True)
    steps.append(("Session started", text_of(r.text)))
    r = c.post("/sessions/1/stop", follow_redirects=True)
    steps.append(("Session stopped", text_of(r.text)))
    steps.append(("Account afterwards", text_of(c.get("/account").text)))
    steps.append(("Paste a Hugging Face link with no quantization", text_of(c.get("/?model=https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF").text)))
    steps.append(("Try a model that is too big", text_of(c.get("/?model=x/Model-70B-Q4_K_M").text)))
    return steps


def main() -> None:
    model = os.environ.get("STRANGER_MODEL", "local")
    steps = walk()
    transcript = "\n\n".join(f"### {name}\n{screen[:2500]}" for name, screen in steps)
    report = ask(model, PROMPT, "Here is every screen, in order:\n\n" + transcript, max_tokens=3000)
    print(f"# Stranger report (model: {model})\n\n{report}\n")


if __name__ == "__main__":
    main()
