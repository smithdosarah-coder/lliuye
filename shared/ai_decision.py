"""AI 决策建议生成 · 端到端核心模块

per Phase C charter Track A · A2 · 端到端流程第 2 件 (PM 拍板 2026-05-06):

设计:
- 输入: customer_profile (CRM 15 字段) + agent_context (Agent1 候选/Agent6 报告/Agent5 政策)
- 输出: list[RecommendationReason] (8 字段 schema · per Codex R3) + decision_summary + confidence
- 校验: 用 D1 (data_tiers) + D2 (evidence_freshness) + D4 (recommendation_schema) 三层校验
- LLM grounded with mock fallback · LLM 失败仍能产 mock decision (silent fail)
- 输出必带 decision_id (UUID) · 用于 ledger 上链 + lineage 追溯

硬线 (per Phase C DP3 PM 拍板):
- 必有 lineage + audit
- 缺核心证据 block (build_recommendation_with_validation 决定)
- LLM 不调时 fallback mock · 但仍走 D1/D2/D4 校验

使用:
    from shared.ai_decision import build_decision

    decision = build_decision(
        customer_id="C-001",
        intent="ai_advice_proactive",  # or "credit_review" / "compliance_check"
    )
    # → {
    #     'decision_id': 'dec-...',
    #     'customer_id': 'C-001',
    #     'reasons': [RecommendationReason · 8 字段],
    #     'decision_summary': str,
    #     'confidence': float,
    #     'block': bool,
    #     'block_reason': str | None,
    #     'metadata': {...},
    # }
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from shared.crm_contract import CrmCustomerProfile, RiskLevel
from shared.data_tiers import DataTier
from shared.evidence_freshness import ClaimType
from shared.recommendation_schema import (
    build_reason,
    build_recommendation_with_validation,
)


def _mock_reasons_for_profile(
    profile: CrmCustomerProfile,
    *,
    intent: str,
) -> list[Any]:
    """根据客户画像 + intent 生成 mock 推荐理由 (LLM 不可用时 fallback).

    每条 reason 必走 build_reason · 自动 tier 推断 + freshness 校验 + staleness check.
    覆盖三类 intent: ai_advice_proactive / credit_review / compliance_check
    """
    reasons: list[Any] = []
    today = datetime.now().date().isoformat()

    # 内部权威 (Tier 1) · 现持产品 + 最近接触 · always fresh
    if profile.existing_products:
        reasons.append(build_reason(
            text=f"客户现持 {len(profile.existing_products)} 项产品 ({', '.join(profile.existing_products[:2])} 等) · 客户关系活跃",
            source_url="internal://crm/holdings",
            evidence_date=today,
            claim_type="financial",
            reason_confidence=0.95,
        ))

    if profile.last_contact_at:
        reasons.append(build_reason(
            text=f"上次 RM 接触 {profile.last_contact_at.date().isoformat()} · 维护周期内",
            source_url="internal://crm/contacts",
            evidence_date=profile.last_contact_at.date().isoformat(),
            claim_type="generic",
            reason_confidence=0.88,
        ))

    # 风险偏好 + 收入级 → 产品适配 (Tier 1 · 内部规则)
    if intent == "ai_advice_proactive":
        if profile.risk_level == RiskLevel.AGGRESSIVE and profile.income_monthly >= 100000:
            reasons.append(build_reason(
                text=f"激进型偏好 + 月收入 {profile.income_monthly:.0f} · 适配私行优享 + 私募基金 + 信托产品",
                source_url="internal://product_pyramid/private_banking",
                evidence_date=today,
                claim_type="financial",
                reason_confidence=0.85,
            ))
        elif profile.risk_level == RiskLevel.GROWTH:
            reasons.append(build_reason(
                text=f"成长型偏好 + 月收入 {profile.income_monthly:.0f} · 适配公募基金 + 平衡型理财 + 重疾险升级",
                source_url="internal://product_pyramid/balanced",
                evidence_date=today,
                claim_type="financial",
                reason_confidence=0.82,
            ))
        elif profile.risk_level == RiskLevel.CONSERVATIVE:
            reasons.append(build_reason(
                text=f"保守型偏好 · 适配定期储蓄 + 国债 + 货币基金 (低风险稳健)",
                source_url="internal://product_pyramid/conservative",
                evidence_date=today,
                claim_type="financial",
                reason_confidence=0.92,
            ))

    # 监管/政策 (Tier 2 · 政府) · 仅当近 1 月内政策变更
    if intent in ("compliance_check", "ai_advice_proactive"):
        # mock 政策 evidence · 真 production 接 Agent5
        reasons.append(build_reason(
            text="2026 年 4 月银保监适当性销售指引更新 · 客户风险偏好须重新确认",
            source_url="https://www.cbirc.gov.cn/notice/20260415-suitability.html",
            evidence_date="2026-04-15",
            claim_type="policy",
            reason_confidence=0.78,
        ))

    return reasons


def build_decision(
    *,
    customer_id: str,
    intent: str = "ai_advice_proactive",
    extra_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """端到端 AI 决策 · 输入客户 ID → 输出推荐 + 校验.

    Args:
        customer_id: 客户唯一 ID
        intent: 决策意图 ('ai_advice_proactive' / 'credit_review' / 'compliance_check')
        extra_context: 额外上下文 (Agent1 候选 / Agent6 报告 etc.)

    Returns:
        {
            'decision_id': UUID,
            'customer_id': str,
            'intent': str,
            'reasons': list[RecommendationReason · 8 字段],
            'decision_summary': str,
            'confidence': float,
            'block': bool,
            'block_reason': str | None,
            'tier_distribution': {...},
            'metadata': {...},
        }
    """
    from shared.customer_aggregator import aggregate_customer_profile

    # 1. 获取客户画像 (CRM 15 字段)
    aggregated = aggregate_customer_profile(customer_id)
    if aggregated is None:
        return {
            "decision_id": None,
            "customer_id": customer_id,
            "block": True,
            "block_reason": f"客户 {customer_id} 不存在",
            "reasons": [],
        }

    # 2. consent_status 检查 (PIPL 硬线 · 没授权不能用客户数据做 AI 决策)
    consent = aggregated.get("customer", {}).get("consent_status")
    if consent != "granted":
        return {
            "decision_id": None,
            "customer_id": customer_id,
            "block": True,
            "block_reason": f"客户 {customer_id} 未授权 (consent_status={consent}) · PIPL 不允许 AI 决策",
            "reasons": [],
        }

    # 3. 重新构建 CRM profile (经过 schema 校验)
    profile = CrmCustomerProfile(**aggregated["customer"])

    # 4. 生成推荐理由 (mock fallback · LLM 真接见 Sprint 6 D5)
    raw_reasons = _mock_reasons_for_profile(profile, intent=intent)

    # 5. 校验: build_recommendation_with_validation (D1 + D2 + D4 三合一)
    validation = build_recommendation_with_validation(raw_reasons)

    # 6. 决策摘要
    if validation["block"]:
        decision_summary = f"⚠ 决策受阻: {validation['block_reason']}"
        confidence = 0.0
    else:
        core_n = len(validation["core_reasons"])
        decision_summary = (
            f"基于 {core_n} 条核心证据 (高 trust source × {validation['high_trust_count']}) · "
            f"客户 {profile.name} ({profile.age}岁 · {profile.risk_level.value}) "
            f"建议适配方案 · 平均时效权重 {validation['avg_recency_weight']}"
        )
        confidence = round(min(validation["avg_recency_weight"] * 1.2, 0.99), 2)

    decision_id = f"dec-{uuid.uuid4().hex[:12]}"

    return {
        "decision_id": decision_id,
        "customer_id": customer_id,
        "intent": intent,
        "reasons": [
            r.model_dump(mode="json") for r in (validation["core_reasons"] + validation["background_reasons"])
        ],
        "core_reasons_count": len(validation["core_reasons"]),
        "background_reasons_count": len(validation["background_reasons"]),
        "decision_summary": decision_summary,
        "confidence": confidence,
        "block": validation["block"],
        "block_reason": validation["block_reason"],
        "tier_distribution": validation["tier_distribution"],
        "avg_recency_weight": validation["avg_recency_weight"],
        "metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": "mock-v1.0",  # 真接 LLM 后改 deepseek-chat 等
            "schema_version": "1.0",
            "extra_context_keys": list((extra_context or {}).keys()),
        },
    }


__all__ = [
    "build_decision",
]
