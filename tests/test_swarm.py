"""The deterministic parts of the swarm: scoreboard, the stranger's walk, the director's edit."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbit import db  # noqa: E402
from swarm import scoreboard  # noqa: E402



def test_stranger_walk_sees_every_screen():
    from swarm import stranger
    steps = stranger.walk()
    names = [n for n, _ in steps]
    assert "Session started" in names and "Session stopped" in names
    started = dict(steps)["Session started"]
    assert "Stop session" in started
    assert "<" not in started  # plain text, no tags


def test_director_replaces_now_section(tmp_path, monkeypatch):
    from swarm import director
    next_md = tmp_path / "NEXT.md"
    next_md.write_text("# What is next\n\n## Now\n1. old item\n\n## Then\n2. keep me\n\n## Later\n- x\n")
    monkeypatch.setattr(director, "ROOT", str(tmp_path))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "NEXT.md").write_text(next_md.read_text())
    (tmp_path / "CLAUDE.md").write_text("# goal")
    monkeypatch.setattr(director, "ask", lambda *a, **k: "## Now\nguidance\n1. **new item.** path/file.py\n\n## Then\nignored")
    director.main()
    out = (tmp_path / "docs" / "NEXT.md").read_text()
    assert "new item" in out and "old item" not in out
    assert "2. keep me" in out and "## Later" in out


def test_scoreboard_does_not_write(tmp_path):
    path = str(tmp_path / "s.db")
    db.init(path)
    before = open(path, "rb").read()
    scoreboard.read(path)
    assert open(path, "rb").read() == before


def test_scoreboard_counts_use_and_no_money(tmp_path):
    path = str(tmp_path / "s.db")
    db.init(path)
    conn = db.connect(path)
    conn.execute("INSERT INTO users (email, pw_hash, pw_salt) VALUES ('a@b.co', X'00', X'00')")
    conn.execute("INSERT INTO hosts (owner_id, name, gpu, vram_gb, token, status) VALUES (1, 'Box', 'RX 580', 8, 't', 'online')")
    conn.execute("INSERT INTO sessions (user_id, host_id, model, minutes) VALUES (1, 1, 'm', 7)")
    conn.close()
    s = scoreboard.read(path)
    assert (s["users"], s["machines"], s["machines_online"], s["sessions"], s["minutes"]) == (1, 1, 1, 1, 7)
    assert not any("cents" in k or "paid" in k for k in s)
    assert scoreboard.read("/nonexistent/orbit.db")["exists"] is False
