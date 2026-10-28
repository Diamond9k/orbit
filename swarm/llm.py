"""One call for every swarm role: ask(model, system, user) -> text.

A model name starting with "claude-" goes to Anthropic (needs ANTHROPIC_API_KEY).
Anything else goes to the local llama.cpp server on port 8080, which speaks the
OpenAI chat format. So each role picks its model with one environment variable.
"""
import json
import os
import urllib.request

LOCAL_URL = os.environ.get("LOCAL_LLM_URL", "http://127.0.0.1:8080/v1/chat/completions")


def ask(model: str, system: str, user: str, max_tokens: int = 4000) -> str:
    if model.startswith("claude-"):
        return _anthropic(model, system, user, max_tokens)
    return _local(model, system, user, max_tokens)


def _anthropic(model: str, system: str, user: str, max_tokens: int) -> str:
    import anthropic  # only needed for paid roles

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": user}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        return "REFUSED: the model declined this request."
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _local(model: str, system: str, user: str, max_tokens: int) -> str:
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(LOCAL_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"].strip()
