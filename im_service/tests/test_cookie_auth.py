# -*- coding: utf-8 -*-
"""Pytest · IM cookie auth (W-FIX2-A2-im-cookie-auth · 2026-04-29).

bug 根因 (Codex bug #8): frontend `web/src/lib/api/im.ts:34` 读
`document.cookie` 找 `auth_token` · 但 D.1 backend 真 cookie 名 `zhongan_auth`
+ httpOnly (JS 不可读) · resolve 全 fall to demo · 真 user 用 IM 时整链断。

修法: backend 各 IM endpoint 加 `zhongan_auth: str | None = Cookie(default=None)`
param · 优先 cookie path 走 `auth_service.jwt_util.verify` · frontend 改用
`credentials: "include"` 让 browser 自动带 zhongan_auth cookie。

本测试 ≥5 case 覆盖:
  1. 真 D.1 cookie (issue → set cookie → /api/im/threads 200)
  2. 缺 cookie + Authorization Bearer (legacy demo path 仍接受)
  3. 缺 cookie + 缺 Authorization → 401
  4. 真 D.1 cookie 已过期 → fallback Authorization Bearer 仍 200 (不阻断)
  5. 无效 cookie + 无效 Authorization → 401
  6. cookie 优先级 vs Authorization Bearer (cookie 命中即用 cookie 解的 user)
  7. im_service.auth.decode_jwt_cookie 单元测试 (None / 空 / 真 JWT / 已过期)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from auth_service.jwt_util import issue, issue_expired
from im_service.auth import decode_jwt_cookie


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    """FastAPI app + 隔离 sqlite db (与 test_send_rest 一致)."""
    monkeypatch.setenv("DEV_MODE", "true")  # 让 jwt_util 接受 demo secret
    from im_service import threads as db
    test_db = tmp_path / "im_cookie_auth.db"
    monkeypatch.setattr(db, "_db_path", test_db)

    import api_server  # noqa: WPS433
    return TestClient(api_server.app)


# ---------------------------------------------------------------------------
# decode_jwt_cookie unit tests
# ---------------------------------------------------------------------------


def test_decode_jwt_cookie_returns_none_for_blank(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    assert decode_jwt_cookie(None) is None
    assert decode_jwt_cookie("") is None
    assert decode_jwt_cookie("   ") is None or decode_jwt_cookie("   ") is None


def test_decode_jwt_cookie_accepts_real_d1_jwt(monkeypatch):
    """D.1 issue 的真 JWT · decode_jwt_cookie 应解出 sub."""
    monkeypatch.setenv("DEV_MODE", "true")
    token = issue("u_wangzhe", "rm")
    assert decode_jwt_cookie(token) == "u_wangzhe"


def test_decode_jwt_cookie_rejects_expired(monkeypatch):
    """已过期的 JWT · decode_jwt_cookie 返 None (caller 应 fallback)."""
    monkeypatch.setenv("DEV_MODE", "true")
    expired = issue_expired("u_lihua", "auditor")
    assert decode_jwt_cookie(expired) is None


def test_decode_jwt_cookie_rejects_garbage(monkeypatch):
    """非 JWT 字符串 · decode_jwt_cookie 返 None."""
    monkeypatch.setenv("DEV_MODE", "true")
    assert decode_jwt_cookie("not-a-real-jwt") is None
    assert decode_jwt_cookie("demo-u_wangzhe") is None  # demo token 不走 cookie path


# ---------------------------------------------------------------------------
# REST endpoint cookie auth (P0 bug #8 修复验证)
# ---------------------------------------------------------------------------


def test_threads_accepts_d1_cookie(client, monkeypatch):
    """真 D.1 zhongan_auth cookie · /api/im/threads 应 200 · 无需 Authorization Bearer."""
    monkeypatch.setenv("DEV_MODE", "true")
    token = issue("u_wangzhe", "rm")
    client.cookies.set("zhongan_auth", token)
    resp = client.get("/api/im/threads")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_id"] == "u_wangzhe"


def test_threads_cookie_priority_over_bearer(client, monkeypatch):
    """cookie 走真 D.1 path · Authorization Bearer 走 demo path · cookie 应优先。

    cookie 解 u_wangzhe · header 写 demo-u_lihua · 应返 u_wangzhe。
    """
    monkeypatch.setenv("DEV_MODE", "true")
    token = issue("u_wangzhe", "rm")
    client.cookies.set("zhongan_auth", token)
    resp = client.get(
        "/api/im/threads",
        headers={"Authorization": "Bearer demo-u_lihua"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "u_wangzhe"


def test_threads_falls_back_to_bearer_when_cookie_invalid(client, monkeypatch):
    """无效 cookie + 有效 demo Bearer → fallback 接受 demo path · 200。"""
    monkeypatch.setenv("DEV_MODE", "true")
    client.cookies.set("zhongan_auth", "garbage-not-jwt")
    resp = client.get(
        "/api/im/threads",
        headers={"Authorization": "Bearer demo-u_lihua"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "u_lihua"


def test_threads_falls_back_when_cookie_expired(client, monkeypatch):
    """expired cookie + 有效 demo Bearer → fallback 接受 demo path · 200。"""
    monkeypatch.setenv("DEV_MODE", "true")
    expired = issue_expired("u_wangzhe", "rm")
    client.cookies.set("zhongan_auth", expired)
    resp = client.get(
        "/api/im/threads",
        headers={"Authorization": "Bearer demo-u_zhoumin"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "u_zhoumin"


def test_threads_rejects_when_no_cookie_no_bearer(client, monkeypatch):
    """缺 cookie + 缺 Authorization + 缺 query token → 401 MISSING_TOKEN."""
    monkeypatch.setenv("DEV_MODE", "true")
    resp = client.get("/api/im/threads")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"]["code"] == "MISSING_TOKEN"


def test_threads_rejects_invalid_cookie_and_invalid_bearer(client, monkeypatch):
    """无效 cookie + 无效 Authorization → 401 (cookie 失败 fallback bearer 也失败)."""
    monkeypatch.setenv("DEV_MODE", "true")
    client.cookies.set("zhongan_auth", "garbage-not-jwt")
    resp = client.get(
        "/api/im/threads",
        headers={"Authorization": "Bearer also-garbage"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"]["code"] == "TOKEN_INVALID"


def test_messages_endpoint_accepts_cookie(client, monkeypatch):
    """完整流: 真 cookie 创 thread + send message + list messages · 全走 cookie."""
    monkeypatch.setenv("DEV_MODE", "true")
    token = issue("u_wangzhe", "rm")
    client.cookies.set("zhongan_auth", token)

    # create thread
    resp = client.post(
        "/api/im/threads",
        json={"title": "cookie-only thread", "kind": "group", "participants": ["u_lihua"]},
    )
    assert resp.status_code == 200, resp.text
    tid = resp.json()["id"]

    # send message
    resp = client.post(
        "/api/im/messages",
        json={"thread_id": tid, "content": "hello via cookie", "kind": "text"},
    )
    assert resp.status_code == 200, resp.text

    # list messages
    resp = client.get(f"/api/im/threads/{tid}/messages")
    assert resp.status_code == 200, resp.text
    msgs = resp.json()["messages"]
    assert len(msgs) >= 1
    assert msgs[-1]["content"] == "hello via cookie"
    assert msgs[-1]["from_id"] == "u_wangzhe"


def test_mark_read_accepts_cookie(client, monkeypatch):
    """POST /api/im/threads/{tid}/read · 走 cookie 应通."""
    monkeypatch.setenv("DEV_MODE", "true")
    token = issue("u_wangzhe", "rm")
    client.cookies.set("zhongan_auth", token)

    resp = client.post(
        "/api/im/threads",
        json={"title": "read test", "kind": "group", "participants": ["u_lihua"]},
    )
    tid = resp.json()["id"]

    resp = client.post(f"/api/im/threads/{tid}/read")
    assert resp.status_code == 200, resp.text
    assert resp.json()["unread_count"] == 0
