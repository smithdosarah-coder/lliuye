# -*- coding: utf-8 -*-
"""Tests for POST /api/riskctrl/dsl_gen (v4.0 JSON · LLM 真接 · Stage C onboarding W-C2-A2).

Coverage:
  - mock=true → 预设 RuleSet · 不调 LLM · curl-friendly
  - LLM 真接路径 (monkeypatch llm.LLMClient.chat_json) · 验 endpoint 流程通
  - sample_csv_path 可选 · 字段 hint 注入 prompt
  - LLM 返非 dict (list / 空) · normalize 兜底
  - LLM 解析后 0 rules → 400

不依赖 .env / DEEPSEEK_API_KEY · LLM 真接路径靠 monkeypatch.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


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
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "mock"
    rs = data["ruleset"]
    assert len(rs["rules"]) == 2
    assert rs["rules"][0]["rule_id"] == "R001"
    assert rs["rules"][0]["conditions"][0]["field"] == "debt_ratio"
    assert rs["rules"][0]["action"] == "reject"
    assert rs["rules"][1]["action"] == "manual_review"


# ----------------------------------------------------------------------------
# LLM 真接 · monkeypatch chat_json 注 fake response
# ----------------------------------------------------------------------------


def test_dsl_gen_llm_path_with_monkeypatch(client, monkeypatch):
    """模拟 LLMClient.chat_json 返合法 RuleSet JSON · 验 endpoint 解析 + 返回."""
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

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "近 3 月查询次数过多直接拒绝",
            "mock": False,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "llm"
    assert len(data["ruleset"]["rules"]) == 1
    assert data["ruleset"]["rules"][0]["rule_id"] == "R010"
    assert data["ruleset"]["rules"][0]["conditions"][0]["field"] == "query_times_3m"


# ----------------------------------------------------------------------------
# sample_csv_path · LLM prompt 字段 hint 注入
# ----------------------------------------------------------------------------


def test_dsl_gen_csv_columns_injected(client, monkeypatch, tmp_path):
    """csv 字段被注入 prompt + 返回 csv_columns · 让 LLM rule field 对齐."""
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

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={
            "strategy_intent": "高负债拒",
            "sample_csv_path": str(csv),
            "mock": False,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["csv_columns"] == ["debt_ratio", "company_age_years", "days_past_due"]
    # prompt 应含 csv 字段 hint
    assert "debt_ratio" in captured["user_content"]
    assert "前 3 行示例" in captured["user_content"] or "company_age_years" in captured["user_content"]


# ----------------------------------------------------------------------------
# LLM 返 list / 空结果 → 兜底 + 400
# ----------------------------------------------------------------------------


def test_dsl_gen_llm_returns_list_normalised(client, monkeypatch):
    """chat_json 直返 rules 列表 (非 dict 包裹) · 端点应正常 normalize."""
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

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "demo", "mock": False},
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["ruleset"]["rules"]) == 1


def test_dsl_gen_no_rules_returns_400(client, monkeypatch):
    """LLM 返空 rules → endpoint 400."""

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def chat_json(self, *a, **kw):
            return {"rules": []}

    import llm as llm_module
    monkeypatch.setattr(llm_module, "LLMClient", FakeLLM)

    resp = client.post(
        "/api/riskctrl/dsl_gen",
        json={"strategy_intent": "无意义", "mock": False},
    )
    assert resp.status_code == 400


# ----------------------------------------------------------------------------
# /api/riskctrl/run · placeholder
# ----------------------------------------------------------------------------


def test_run_placeholder(client):
    """run endpoint 接 ruleset · 返 confirmation · 不真上线."""
    ruleset = {
        "rules": [
            {
                "rule_id": "R001",
                "name": "demo",
                "conditions": [{"field": "debt_ratio", "operator": ">", "value": 0.8}],
                "action": "reject",
                "priority": 1,
            }
        ],
        "description": "test",
    }
    resp = client.post(
        "/api/riskctrl/run",
        json={"ruleset": ruleset, "note": "本批 demo"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "queued"
    assert data["ruleset_id"].startswith("rs_")
    assert data["rules_count"] == 1
    assert "placeholder" in data["message"]


def test_run_invalid_ruleset(client):
    """非法 ruleset → 400."""
    resp = client.post(
        "/api/riskctrl/run",
        json={"ruleset": {"rules": "not a list"}, "note": ""},
    )
    assert resp.status_code == 400
