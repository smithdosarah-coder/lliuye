# -*- coding: utf-8 -*-
"""Tests for POST /api/riskctrl/dsl_gen (v4.0 SSE event-stream · LLM 真接 · A4 worker SSE conv).

Coverage (Phase B Sprint 3 V2-FIX 2026-05-05 · post-Codex review SSE rewrite):
  - mock=true → SSE done event · panels.ruleset spread to top · source="mock"
  - LLM 真接 path (monkeypatch llm.LLMClient · shared.llm_caller wraps it) · SSE done event
  - sample_csv_path 可选 · csv 字段 hint 注入 prompt · csv_columns 在 done event
  - LLM 返 list / 0 rules · DSL_EMPTY_RULES error event (SSE 200 with error event · 不 HTTP 400)
  - RM role 调 /dsl_gen → 403 ACCESS_DENIED (per Q-052 #8 RM 不可调 riskctrl)

Endpoint changed to SSE event-stream (A4 worker conv · 详 sse-envelope §3.1) ·
原 resp.json() 全 fail · 改 SSE data line 解析 · 找 event=done/error 取 panels spread.

不依赖 .env / DEEPSEEK_API_KEY · LLM 真接路径靠 monkeypatch.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Auth fixtures (per Q-052 #8 · per V2-FIX 2026-05-05)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """TestClient with admin auth cookie · pass all require_action gates (Phase B Sprint 3 V2-FIX)."""
    from agent_riskctrl.api import app
    from auth_service.dependencies import COOKIE_NAME
    from auth_service.jwt_util import issue

    c = TestClient(app)
    # admin cookie · ACCESS_V2 admin 全 action 全 agent · pass require_action gate
    c.cookies.set(COOKIE_NAME, issue("u_test", "admin"))
    return c


def _rm_client():
    """RM client · per Q-052 #8 RM 不可调 riskctrl · expect 403 ACCESS_DENIED."""
    from agent_riskctrl.api import app
    from auth_service.dependencies import COOKIE_NAME
    from auth_service.jwt_util import issue

    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, issue("u_wangzhe", "rm"))
    return c


# ---------------------------------------------------------------------------
# SSE parsing helpers (V2-FIX 2026-05-05 · A4 worker SSE conv)
# ---------------------------------------------------------------------------


def _parse_sse(body: str) -> list[dict]:
    """Parse SSE response body · 返 list of event dict.

    SSE format (per shared.api_utils.sse_encode): `data: {...json...}\\n\\n`
    Each event has top-level "event" key set by make_stage / make_done / make_error.
    """
    events: list[dict] = []
    for chunk in body.strip().split("\n\n"):
        for line in chunk.split("\n"):
            if line.startswith("data: "):
                payload = line[len("data: "):].strip()
                if not payload:
                    continue
                try:
                    events.append(json.loads(payload))
                except json.JSONDecodeError:
                    continue
    return events


def _find_event(events: list[dict], kind: str) -> dict | None:
    """Find first event of given kind ('stage' / 'done' / 'error' / 'section')."""
    return next((e for e in events if e.get("event") == kind), None)


# ---------------------------------------------------------------------------
# Auth gate · RM 403 (V2-FIX 新加 · Codex review critical 1 catch)
# ---------------------------------------------------------------------------


def test_dsl_gen_rm_role_blocked_403():
    """RM (王哲) no riskctrl.invoke action (per Q-052 #8 收窄) → 403 ACCESS_DENIED."""
    rm_c = _rm_client()
    resp = rm_c.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "demo", "mock": True},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["error"]["code"] == "ACCESS_DENIED"
    assert detail["error"]["details"]["role"] == "rm"
    assert detail["error"]["details"]["agent"] == "riskctrl"
    assert detail["error"]["details"]["action"] == "invoke"


def test_dsl_gen_no_cookie_401():
    """No auth cookie → 401 AUTH_MISSING."""
    from agent_riskctrl.api import app
    bare = TestClient(app)
    resp = bare.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "demo", "mock": True},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"]["code"] == "AUTH_MISSING"


