"""Test Signal trailer parsing + validation."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `py scripts/orchestrator/tests/test_signal.py` from project root
_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))  # project_root/scripts

from orchestrator.lib import signal  # noqa: E402


def test_basic_parse():
    msg = """feat(foo): add bar

Some body text here.

Signal: REVIEW-READY
Co-Authored-By: Claude <noreply@anthropic.com>
"""
    res = signal.parse(msg)
    assert res.found, "should find Signal trailer"
    assert res.trailer == "REVIEW-READY"
    assert res.is_known, "REVIEW-READY should match known patterns"
    assert res.line_count == 1


def test_missing_signal():
    msg = "fix(bar): something\n\nNo trailer here.\n"
    res = signal.parse(msg)
    assert not res.found
    assert res.trailer is None


def test_malformed_signal_lowercase():
    """Lowercase signal name should NOT match (format requires uppercase)."""
    msg = "feat(x): y\n\nSignal: review-ready"
    res = signal.parse(msg)
    assert not res.found, "lowercase signal name should not match strict regex"


def test_validate_pass():
    msg = "feat(x): y\n\nSignal: P0-WT-LAUNCHER-UPGRADED"
    ok, errs = signal.validate(msg)
    assert ok, f"should pass validation, got errors: {errs}"
    assert errs == []


def test_validate_fail_missing():
    ok, errs = signal.validate("just a subject\n")
    assert not ok
    assert any("missing Signal trailer" in e for e in errs)


def test_p_phase_signal_recognized():
    msg = "scaffold(orchestrator): foundation lib\n\nSignal: P1-FOUNDATION-LIB-READY"
    res = signal.parse(msg)
    assert res.found
    assert res.is_known, f"P-phase pattern should match {res.trailer!r}"


def test_qa_protocol_recognized():
    msg = "fix(agent3): apply A-007 decision\n\nSignal: A-007-ACK"
    res = signal.parse(msg)
    assert res.found
    assert res.is_known


def test_multiple_signals_invalid():
    msg = """feat(x): y

Signal: PHASE-1-DISPATCHED
Signal: REVIEW-READY
"""
    ok, errs = signal.validate(msg)
    assert not ok
    assert any("multiple" in e.lower() for e in errs)


def test_unknown_signal_warn_only():
    """Unknown name passes by default (require_known=False)."""
    msg = "feat(x): y\n\nSignal: COMPLETELY-MADE-UP-NAME"
    ok, errs = signal.validate(msg)
    assert ok, f"unknown name should pass when not strict: {errs}"

    ok, errs = signal.validate(msg, require_known=True)
    assert not ok, "unknown name should fail when require_known=True"
    assert any("unknown Signal name" in e for e in errs)


if __name__ == "__main__":
    tests = [
        test_basic_parse,
        test_missing_signal,
        test_malformed_signal_lowercase,
        test_validate_pass,
        test_validate_fail_missing,
        test_p_phase_signal_recognized,
        test_qa_protocol_recognized,
        test_multiple_signals_invalid,
        test_unknown_signal_warn_only,
    ]
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            sys.exit(1)
    print(f"\n[ALL PASS] {len(tests)} signal tests")
