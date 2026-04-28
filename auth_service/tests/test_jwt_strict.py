# -*- coding: utf-8 -*-
"""auth_service.jwt_util · Stage E.3 strict secret config tests."""
from __future__ import annotations

import pytest

from auth_service.jwt_util import (
    JWTConfigError,
    _DEFAULT_DEMO_SECRET,
    assert_jwt_config_valid,
    is_demo_secret,
    issue,
    verify,
)


def test_strict_no_key_no_dev_mode_raises(monkeypatch):
    """production 启动 (DEV_MODE 未设) · JWT_SECRET_KEY 缺 → JWTConfigError."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("DEV_MODE", raising=False)
    with pytest.raises(JWTConfigError, match="JWT_SECRET_KEY 缺"):
        assert_jwt_config_valid()


def test_strict_dev_mode_allows_no_key(monkeypatch):
    """DEV_MODE=true · 缺 key 也 pass (demo 体验保留)."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("DEV_MODE", "true")
    assert_jwt_config_valid()  # 不抛


def test_strict_with_real_key_passes(monkeypatch):
    """有 JWT_SECRET_KEY · 不论 DEV_MODE 都 pass."""
    monkeypatch.setenv("JWT_SECRET_KEY", "my-strong-random-key-32-chars-min")
    monkeypatch.delenv("DEV_MODE", raising=False)
    assert_jwt_config_valid()


def test_is_demo_secret_when_using_demo(monkeypatch):
    """DEV_MODE=true · 缺 key 走 demo · is_demo_secret() True."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("DEV_MODE", "true")
    assert is_demo_secret() is True


def test_is_demo_secret_with_real_key(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "my-strong-random-key-different-from-demo")
    assert is_demo_secret() is False


def test_jwt_issue_verify_still_works_in_dev(monkeypatch):
    """DEV_MODE 下 demo secret 仍能 issue + verify · 不破现有 D.1 dev 体验."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("DEV_MODE", "true")
    t = issue("u_wangzhe", "rm")
    payload = verify(t)
    assert payload["sub"] == "u_wangzhe"
