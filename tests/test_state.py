import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from swarm import state  # noqa: E402

NEXT = """# What is next

## Now
guidance line

1. **First item.** details
2. **Second item.** details

## Then
3. **Later thing.**

## Later
- x
"""


def test_top_fails_and_escalate(tmp_path, monkeypatch):
    nxt = tmp_path / "NEXT.md"; nxt.write_text(NEXT)
    monkeypatch.setattr(state, "NEXT", str(nxt))
    monkeypatch.setattr(state, "STATE", str(tmp_path / "state.json"))
    monkeypatch.setattr(state, "ESC", str(tmp_path / "ESCALATE.md"))
    assert state.top_item() == "First item."
    assert state.load()["fails"].get("First item.", 0) == 0
    state.main(["x", "failed"]); state.main(["x", "failed"])
    assert state.load()["fails"]["First item."] == 2
    assert not state.top_is_escalated()
    state.main(["x", "escalate", "tests kept failing"])
    assert state.top_is_escalated()
    assert "First item." in (tmp_path / "ESCALATE.md").read_text()
    assert state.load()["fails"].get("First item.", 0) == 0


def test_needs_director_when_now_empty(tmp_path, monkeypatch):
    nxt = tmp_path / "NEXT.md"; nxt.write_text("# x\n\n## Now\n\n## Then\n1. **a**\n")
    monkeypatch.setattr(state, "NEXT", str(nxt))
    assert state.top_item() == ""


def test_cycle_begin_and_end_are_remembered(tmp_path, monkeypatch):
    nxt = tmp_path / "NEXT.md"; nxt.write_text(NEXT)
    monkeypatch.setattr(state, "NEXT", str(nxt))
    monkeypatch.setattr(state, "STATE", str(tmp_path / "state.json"))
    assert state.load().get("cycle") is None
    state.main(["x", "begin", "2026-10-29-0100"])
    c = state.load()["cycle"]
    assert c["stamp"] == "2026-10-29-0100" and c["item"] == "First item." and not c["ended"]
    # a cycle that began and never ended is visible to the next start
    import io, contextlib
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        state.main(["x", "unfinished"])
    assert out.getvalue().strip() == "2026-10-29-0100"
    state.main(["x", "end", "2026-10-29-0100", "tests=pass critic=clean guard=ok branch=build/x"])
    c = state.load()["cycle"]
    assert c["ended"] is True and c["how"].startswith("tests=pass")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        state.main(["x", "unfinished"])
    assert out.getvalue().strip() == ""
    # ending a different stamp does not overwrite the record of the one that began
    state.main(["x", "begin", "2026-10-29-0200"])
    state.main(["x", "end", "2026-10-29-0100", "late"])
    assert state.load()["cycle"]["stamp"] == "2026-10-29-0200" and not state.load()["cycle"]["ended"]
