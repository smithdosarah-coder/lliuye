"""Test the validator.py CLI by invoking it as a subprocess."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve()
_VALIDATOR = _HERE.parent.parent / "validator.py"


def _run(msg: str, *extra: str) -> subprocess.CompletedProcess:
    """Write msg to a tempfile, invoke validator.py on it, return result."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(msg)
        path = f.name
    try:
        return subprocess.run(
            [sys.executable, str(_VALIDATOR), *extra, path],
            capture_output=True,
            text=True,
        )
    finally:
        Path(path).unlink(missing_ok=True)


def test_legal_trailer_exits_zero():
    msg = "feat(x): add y\n\nSignal: REVIEW-READY\n"
    res = _run(msg)
    assert res.returncode == 0, (
        f"expected exit 0 for legal trailer, got {res.returncode}\n"
        f"stderr: {res.stderr}"
    )


def test_missing_trailer_exits_one():
    msg = "fix(y): nope, no trailer here\n"
    res = _run(msg)
    assert res.returncode == 1, (
        f"expected exit 1 for missing trailer, got {res.returncode}"
    )
    assert "missing Signal trailer" in res.stderr, (
        f"expected error message on stderr, got: {res.stderr!r}"
    )


def test_multiple_trailers_rejected():
    msg = (
        "feat(x): two signals\n\n"
        "Signal: PHASE-1-DISPATCHED\n"
        "Signal: REVIEW-READY\n"
    )
    res = _run(msg)
    assert res.returncode == 1, (
        f"expected exit 1 for multiple trailers, got {res.returncode}"
    )
    assert "multiple" in res.stderr.lower(), (
        f"expected 'multiple' in stderr, got: {res.stderr!r}"
    )


def test_lowercase_name_does_not_match():
    """Lowercase name fails strict format -> treated as missing trailer."""
    msg = "feat(x): y\n\nSignal: review-ready\n"
    res = _run(msg)
    assert res.returncode == 1, (
        f"expected exit 1 for lowercase signal name, got {res.returncode}"
    )
    assert "missing Signal trailer" in res.stderr, (
        f"lowercase should be rejected as missing, got: {res.stderr!r}"
    )


def test_check_known_flag_rejects_unknown():
    msg = "feat(x): y\n\nSignal: COMPLETELY-MADE-UP-NAME\n"
    res_loose = _run(msg)
    assert res_loose.returncode == 0, (
        f"unknown name should pass without --check-known, got exit "
        f"{res_loose.returncode}"
    )
    res_strict = _run(msg, "--check-known")
    assert res_strict.returncode == 1, (
        f"unknown name should fail with --check-known, got exit "
        f"{res_strict.returncode}"
    )
    assert "unknown Signal name" in res_strict.stderr, (
        f"expected unknown-name error, got: {res_strict.stderr!r}"
    )


if __name__ == "__main__":
    tests = [
        test_legal_trailer_exits_zero,
        test_missing_trailer_exits_one,
        test_multiple_trailers_rejected,
        test_lowercase_name_does_not_match,
        test_check_known_flag_rejects_unknown,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[OK] {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"[FAIL] {t.__name__}: {e}")
    if failed:
        print(f"\n[FAIL] {failed}/{len(tests)} validator tests failed")
        sys.exit(1)
    print(f"\n[ALL PASS] {len(tests)} validator tests")
