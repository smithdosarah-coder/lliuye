# -*- coding: utf-8 -*-
"""Tests for POST /api/compliance/policy_diff endpoint (B5 sub-PR 2 implementation).

Coverage:
  - 200 SSE stage events + done envelope (auth: compliance_officer)
  - 401 no cookie (require_action enforce)
  - 403 wrong role (RM · per Q-052 #8 RM 不可调 compliance · sub-PR 2 added)
  - 400 validation (old_policy / new_policy empty)
  - done payload contains diffs/summary/lengths (real biz · 替 stub)
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from agent_compliance.api import app
from auth_service.dependencies import COOKIE_NAME
from auth_service.jwt_util import issue


client = TestClient(app)


# ---------------------------------------------------------------------------
# Auth fixtures (per Q-052 #8)
#   - compliance_officer (周敏 u_zhoumin) · invoke OK
#   - rm (王哲 u_wangzhe) · NO compliance.invoke (Q-052 #8 收窄)
#   - credit_officer (李华 u_lihua) · NO compliance.invoke
# ---------------------------------------------------------------------------

def _cookies_for(role: str, user_id: str = "u_test") -> dict[str, str]:
    """Mint JWT for given role · drop into TestClient cookies dict."""
    return {COOKIE_NAME: issue(user_id, role)}


COMPLIANCE_OFFICER_COOKIE = _cookies_for("compliance_officer", "u_zhoumin")
RM_COOKIE = _cookies_for("rm", "u_wangzhe")
ADMIN_COOKIE = _cookies_for("admin", "u_liuye")


# ---------------------------------------------------------------------------
# Auth gates (B5 sub-PR 2 added)
# ---------------------------------------------------------------------------


def test_policy_diff_401_no_cookie():
    """No auth cookie → 401 AUTH_MISSING (per require_action gate)."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "old", "new_policy": "new"},
    )
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "AUTH_MISSING"


def test_policy_diff_403_rm_role_blocked():
    """RM role no compliance.invoke action (per Q-052 #8 收窄) → 403 ACCESS_DENIED."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "old", "new_policy": "new"},
        cookies=RM_COOKIE,
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "ACCESS_DENIED"
    assert detail["error"]["details"]["role"] == "rm"
    assert detail["error"]["details"]["agent"] == "compliance"
    assert detail["error"]["details"]["action"] == "invoke"


# ---------------------------------------------------------------------------
# Happy path (compliance_officer · admin)
# ---------------------------------------------------------------------------


def test_policy_diff_200_compliance_officer():
    """compliance_officer (周敏) has compliance.invoke · 200 SSE stream."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={
            "old_policy": "第一条 客户经理不得超过 12 个月未回访客户",
            "new_policy": "第一条 客户经理不得超过 6 个月未回访客户。第二条 新增 KYC 复核要求",
            "scope": "对公授信",
        },
        cookies=COMPLIANCE_OFFICER_COOKIE,
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    # 3 stage events fired (extract_old / extract_new / diff)
    assert '"event":"stage"' in body or '"event": "stage"' in body
    assert '"stage":"extract_old"' in body or '"stage": "extract_old"' in body
    assert '"stage":"extract_new"' in body or '"stage": "extract_new"' in body
    assert '"stage":"diff"' in body or '"stage": "diff"' in body
    # done envelope
    assert '"event":"done"' in body or '"event": "done"' in body
    # done payload contains diffs structure (not stub)
    assert '"diffs"' in body
    assert '"summary"' in body
    # status:"stub" 已被真业务替代 · 不应出现
    assert '"status":"stub"' not in body and '"status": "stub"' not in body


def test_policy_diff_200_admin():
    """admin has all actions on all agents · 200 OK."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "old policy text", "new_policy": "new policy text"},
        cookies=ADMIN_COOKIE,
    )
    assert resp.status_code == 200


def test_policy_diff_200_without_scope():
    """200 SSE · scope optional."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "a", "new_policy": "b"},
        cookies=COMPLIANCE_OFFICER_COOKIE,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Validation (400 · pre-auth note: 401 fires first if no cookie)
# ---------------------------------------------------------------------------


def test_policy_diff_400_empty_old_policy():
    """400 VALIDATION_FAILED · old_policy 不能为空 (compliance_officer cookie · 过 auth gate)."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "", "new_policy": "new"},
        cookies=COMPLIANCE_OFFICER_COOKIE,
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "VALIDATION_FAILED"
    assert "old_policy" in detail["error"]["message"]


def test_policy_diff_400_whitespace_old_policy():
    """400 · old_policy 全空白."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "   ", "new_policy": "new"},
        cookies=COMPLIANCE_OFFICER_COOKIE,
    )
    assert resp.status_code == 400


def test_policy_diff_400_empty_new_policy():
    """400 VALIDATION_FAILED · new_policy 不能为空."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "old", "new_policy": ""},
        cookies=COMPLIANCE_OFFICER_COOKIE,
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "VALIDATION_FAILED"
    assert "new_policy" in detail["error"]["message"]


# ---------------------------------------------------------------------------
# Done payload shape (B5 sub-PR 2 真业务 · diff 结构)
# ---------------------------------------------------------------------------


def test_policy_diff_done_payload_includes_lengths():
    """done payload 含 old_policy_length + new_policy_length (backward compat)."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={"old_policy": "abc", "new_policy": "abcde"},
        cookies=COMPLIANCE_OFFICER_COOKIE,
    )
    assert resp.status_code == 200
    body = resp.text
    assert '"old_policy_length":3' in body or '"old_policy_length": 3' in body
    assert '"new_policy_length":5' in body or '"new_policy_length": 5' in body


def test_policy_diff_done_payload_diffs_structure():
    """done payload 含 diffs.added/removed/modified + summary 5 字段."""
    resp = client.post(
        "/api/compliance/policy_diff",
        json={
            "old_policy": "第一条 不得超过 12 个月。第二条 风险等级 ≥ B 级",
            "new_policy": "第一条 不得超过 6 个月。第三条 新增反洗钱要求",
        },
        cookies=COMPLIANCE_OFFICER_COOKIE,
    )
    assert resp.status_code == 200
    body = resp.text
    # diffs sub-keys
    assert '"added"' in body
    assert '"removed"' in body
    assert '"modified"' in body
    # summary fields
    assert '"old_rule_count"' in body
    assert '"new_rule_count"' in body
    assert '"total_change_count"' in body