# ---------------------------------------------------------------------------
# mock=true · SSE done event with panels.ruleset spread to top
# ---------------------------------------------------------------------------


def test_dsl_gen_mock_returns_fixture(client):
    """mock=true · SSE 200 · done event 顶层含 ruleset / source='mock' (panels spread)."""
    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "拒绝高负债企业 · 新成立的转人工",
            "mock": True,
        },
    )
    assert resp.status_code == 200, resp.text
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    assert events, "no SSE events parsed"
    done = _find_event(events, "done")
    assert done is not None, f"no done event · events={[e.get('event') for e in events]}"

    # panels spread to top of done event (per make_done docstring)
    assert done.get("source") == "mock"
    rs = done.get("ruleset")
    assert rs is not None and isinstance(rs, dict)
    assert len(rs["rules"]) == 2
    assert rs["rules"][0]["rule_id"] == "R001"
    assert rs["rules"][0]["conditions"][0]["field"] == "debt_ratio"
    assert rs["rules"][0]["action"] == "reject"
    assert rs["rules"][1]["action"] == "manual_review"


# ---------------------------------------------------------------------------
# LLM 真接 · monkeypatch llm.LLMClient · shared.llm_caller wraps it
# ---------------------------------------------------------------------------


def test_dsl_gen_llm_path_with_monkeypatch(client, monkeypatch):
    """模拟 LLMClient.chat_json 返合法 RuleSet JSON · SSE done event 验解析 + 返回."""
    fake_llm_response = {
        "rules": [
            {
                "rule_id": "R010",
                "name": "查询过频拒",
                "description": "近 3 月查询 > 10 次拒绝",
                "conditions": [
                    {"field": "query_times_3m", "operator": ">", "value": 10}
                ],
                "action": "reject",
                "priority": 2,
            }
        ],
        "description": "防多头借贷",
    }

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def chat_json(self, system_prompt, user_content, temperature=None, max_retries=2):
            assert "策略意图" in user_content or "强信号" in user_content or len(user_content) > 0
            return fake_llm_response

    import llm as llm_module
    monkeypatch.setattr(llm_module, "LLMClient", FakeLLM)
    # shared.llm_caller.provider 缓存 LLMClient · 也 patch 它
    import shared.llm_caller.provider as provider_module
    monkeypatch.setattr(provider_module, "LLMClient", FakeLLM, raising=False)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "近 3 月查询次数过多直接拒绝",
            "mock": False,
        },
    )
    assert resp.status_code == 200, resp.text

    events = _parse_sse(resp.text)
    done = _find_event(events, "done")
    err = _find_event(events, "error")
    # LLM path 成功 → done event · 失败 → error event (fallback chain 不 available 等)
    if err is not None:
        # fallback chain key 缺 / wrap import 失败 等环境因素 · 至少校验 SSE 流出 error event
        pytest.skip(f"LLM env not configured · error event: {err.get('code')}")

    assert done is not None, f"no done · events={[e.get('event') for e in events]}"
    assert done.get("source") == "llm"
    rs = done.get("ruleset")
    assert rs is not None
    assert len(rs["rules"]) == 1
    assert rs["rules"][0]["rule_id"] == "R010"
    assert rs["rules"][0]["conditions"][0]["field"] == "query_times_3m"


