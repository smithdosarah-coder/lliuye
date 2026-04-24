"""Test scoreboard pure helpers: format_age, status_emoji, extract_signal."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `py scripts/orchestrator/tests/test_scoreboard.py` from project root
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))  # project_root/scripts

from orchestrator import scoreboard  # noqa: E402


# ---------- format_age ----------

def test_format_age_minutes():
    assert scoreboard.format_age(120) == "2m ago"


def test_format_age_zero():
    assert scoreboard.format_age(0) == "0m ago"


def test_format_age_under_hour():
    assert scoreboard.format_age(59 * 60) == "59m ago"


def test_format_age_hours():
    assert scoreboard.format_age(3600 * 5) == "5h ago"


def test_format_age_just_over_day():
    # 25 hours -> 1d ago
    assert scoreboard.format_age(3600 * 25) == "1d ago"


def test_format_age_days():
    assert scoreboard.format_age(86400 * 3) == "3d ago"


def test_format_age_none():
    assert scoreboard.format_age(None) == "-"


def test_format_age_negative_clamps():
    # Clock skew between systems shouldn't crash
    assert scoreboard.format_age(-10) == "0m ago"


# ---------- status_emoji ----------

UNKNOWN = "\U000026AB unknown"
FRESH = "\U0001F7E2 fresh"
IDLE = "\U0001F7E1 idle"
STALE = "\U0001F534 stale"


def test_status_unknown_when_no_head():
    assert scoreboard.status_emoji(None, head_present=False) == UNKNOWN
    assert scoreboard.status_emoji(100, head_present=False) == UNKNOWN


def test_status_unknown_when_age_none():
    assert scoreboard.status_emoji(None, head_present=True) == UNKNOWN


def test_status_fresh_under_4h():
    # 1 hour
    assert scoreboard.status_emoji(3600, head_present=True) == FRESH
    # just under 4h
    assert scoreboard.status_emoji(4 * 3600 - 1, head_present=True) == FRESH


def test_status_idle_4h_to_7d():
    # exactly 4h
    assert scoreboard.status_emoji(4 * 3600, head_present=True) == IDLE
    # 3 days
    assert scoreboard.status_emoji(86400 * 3, head_present=True) == IDLE
    # just under 7 days
    assert scoreboard.status_emoji(7 * 86400 - 1, head_present=True) == IDLE


def test_status_stale_over_7d():
    # exactly 7 days
    assert scoreboard.status_emoji(7 * 86400, head_present=True) == STALE
    # 30 days
    assert scoreboard.status_emoji(30 * 86400, head_present=True) == STALE


# ---------- extract_signal ----------

def test_extract_signal_basic():
    body = "Some body\n\nSignal: REVIEW-READY\nCo-Authored-By: x\n"
    assert scoreboard.extract_signal(body) == "REVIEW-READY"


def test_extract_signal_with_phase():
    body = "Body line\n\nSignal: P1-FOUNDATION-LIB-READY"
    assert scoreboard.extract_signal(body) == "P1-FOUNDATION-LIB-READY"


def test_extract_signal_missing():
    assert scoreboard.extract_signal("just a body, no signal") is None


def test_extract_signal_none_input():
    assert scoreboard.extract_signal(None) is None


def test_extract_signal_empty_input():
    assert scoreboard.extract_signal("") is None


# ---------- Y3 · signal lag ----------

from datetime import datetime, timedelta, timezone  # noqa: E402
from types import SimpleNamespace  # noqa: E402


def test_signal_age_none_when_commit_none():
    assert scoreboard.signal_age_seconds(None) is None


def test_signal_age_computes_from_timestamp():
    fixed_now = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)
    commit = SimpleNamespace(timestamp=fixed_now - timedelta(hours=2))
    assert scoreboard.signal_age_seconds(commit, now=fixed_now) == 2 * 3600


def test_signal_age_handles_naive_datetime():
    """Commit timestamp without tz should be treated as UTC."""
    fixed_now = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)
    naive = datetime(2026, 4, 24, 11, 45, 0)  # no tzinfo
    commit = SimpleNamespace(timestamp=naive)
    assert scoreboard.signal_age_seconds(commit, now=fixed_now) == 15 * 60


def test_signal_age_returns_none_on_malformed_timestamp():
    commit = SimpleNamespace(timestamp="not-a-datetime")
    assert scoreboard.signal_age_seconds(commit) is None


def test_worktree_record_carries_signal_lag_defaults():
    """Default dataclass construction yields None age + '-' human string."""
    rec = scoreboard.WorktreeRecord(
        name="w",
        role="worker",
        branch="feat/x",
        path="/tmp/x",
        head_sha=None,
        head_short=None,
        head_subject=None,
        last_signal=None,
        age_seconds=None,
        age_human="-",
        status="unknown",
        status_emoji="⚫",
    )
    assert rec.last_signal_age_seconds is None
    assert rec.last_signal_age_human == "-"


if __name__ == "__main__":
    tests = [
        test_format_age_minutes,
        test_format_age_zero,
        test_format_age_under_hour,
        test_format_age_hours,
        test_format_age_just_over_day,
        test_format_age_days,
        test_format_age_none,
        test_format_age_negative_clamps,
        test_status_unknown_when_no_head,
        test_status_unknown_when_age_none,
        test_status_fresh_under_4h,
        test_status_idle_4h_to_7d,
        test_status_stale_over_7d,
        test_extract_signal_basic,
        test_extract_signal_with_phase,
        test_extract_signal_missing,
        test_extract_signal_none_input,
        test_extract_signal_empty_input,
        test_signal_age_none_when_commit_none,
        test_signal_age_computes_from_timestamp,
        test_signal_age_handles_naive_datetime,
        test_signal_age_returns_none_on_malformed_timestamp,
        test_worktree_record_carries_signal_lag_defaults,
    ]
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            sys.exit(1)
    print(f"\n[ALL PASS] {len(tests)} scoreboard tests")
