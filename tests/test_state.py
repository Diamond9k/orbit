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
