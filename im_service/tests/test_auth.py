# -*- coding: utf-8 -*-
"""Pytest for im_service.auth · demo decoder + auth_service shim."""
from __future__ import annotations

import pytest

from im_service.auth import (
    DEMO_USERS,
    TokenInvalidError,
    decode_token,
    issue_demo_token,
)


def test_demo_users_5():
    """im-protocol §2 列 5 个固定 user."""
    assert set(DEMO_USERS) == {
        "u_wangzhe", "u_lihua", "u_zhoumin", "u_chenkai", "u_liuye",
    }


def test_issue_and_decode_each_user():
    for uid in DEMO_USERS:
        token = issue_demo_token(uid)
        assert token == f"demo-{uid}"
        decoded = decode_token(token)
        assert decoded == uid


def test_issue_unknown_user_raises():
    with pytest.raises(ValueError):
        issue_demo_token("u_intruder")


def test_decode_empty_raises():
    with pytest.raises(TokenInvalidError):
        decode_token("")


def test_decode_invalid_format_raises():
    with pytest.raises(TokenInvalidError):
        decode_token("bearer xyz")


def test_decode_demo_with_signature_suffix():
    """容忍 demo-u_wangzhe.<signature> 格式."""
    decoded = decode_token("demo-u_wangzhe.fake-sig")
    assert decoded == "u_wangzhe"


def test_decode_unknown_user_in_demo_raises():
    with pytest.raises(TokenInvalidError):
        decode_token("demo-u_unknown")
