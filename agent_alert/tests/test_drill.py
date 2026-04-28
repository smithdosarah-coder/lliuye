# -*- coding: utf-8 -*-
"""Pytest for agent_alert.scan_engine · drill detail + LLM disposition + template fallback."""
from __future__ import annotations

import pytest

from agent_alert.scan_engine import (
    ClientNotFoundError,
    _template_disposition,
    build_drill_payload,
    find_hit_by_client_id,
)


@pytest.fixture
def fake_payload():
    """模拟 load_hitlist 返回的 payload (3 家客户)."""
    return {
        "session_id": "test-sid",
        "generated_at": "2026-04-28T12:00:00",
        "scenario_key": "test",
        "mode": "demo_forced",
        "hit_list": {
            "list_id": "lst-1",
            "agent_name": "alert",
            "red_count": 1, "yellow_count": 1, "green_count": 1,
            "total_scanned": 3, "total_hit": 3,
            "hits": [
                {
                    "hit_id": "LC10001",
                    "level": "red",
                    "score": 90.0,
                    "target": {"target_id": "LC10001", "target_type": "loan_customer",
                               "payload": {"company_name": "华联精密制造有限公司"}},
                    "matched_rules": ["FIN-002", "LAW-001"],
                    "reasons": ["[外部 × FIN-002] 净利润转负", "[外部 × LAW-001] 涉诉 1200 万"],
                    "evidences": [
                        {"source": "财报", "snippet": "2025Q4 亏损 680 万", "url": ""},
                        {"source": "裁判文书网", "snippet": "(2025)沪0115民初12345号",
                         "url": "https://example.com/1"},
                    ],
                },
                {
                    "hit_id": "LC10002",
                    "level": "yellow",
                    "score": 60.0,
                    "target": {"target_id": "LC10002", "target_type": "loan_customer",
                               "payload": {"company_name": "盛达汽配有限公司"}},
                    "matched_rules": ["FIN-003"],
                    "reasons": ["[外部 × FIN-003] 应收账款周转 78 天"],
                    "evidences": [
                        {"source": "财报", "snippet": "应收周转恶化", "url": ""},
                    ],
                },
                {
                    "hit_id": "LC10003",
                    "level": "green",
                    "score": 20.0,
                    "target": {"target_id": "LC10003", "target_type": "loan_customer",
                               "payload": {"company_name": "顺通物流有限公司"}},
                    "matched_rules": [],
                    "reasons": [],
                    "evidences": [],
                },
            ],
        },
        "dispositions": {
            "华联精密制造有限公司": {
                "company_name": "华联精密制造有限公司",
                "actions": [{"action_type": "现场核查", "urgency": "立即",
                             "description": "saved", "responsible": "客户经理"}],
                "follow_up_date": "",
                "notes": "saved disposition",
            },
        },
    }


# ---------------------------------------------------------------------------
# Test 1: find_hit_by_client_id 三种匹配规则
# ---------------------------------------------------------------------------


def test_find_by_hit_id(fake_payload):
    h = find_hit_by_client_id(fake_payload, "LC10001")
    assert h["target"]["payload"]["company_name"] == "华联精密制造有限公司"


def test_find_by_company_name(fake_payload):
    h = find_hit_by_client_id(fake_payload, "盛达汽配有限公司")
    assert h["hit_id"] == "LC10002"


def test_find_unknown_raises(fake_payload):
    with pytest.raises(ClientNotFoundError):
        find_hit_by_client_id(fake_payload, "no-such-client")


# ---------------------------------------------------------------------------
# Test 2: build_drill_payload 三个分支 (saved / llm / template)
# ---------------------------------------------------------------------------


def test_drill_uses_saved_disposition(fake_payload):
    """华联红灯有 saved disposition · 直接用 saved · disposition_source=saved."""
    drill = build_drill_payload(fake_payload, "LC10001")
    assert drill["client_id"] == "LC10001"
    assert drill["company_name"] == "华联精密制造有限公司"
    assert drill["level"] == "red"
    assert drill["disposition_source"] == "saved"
    assert drill["disposition"]["notes"] == "saved disposition"
    # signal_timeline 来自 evidences
    assert len(drill["signal_timeline"]) == 2
    assert drill["signal_timeline"][1]["source"] == "裁判文书网"


def test_drill_uses_llm_when_no_saved(fake_payload):
    """盛达黄灯无 saved · 传 llm_caller · disposition_source=llm."""
    captured = {}

    def fake_llm(system, user):
        captured["system"] = system
        captured["user"] = user
        return "建议一周内财务跟踪 + 持续舆情监控 · 责任客户经理"

    drill = build_drill_payload(fake_payload, "LC10002", llm_caller=fake_llm)
    assert drill["disposition_source"] == "llm"
    assert drill["disposition"]["narrative"].startswith("建议一周内")
    assert "盛达汽配有限公司" in captured["user"]
    assert "yellow" in captured["user"]


def test_drill_falls_back_to_template_when_llm_raises(fake_payload):
    """LLM 抛错 → 模板兜底 · disposition_source=template."""
    def broken_llm(system, user):
        raise RuntimeError("LLM down")

    drill = build_drill_payload(fake_payload, "LC10002", llm_caller=broken_llm)
    assert drill["disposition_source"] == "template"
    actions = drill["disposition"]["actions"]
    assert len(actions) >= 1
    assert any(a["urgency"] in {"立即", "一周内", "持续关注"} for a in actions)


def test_drill_template_no_llm(fake_payload):
    """无 saved · 不传 llm_caller · 直接走模板 · disposition_source=template."""
    # 把盛达的 saved 删掉模拟 nothing
    drill = build_drill_payload(fake_payload, "LC10002", llm_caller=None)
    assert drill["disposition_source"] == "template"


# ---------------------------------------------------------------------------
# Test 3: 模板按 level 分支
# ---------------------------------------------------------------------------


def test_template_red_actions():
    plan = _template_disposition({"level": "red", "target": {"payload": {"company_name": "A"}}})
    urgencies = {a["urgency"] for a in plan["actions"]}
    assert "立即" in urgencies
    assert plan["company_name"] == "A"


def test_template_yellow_actions():
    plan = _template_disposition({"level": "yellow", "target": {"payload": {"company_name": "B"}}})
    urgencies = {a["urgency"] for a in plan["actions"]}
    assert urgencies & {"一周内", "持续关注"}


def test_template_green_actions():
    plan = _template_disposition({"level": "green", "target": {"payload": {"company_name": "C"}}})
    assert all(a["urgency"] == "持续关注" for a in plan["actions"])


def test_template_unknown_level_falls_to_green():
    plan = _template_disposition({"level": "", "target": {"payload": {"company_name": "X"}}})
    assert plan["actions"][0]["urgency"] == "持续关注"
