"""Tiny local memory for the swarm: how often the top item failed, what is escalated.

    python swarm/state.py top            title of the top Now item in docs/NEXT.md
    python swarm/state.py fails          how many cycles that item has failed
    python swarm/state.py failed         record one more failure, print the new count
    python swarm/state.py reset          clear the count for it
    python swarm/state.py escalate "why" mark it escalated in NEXT.md, append to workspace/ESCALATE.md
    python swarm/state.py needs_director yes if Now is empty or its top item is escalated
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEXT = os.path.join(ROOT, "docs", "NEXT.md")
STATE = os.path.join(ROOT, "workspace", "state.json")
ESC = os.path.join(ROOT, "workspace", "ESCALATE.md")


def now_section() -> str:
    s = open(NEXT, encoding="utf-8").read()
    a = s.find("## Now")
    if a < 0:
        return ""
    rest = s[a:]
    b = re.search(r"\n## (?!Now)", rest)
    return rest[: b.start()] if b else rest


def top_item() -> str:
    m = re.search(r"^1\. \*\*(.+?)\*\*", now_section(), re.M)
    return m.group(1).strip() if m else ""


def top_is_escalated() -> bool:
    first = re.split(r"\n2\. ", now_section())[0]
    return "(escalated" in first


def load() -> dict:
    return json.load(open(STATE)) if os.path.exists(STATE) else {"fails": {}}


def save(d: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(d, open(STATE, "w"), indent=2)


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "top"
    top = top_item()
    d = load()
    if cmd == "top":
        print(top)
    elif cmd == "fails":
        print(d["fails"].get(top, 0))
    elif cmd == "failed":
        d["fails"][top] = d["fails"].get(top, 0) + 1
        save(d)
        print(d["fails"][top])
    elif cmd == "reset":
        d["fails"].pop(top, None)
        save(d)
    elif cmd == "escalate":
        why = argv[2] if len(argv) > 2 else "local agents could not finish it"
        s = open(NEXT, encoding="utf-8").read()
        s = s.replace(f"1. **{top}**", f"1. **{top}** _(escalated: needs Claude or Cooper)_", 1)
        open(NEXT, "w", encoding="utf-8").write(s)
        with open(ESC, "a", encoding="utf-8") as f:
            f.write(f"\n## {top}\n\n{why}\n\nSee the latest review/ branch on GitHub and workspace/runs/ for the log.\n")
        d["fails"].pop(top, None)
        save(d)
        print(f"escalated: {top}")
    elif cmd == "needs_director":
        print("yes" if (not top or top_is_escalated()) else "no")


if __name__ == "__main__":
    main(sys.argv)
