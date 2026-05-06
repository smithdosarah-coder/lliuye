"""推荐理由 schema 化 · per Codex R3 final 加 (PM 拍 2026-05-06)

per Phase C charter Track D · D4 推荐理由 schema 化:

设计目标 (Codex 原话): 推荐理由不能只是自然语言 · 必须含可审计结构化字段 · 系统才能强制
检查"新闻日期/来源等级/适用对象/结论链路".

Schema 字段 (Codex R3 最终):
- source_tier: 数据源 Tier (来自 shared.data_tiers.DataTier)
- source_url: 出处 URL (or 内部源标识 internal://...)
- evidence_date: 证据事件发生时间
- retrieved_at: 我们抓取时间
- freshness_days: 计算属性 (今天 - evidence_date)
- claim_type: 证据类型 (news/financial/penalty/policy/...)
- reason_confidence: 0.0-1.0 置信度
- staleness_policy_passed: 是否通过 freshness SLA 校验

硬线 (per Phase C charter):
- 推荐核心理由必走此 schema
- 缺 source_tier / evidence_date / claim_type 任一 → invalid
- staleness_policy_passed=False → 不可作核心理由 (可作 background)
- LLM 输出 prompt 必带此 schema 结构化要求

使用:
    from shared.recommendation_schema import RecommendationReason, build_reason

    # 构建一条推荐理由
    reason = build_reason(
        text="该客户近 3 月持有理财产品到期 · 适合升级私行优享",
        source_url="internal://crm/holdings",
        evidence_date="2026-04-15",
        claim_type="financial",
        reason_confidence=0.85,
    )
    # → 自动计算 freshness_days + 自动 staleness_policy_passed
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from shared.data_tiers import DataTier, classify_source
from shared.evidence_freshness import (
    ClaimType,
    compute_freshness_days,
    compute_recency_weight,
    validate_evidence_freshness,
)


class RecommendationReason(BaseModel):
    """单条推荐理由 · 8 字段结构化 · per Codex R3 final."""

    # === 内容 ===
    text: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="推荐理由文本 · 客户经理可读 · 但 evidence 必须结构化",
    )

    # === 数据来源 ===
    source_tier: DataTier = Field(
        ...,
        description="数据源 Tier · 决定是否能作核心理由 (Tier 4 单独不行)",
    )
    source_url: str = Field(
        ...,
        min_length=1,
        description="出处 URL 或内部源标识 (internal://...)",
    )

    # === 时效 ===
    evidence_date: str = Field(
        ...,
        description="证据事件发生时间 · ISO 格式 (YYYY-MM-DD or full datetime)",
    )
    retrieved_at: str = Field(
        ...,
        description="我们抓取时间 · ISO 格式",
    )
    freshness_days: int = Field(
        ...,
        ge=0,
        description="计算属性 · 今天 - evidence_date · 单位天",
    )

    # === claim 分类 ===
    claim_type: ClaimType = Field(
        ...,
        description="证据 claim 类型 · 决定 freshness SLA",
    )

    # === 置信度 ===
    reason_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="0.0-1.0 置信度 · LLM/规则给出",
    )

    # === 硬约束校验结果 ===
    staleness_policy_passed: bool = Field(
        ...,
        description="是否通过 freshness SLA 校验 · False = 不可作核心理由",
    )

    # ---------------------------------------------------------------------------
    # 校验
    # ---------------------------------------------------------------------------

    @field_validator("source_url")
    @classmethod
    def _no_empty_url(cls, v: str) -> str:
        if not v or v.lower() in ("none", "null", "—", "-"):
            raise ValueError("source_url 不能空 · 推荐理由必带可追溯出处")
        return v

    @model_validator(mode="after")
    def _check_consistency(self) -> "RecommendationReason":
        """跨字段一致性 · source_url tier vs source_tier 应一致 (允许显式 override)."""
        # 仅 warning · 不抛 (允许内部源显式标 tier)
        return self


def build_reason(
    *,
    text: str,
    source_url: str,
    evidence_date: str,
    claim_type: str = "generic",
    reason_confidence: float = 0.7,
    retrieved_at: Optional[str] = None,
    source_tier: Optional[str] = None,
) -> RecommendationReason:
    """构建一条推荐理由 · 自动计算 freshness_days + staleness_policy_passed.

    Args:
        text: 推荐理由文本
        source_url: 出处 URL 或内部源
        evidence_date: 证据时间 (ISO)
        claim_type: claim 类型 (默认 generic)
        reason_confidence: 0.0-1.0
        retrieved_at: 抓取时间 (默认 now)
        source_tier: 显式 tier override · 默认从 source_url 推断

    Returns:
        RecommendationReason 实例
    """
    # 推断 tier
    if source_tier:
        tier = DataTier(source_tier)
    else:
        tier = classify_source(source_url)

    # 计算 freshness
    fd = compute_freshness_days(evidence_date)
    if fd is None:
        raise ValueError(
            f"evidence_date 不可解析: {evidence_date} · 推荐理由必带合法时间"
        )

    # 校验 freshness
    try:
        ct = ClaimType(claim_type)
    except ValueError:
        ct = ClaimType.GENERIC

    fresh_check = validate_evidence_freshness(
        evidence_date=evidence_date, claim_type=ct,
    )
    staleness_passed = not fresh_check["is_stale"] and not fresh_check["is_missing_date"]

    return RecommendationReason(
        text=text,
        source_tier=tier,
        source_url=source_url,
        evidence_date=evidence_date,
        retrieved_at=retrieved_at or datetime.now().isoformat(timespec="seconds"),
        freshness_days=fd,
        claim_type=ct,
        reason_confidence=reason_confidence,
        staleness_policy_passed=staleness_passed,
    )


def build_recommendation_with_validation(
    reasons: List[RecommendationReason],
) -> dict[str, Any]:
    """组装多 reason 推荐 + 整体校验.

    Returns:
        {
            'core_reasons': [reason that passed staleness],
            'background_reasons': [reason that failed staleness · 仅作背景],
            'block': bool · 是否整推荐被阻断,
            'block_reason': str | None,
            'high_trust_count': int,
            'tier_distribution': {...},
            'avg_recency_weight': float,
        }
    """
    core_reasons: list[RecommendationReason] = []
    background_reasons: list[RecommendationReason] = []
    high_trust = 0
    tier_dist: dict[str, int] = {t.value: 0 for t in DataTier}
    total_weight = 0.0

    for r in reasons:
        tier_dist[r.source_tier.value] += 1
        if r.source_tier in (
            DataTier.INTERNAL_AUTHORITATIVE,
            DataTier.GOVERNMENT,
            DataTier.INDUSTRY,
        ):
            high_trust += 1
        weight = compute_recency_weight(r.freshness_days)
        total_weight += weight
        if r.staleness_policy_passed and weight >= 0.4:
            core_reasons.append(r)
        else:
            background_reasons.append(r)

    n = max(len(reasons), 1)
    avg_weight = round(total_weight / n, 3)

    block_reason: Optional[str] = None
    if not reasons:
        block_reason = "无推荐理由 · 不可信"
    elif not core_reasons:
        block_reason = (
            f"0 条核心理由 · 全部 stale 或低置信 · "
            f"high_trust={high_trust} avg_weight={avg_weight}"
        )
    elif high_trust == 0:
        block_reason = "核心理由全 Tier 4 公开 web · 必交叉 Tier 1/2/3"

    return {
        "core_reasons": core_reasons,
        "background_reasons": background_reasons,
        "block": block_reason is not None,
        "block_reason": block_reason,
        "high_trust_count": high_trust,
        "tier_distribution": tier_dist,
        "avg_recency_weight": avg_weight,
    }


__all__ = [
    "RecommendationReason",
    "build_reason",
    "build_recommendation_with_validation",
]
