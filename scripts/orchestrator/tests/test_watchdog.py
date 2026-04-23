"""Tests for watchdog.detect_stuck — pure classification function, 4 cases."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `py scripts/orchestrator/tests/test_watchdog.py` from project root.
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))  # project_root/scripts

from orchestrator import watchdog  # noqa: E402
from orchestrator.lib.mesh import Worktree  # noqa: E402


def _wt(role: str = "worker", name: str = "wt-test") -> Worktree:
    return Worktree(
        name=name,
        path=Path("/nonexistent"),
        branch="feat/test",
        role=role,
    )


def test_fresh_worker_no_stuck():
    """Worker with recent commit + HEAD just moved => no stuck tag."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(wt, head_sha="abc123", age=120, prev_sha="def456")
    assert res is None, f"expected None for fresh worker, got {res!r}"


def test_idle_1h_when_worker_stale_and_head_unchanged():
    """Worker, age > 1h, HEAD same as last tick => stuck:idle-1h."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(wt, head_sha="abc123", age=3700, prev_sha="abc123")
    assert res == "stuck:idle-1h", f"expected idle-1h, got {res!r}"


def test_idle_1h_not_fired_when_head_moved():
    """Worker, age > 1h but HEAD just moved => not stuck (commit just happened)."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(wt, head_sha="abc123", age=3700, prev_sha="old999")
    assert res is None, f"HEAD-moved worker should not be idle, got {res!r}"


def test_abandoned_3d_takes_priority_over_idle():
    """Worker, age > 3d => stuck:abandoned-3d (even if HEAD unchanged)."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(
        wt,
        head_sha="abc123",
        age=86400 * 4,  # 4 days
        prev_sha="abc123",
    )
    assert res == "stuck:abandoned-3d", f"expected abandoned-3d, got {res!r}"


def test_git_unreachable_when_head_sha_none():
    """head_sha None => stuck:git-unreachable, regardless of role/age."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(wt, head_sha=None, age=None, prev_sha=None)
    assert res == "stuck:git-unreachable", f"expected git-unreachable, got {res!r}"


def test_orchestrator_never_stuck_for_idle():
    """Orchestrator role is allowed to idle indefinitely => no idle-1h tag."""
    wt = _wt("orchestrator")
    res = watchdog.detect_stuck(wt, head_sha="abc", age=99999, prev_sha="abc")
    assert res is None, f"orchestrator should not be flagged idle, got {res!r}"


def test_orchestrator_still_flagged_git_unreachable():
    """git-unreachable applies to all roles (a broken worktree is always news)."""
    wt = _wt("orchestrator")
    res = watchdog.detect_stuck(wt, head_sha=None, age=None, prev_sha="abc")
    assert res == "stuck:git-unreachable"


if __name__ == "__main__":
    tests = [
        test_fresh_worker_no_stuck,
        test_idle_1h_when_worker_stale_and_head_unchanged,
        test_idle_1h_not_fired_when_head_moved,
        test_abandoned_3d_takes_priority_over_idle,
        test_git_unreachable_when_head_sha_none,
        test_orchestrator_never_stuck_for_idle,
        test_orchestrator_still_flagged_git_unreachable,
    ]
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            sys.exit(1)
    print(f"\n[ALL PASS] {len(tests)} watchdog tests")