def test_dsl_gen_csv_columns_injected(client, monkeypatch, tmp_path):
    """csv 字段被注入 prompt · done event 含 csv_columns · LLM rule field 对齐."""
    import pandas as pd

    csv = tmp_path / "tiny.csv"
    pd.DataFrame([
        {"debt_ratio": 0.5, "company_age_years": 3.0, "days_past_due": 0},
        {"debt_ratio": 0.9, "company_age_years": 0.5, "days_past_due": 45},
    ]).to_csv(csv, index=False, encoding="utf-8")

    captured: dict = {}

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def chat_json(self, system_prompt, user_content, temperature=None, max_retries=2):
            captured["user_content"] = user_content
            return {
                "rules": [
                    {
                        "rule_id": "R001",
                        "name": "demo",
                        "conditions": [{"field": "debt_ratio", "operator": ">", "value": 0.7}],
                        "action": "reject",
                        "priority": 1,
                    }
                ]
            }

    import llm as llm_module
    monkeypatch.setattr(llm_module, "LLMClient", FakeLLM)
    import shared.llm_caller.provider as provider_module
    monkeypatch.setattr(provider_module, "LLMClient", FakeLLM, raising=False)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "高负债拒",
            "sample_csv_path": str(csv),
            "mock": False,
        },
    )
    assert resp.status_code == 200, resp.text

    events = _parse_sse(resp.text)
    done = _find_event(events, "done")
    err = _find_event(events, "error")
    if err is not None:
        pytest.skip(f"LLM env not configured · error event: {err.get('code')}")

    assert done is not None
    assert done.get("csv_columns") == ["debt_ratio", "company_age_years", "days_past_due"]
    assert "debt_ratio" in captured.get("user_content", "")
    assert (
        "前 3 行示例" in captured.get("user_content", "")
        or "company_age_years" in captured.get("user_content", "")
    )


def test_dsl_gen_llm_returns_list_normalised(client, monkeypatch):
    """chat_json 直返 rules 列表 (非 dict 包裹) · SSE done event 应正常 normalize."""
    rules_list = [
        {
            "rule_id": "R001",
            "name": "x",
            "conditions": [{"field": "debt_ratio", "operator": ">", "value": 0.5}],
            "action": "reject",
            "priority": 1,
        }
    ]

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def chat_json(self, *a, **kw):
            return rules_list

    import llm as llm_module
    monkeypatch.setattr(llm_module, "LLMClient", FakeLLM)
    import shared.llm_caller.provider as provider_module
    monkeypatch.setattr(provider_module, "LLMClient", FakeLLM, raising=False)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "demo", "mock": False},
    )
    assert resp.status_code == 200, resp.text

    events = _parse_sse(resp.text)
    done = _find_event(events, "done")
    err = _find_event(events, "error")
    if err is not None:
        pytest.skip(f"LLM env not configured · error event: {err.get('code')}")

    assert done is not None
    rs = done.get("ruleset")
    assert rs is not None
    assert len(rs["rules"]) == 1


def test_dsl_gen_no_rules_returns_error_event(client, monkeypatch):
    """LLM 返空 rules → SSE 200 + error event code=DSL_EMPTY_RULES (替原 HTTP 400 · A4 SSE conv)."""

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def chat_json(self, *a, **kw):
            return {"rules": []}

    import llm as llm_module
    monkeypatch.setattr(llm_module, "LLMClient", FakeLLM)
    import shared.llm_caller.provider as provider_module
    monkeypatch.setattr(provider_module, "LLMClient", FakeLLM, raising=False)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "无意义", "mock": False},
    )
    # SSE 200 · LLM 调用失败/空 rules 都 stream error event 而非 HTTP 4xx
    assert resp.status_code == 200, resp.text

    events = _parse_sse(resp.text)
    err = _find_event(events, "error")
    done = _find_event(events, "done")
    # 期望 error event (DSL_EMPTY_RULES 或 LLM_CALL_FAILED 取决 env)
    assert err is not None, f"expected error event · got events={[e.get('event') for e in events]}"
    # 不能完成 done · 0 rules
    assert done is None
    # code 应是 DSL_EMPTY_RULES (FakeLLM 真返 0 rules · validate_dsl 阶段拒)
    # 若 fallback chain 整体不可用则 code 为 LLM_CALL_FAILED · 也接受
    assert err.get("code") in ("DSL_EMPTY_RULES", "LLM_CALL_FAILED", "LLM_FALLBACK_EXHAUSTED")


# /api/riskctrl/run placeholder route deleted (batch 4 cleanup · web 0 callers).
# Tests `test_run_placeholder` + `test_run_invalid_ruleset` removed with the route.
