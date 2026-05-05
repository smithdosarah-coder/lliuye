# -*- coding: utf-8 -*-
"""Tests for POST /api/riskctrl/dsl_gen (SSE form · V2 fix codex critical 3).

V1 (worker-A4 SSE 化前): JSON response · monkeypatch llm.LLMClient
V2 (current · post Phase A SSE migration): SSE event-stream · monkeypatch
    shared.llm_caller.make_json_caller (因为 api.py 已迁 LLMCaller)

Coverage:
  - mock=true → 预设 RuleSet · 不调 LLM (SSE done event 含 ruleset)
  - LLM 真接路径 (monkeypatch shared.llm_caller.make_json_caller)
  - sample_csv_path 字段 hint 注入 prompt
  - LLM 返非 dict (list / 空) · normalize 兜底
  - LLM 解析后 0 rules → SSE error event (code=DSL_EMPTY_RULES)

不依赖 .env / DEEPSEEK_API_KEY · LLM 路径靠 monkeypatch.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent_riskctrl.tests._sse_helper import (
    assert_sse_done,
    assert_sse_error,
    find_stages,
    get_panel,
)


@pytest.fixture(scope="module")
def client():
    from agent_riskctrl.api import app
    return TestClient(app)


# ----------------------------------------------------------------------------
# mock=true · 不调 LLM · 直接返 fixture RuleSet
# ----------------------------------------------------------------------------


def test_dsl_gen_mock_returns_fixture(client):
    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "拒绝高负债企业 · 新成立的转人工",
            "mock": True,
        },
    )
    done = assert_sse_done(resp, msg="mock dsl_gen")
    assert done.get("source") == "mock"
    rs = get_panel(done, "ruleset")
    assert rs is not None
    assert len(rs["rules"]) == 2
    assert rs["rules"][0]["rule_id"] == "R001"
    assert rs["rules"][0]["conditions"][0]["field"] == "debt_ratio"
    assert rs["rules"][0]["action"] == "reject"
    assert rs["rules"][1]["action"] == "manual_review"


# ----------------------------------------------------------------------------
# LLM 真接 · monkeypatch shared.llm_caller.make_json_caller
# (Phase A worker-A4 后 · api.py 用 LLMCaller · 不再直接调 llm.LLMClient)
# ----------------------------------------------------------------------------


def _patch_json_caller(monkeypatch, fake_response_or_fn):
    """Monkeypatch make_json_caller to return a fake closure.

    fake_response_or_fn: dict | list | None (静态返) OR
                        callable(system, user, schema_hint="") → 同
    """
    def make_fake_caller(**kwargs):
        def fn(system, user, schema_hint=""):
            if callable(fake_response_or_fn):
                return fake_response_or_fn(system, user, schema_hint)
            return fake_response_or_fn
        return fn

    # patch source module · agent_riskctrl.api 在 generator 内 import (lazy)
    import shared.llm_caller as llm_caller_mod
    monkeypatch.setattr(
        llm_caller_mod, "make_json_caller", make_fake_caller,
    )


def test_dsl_gen_llm_path_with_monkeypatch(client, monkeypatch):
    """模拟 make_json_caller 返合法 RuleSet JSON · 验 endpoint 解析."""
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
    _patch_json_caller(monkeypatch, fake_llm_response)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "近 3 月查询次数过多直接拒绝",
            "mock": False,
        },
    )
    done = assert_sse_done(resp, msg="dsl_gen llm path")
    assert done.get("source") == "llm"
    rs = get_panel(done, "ruleset")
    assert len(rs["rules"]) == 1
    assert rs["rules"][0]["rule_id"] == "R010"
    assert rs["rules"][0]["conditions"][0]["field"] == "query_times_3m"


def test_dsl_gen_csv_columns_injected(client, monkeypatch, tmp_path):
    """csv 字段被注入 prompt + 返回 csv_columns · 让 LLM rule field 对齐."""
    import pandas as pd

    csv = tmp_path / "tiny.csv"
    pd.DataFrame([
        {"debt_ratio": 0.5, "company_age_years": 3.0, "days_past_due": 0},
        {"debt_ratio": 0.9, "company_age_years": 0.5, "days_past_due": 45},
    ]).to_csv(csv, index=False, encoding="utf-8")

    captured: dict = {}

    def fake_caller(system, user, schema_hint=""):
        captured["user"] = user
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

    _patch_json_caller(monkeypatch, fake_caller)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "高负债拒",
            "sample_csv_path": str(csv),
            "mock": False,
        },
    )
    done = assert_sse_done(resp, msg="csv injection")
    assert get_panel(done, "csv_columns") == [
        "debt_ratio", "company_age_years", "days_past_due",
    ]
    # prompt 应含 csv 字段 hint
    assert "debt_ratio" in captured["user"]
    assert (
        "前 3 行示例" in captured["user"]
        or "company_age_years" in captured["user"]
    )


def test_dsl_gen_llm_returns_list_normalised(client, monkeypatch):
    """make_json_caller 直返 rules 列表 (非 dict 包裹) · 端点应正常 normalize."""
    rules_list = [
        {
            "rule_id": "R001",
            "name": "x",
            "conditions": [{"field": "debt_ratio", "operator": ">", "value": 0.5}],
            "action": "reject",
            "priority": 1,
        }
    ]
    _patch_json_caller(monkeypatch, rules_list)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "demo", "mock": False},
    )
    done = assert_sse_done(resp, msg="list normalize")
    rs = get_panel(done, "ruleset")
    assert len(rs["rules"]) == 1


def test_dsl_gen_no_rules_returns_error_event(client, monkeypatch):
    """LLM 返空 rules → SSE error event (code=DSL_EMPTY_RULES)."""
    _patch_json_caller(monkeypatch, {"rules": []})

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "无意义", "mock": False},
    )
    err = assert_sse_error(resp, expected_code="DSL_EMPTY_RULES")
    assert "未能解析" in err.get("message", "")


# ----------------------------------------------------------------------------
# Stage events · sanity (SSE 必有 parse_intent / build_prompt / call_llm)
# ----------------------------------------------------------------------------


def test_dsl_gen_emits_stage_events(client):
    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "demo",
            "mock": True,
        },
    )
    stages = find_stages(resp.text)
    stage_names = {s.get("stage") for s in stages}
    # mock 路径必发 parse_intent · build_prompt skipped
    assert "parse_intent" in stage_names


# /api/riskctrl/run placeholder route deleted (batch 4 cleanup · web 0 callers).
