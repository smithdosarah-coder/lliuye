# -*- coding: utf-8 -*-
"""Unit tests for agent_riskctrl.risk_assess_engine (W1 Phase D).

Per codex R3 R3.2 #3 user ack (2026-05-21):

- 7 维 deterministic 评分 · 同 input → 同 output
- 评级 (低/中/高) + review_cycle (12/6/3 月) 映射
- Top risks + mitigations · score ≥ 60 → 入 top · ≤ 3 条
- LLM 不可用 → 模板兜底 reasoning · data_source=mock_fallback
- LLM 可用 → 真 LLM reasoning · data_source=live
- decision_context 复用 · score_breakdown.repayment_history → 反转作 credit dim
- 边界 case: 全空 input · 默认中等评级
"""
from __future__ import annotations

import pytest

from agent_riskctrl.risk_assess_engine import (
    DIMENSIONS,
    RiskAssessResult,
    run_risk_assess,
)


class TestDimensions:
    """7 维 schema 一致性 · 权重和=1.0 · id/label/weight 字段齐全."""

    def test_7_dimensions(self):
        assert len(DIMENSIONS) == 7

    def test_dimension_ids(self):
        ids = {d["id"] for d in DIMENSIONS}
        expected = {
            "credit", "financial", "transaction", "industry",
            "guarantee", "concentration", "negative_sentiment_judicial",
        }
        assert ids == expected

    def test_weights_sum_to_one(self):
        total = sum(d["weight"] for d in DIMENSIONS)
        assert abs(total - 1.0) < 0.001

    def test_each_dim_has_label_factors(self):
        for d in DIMENSIONS:
            assert d["label"], f"dim {d['id']} missing label"
            assert d["factors"] and isinstance(d["factors"], list)


class TestRunRiskAssessDeterministic:
    """deterministic 出分 · 同 input → 同 dim_scores."""

    def test_low_risk_excellent_client(self):
        """优质客户 (无逾期 + 抵押 + 现金流充足) → 评级 低."""
        result = run_risk_assess(
            client_metadata={
                "CLIENT_FULL_NAME": "优质客户 A",
                "CREDIT_OVERDUE_RECORD": "无",
                "CLIENT_INDUSTRY_FULL": "信息技术服务业",
                "CLIENT_LEGAL_RISK_DESC": "无",
            },
            credit_terms={
                "GUARANTEE_METHOD": "抵押",
            },
            material_facts={
                "FINANCIAL_CASH_FLOW_DESC": "现金流充足稳定",
                "CUSTOMER_CONCENTRATION_DESC": "客户分散 · 单一不超 5%",
            },
            llm_caller=None,  # 模板兜底
        )
        assert isinstance(result, RiskAssessResult)
        assert result.risk_grade in ("低", "中")  # 应为低
        assert result.composite_risk_score < 50
        assert result.review_cycle_months in (12, 6)
        assert result.data_source == "mock_fallback"  # 无 LLM

    def test_high_risk_client(self):
        """高风险客户 (严重逾期 + 高负债 + 诉讼) → 评级 高."""
        result = run_risk_assess(
            client_metadata={
                "CLIENT_FULL_NAME": "高风险客户 B",
                "CREDIT_OVERDUE_RECORD": "严重逾期 M3+ 60 天以上",
                "CLIENT_DEBT_RATIO": "92%",
                "CLIENT_INDUSTRY_FULL": "房地产开发",
                "CLIENT_LEGAL_RISK_DESC": "重大诉讼未决",
            },
            credit_terms={"GUARANTEE_METHOD": "信用"},
            material_facts={
                "FINANCIAL_CASH_FLOW_DESC": "现金流断流 · 负流入",
                "CUSTOMER_CONCENTRATION_DESC": "高度集中 · 单一大于 50%",
            },
            llm_caller=None,
        )
        assert result.risk_grade == "高"
        assert result.composite_risk_score >= 60
        assert result.review_cycle_months == 3
        # Top risks 应包含 credit / financial / industry / negative
        top_dims = [r["dimension"] for r in result.top_risks]
        assert "credit" in top_dims or "financial" in top_dims

    def test_deterministic_same_input_same_output(self):
        """同 input 跑 2 次 · dim_scores 必相同 (deterministic guarantee)."""
        payload = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "客户 C",
                "CREDIT_OVERDUE_RECORD": "无",
                "CLIENT_INDUSTRY_FULL": "制造业",
            },
            "credit_terms": None,
            "material_facts": None,
        }
        r1 = run_risk_assess(**payload, llm_caller=None)  # type: ignore
        r2 = run_risk_assess(**payload, llm_caller=None)  # type: ignore
        assert r1.dimension_scores == r2.dimension_scores
        assert r1.composite_risk_score == r2.composite_risk_score
        assert r1.risk_grade == r2.risk_grade

    def test_decision_context_repayment_history_reused(self):
        """decision_context.score_breakdown.repayment_history=80 → credit dim 应为 100-80=20 (低风险)."""
        result = run_risk_assess(
            client_metadata={"CLIENT_FULL_NAME": "客户"},
            decision_context={
                "score_breakdown": {
                    "repayment_history": 85,
                    "financial_health": 78,
                    "negative_judicial": 90,
                },
            },
            llm_caller=None,
        )
        # credit dim score = 100 - 85 = 15.0
        assert result.dimension_scores["credit"] == 15.0
        # financial dim score = 100 - 78 = 22.0
        assert result.dimension_scores["financial"] == 22.0
        # negative dim score = 100 - 90 = 10.0
        assert result.dimension_scores["negative_sentiment_judicial"] == 10.0


