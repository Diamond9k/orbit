"""The fleet ledger: one row per piece of work, so Cooper can see what each worker cost and produced.

These tests are the specification. swarm/ledger.py must make them pass without changing them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from swarm import ledger  # noqa: E402

HEADER = "| date | task | worker | minutes | result | note |\n|---|---|---|---|---|---|\n"


def test_add_creates_the_file_with_a_header_and_one_row(tmp_path):
    p = tmp_path / "ledger.md"
    ledger.add(str(p), task="T6", worker="local", minutes=7, result="accepted", note="ledger tool", date="2026-10-29 04:30")
    text = p.read_text(encoding="utf-8")
    assert text.startswith(HEADER)
    assert text.endswith("| 2026-10-29 04:30 | T6 | local | 7 | accepted | ledger tool |\n")


def test_add_appends_without_repeating_the_header(tmp_path):
    p = tmp_path / "ledger.md"
    ledger.add(str(p), task="T6", worker="local", minutes=7, result="accepted", note="one", date="2026-10-29 04:30")
    ledger.add(str(p), task="T7", worker="claude:fable", minutes=19, result="accepted", note="two", date="2026-10-29 04:40")
    ledger.add(str(p), task="T8", worker="local", minutes=12, result="failed", note="three", date="2026-10-29 05:00")
    text = p.read_text(encoding="utf-8")
    assert text.count("| date |") == 1
    assert text.count("\n") == 5  # header, separator, three rows


def test_a_pipe_in_the_note_is_escaped_so_the_table_keeps_its_columns(tmp_path):
    p = tmp_path / "ledger.md"
    ledger.add(str(p), task="T9", worker="local", minutes=1, result="failed", note="a | b", date="2026-10-29 05:10")
    last = p.read_text(encoding="utf-8").splitlines()[-1]
    assert last.count("|") == 7  # six cells need seven pipes; the note's pipe is escaped as \|
    assert "a \\| b" in last


def test_totals_sum_minutes_and_count_results_per_worker(tmp_path):
    p = tmp_path / "ledger.md"
    ledger.add(str(p), task="T6", worker="local", minutes=7, result="accepted", note="", date="2026-10-29 04:30")
    ledger.add(str(p), task="T7", worker="claude:fable", minutes=19, result="accepted", note="", date="2026-10-29 04:40")
    ledger.add(str(p), task="T8", worker="local", minutes=12, result="failed", note="", date="2026-10-29 05:00")
    assert ledger.totals(str(p)) == {
        "local": {"rows": 2, "minutes": 19, "accepted": 1, "failed": 1},
        "claude:fable": {"rows": 1, "minutes": 19, "accepted": 1, "failed": 0},
    }


def test_totals_of_a_missing_file_is_empty(tmp_path):
    assert ledger.totals(str(tmp_path / "nothing.md")) == {}


def test_the_command_line_adds_and_sums(tmp_path, capsys):
    p = str(tmp_path / "ledger.md")
    assert ledger.main(["add", "--file", p, "--task", "T6", "--worker", "local", "--minutes", "7",
                        "--result", "accepted", "--note", "ledger tool", "--date", "2026-10-29 04:30"]) == 0
    assert ledger.main(["add", "--file", p, "--task", "T7", "--worker", "local", "--minutes", "3",
                        "--result", "failed", "--note", "", "--date", "2026-10-29 04:35"]) == 0
    assert ledger.main(["sum", "--file", p]) == 0
    out = capsys.readouterr().out
    assert "local: 2 rows, 10 minutes, 1 accepted, 1 failed" in out


def test_an_unknown_result_is_refused(tmp_path):
    p = str(tmp_path / "ledger.md")
    try:
        ledger.add(p, task="T6", worker="local", minutes=7, result="maybe", note="", date="2026-10-29 04:30")
    except ValueError:
        pass
    else:
        raise AssertionError("result must be 'accepted' or 'failed'")
    assert not os.path.exists(p)
