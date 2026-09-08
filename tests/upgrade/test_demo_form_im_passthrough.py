# -*- coding: utf-8 -*-
"""形态模式下人对人 IM（/api/im/messages、已读回执）不被只读中间件拦截；@智能体的 /api/im/send 仍 403。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api_server

READONLY_CODE = "DEMO_FORM_READONLY"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.delenv("ALLOW_LEGACY_DEMO_TOKEN", raising=False)
    return TestClient(api_server.app)


def _login(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"user_id": "u_liuye", "password": "LIUYE"})
    assert r.status_code == 200, r.text


def _is_readonly_block(resp) -> bool:
    try:
        return resp.status_code == 403 and resp.json().get("detail", {}).get("error", {}).get("code") == READONLY_CODE
    except Exception:
        return False


def test_form_mode_lets_human_im_through_but_blocks_agent_chat(monkeypatch, client):
    monkeypatch.setenv("DEMO_FORM_MODE", "1")
    _login(client)
    # 人对人消息：不应被只读中间件拦（业务层可能因线程不存在返回 403 NOT_IN_THREAD / 400，但不是 READONLY）
    human = client.post("/api/im/messages", json={"thread_id": "no-such-thread", "content": "hi", "kind": "text"})
    assert not _is_readonly_block(human), human.text
    read = client.post("/api/im/threads/no-such-thread/read", json={})
    assert not _is_readonly_block(read), read.text
    # @智能体 → DeepSeek 的旧接口仍被只读中间件拦
    agent = client.post("/api/im/send", json={"message": "@报告 你好"})
    assert _is_readonly_block(agent), agent.text


def test_allowlist_helper_shapes():
    assert api_server._demo_form_write_allowed("POST", "/api/im/messages")
    assert api_server._demo_form_write_allowed("POST", "/api/im/threads/t1/read")
    assert not api_server._demo_form_write_allowed("POST", "/api/im/send")
    assert not api_server._demo_form_write_allowed("POST", "/api/im/threads")
    assert not api_server._demo_form_write_allowed("DELETE", "/api/im/threads/t1/read")


def test_form_mode_blocks_get_endpoints_that_invoke_models(monkeypatch, client):
    monkeypatch.setenv("DEMO_FORM_MODE", "1")
    _login(client)
    for path in ("/api/channel/personal_insight/cand-1", "/api/alert/drill/cust-1"):
        r = client.get(path)
        assert _is_readonly_block(r), (path, r.status_code, r.text[:200])
    # 普通读接口不受影响
    assert not _is_readonly_block(client.get("/api/im/threads"))


def test_get_denylist_helper():
    assert not api_server._demo_form_write_allowed("GET", "/api/channel/personal_insight/x")
    assert not api_server._demo_form_write_allowed("GET", "/api/alert/drill/x")
    assert api_server._demo_form_write_allowed("GET", "/api/alert/health")
