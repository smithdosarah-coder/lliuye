# -*- coding: utf-8 -*-
"""Evidence-First Protocol 冒烟测试（CLAUDE.md §3.3）

覆盖 5 + Agent6 共 6 个 evidence_pipeline，验证：
1. 继承 `EvidenceFirstPipeline` 抽象基类
2. `run(ctx)` 返回 `AuditedResult`，含 `evidence_trail` / `unfilled_fields`
3. 缺关键字段时 audit 能 block 并标 UNFILLED_MARKER
4. 正常输入时 content 含输入中的关键实体
"""

from __future__ import annotations

import pytest

from shared.evidence import (
    AuditedResult,
    EvidenceFirstPipeline,
    UNFILLED_MARKER,
)


# ---------------------------------------------------------------------------
# Agent1 channel
# ---------------------------------------------------------------------------


def test_channel_pitch_pipeline_happy():
    from agent_channel.evidence_pipeline import (
        ChannelPitchContext,
        ChannelPitchPipeline,
    )

    ctx = ChannelPitchContext(
        candidate={"company_name": "测试智能科技", "industry": "软件"},
        signals=[
            {"signal_type": "中标", "title": "中标 500 万订单", "url": "https://x"},
            {"signal_type": "专精特新", "title": "入选省级专精特新", "url": "https://y"},
        ],
        products=["流动资金贷款", "知产质押贷"],
    )
    result = ChannelPitchPipeline().run(ctx)

    assert isinstance(result, AuditedResult)
    assert "测试智能科技" in result.content
    assert len(result.evidence_trail) >= 3
    assert not result.blocked


def test_channel_pitch_missing_candidate_blocks():
    from agent_channel.evidence_pipeline import (
        ChannelPitchContext,
        ChannelPitchPipeline,
    )

    ctx = ChannelPitchContext(candidate={}, signals=[], products=[])
    result = ChannelPitchPipeline().run(ctx)

    assert UNFILLED_MARKER in result.content
    assert "company_name" in result.unfilled_fields
    assert result.blocked


# ---------------------------------------------------------------------------
# Agent3 credit
# ---------------------------------------------------------------------------


def test_credit_decision_pipeline_happy():
    from agent_credit.evidence_pipeline import (
        CreditDecisionContext,
        CreditDecisionPipeline,
    )

    ctx = CreditDecisionContext(
        profile={"company_name": "鼎盛贸易"},
        scoring={"composite_score": 82},
        rule_hits=[{"rule_id": "R-007", "severity": "中"}],
        cases=[{"case_id": "C-101", "summary": "同业案例"}],
        request={"amount": 500},
        segment="corporate",
    )
    result = CreditDecisionPipeline().run(ctx)

    assert isinstance(result, AuditedResult)
    assert "鼎盛贸易" in result.content
    assert "82" in result.content
    assert "500" in result.content


def test_credit_decision_missing_core_blocks():
    from agent_credit.evidence_pipeline import (
        CreditDecisionContext,
        CreditDecisionPipeline,
    )

    ctx = CreditDecisionContext(profile={}, scoring=None, rule_hits=[], cases=[],
                                 request={}, segment="corporate")
    result = CreditDecisionPipeline().run(ctx)
    assert result.blocked
    assert "customer_name" in result.unfilled_fields
    assert "composite_score" in result.unfilled_fields


# ---------------------------------------------------------------------------
# Agent4 alert
# ---------------------------------------------------------------------------


def test_alert_summary_pipeline_red_level():
    from agent_alert.evidence_pipeline import (
        AlertSummaryContext,
        AlertSummaryPipeline,
    )

    ctx = AlertSummaryContext(
        customer_name="某制造企业",
        external_hits=[{"title": "被起诉 200 万", "url": "https://c"}],
        internal_signals=[{"level": "红", "description": "近三月营收下滑 40%"}],
        cross_hits=[
            {"rule_id": "R1", "route": "外部"},
            {"rule_id": "R2", "route": "内部"},
        ],
    )
    result = AlertSummaryPipeline().run(ctx)

    assert "某制造企业" in result.content
    assert "红灯" in result.content
    assert not result.blocked


def test_alert_summary_missing_customer_blocks():
    from agent_alert.evidence_pipeline import (
        AlertSummaryContext,
        AlertSummaryPipeline,
    )

    ctx = AlertSummaryContext(customer_name="")
    result = AlertSummaryPipeline().run(ctx)
    assert result.blocked


# ---------------------------------------------------------------------------
# Agent5 compliance
# ---------------------------------------------------------------------------