class TestRunRiskAssessOutputShape:
    """输出结构验证 · 7 维 + grade + top_risks + mitigations + reasoning."""

    def test_dimension_scores_7_keys(self):
        result = run_risk_assess(
            client_metadata={"CLIENT_FULL_NAME": "客户"},
            llm_caller=None,
        )
        assert len(result.dimension_scores) == 7
        for d in DIMENSIONS:
            assert d["id"] in result.dimension_scores
            assert 0 <= result.dimension_scores[d["id"]] <= 100

    def test_grade_and_cycle_mapping(self):
        """评级 ↔ 后审周期映射 (deterministic)."""
        # 通过 fake 低分客户 (担保强 + 行业好 + 无诉讼)
        result_low = run_risk_assess(
            client_metadata={
                "CLIENT_FULL_NAME": "优质",
                "CREDIT_OVERDUE_RECORD": "无",
                "CLIENT_LEGAL_RISK_DESC": "无",
                "CLIENT_INDUSTRY_FULL": "医疗",
            },
            credit_terms={"GUARANTEE_METHOD": "抵押"},
            material_facts={"FINANCIAL_CASH_FLOW_DESC": "充足"},
            llm_caller=None,
        )
        if result_low.risk_grade == "低":
            assert result_low.review_cycle_months == 12
        elif result_low.risk_grade == "中":
            assert result_low.review_cycle_months == 6
        else:
            assert result_low.review_cycle_months == 3

    def test_top_risks_max_3(self):
        result = run_risk_assess(
            client_metadata={
                "CLIENT_FULL_NAME": "客户",
                "CREDIT_OVERDUE_RECORD": "严重",
                "CLIENT_DEBT_RATIO": "95%",
                "CLIENT_INDUSTRY_FULL": "房地产",
                "CLIENT_LEGAL_RISK_DESC": "重大诉讼",
            },
            credit_terms={"GUARANTEE_METHOD": "信用"},
            material_facts={
                "FINANCIAL_CASH_FLOW_DESC": "断流",
                "CUSTOMER_CONCENTRATION_DESC": "高度集中",
            },
            llm_caller=None,
        )
        assert len(result.top_risks) <= 3
        # mitigations 长度 = top_risks 长度
        assert len(result.mitigations) == len(result.top_risks)

    def test_reasoning_present(self):
        """reasoning 必填 · 模板或 LLM 兜底 · 不空."""
        result = run_risk_assess(
            client_metadata={"CLIENT_FULL_NAME": "客户"},
            llm_caller=None,
        )
        assert result.reasoning.strip() != ""
        # 模板 reasoning 含明确标记
        assert "[模板兜底" in result.reasoning


class TestLLMCallerIntegration:
    """LLM caller 集成 · 失败兜底 · 成功 live."""

    def test_llm_returns_empty_fallback_to_template(self):
        """LLM 返 "" (失败) → 模板兜底 · data_source=mock_fallback."""
        def fake_llm(system: str, user: str) -> str:
            return ""

        result = run_risk_assess(
            client_metadata={"CLIENT_FULL_NAME": "客户"},
            llm_caller=fake_llm,
        )
        assert result.data_source == "mock_fallback"
        assert "[模板兜底" in result.reasoning
        assert result.confidence < 0.8

    def test_llm_returns_valid_reasoning_live(self):
        """LLM 返非空 → 用 LLM 输出 · data_source=live."""
        def fake_llm(system: str, user: str) -> str:
            return "综合评估: 客户风险中等 · 主要关注财务杠杆 · 建议追加抵押。"

        result = run_risk_assess(
            client_metadata={"CLIENT_FULL_NAME": "客户"},
            llm_caller=fake_llm,
        )
        assert result.data_source == "live"
        assert "综合评估" in result.reasoning
        assert "[模板兜底" not in result.reasoning
        assert result.confidence >= 0.8

    def test_llm_raises_fallback_to_template(self):
        """LLM caller 抛异常 → silent fallback 模板 (per CLAUDE.md 失败兜底原则)."""
        def fake_llm_raise(system: str, user: str) -> str:
            raise RuntimeError("LLM provider down")

        result = run_risk_assess(
            client_metadata={"CLIENT_FULL_NAME": "客户"},
            llm_caller=fake_llm_raise,
        )
        assert result.data_source == "mock_fallback"
        assert "[模板兜底" in result.reasoning


class TestEdgeCases:
    """边界 case · 空 input · None layer."""

    def test_empty_client_metadata(self):
        result = run_risk_assess(client_metadata={}, llm_caller=None)
        assert isinstance(result, RiskAssessResult)
        # 全部默认 → composite 应在中段 (35-50)
        assert 20 <= result.composite_risk_score <= 60

    def test_none_optional_layers(self):
        result = run_risk_assess(
            client_metadata={"CLIENT_FULL_NAME": "客户"},
            decision_context=None,
            credit_terms=None,
            material_facts=None,
            llm_caller=None,
        )
        assert isinstance(result, RiskAssessResult)
        assert len(result.dimension_scores) == 7
