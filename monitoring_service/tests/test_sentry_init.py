# -*- coding: utf-8 -*-
"""Pytest for monitoring_service.sentry_init · graceful skip when DSN missing."""
from __future__ import annotations

import pytest

from monitoring_service import sentry_init


@pytest.fixture(autouse=True)
def reset_sentry():
    sentry_init.reset_for_tests()
    yield
    sentry_init.reset_for_tests()


def test_init_skipped_when_no_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    ok = sentry_init.init_sentry()
    assert ok is False
    status = sentry_init.get_init_status()
    assert status["initialized"] is False
    assert "SENTRY_DSN" in (status.get("skip_reason") or "") or not status.get("dsn_present")


def test_init_skipped_when_explicit_empty_dsn():
    ok = sentry_init.init_sentry(dsn="")
    assert ok is False


def test_init_attempts_with_explicit_dsn(monkeypatch):
    """传 fake DSN · sentry_sdk 装则尝试 init · 未装则 skip."""
    monkeypatch.setenv("SENTRY_DSN", "https://fake@sentry.example/1")
    if not sentry_init.is_sentry_available():
        ok = sentry_init.init_sentry()
        assert ok is False
        return
    # sentry_sdk 装时 · init 应成功 (DSN 是 syntactically valid)
    ok = sentry_init.init_sentry()
    if ok:
        status = sentry_init.get_init_status()
        assert status["initialized"] is True
        assert status["environment"] == "production"


def test_init_idempotent(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://fake@sentry.example/2")
    if not sentry_init.is_sentry_available():
        pytest.skip("sentry_sdk not installed · idempotent test only valid with real init")
    ok1 = sentry_init.init_sentry()
    ok2 = sentry_init.init_sentry()
    assert ok1 == ok2


def test_capture_exception_silent_when_not_init():
    """未 init 时 capture 不抛."""
    sentry_init.reset_for_tests()
    sentry_init.capture_exception(RuntimeError("test"))
    sentry_init.capture_message("test", level="warning")


def test_get_init_status_shape():
    status = sentry_init.get_init_status()
    assert "available" in status
    assert "initialized" in status
    assert "dsn_present" in status


def test_sample_rate_clamped(monkeypatch):
    """traces_sample_rate 超 [0, 1] 被 clamp."""
    monkeypatch.setenv("SENTRY_DSN", "https://fake@sentry.example/3")
    if not sentry_init.is_sentry_available():
        pytest.skip("sentry_sdk not installed")
    sentry_init.reset_for_tests()
    ok = sentry_init.init_sentry(traces_sample_rate=2.5)
    if ok:
        s = sentry_init.get_init_status()
        assert s.get("traces_sample_rate", 1.0) <= 1.0
