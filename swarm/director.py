"""The director: owns the goal and writes the build order.

Reads CLAUDE.md, the scoreboard, the latest stranger report, the latest cycle result and the
current docs/NEXT.md, then rewrites the "## Now" section of docs/NEXT.md with the next three
items, each small enough for a 7B builder. Nobody writes NEXT.md by hand any more.

    DIRECTOR_MODEL=claude-opus-5-5 python swarm/director.py
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from swarm import scoreboard  # noqa: E402
from swarm.llm import ask  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT = open(os.path.join(ROOT, "prompts", "director.md")).read()


def latest(pattern: str) -> str:
    files = sorted(glob.glob(os.path.join(ROOT, "workspace", "runs", pattern)))
    return open(files[-1]).read() if files else "(none yet)"


def main() -> None:
    model = os.environ.get("DIRECTOR_MODEL", "local")
    bible = open(os.path.join(ROOT, "CLAUDE.md")).read()
    next_md = open(os.path.join(ROOT, "docs", "NEXT.md")).read()
    board = json.dumps(scoreboard.read(os.environ.get("ORBIT_DB", os.path.join(ROOT, "orbit.db"))), indent=2)
    stranger = latest("*-stranger.md")[:8000]
    last_run = latest("20*.md")
    last_run = last_run[-4000:] if last_run != "(none yet)" else last_run
    tree = "\n".join(sorted(
        os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
        if "/.venv/" not in p and "/node_modules/" not in p
    ))

    user = (
        f"# CLAUDE.md (the goal and the rules)\n{bible}\n\n"
        f"# Scoreboard\n{board}\n\n"
        f"# Latest stranger report\n{stranger}\n\n"
        f"# Last cycle result (tail)\n{last_run}\n\n"
        f"# Python files in the repo\n{tree}\n\n"
        f"# Current docs/NEXT.md\n{next_md}\n\n"
        "Write the new '## Now' section only, exactly as it should appear in docs/NEXT.md, "
        "starting with the line '## Now'. Three numbered items at most."
    )
    out = ask(model, PROMPT, user, max_tokens=3000)
    m = re.search(r"## Now.*", out, re.S)
    if not m:
        print("Director produced no '## Now' section. NEXT.md left unchanged.\n\n" + out)
        return
    new_now = m.group(0).strip()
    # drop anything after a following top-level section the model may have echoed
    new_now = re.split(r"\n## (?!Now)", new_now)[0].rstrip() + "\n\n"
    start = next_md.index("## Now")
    end = next_md.index("## Then") if "## Then" in next_md else next_md.index("## Later")
    updated = next_md[:start] + new_now + next_md[end:]
    open(os.path.join(ROOT, "docs", "NEXT.md"), "w").write(updated)
    print(f"# Director (model: {model})\n\n{new_now}")


if __name__ == "__main__":
    main()
