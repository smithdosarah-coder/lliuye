# -*- coding: utf-8 -*-
"""Pytest for matrix_check · 硬规则 + LLM slow path · 改/补/强 修订生成."""
from __future__ import annotations

import pytest

from agent_compliance import scan_engine
from agent_compliance.scan_engine import (
    REVISION_CATEGORIES,
    extract_events_from_business_docs,
    generate_revisions,
    matrix_check,
)


# ---------------------------------------------------------------------------
# 硬规则 fast path
# ---------------------------------------------------------------------------


def test_matrix_hard_rule_violate():
    """期限 18 > 12 → violate · 不需 LLM."""
    rules = [{
        "rule_id": "POL-001",
        "article": "第六条",
        "category": "期限",
        "condition": "期限不超 12 月",
        "threshold": {"max_months": 12},
        "severity_hint": "critical",
    }]
    events = [{
        "event_id": "LN001",
        "event_type": "loan",
        "fields": {"months": 18, "purpose": "消费"},
    }]
    result = matrix_check(rules, events, llm_json_caller=None)
    assert result["rule_count"] == 1
    assert result["event_count"] == 1
    assert result["cell_count"] == 1
    assert len(result["violations"]) == 1
    v = result["violations"][0]
    assert v["rule_id"] == "POL-001"
    assert v["event_id"] == "LN001"
    assert v["severity"] == "critical"
    assert "18" in v["evidence"]


def test_matrix_hard_rule_comply():
    """期限 6 < 12 → comply · 不进 violations."""
    rules = [{
        "rule_id": "POL-001",
        "article": "第六条",
        "category": "期限",
        "condition": "期限不超 12 月",
        "threshold": {"max_months": 12},
        "severity_hint": "critical",
    }]
    events = [{"event_id": "LN001", "event_type": "loan", "fields": {"months": 6}}]
    result = matrix_check(rules, events, llm_json_caller=None)
    assert len(result["violations"]) == 0


def test_matrix_no_threshold_no_llm_falls_to_na():
    """无 threshold + 无 LLM → not_applicable · 不进 violations."""
    rules = [{
        "rule_id": "POL-X",
        "article": "第七条",
        "category": "其他",
        "condition": "应当遵守监管规定",
        "threshold": {},
        "severity_hint": "minor",
    }]
    events = [{"event_id": "EVT-1", "event_type": "loan", "fields": {"a": 1}}]
    result = matrix_check(rules, events, llm_json_caller=None)
    assert len(result["violations"]) == 0
    assert result["matrix"][0][0] == "not_applicable"


def test_matrix_llm_slow_path():
    """无硬 threshold · LLM 判 violate · 进 violations."""
    rules = [{
        "rule_id": "POL-Y",
        "article": "第八条",
        "category": "披露",
        "condition": "应当披露关键风险",
        "threshold": {},
        "severity_hint": "major",
    }]
    events = [{"event_id": "EVT-2", "event_type": "loan", "fields": {"disclosure": "缺失"}}]

    def fake_llm(system, user, schema_hint=""):
        return {"status": "violate", "severity": "major",
                "evidence": "缺失披露", "match_reason": "披露字段为空"}

    result = matrix_check(rules, events, llm_json_caller=fake_llm)
    assert len(result["violations"]) == 1
    v = result["violations"][0]
    assert v["severity"] == "major"
    assert "披露" in v["evidence"]


# ---------------------------------------------------------------------------
# extract_events_from_business_docs · dict / str 混合
# ---------------------------------------------------------------------------


def test_extract_events_from_dicts():
    docs = [
        {"event_id": "E1", "event_type": "loan", "fields": {"months": 12}},
        {"id": "E2", "type": "cooperation", "amount": 1000},  # 旧 key 兼容 + 顶层字段
    ]
    events = extract_events_from_business_docs(docs)
    assert events[0]["event_id"] == "E1"
    assert events[0]["event_type"] == "loan"
    assert events[1]["event_id"] == "E2"
    assert events[1]["event_type"] == "cooperation"
    assert events[1]["fields"]["amount"] == 1000


def test_extract_events_from_text_no_llm():
    """无 LLM · text 走 fallback · 整段作为单事件."""
    docs = ["放款记录 LN001 期限 18 月"]
    events = extract_events_from_business_docs(docs, llm_json_caller=None)
    assert len(events) == 1
    assert events[0]["event_type"] == "text_fragment"
    assert "LN001" in events[0]["fields"]["raw"]


# ---------------------------------------------------------------------------
# generate_revisions · 改/补/强 三类
# ---------------------------------------------------------------------------


def test_generate_revisions_with_llm():
    """LLM 返 改 + 强 → 都收下."""
    violation = {
        "violation_id": "VIO-001",
        "rule_id": "POL-001",
        "rule_article": "第六条",
        "rule_condition": "期限 ≤ 12 月",
        "event_id": "LN001",
        "event_type": "loan",
        "severity": "critical",
        "match_reason": "期限 18 > 12",
    }

    def fake_llm(system, user, schema_hint=""):
        return [
            {"category": "改", "title": "缩短期限", "text": "把期限改到 12 个月以内"},
            {"category": "强", "title": "审查机制", "text": "强化期限审查"},
            {"category": "无效类", "title": "x", "text": "y"},  # 测过滤
        ]

    revisions = generate_revisions(violation, llm_json_caller=fake_llm)
    cats = {r["category"] for r in revisions}
    assert cats == {"改", "强"}  # 无效类被过滤
    assert all(r["title"] for r in revisions)


def test_generate_revisions_template_fallback_no_llm():
    """无 LLM → 模板兜底 给一条「改」类建议."""
    violation = {
        "violation_id": "VIO-002",
        "rule_id": "POL-002",
        "rule_article": "第三条",
        "event_id": "COOP001",
        "severity": "critical",
    }
    revisions = generate_revisions(violation, llm_json_caller=None)
    assert len(revisions) == 1
    assert revisions[0]["category"] == "改"
    assert "VIO-002" in revisions[0]["text"] or "COOP001" in revisions[0]["text"]


def test_generate_revisions_template_fallback_when_llm_returns_invalid():
    """LLM 返非合规结构 → 模板兜底."""
    violation = {"violation_id": "VIO-003", "rule_article": "x", "severity": "minor"}

    def fake_llm(system, user, schema_hint=""):
        return "not a list"  # invalid

    revisions = generate_revisions(violation, llm_json_caller=fake_llm)
    # 模板兜底
    assert len(revisions) == 1
    assert revisions[0]["category"] == "改"


def test_revision_categories_constant():
    assert REVISION_CATEGORIES == ("改", "补", "强")
