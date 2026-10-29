"""Run one bounded task on the local model: one file, tests written first, two attempts at most.

    python -I local_task.py --repo <worktree> --prompt <spec.md> --target swarm/ledger.py --tests tests/test_ledger.py

The model gets the spec and the tests and must answer with one complete Python file in a fenced
block. This script writes that file, runs the tests, and on failure gives the model one more
chance with the failure output. It prints a JSON summary: attempts, seconds, tokens, result.
No tools, no autonomy for the model: it only ever produces text; this script does the rest.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

SYSTEM = ("You are a careful Python programmer. Answer with exactly one fenced code block, "
          "```python ... ```, containing the COMPLETE contents of the requested file, and nothing "
          "else: no prose before or after, no second block.")


def ask(url, model, system, user, max_tokens, timeout):
    body = json.dumps({"model": model, "max_tokens": max_tokens, "temperature": 0.2,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return text, usage, time.time() - t0


def code_block(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).rstrip() + "\n"


def run_tests(repo, tests, timeout):
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", tests], cwd=repo, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return p.returncode == 0, (p.stdout + p.stderr)[-6000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--tests", required=True)
    ap.add_argument("--attempts", type=int, default=2)
    ap.add_argument("--max-tokens", type=int, default=2400)
    ap.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    ap.add_argument("--model", default="local")
    ap.add_argument("--timeout", type=int, default=1500)
    ap.add_argument("--log", default=None)
    a = ap.parse_args()

    spec = open(a.prompt, encoding="utf-8").read()
    tests_src = open(os.path.join(a.repo, a.tests), encoding="utf-8").read()
    user = spec + "\n\nThe tests the file must pass, unchanged:\n```python\n" + tests_src + "\n```\n"
    log = open(a.log, "w", encoding="utf-8") if a.log else None
    summary = {"target": a.target, "attempts": 0, "seconds_model": 0.0, "prompt_tokens": 0, "completion_tokens": 0,
               "result": "failed", "notes": []}
    target = os.path.join(a.repo, a.target)
    started = time.time()
    for attempt in range(1, a.attempts + 1):
        summary["attempts"] = attempt
        try:
            text, usage, secs = ask(a.url, a.model, SYSTEM, user, a.max_tokens, a.timeout)
        except Exception as e:  # the server failed or timed out: that is a failed attempt, recorded
            summary["notes"].append(f"attempt {attempt}: model call failed: {e}")
            break
        summary["seconds_model"] += secs
        summary["prompt_tokens"] += int(usage.get("prompt_tokens", 0))
        summary["completion_tokens"] += int(usage.get("completion_tokens", 0))
        if log:
            log.write(f"\n===== attempt {attempt}: model answer ({secs:.0f}s, usage {usage}) =====\n{text}\n")
        code = code_block(text)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        ok, out = run_tests(a.repo, a.tests, 300)
        if log:
            log.write(f"\n===== attempt {attempt}: tests {'PASS' if ok else 'FAIL'} =====\n{out}\n")
        summary["notes"].append(f"attempt {attempt}: {'tests pass' if ok else 'tests fail'}, {len(code.splitlines())} lines")
        if ok:
            summary["result"] = "accepted"
            break
        user = (spec + "\n\nYour previous version of the file:\n```python\n" + code + "\n```\n\nIt fails these tests. "
                "Return the whole corrected file.\n\nTest output:\n```\n" + out[-3000:] + "\n```\n"
                "\nThe tests, unchanged:\n```python\n" + tests_src + "\n```\n")
    summary["seconds_total"] = round(time.time() - started, 1)
    summary["seconds_model"] = round(summary["seconds_model"], 1)
    if log:
        log.write("\n===== summary =====\n" + json.dumps(summary, indent=2) + "\n")
        log.close()
    print(json.dumps(summary, indent=2))
    return 0 if summary["result"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
