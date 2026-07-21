# -*- coding: utf-8 -*-
import inspect
import json
from pathlib import Path

import agent_compliance.agent as agent_module
from agent_compliance.agent import ComplianceRadarAgent
from agent_compliance.knowledge_base import ComplianceKnowledgeBase


def _rule_ids(ledger) -> set[str]:
    return {
        violation.rule.rule_id
        for violation in ledger.severe + ledger.normal + ledger.observation
    }


def test_demo_and_live_same_input_have_same_violation_rule_ids(monkeypatch):
    monkeypatch.setattr(agent_module, "export_ledger_excel", lambda *args, **kwargs: "ledger.xlsx")
    monkeypatch.setattr(agent_module, "export_remediation_word", lambda *args, **kwargs: "report.docx")

    demo_agent = ComplianceRadarAgent()
    list(demo_agent._run_scenario("internet_loan"))
    demo_ids = _rule_ids(demo_agent.last_ledger)

    scenario_kb = ComplianceKnowledgeBase.from_scenario("internet_loan")
    monkeypatch.setattr(
        ComplianceKnowledgeBase,
        "from_uploads",
        staticmethod(lambda **_kwargs: scenario_kb),
    )
    live_agent = ComplianceRadarAgent()
    list(live_agent._run_custom(["policy.md", "business.xlsx"]))

    assert demo_ids, "真实规则引擎未检出违规，演示明细会空屏"
    assert demo_ids == _rule_ids(live_agent.last_ledger)
    assert all(
        violation.rule.source_doc != "scenario.json"
        for violation in (
            demo_agent.last_ledger.severe
            + demo_agent.last_ledger.normal
            + demo_agent.last_ledger.observation
        )
    )


def test_source_does_not_clear_real_findings():
    source = inspect.getsource(ComplianceRadarAgent)
    assert "ledger.normal.clear()" not in source


def test_scenario_asset_has_no_planted_conclusions():
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "demo_data" / "agent_compliance" / "scenarios" / "internet_loan" / "scenario.json"
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    assert "planted_violations" not in scenario