def test_compliance_summary_severe_violation():
    from agent_compliance.evidence_pipeline import (
        ComplianceSummaryContext,
        ComplianceSummaryPipeline,
    )

    ctx = ComplianceSummaryContext(
        policy_title="小贷管理办法 2026 版",
        policy_requirements=[
            {"text": "利率上限调整为 24%", "category": "pricing"},
        ],
        matrix_violations=[
            {"rule_id": "V1", "severity": "严重"},
            {"rule_id": "V2", "severity": "一般"},
        ],
        defects=[{"category": "pricing", "severity": "严重"}],
    )
    result = ComplianceSummaryPipeline().run(ctx)

    assert "小贷管理办法 2026 版" in result.content
    assert "严重" in result.content


def test_compliance_summary_missing_policy_blocks():
    from agent_compliance.evidence_pipeline import (
        ComplianceSummaryContext,
        ComplianceSummaryPipeline,
    )

    result = ComplianceSummaryPipeline().run(ComplianceSummaryContext())
    assert result.blocked


# ---------------------------------------------------------------------------
# Agent2 riskctrl
# ---------------------------------------------------------------------------


def test_riskctrl_commentary_happy():
    from agent_riskctrl.evidence_pipeline import (
        RiskctrlCommentaryContext,
        RiskctrlCommentaryPipeline,
    )

    ctx = RiskctrlCommentaryContext(
        ruleset_name="V1.2-反欺诈组",
        metrics={"ks": 0.35, "pass_rate": 0.72, "bad_rate": 0.018, "psi": 0.05},
        per_rule_fp=[{"rule_id": "R001", "fp_rate": 0.08}],
    )
    result = RiskctrlCommentaryPipeline().run(ctx)

    assert "V1.2-反欺诈组" in result.content
    assert "KS=0.35" in result.content


def test_riskctrl_commentary_missing_metrics_blocks():
    from agent_riskctrl.evidence_pipeline import (
        RiskctrlCommentaryContext,
        RiskctrlCommentaryPipeline,
    )

    ctx = RiskctrlCommentaryContext(ruleset_name="X", metrics={})
    result = RiskctrlCommentaryPipeline().run(ctx)
    assert result.blocked


# ---------------------------------------------------------------------------
# Agent6 report (结构对齐，不改既有行为)
# ---------------------------------------------------------------------------


def test_report_section_pipeline_structure_alignment():
    from agent_report.evidence_pipeline import (
        ReportSectionContext,
        ReportSectionPipeline,
    )

    ctx = ReportSectionContext(
        section_title="二、财务分析",
        financial_anchors="资产负债率 42.5% (较年初下降 7.7 个百分点)",
        industry_card="软件和信息技术服务业 典型账期 90-180 天",
        material_anchor="2024 年报关键科目期末值",
        evidence_text="客户材料已上传 3 份",
        generated_text="资产负债率较年初下降 7.7 个百分点至 42.5%。",
    )
    result = ReportSectionPipeline().run(ctx)

    assert isinstance(result, AuditedResult)
    assert "42.5" in result.content
    assert not result.blocked
    trails = {it["source"] for it in result.evidence_trail}
    assert "financial_analyzer" in trails


def test_report_section_pipeline_missing_generation_blocks():
    from agent_report.evidence_pipeline import (
        ReportSectionContext,
        ReportSectionPipeline,
    )

    ctx = ReportSectionContext(section_title="二、财务分析", financial_anchors="x",
                                generated_text="")
    result = ReportSectionPipeline().run(ctx)
    assert result.blocked


# ---------------------------------------------------------------------------
# 抽象基类契约
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        lambda: __import__("agent_channel.evidence_pipeline",
                           fromlist=["ChannelPitchPipeline"]).ChannelPitchPipeline(),
        lambda: __import__("agent_credit.evidence_pipeline",
                           fromlist=["CreditDecisionPipeline"]).CreditDecisionPipeline(),
        lambda: __import__("agent_alert.evidence_pipeline",
                           fromlist=["AlertSummaryPipeline"]).AlertSummaryPipeline(),
        lambda: __import__("agent_compliance.evidence_pipeline",
                           fromlist=["ComplianceSummaryPipeline"]).ComplianceSummaryPipeline(),
        lambda: __import__("agent_riskctrl.evidence_pipeline",
                           fromlist=["RiskctrlCommentaryPipeline"]).RiskctrlCommentaryPipeline(),
        lambda: __import__("agent_report.evidence_pipeline",
                           fromlist=["ReportSectionPipeline"]).ReportSectionPipeline(),
    ],
)
def test_pipeline_is_evidence_first_subclass(factory):
    pipeline = factory()
    assert isinstance(pipeline, EvidenceFirstPipeline)
    assert pipeline.name != "unnamed_pipeline"
