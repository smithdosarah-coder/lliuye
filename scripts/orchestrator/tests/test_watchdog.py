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


# ---------- Y2 · per-mesh tunable thresholds ----------

def test_custom_idle_threshold_fires_earlier():
    """Shorten idle_threshold to 30m => a 35m-old worker gets flagged idle."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(
        wt,
        head_sha="abc",
        age=35 * 60,  # 35 minutes
        prev_sha="abc",
        idle_threshold=30 * 60,  # 30-minute window
    )
    assert res == "stuck:idle-1h", f"expected idle tag on shortened window, got {res!r}"


def test_custom_idle_threshold_relaxed_keeps_fresh():
    """Loosen idle_threshold to 4h => a 2h-old worker is still fine."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(
        wt,
        head_sha="abc",
        age=2 * 3600,
        prev_sha="abc",
        idle_threshold=4 * 3600,
    )
    assert res is None


def test_custom_abandoned_threshold_overrides_default():
    """Set abandoned_threshold to 1h => a 90m-old silent worker goes straight to abandoned."""
    wt = _wt("worker")
    res = watchdog.detect_stuck(
        wt,
        head_sha="abc",
        age=90 * 60,
        prev_sha="abc",
        idle_threshold=30 * 60,
        abandoned_threshold=3600,
    )
    assert res == "stuck:abandoned-3d", f"expected abandoned tag, got {res!r}"


# ---------- G2 · git-unreachable sub-classification ----------

def test_unreachable_subtype_path_missing():
    wt = _wt("worker")
    res = watchdog.detect_stuck(
        wt, head_sha=None, age=None, prev_sha=None,
        unreachable_subtype="path-missing",
    )
    assert res == "stuck:git-path-missing"


def test_unreachable_subtype_perm_denied():
    wt = _wt("worker")
    res = watchdog.detect_stuck(
        wt, head_sha=None, age=None, prev_sha=None,
        unreachable_subtype="perm-denied",
    )
    assert res == "stuck:git-perm-denied"


def test_unreachable_subtype_binary_missing():
    wt = _wt("worker")
    res = watchdog.detect_stuck(
        wt, head_sha=None, age=None, prev_sha=None,
        unreachable_subtype="binary-missing",
    )
    assert res == "stuck:git-binary-missing"


def test_unreachable_subtype_unknown_falls_back_to_umbrella():
    """subtype='unreachable' or None → legacy stuck:git-unreachable tag."""
    wt = _wt("worker")
    res1 = watchdog.detect_stuck(
        wt, head_sha=None, age=None, prev_sha=None,
        unreachable_subtype="unreachable",
    )
    assert res1 == "stuck:git-unreachable"
    res2 = watchdog.detect_stuck(
        wt, head_sha=None, age=None, prev_sha=None,
    )
    assert res2 == "stuck:git-unreachable"


if __name__ == "__main__":
    tests = [
        test_fresh_worker_no_stuck,
        test_idle_1h_when_worker_stale_and_head_unchanged,
        test_idle_1h_not_fired_when_head_moved,
        test_abandoned_3d_takes_priority_over_idle,
        test_git_unreachable_when_head_sha_none,
        test_orchestrator_never_stuck_for_idle,
        test_orchestrator_still_flagged_git_unreachable,
        test_custom_idle_threshold_fires_earlier,
        test_custom_idle_threshold_relaxed_keeps_fresh,
        test_custom_abandoned_threshold_overrides_default,
        test_unreachable_subtype_path_missing,
        test_unreachable_subtype_perm_denied,
        test_unreachable_subtype_binary_missing,
        test_unreachable_subtype_unknown_falls_back_to_umbrella,
    ]
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            sys.exit(1)
    print(f"\n[ALL PASS] {len(tests)} watchdog tests")
