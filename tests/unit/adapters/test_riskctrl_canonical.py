# -*- coding: utf-8 -*-
"""Unit tests for riskctrl canonical input mapper (W1 Phase D).

Per codex R3 R3.2 #3 user ack (2026-05-21):

- canonical signature detection (含 ``client_metadata`` layer → canonical 路径)
- backward compat (raw payload 不含 ``client_metadata`` → passthrough 不变)
- CanonicalInput → RiskAssessRequest shape mapping
- 4 layer canonical 全透传 (client_metadata + decision_context + credit_terms + material_facts)
- use_llm passthrough (默认 True · 显式 False 走模板兜底)
- RiskctrlAdapter import + boundary + endpoint 验证
- 旧 DSL endpoint 保留 (RISKCTRL_LEGACY_BACKTEST_ENDPOINT 仍 export)
"""
from __future__ import annotations

import pytest

from liuye_service.adapters.riskctrl import (
    RiskctrlAdapter,
    RISKCTRL_AGENT_ID,
    RISKCTRL_ENDPOINT,
    RISKCTRL_LEGACY_BACKTEST_ENDPOINT,
    _canonical_to_risk_assess_input,
)


class TestRiskctrlAdapterClass:
    """RiskctrlAdapter 类层 · 新业务方向 risk_assess · 旧 backtest 保留."""

    def test_agent_id(self):
        assert RiskctrlAdapter.agent_id == "riskctrl"
        assert RISKCTRL_AGENT_ID == "riskctrl"

    def test_boundary_managed(self):
        # Phase D 保留 managed_readonly
        assert RiskctrlAdapter.boundary == "managed_readonly"

    def test_endpoint_new_risk_assess(self):
        # Phase D · 新业务 risk_assess 主入口
        assert RISKCTRL_ENDPOINT == "/api/riskctrl/risk_assess"

    def test_endpoint_legacy_backtest_preserved(self):
        # 旧 DSL 业务 backtest endpoint 保留 (backward compat)
        assert RISKCTRL_LEGACY_BACKTEST_ENDPOINT == "/api/riskctrl/backtest"

    def test_can_instantiate(self):
        adapter = RiskctrlAdapter()
        assert adapter.agent_id == "riskctrl"
        assert adapter.boundary == "managed_readonly"

    def test_no_longer_raises_on_init(self):
        adapter = RiskctrlAdapter(backend_url="http://test-only:9999")
        assert adapter.backend_url == "http://test-only:9999"


class TestCanonicalToRiskAssessInput:
    """`_canonical_to_risk_assess_input` mapper · backward compat + canonical."""

    def test_backward_compat_raw_payload(self):
        """Raw payload (无 ``client_metadata`` key) → passthrough 不变 (老 DSL 路径不破)."""
        raw = {
            "strategy_intent": "高负债拒绝",
            "sample_csv_path": "/tmp/sample.csv",
            "mock": False,
        }
        result = _canonical_to_risk_assess_input(raw)
        assert result == raw

    def test_canonical_4layer_all_passthrough(self):
        """Canonical 4 layer 全透传 (client_metadata + decision_context + credit_terms + material_facts)."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "鼎盛商贸",
                "CLIENT_USCC": "91310000XXXXXXXXXX",
                "CLIENT_INDUSTRY_FULL": "批发和零售业",
                "CLIENT_INDUSTRY_CODE": "F51",
            },
            "decision_context": {
                "verdict": "conditional",
                "score": 72,
                "score_breakdown": {
                    "financial_health": 75,
                    "repayment_history": 80,
                    "negative_judicial": 70,
                },
                "redlines_triggered": ["corp_rl_005"],
                "cases_referenced": ["case_022"],
                "reasoning": "综合 72 分",
                "confidence": 0.82,
            },
            "credit_terms": {
                "CREDIT_AMOUNT": "5000 万元",
                "GUARANTEE_METHOD": "抵押",
            },
            "material_facts": {
                "BUSINESS_HISTORY_DESC": "8 年深耕",
                "FINANCIAL_CASH_FLOW_DESC": "现金流充足",
            },
        }
        result = _canonical_to_risk_assess_input(canonical)
        # client_metadata 全字段透传
        assert result["client_metadata"]["CLIENT_FULL_NAME"] == "鼎盛商贸"
        assert result["client_metadata"]["CLIENT_INDUSTRY_FULL"] == "批发和零售业"
        # decision_context 7 字段透传 + verdict
        assert result["decision_context"]["verdict"] == "conditional"
        assert result["decision_context"]["score"] == 72
        assert result["decision_context"]["score_breakdown"]["financial_health"] == 75
        assert result["decision_context"]["redlines_triggered"] == ["corp_rl_005"]
        # credit_terms + material_facts 透传
        assert result["credit_terms"]["CREDIT_AMOUNT"] == "5000 万元"
        assert result["material_facts"]["BUSINESS_HISTORY_DESC"] == "8 年深耕"
        # use_llm 默认 True
        assert result["use_llm"] is True

    def test_canonical_use_llm_passthrough_false(self):
        """passthrough.use_llm=False → 走模板兜底 (test 路径)."""
        canonical = {
            "client_metadata": {"CLIENT_FULL_NAME": "测试客户"},
            "use_llm": False,
        }
        result = _canonical_to_risk_assess_input(canonical)
        assert result["use_llm"] is False

    def test_canonical_no_decision_context(self):
        """canonical 不含 decision_context · 仅 client_metadata · OK · risk_assess engine 自适应."""
        canonical = {
            "client_metadata": {"CLIENT_FULL_NAME": "客户 A"},
        }
        result = _canonical_to_risk_assess_input(canonical)
        assert "decision_context" not in result  # None dropped
        assert result["client_metadata"]["CLIENT_FULL_NAME"] == "客户 A"

    def test_canonical_invalid_fallback_raw(self):
        """canonical pydantic validation fail · fallback raw."""
        canonical = {
            "client_metadata": {
                # CLIENT_FULL_NAME 缺 · pydantic raise
                "CLIENT_USCC": "91XXX",
            },
            "use_llm": False,
        }
        result = _canonical_to_risk_assess_input(canonical)
        # raw 透传
        assert result["use_llm"] is False

    def test_non_dict_returns_empty(self):
        assert _canonical_to_risk_assess_input(None) == {}  # type: ignore[arg-type]
        assert _canonical_to_risk_assess_input("not a dict") == {}  # type: ignore[arg-type]
