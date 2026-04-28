# -*- coding: utf-8 -*-
"""Pytest for run_policy_scan_and_persist · 4 阶段 + 持久化 · 全 mock LLM."""
from __future__ import annotations

import json

import pytest

from agent_compliance import scan_engine


@pytest.fixture
def isolated_compli_dir(tmp_path, monkeypatch):
    compli_dir = tmp_path / "compliance"
    sessions_dir = compli_dir / "sessions"
    monkeypatch.setattr(scan_engine, "COMPLI_DATA_DIR", compli_dir)
    monkeypatch.setattr(scan_engine, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(scan_engine, "LATEST_POINTER", compli_dir / "latest.json")
    return compli_dir


@pytest.fixture
def fake_llm_json():
    """Mock chat_json caller · 按 system prompt 不同返不同结果."""
    def caller(system, user, schema_hint=""):
        if "抽取条款规则" in system:
            return [
                {
                    "rule_id": "POL-001",
                    "article": "第六条",
                    "category": "期限",
                    "condition": "个人消费贷款期限不得超过 12 个月",
                    "threshold": {"max_months": 12},
                    "severity_hint": "critical",
                },
                {
                    "rule_id": "POL-002",
                    "article": "第三条",
                    "category": "出资比例",
                    "condition": "联合贷款本行出资比例不得低于 30%",
                    "threshold": {"min_bank_share_ratio": 0.30},
                    "severity_hint": "critical",
                },
            ]
        if "事件抽取专家" in system:
            return [
                {"event_id": "LN001", "event_type": "loan",
                 "fields": {"months": 18, "amount": 100000, "purpose": "消费"}},
                {"event_id": "COOP001", "event_type": "cooperation",
                 "fields": {"bank_share": 0.15, "amount": 5000000}},
            ]
        if "合规判定专家" in system:
            return {"status": "violate", "severity": "critical",
                    "evidence": "fake evidence", "match_reason": "fake reason"}
        if "合规修订专家" in system:
            return [
                {"category": "改", "title": "缩短期限", "text": "把期限改到 12 个月以内"},
                {"category": "强", "title": "出资比例", "text": "强化出资比例审查"},
            ]
        return None
    return caller


def test_run_policy_scan_end_to_end(isolated_compli_dir, fake_llm_json, monkeypatch):
    """完整 4 阶段 run_policy_scan_and_persist · 验事件流 + 持久化."""
    monkeypatch.setattr(scan_engine, "build_llm_json_caller", lambda: fake_llm_json)

    events = []
    scan_id = ""
    gen = scan_engine.run_policy_scan_and_persist(
        policy_doc="第六条 个人消费贷款期限不得超过 12 个月。\n第三条 联合贷款本行出资比例不得低于 30%。",
        business_docs=[
            {"event_id": "LN001", "event_type": "loan",
             "fields": {"months": 18, "amount": 100000, "purpose": "消费"}},
        ],
        force_mock=True,
    )
    try:
        while True:
            events.append(next(gen))
    except StopIteration as stop:
        scan_id = stop.value or ""

    types = [e.get("type") for e in events if isinstance(e, dict)]
    stages = [e.get("stage") for e in events if isinstance(e, dict)]

    assert "tool_result" in types
    assert "stage" in types
    assert "scan" in types
    # 4 阶段必出现
    for phase in ("rule_extract", "event_extract", "matrix_match", "revision_generate"):
        assert phase in stages, f"missing stage {phase} in {stages}"

    # scan_id 落盘
    scan_evt = next(e for e in events if e.get("type") == "scan")
    sid = scan_evt["scan_id"]
    assert sid == scan_id

    out_path = isolated_compli_dir / "sessions" / f"{sid}.json"
    assert out_path.is_file()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["scan_id"] == sid
    assert payload["mode"] == "demo_forced"
    assert payload["rule_count"] == 2
    assert payload["event_count"] == 1
    # 至少一条违规 (LN001 期限 18 月 > 12)
    assert payload["stats"]["violation_count"] >= 1
    # 修订建议 attached
    for v in payload["violations"]:
        assert "revisions" in v
        assert isinstance(v["revisions"], list)


def test_run_policy_scan_persists_latest(isolated_compli_dir, fake_llm_json, monkeypatch):
    monkeypatch.setattr(scan_engine, "build_llm_json_caller", lambda: fake_llm_json)
    events = []
    gen = scan_engine.run_policy_scan_and_persist(
        policy_doc="第六条 ...",
        business_docs=[],
        force_mock=True,
    )
    try:
        while True:
            events.append(next(gen))
    except StopIteration:
        pass

    # latest pointer 写好
    latest = isolated_compli_dir / "latest.json"
    assert latest.is_file()
    pointer = json.loads(latest.read_text(encoding="utf-8"))
    assert pointer["scan_id"]


def test_extract_rules_heuristic_fallback_when_no_llm():
    """LLM 不可用时 走「第 X 条」正则启发式."""
    text = (
        "第一条 商业银行应当遵守监管规定。\n"
        "第二条 个人消费贷款期限不得超过 12 个月。\n"
        "第三条 联合贷款出资比例不低于 30%。"
    )
    rules = scan_engine.extract_rules_from_policy_text(text, llm_json_caller=None)
    # 启发式应能切出 ≥2 条
    assert len(rules) >= 2
    rule_ids = {r["rule_id"] for r in rules}
    assert any(rid.startswith("POL-") for rid in rule_ids)
    # 都有 article + condition
    for r in rules:
        assert r["article"].startswith("第")
        assert r["condition"]


def test_extract_rules_empty_text():
    assert scan_engine.extract_rules_from_policy_text("") == []
    assert scan_engine.extract_rules_from_policy_text("   ", llm_json_caller=None) == []
