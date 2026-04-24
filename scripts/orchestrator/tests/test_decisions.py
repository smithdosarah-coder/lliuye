"""Tests for orchestrator/decisions.py — decisions-log parser + CLI helpers."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))

from orchestrator import decisions  # noqa: E402


SAMPLE_LOG = """# Decisions Log

**协议**：xxx
---

## [Q-001] 2026-04-18 · report · regex patch

**CLI**: report

### 选项
- A
- B

### [A-001] 2026-04-18 · 主 CLI

**Decision**: A
**Rationale**: because.

---

## [Q-002] 2026-04-19 · data · mock scope

### 选项
- A
- B

---

## [Q-003] 2026-04-20 · eval · baseline

### [A-003] 2026-04-20 · 主 CLI

**Decision**: approved.
"""


def test_parse_log_collects_q_and_a_entries():
    entries = decisions.parse_log(SAMPLE_LOG)
    ids = [e.id for e in entries]
    assert ids == ["Q-001", "A-001", "Q-002", "Q-003", "A-003"]


def test_parse_log_extracts_titles():
    entries = decisions.parse_log(SAMPLE_LOG)
    q1 = next(e for e in entries if e.id == "Q-001")
    assert "regex patch" in q1.title


def test_parse_log_bodies_span_to_next_header():
    entries = decisions.parse_log(SAMPLE_LOG)
    q1 = next(e for e in entries if e.id == "Q-001")
    assert "CLI" in q1.body
    # Q-001 body should stop before A-001 header.
    assert "Rationale" not in q1.body


def test_find_entries_pairs_q_with_matching_a():
    entries = decisions.parse_log(SAMPLE_LOG)
    hits = decisions.find_entries(entries, "Q-001")
    assert [e.id for e in hits] == ["Q-001", "A-001"]


def test_find_entries_accepts_a_id_and_pairs_backwards():
    entries = decisions.parse_log(SAMPLE_LOG)
    hits = decisions.find_entries(entries, "A-003")
    # A-003 + its matching Q-003 come back (order: matched-id first, pair second).
    assert set(e.id for e in hits) == {"A-003", "Q-003"}


def test_find_entries_empty_on_unknown_id():
    entries = decisions.parse_log(SAMPLE_LOG)
    assert decisions.find_entries(entries, "Q-999") == []


def test_find_entries_rejects_malformed_id():
    entries = decisions.parse_log(SAMPLE_LOG)
    assert decisions.find_entries(entries, "QQQ") == []
    assert decisions.find_entries(entries, "Q-") == []


def test_unresolved_returns_qs_without_a():
    entries = decisions.parse_log(SAMPLE_LOG)
    open_qs = decisions.unresolved(entries)
    # Q-001 has A-001, Q-003 has A-003. Only Q-002 should be unresolved.
    assert [e.id for e in open_qs] == ["Q-002"]


def test_parse_log_handles_empty_input():
    assert decisions.parse_log("") == []


def test_cmd_find_returns_zero_on_hit(capsys):
    entries = decisions.parse_log(SAMPLE_LOG)
    rc = decisions.cmd_find(entries, "Q-001")
    assert rc == 0
    out = capsys.readouterr().out
    assert "Q-001" in out and "A-001" in out


def test_cmd_find_returns_one_on_miss(capsys):
    entries = decisions.parse_log(SAMPLE_LOG)
    rc = decisions.cmd_find(entries, "Q-999")
    assert rc == 1
    err = capsys.readouterr().err
    assert "no entry matching" in err


def test_cmd_list_unresolved_prints_only_open_qs(capsys):
    entries = decisions.parse_log(SAMPLE_LOG)
    rc = decisions.cmd_list(entries, unresolved_only=True)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Q-002" in out
    assert "Q-001" not in out
    assert "A-001" not in out


def test_cmd_list_all_prints_every_entry(capsys):
    entries = decisions.parse_log(SAMPLE_LOG)
    rc = decisions.cmd_list(entries, unresolved_only=False)
    assert rc == 0
    out = capsys.readouterr().out
    for expected in ("Q-001", "A-001", "Q-002", "Q-003", "A-003"):
        assert expected in out


def test_main_with_explicit_log_path_finds_entry(capsys):
    with tempfile.TemporaryDirectory() as td:
        log_path = Path(td) / "log.md"
        log_path.write_text(SAMPLE_LOG, encoding="utf-8")
        rc = decisions.main(["--log", str(log_path), "find", "Q-002"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Q-002" in out
