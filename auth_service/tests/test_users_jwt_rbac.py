# -*- coding: utf-8 -*-
"""auth_service unit tests · users + jwt_util + rbac · pure logic.

Coverage:
  - bcrypt hash + verify roundtrip
  - 5 user authenticate happy path · all 5 ids
  - authenticate invalid pwd · None
  - authenticate unknown user · None (constant-time · 不 leak existence)
  - JWT issue + verify roundtrip
  - JWT expired token → JWTError
  - JWT tampered token → JWTError
  - ACCESS matrix · 5 role × 6 agent matrix
  - HANDOFFS rm 3 pair
"""
from __future__ import annotations

import time

import pytest

from auth_service.jwt_util import JWTError, issue, issue_expired, verify
from auth_service.rbac import access_for, can_access, can_handoff, VALID_AGENTS, VALID_ROLES
from auth_service.users import (
    authenticate,
    get_user,
    get_user_public,
    hash_password,
    list_user_ids,
    verify_password,
)


# ============================================================================
# users.py · bcrypt + 5 user authenticate
# ============================================================================


def test_bcrypt_hash_verify_roundtrip():
    h = hash_password("zhongan-2026")
    assert h.startswith("$2b$") or h.startswith("$2a$") or h.startswith("$2y$")
    assert verify_password("zhongan-2026", h)
    assert not verify_password("wrong", h)


def test_5_user_authenticate_happy():
    """5 fixed user · password = user 名拼音 (per LoginForm.tsx:33 注释)."""
    expected = {
        "u_wangzhe": "wangzhe",
        "u_lihua":   "lihua",
        "u_zhoumin": "zhoumin",
        "u_chenkai": "chenkai",
        "u_liuye":   "liuye",
    }
    assert set(list_user_ids()) == set(expected.keys())
    for uid, pwd in expected.items():
        u = authenticate(uid, pwd)
        assert u is not None, f"{uid} login fail"
        assert u["id"] == uid
        assert "password_hash" not in u  # public dict 不返 hash


def test_authenticate_invalid_password_returns_none():
    assert authenticate("u_wangzhe", "wrong-pwd") is None


def test_authenticate_unknown_user_returns_none():
    """Unknown user 也走一次 verify · 防 timing attack reveal existence."""
    t0 = time.time()
    r = authenticate("u_does_not_exist", "any-password")
    elapsed = time.time() - t0
    assert r is None
    # bcrypt verify 至少 50ms · 防 timing leak (松验)
    assert elapsed >= 0.01


def test_get_user_public_strips_hash():
    full = get_user("u_wangzhe")
    assert full is not None
    assert "password_hash" in full
    pub = get_user_public("u_wangzhe")
    assert pub is not None
    assert "password_hash" not in pub
    assert pub["role"] == "rm"


# ============================================================================
# jwt_util.py · HS256 sign / verify
# ============================================================================


def test_jwt_issue_verify_roundtrip():
    t = issue("u_wangzhe", "rm")
    payload = verify(t)
    assert payload["sub"] == "u_wangzhe"
    assert payload["role"] == "rm"
    assert payload["exp"] > payload["iat"]


def test_jwt_expired_token_raises():
    t = issue_expired("u_wangzhe", "rm")
    with pytest.raises(JWTError, match="过期"):
        verify(t)


def test_jwt_tampered_signature_raises():
    t = issue("u_wangzhe", "rm")
    # 改最后 1 char (signature segment) → 必失败
    tampered = t[:-1] + ("a" if t[-1] != "a" else "b")
    with pytest.raises(JWTError):
        verify(tampered)


def test_jwt_empty_token_raises():
    with pytest.raises(JWTError):
        verify("")


# ============================================================================
# rbac.py · ACCESS matrix
# ============================================================================


def test_access_matrix_rm_narrowed():
    """RM 收窄 (Phase B Sprint 3 · per Q-052 #8): 主调 channel/report · 看 credit/alert read-only · 不可调 riskctrl/compliance."""
    # 主调 + read-only (4 agent)
    for ag in ("channel", "report", "credit", "alert"):
        assert can_access("rm", ag), f"rm should access {ag}"
    # 不可调 (per Q-052 #8 收窄)
    assert not can_access("rm", "riskctrl"), "rm should NOT access riskctrl (Q-052 #8 收窄)"
    assert not can_access("rm", "compliance"), "rm should NOT access compliance (Q-052 #8 收窄)"


def test_access_v2_rm_action_gate():
    """RM row-level/action gate (Phase B Sprint 3 contract sub-PR 1)."""
    from auth_service.rbac import can_action

    # 主调 channel + report: invoke/read/export/handoff (operational 4 actions · 不含 approve · RM 不是审批方)
    for ag in ("channel", "report"):
        for act in ("invoke", "read", "export", "handoff"):
            assert can_action("rm", ag, act), f"rm should have {act} on {ag}"
        assert not can_action("rm", ag, "approve"), f"rm should NOT have approve on {ag} (RM 不是审批方)"

    # 看 credit + alert: read only
    for ag in ("credit", "alert"):
        assert can_action("rm", ag, "read"), f"rm should have read on {ag}"
        for act in ("invoke", "export", "handoff", "approve"):
            assert not can_action("rm", ag, act), f"rm should NOT have {act} on {ag} (read-only · per Q-052 #8)"

    # 不可调 riskctrl + compliance: 任何 action 都 false
    for ag in ("riskctrl", "compliance"):
        for act in ("invoke", "read", "export", "handoff", "approve"):
            assert not can_action("rm", ag, act), f"rm should NOT have {act} on {ag} (Q-052 #8 收窄)"


def test_access_matrix_credit_officer_only_3():
    """credit_officer 仅 credit/report/alert (per auth-store.ts:63)."""
    assert set(access_for("credit_officer")) == {"credit", "report", "alert"}
    assert not can_access("credit_officer", "channel")
    assert not can_access("credit_officer", "compliance")
    assert not can_access("credit_officer", "riskctrl")


def test_access_matrix_compliance_officer_only_3():
    assert set(access_for("compliance_officer")) == {"compliance", "report", "alert"}
    assert not can_access("compliance_officer", "channel")


def test_access_matrix_risk_manager_only_3():
    assert set(access_for("risk_manager")) == {"riskctrl", "alert", "credit"}
    assert not can_access("risk_manager", "channel")


def test_access_matrix_admin_full():
    for ag in VALID_AGENTS:
        assert can_access("admin", ag)


def test_access_matrix_unknown_role_denied():
    for ag in VALID_AGENTS:
        assert not can_access("hacker", ag)


def test_handoffs_rm_3_pairs():
    """rm 3 pair: channel→report / report→credit / alert→compliance (per auth-store.ts:73-77)."""
    assert can_handoff("rm", "channel", "report")
    assert can_handoff("rm", "report", "credit")
    assert can_handoff("rm", "alert", "compliance")
    assert not can_handoff("rm", "channel", "compliance")  # not in matrix


def test_valid_roles_count():
    assert len(VALID_ROLES) == 5
    assert "admin" in VALID_ROLES
    assert "rm" in VALID_ROLES


def test_valid_agents_count():
    assert len(VALID_AGENTS) == 6
