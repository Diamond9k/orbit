"""The deterministic parts of the swarm: scoreboard, the stranger's walk, the director's edit."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbit import db, ledger  # noqa: E402
from swarm import scoreboard  # noqa: E402


def test_scoreboard_counts_hosts_paid(tmp_path):
    path = str(tmp_path / "s.db")
    db.init(path)
    conn = db.connect(path)
    conn.execute("INSERT INTO users (email, pw_hash, pw_salt) VALUES ('a@b.co', X'00', X'00')")
    conn.execute("INSERT INTO users (email, pw_hash, pw_salt) VALUES ('c@d.co', X'00', X'00')")
    conn.execute("INSERT INTO hosts (owner_id, name, gpu, vram_gb, price_cents_per_hour, token, status) "
                 "VALUES (1, 'Box', 'RX 580', 8, 100, 't', 'online')")
    conn.execute("INSERT INTO sessions (user_id, host_id, model) VALUES (2, 1, 'm')")
    ledger.post(conn, [("user:2", -100), ("host:1", 80), ("orbit:revenue", 20)], memo="session:1")
    conn.close()
    s = scoreboard.read(path)
    assert s["hosts_paid_cents"] == 80
    assert s["sessions_by_strangers"] == 1
    assert s["hosts_online"] == 1
    assert s["users"] == 2


def test_scoreboard_missing_db():
    assert scoreboard.read("/nonexistent/orbit.db")["exists"] is False


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
