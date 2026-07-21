# -*- coding: utf-8 -*-
import json
from dataclasses import asdict
from pathlib import Path

import agent_credit.agent as agent_module
from agent_credit.agent import CreditDecisionAgent, _profile_from_report_json
from agent_credit.decision_engine import DecisionEngine
from agent_credit.decision_graph import _build_decision_node


MISSING_AMOUNT_NOTICE = "申请额度未提供，以下仅为风险评估"


def _report_without_amount_or_employee() -> dict:
    return {
        "client_name": "缺值测试企业",
        "facts": {
            "industry": "C34-通用设备制造业",
            "revenue_latest": "12000 万元",
            "profit_latest": "600 万元",
        },
        "sections": {"ch1": "企业基本情况未载员工人数", "ch2": "", "ch3": "", "ch4": ""},
    }


def test_missing_amount_has_notice_and_no_amount_calculation_numbers():
    profile = _profile_from_report_json(_report_without_amount_or_employee())
    assert profile["request"]["amount"] is None

    result = DecisionEngine().run(profile, "corporate")
    assert "request.amount" not in result.features
    assert "financial.request_to_netasset" not in result.features
    assert "operational.cashflow_coverage" not in result.features
    assert "guarantee.coverage_ratio" not in result.features
    assert result.scoring_result.amount_methods == {}
    assert result.advice.decision_reason == MISSING_AMOUNT_NOTICE

    report = CreditDecisionAgent()._build_report_md(result.advice, "corporate", result)
    assert "300" not in report
    assert "额度测算" not in report
    assert "三法测算" not in report
    assert "建议额度：" not in result.advice.approval_section_text
    assert MISSING_AMOUNT_NOTICE in report


def test_missing_amount_memory_quartet_has_no_zero_amount_leak(monkeypatch):
    result = DecisionEngine().run(
        _profile_from_report_json(_report_without_amount_or_employee()), "corporate"
    )
    advice = result.advice
    structured = advice.to_agent6_writeback()["structured_fields"]
    decision_node = asdict(_build_decision_node(advice, result.rule_hits))
    captured = {}

    def _capture_writeback(**kwargs):
        captured.update(kwargs["decision_meta"])
        return "memory://writeback"

    monkeypatch.setattr(agent_module, "apply_decision_writeback", _capture_writeback)
    CreditDecisionAgent().writeback_to_agent6(advice, "memory://report")

    quartet = (
        structured["amount_provided"],
        structured.get("approved_amount"),
        decision_node["payload"].get("approved_amount"),
        captured["额度"],
    )
    assert quartet == (False, None, None, "额度未提供·仅风险评估")
    assert decision_node["payload"]["amount_provided"] is False
    assert "approved_amount" in decision_node["payload"]
    assert decision_node["payload"]["approved_amount"] is None
    assert "0 万元" not in json.dumps(quartet, ensure_ascii=False)
    decision_summary = advice.decision_graph["decision_summary"]
    assert decision_summary["amount_provided"] is False
    assert "approved_amount" in decision_summary
    assert decision_summary["approved_amount"] is None
    assert not isinstance(decision_summary.get("approved_amount"), (int, float))


def test_missing_employee_count_is_not_scored_as_zero():
    profile = _profile_from_report_json(_report_without_amount_or_employee())
    assert profile["employee_count"] is None

    result = DecisionEngine().run(profile, "corporate")
    assert result.features["operational.employee_count"] is None
    assert "员工规模" not in result.scoring_result.sub_details["operational"]


def test_dingsheng_full_input_keeps_pre_fix_composite_score():
    path = Path("demo_data/agent_credit/corp_dingsheng_trade.json")
    profile = json.loads(path.read_text(encoding="utf-8"))
    result = DecisionEngine().run(profile, "corporate")

    # CP1-R3 CC 裁决：68 为错误锚点；逐维零漂移归因确认正确基线是 44。
    assert result.scoring_result.composite_score == 44
    assert result.scoring_result.operational_score == 52
    assert result.scoring_result.guarantee_score == 38
    assert result.features["request.amount"] == 500
    assert len(result.scoring_result.amount_methods) == 4
