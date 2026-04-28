# -*- coding: utf-8 -*-
"""auth endpoints integration tests via FastAPI TestClient.

Endpoints:
  POST /api/auth/login
  GET  /api/auth/me
  POST /api/auth/logout

Coverage:
  - login happy 5 user × 1 each + Set-Cookie verified
  - login bad pwd 401
  - login bad user 401
  - login missing field 400
  - me 解 cookie 返 user + roles + accessibleAgents
  - me 缺 cookie 401
  - me 过期 cookie 401
  - logout 清 cookie + idempotent (无 cookie 也 200)
  - require_agent factory · 401 if no cookie · 403 if role 无权 · 200 if 有权
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from auth_service.dependencies import COOKIE_NAME, require_agent
from auth_service.jwt_util import issue, issue_expired


@pytest.fixture(scope="module")
def client():
    from api_server import app
    return TestClient(app)


# ============================================================================
# /api/auth/login
# ============================================================================


@pytest.mark.parametrize(
    "uid,pwd,expected_role",
    [
        ("u_wangzhe", "wangzhe", "rm"),
        ("u_lihua",   "lihua",   "credit_officer"),
        ("u_zhoumin", "zhoumin", "compliance_officer"),
        ("u_chenkai", "chenkai", "risk_manager"),
        ("u_liuye",   "liuye",   "admin"),
    ],
)
def test_login_happy_5_user(client, uid, pwd, expected_role):
    resp = client.post("/api/auth/login", json={"user_id": uid, "password": pwd})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user"]["id"] == uid
    assert data["user"]["role"] == expected_role
    assert data["roles"] == [expected_role]
    assert "token" in data
    assert isinstance(data["accessibleAgents"], list)
    assert "password_hash" not in data["user"]
    # Set-Cookie 验证
    set_cookie_hdr = resp.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie_hdr
    assert "HttpOnly" in set_cookie_hdr or "httponly" in set_cookie_hdr.lower()
    assert "samesite=lax" in set_cookie_hdr.lower()


def test_login_bad_password(client):
    resp = client.post(
        "/api/auth/login",
        json={"user_id": "u_wangzhe", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "AUTH_FAILED"


def test_login_unknown_user(client):
    resp = client.post(
        "/api/auth/login",
        json={"user_id": "u_hacker", "password": "anything"},
    )
    assert resp.status_code == 401


def test_login_missing_field_400(client):
    resp = client.post("/api/auth/login", json={"user_id": ""})
    # 空 user_id + 缺 password · pydantic + endpoint 自检
    assert resp.status_code in (400, 422)


# ============================================================================
# /api/auth/me
# ============================================================================


def test_me_with_valid_cookie(client):
    """先 login 拿 cookie · 再 GET /me 验 user shape."""
    login = client.post(
        "/api/auth/login",
        json={"user_id": "u_lihua", "password": "lihua"},
    )
    assert login.status_code == 200
    # TestClient 自动 carry cookie 到下个 request
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user"]["id"] == "u_lihua"
    assert data["user"]["role"] == "credit_officer"
    assert set(data["accessibleAgents"]) == {"credit", "report", "alert"}


def test_me_without_cookie_401(client):
    fresh = TestClient(client.app)
    resp = fresh.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "AUTH_MISSING"


def test_me_with_expired_cookie_401(client):
    fresh = TestClient(client.app)
    expired_token = issue_expired("u_wangzhe", "rm")
    fresh.cookies.set(COOKIE_NAME, expired_token)
    resp = fresh.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "AUTH_INVALID"


def test_me_with_tampered_cookie_401(client):
    fresh = TestClient(client.app)
    fresh.cookies.set(COOKIE_NAME, "not-a-real-jwt")
    resp = fresh.get("/api/auth/me")
    assert resp.status_code == 401


# ============================================================================
# /api/auth/logout
# ============================================================================


def test_logout_clears_cookie(client):
    login = client.post(
        "/api/auth/login",
        json={"user_id": "u_chenkai", "password": "chenkai"},
    )
    assert login.status_code == 200
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    set_cookie = resp.headers.get("set-cookie", "")
    # cookie 被清 (Max-Age=0 or expires past)
    assert COOKIE_NAME in set_cookie
    assert ("max-age=0" in set_cookie.lower()) or ("expires" in set_cookie.lower())


def test_logout_idempotent_no_cookie(client):
    fresh = TestClient(client.app)
    resp = fresh.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["had_cookie"] is False


# ============================================================================
# require_agent factory · ACCESS matrix enforce (defence in depth)
# 单独 mount 一个 mini app 测 factory · 不依赖现有 agent endpoints
# ============================================================================


@pytest.fixture(scope="module")
def secured_app():
    """Mini app 挂 require_agent("channel") · 测 factory."""
    test_app = FastAPI()

    @test_app.get("/secret/channel")
    async def secret_channel(user=Depends(require_agent("channel"))):
        return {"hello": user["sub"], "agent": "channel"}

    @test_app.get("/secret/riskctrl")
    async def secret_riskctrl(user=Depends(require_agent("riskctrl"))):
        return {"hello": user["sub"], "agent": "riskctrl"}

    return TestClient(test_app)


def test_require_agent_no_cookie_401(secured_app):
    resp = secured_app.get("/secret/channel")
    assert resp.status_code == 401


def test_require_agent_rm_can_channel(secured_app):
    """王哲 rm role · channel 可访问."""
    secured_app.cookies.set(COOKIE_NAME, issue("u_wangzhe", "rm"))
    resp = secured_app.get("/secret/channel")
    assert resp.status_code == 200
    assert resp.json()["hello"] == "u_wangzhe"
    secured_app.cookies.clear()


def test_require_agent_credit_officer_blocked_from_channel(secured_app):
    """李华 credit_officer · channel 无权 → 403."""
    secured_app.cookies.set(COOKIE_NAME, issue("u_lihua", "credit_officer"))
    resp = secured_app.get("/secret/channel")
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"]["code"] == "ACCESS_DENIED"
    secured_app.cookies.clear()


def test_require_agent_compliance_officer_blocked_from_riskctrl(secured_app):
    """周敏 compliance_officer · riskctrl 无权 → 403."""
    secured_app.cookies.set(COOKIE_NAME, issue("u_zhoumin", "compliance_officer"))
    resp = secured_app.get("/secret/riskctrl")
    assert resp.status_code == 403
    secured_app.cookies.clear()


def test_require_agent_admin_full(secured_app):
    """admin 全 Agent 都可访问."""
    secured_app.cookies.set(COOKIE_NAME, issue("u_liuye", "admin"))
    resp1 = secured_app.get("/secret/channel")
    resp2 = secured_app.get("/secret/riskctrl")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    secured_app.cookies.clear()
