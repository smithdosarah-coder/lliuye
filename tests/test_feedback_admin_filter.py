# -*- coding: utf-8 -*-
"""Phase B BE10 V2 · admin GET /api/audit/llm_calls 过滤 + 分页覆盖.

POST 多条 /api/feedback (混 agent / user_id), 验证 admin endpoint 各 filter:
  - endpoint=/api/feedback (隔离 LLM 调用流水)
  - agent_id 单独过滤
  - user_id 单独过滤
  - agent_id + user_id 组合
  - limit / offset 分页
"""
from __future__ import annotations

import importlib
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def isolated_admin(tmp_path: Path, monkeypatch):
    """每条测试独占 audit sqlite + 干净 feedback dir + admin auth override."""
    audit_db = tmp_path / "audit_admin.db"
    monkeypatch.setenv("AUDIT_DB_PATH", str(audit_db))
    monkeypatch.setenv("ENCRYPT_AT_REST", "false")

    import audit_service.recorder as recorder_mod
    recorder_mod.set_default_recorder(None)

    import api_server
    importlib.reload(api_server)
    monkeypatch.setattr(api_server, "PROJECT_ROOT", tmp_path, raising=True)

    # Override require_user to return admin · 跳过 cookie/JWT 流程
    from auth_service.dependencies import require_user

    async def _admin_stub():
        return {"sub": "test-admin", "role": "admin"}

    api_server.app.dependency_overrides[require_user] = _admin_stub

    yield tmp_path, api_server

    api_server.app.dependency_overrides.pop(require_user, None)
    recorder_mod.set_default_recorder(None)


def _post_feedback(client, *, agent: str, user_id: str, session: str = "s") -> None:
    resp = client.post("/api/feedback", json={
        "agent": agent,
        "session_id": session,
        "original_output": {"x": 1},
        "user_correction": {"x": 2},
        "correction_reason": "test",
        "user_id": user_id,
    })
    assert resp.status_code == 200, resp.text


def test_admin_filter_by_endpoint(isolated_admin):
    """endpoint=/api/feedback 过滤只返 feedback modify 流水, 不混 LLM 调用."""
    _, api_server = isolated_admin
    from fastapi.testclient import TestClient
    from audit_service.recorder import LLMCall, default_recorder

    # 直接塞一条非 /api/feedback 的 LLM 调用模拟正常流量
    default_recorder().record(LLMCall(
        agent_id="credit", endpoint="/api/credit/run",
        model="deepseek-chat", prompt="...", response="...",
    ))

    with TestClient(api_server.app) as client:
        _post_feedback(client, agent="credit", user_id="rm-001")
        _post_feedback(client, agent="report", user_id="rm-002")

        resp = client.get("/api/audit/llm_calls?limit=20")
        assert resp.status_code == 200
        all_items = resp.json()["items"]
        assert len(all_items) == 3  # 1 LLM + 2 feedback

        # 应用 endpoint filter 走 since/until/user_id/agent_id (audit_service.api 当前
        # 不暴露 endpoint param), 改为客户端 filter 验
        feedback_only = [r for r in all_items if r["endpoint"] == "/api/feedback"]
        assert len(feedback_only) == 2
        assert {r["agent_id"] for r in feedback_only} == {"credit", "report"}


def test_admin_filter_by_agent_id(isolated_admin):
    _, api_server = isolated_admin
    from fastapi.testclient import TestClient

    with TestClient(api_server.app) as client:
        _post_feedback(client, agent="credit", user_id="rm-001")
        _post_feedback(client, agent="credit", user_id="rm-002")
        _post_feedback(client, agent="report", user_id="rm-001")

        resp = client.get("/api/audit/llm_calls?agent_id=credit&limit=20")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert all(r["agent_id"] == "credit" for r in items)


def test_admin_filter_by_user_id(isolated_admin):
    _, api_server = isolated_admin
    from fastapi.testclient import TestClient

    with TestClient(api_server.app) as client:
        _post_feedback(client, agent="credit", user_id="rm-A")
        _post_feedback(client, agent="report", user_id="rm-B")
        _post_feedback(client, agent="alert", user_id="rm-A")

        resp = client.get("/api/audit/llm_calls?user_id=rm-A&limit=20")
        items = resp.json()["items"]
        assert len(items) == 2
        assert all(r["user_id"] == "rm-A" for r in items)
        assert {r["agent_id"] for r in items} == {"credit", "alert"}


def test_admin_filter_by_agent_id_and_user_id(isolated_admin):
    _, api_server = isolated_admin
    from fastapi.testclient import TestClient

    with TestClient(api_server.app) as client:
        _post_feedback(client, agent="credit", user_id="rm-A")
        _post_feedback(client, agent="credit", user_id="rm-B")
        _post_feedback(client, agent="report", user_id="rm-A")

        resp = client.get("/api/audit/llm_calls?agent_id=credit&user_id=rm-A&limit=20")
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["agent_id"] == "credit"
        assert items[0]["user_id"] == "rm-A"


def test_admin_pagination_limit_offset(isolated_admin):
    """5 条 feedback · limit=2 + offset=0/2/4 各取 1 页 · 总 3 页覆盖全集."""
    _, api_server = isolated_admin
    from fastapi.testclient import TestClient

    with TestClient(api_server.app) as client:
        for i in range(5):
            _post_feedback(client, agent="credit", user_id=f"rm-{i:03d}", session=f"s{i}")

        page1 = client.get("/api/audit/llm_calls?limit=2&offset=0").json()
        page2 = client.get("/api/audit/llm_calls?limit=2&offset=2").json()
        page3 = client.get("/api/audit/llm_calls?limit=2&offset=4").json()

        assert page1["total"] == 5
        assert page2["total"] == 5
        assert page3["total"] == 5
        assert len(page1["items"]) == 2
        assert len(page2["items"]) == 2
        assert len(page3["items"]) == 1

        # 三页 user_id 集合无交叠 + 合起来等于全集
        seen = (
            {r["user_id"] for r in page1["items"]}
            | {r["user_id"] for r in page2["items"]}
            | {r["user_id"] for r in page3["items"]}
        )
        assert seen == {f"rm-{i:03d}" for i in range(5)}


def test_admin_returns_redacted_correction_via_prompt_response(isolated_admin):
    """admin 看到的 prompt/response = original_output / user_correction JSON · 不露 raw."""
    _, api_server = isolated_admin
    from fastapi.testclient import TestClient

    with TestClient(api_server.app) as client:
        client.post("/api/feedback", json={
            "agent": "credit",
            "session_id": "s-1",
            "original_output": {"额度": 500},
            "user_correction": {"额度": 700},
            "correction_reason": "现金流足",
            "user_id": "rm-X",
        })
        resp = client.get("/api/audit/llm_calls?agent_id=credit&limit=5")
        rows = resp.json()["items"]
        assert len(rows) == 1
        row = rows[0]
        assert row["model"] == "user-feedback"
        assert "500" in row["prompt"]
        assert "700" in row["response"]
        assert row["error"] == "现金流足"
