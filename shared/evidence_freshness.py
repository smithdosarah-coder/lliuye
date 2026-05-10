"""证据时效硬约束 · 杜绝 Agent1 "推 10 年前新闻当推荐核心理由" 类问题

per Phase C charter Track D · D2 证据时效硬约束 (PM 拍板 2026-05-06):

设计:
- 每条 evidence 必带 evidence_date (字段事件发生时间)
- retrieved_at (我们抓取时间)
- 计算 freshness_days (今天 - evidence_date)
- 按 claim_type 阈值校验 + recency 加权

DP4 PM 拍板 freshness SLA:
- 新闻 (news): 180 天
- 财报 (financial): 120 天
- 监管处罚 (penalty): 365 天
- 政策 (policy): 365 天
- 同行案例 (case_study): 730 天
- 工商变更 (business_change): 730 天 (相对静态)
- 招投标 (bid): 90 天 (高时效信号)
- 招聘 (recruit): 60 天 (高时效信号)
- 司法案件 (legal): 365 天
- 投融资 (funding): 365 天
- 历史贷款样本 (loan_sample): 365 天 (Phase A.1 · per RFC freshness-claim-loan-sample · 信贷周期 12 月 · 银保监年度审计周期)
- 回测固定基线 (backtest_fixture): 730 天 (Phase A.1 · 信贷周期完整覆盖 · 固定基线允许更长)

硬线 (per CLAUDE.md §3.1):
- evidence 缺 evidence_date · 不能作核心 claim
- evidence > sla_days · 标 stale · 不计入"核心理由" 但可作背景
- prompt 强制 "only cite signals from last 12 months unless explicitly historical"
- QC 闸新增 evidence_freshness 维度

Recency 加权 (per Codex+Claude R3 final):
- < 30 天: 1.0 (full weight)
- < 6 月 (180 天): 0.7
- < 12 月 (365 天): 0.4
- < 24 月 (730 天): 0.2
- > 24 月: 0.05 (history note only)

使用:
    from shared.evidence_freshness import (
        ClaimType, FRESHNESS_SLA_DAYS,
        compute_freshness_days, classify_freshness,
        compute_recency_weight, validate_evidence_freshness,
    )

    # 给单 evidence 计算时效
    fd = compute_freshness_days(evidence_date='2024-01-15')
    weight = compute_recency_weight(fd)  # 0.05 (over 2 years)

    # 校验单 evidence 是否合时效
    result = validate_evidence_freshness(
        evidence_date='2024-01-15', claim_type=ClaimType.NEWS,
    )
    # → {'is_stale': True, 'freshness_days': 730, 'sla_days': 180, ...}
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Optional


class ClaimType(str, Enum):
    """证据 claim 类型 · 决定 freshness SLA 阈值."""

    NEWS = "news"  # 新闻
    FINANCIAL = "financial"  # 财报数据
    PENALTY = "penalty"  # 监管处罚
    POLICY = "policy"  # 政策法规
    CASE_STUDY = "case_study"  # 同行案例
    BUSINESS_CHANGE = "business_change"  # 工商变更 (法人/资本/经营范围)
    BID = "bid"  # 招投标
    RECRUIT = "recruit"  # 招聘
    LEGAL = "legal"  # 司法案件
    FUNDING = "funding"  # 投融资
    LOAN_SAMPLE = "loan_sample"  # 历史贷款样本 (riskctrl backtest 用 · Phase A.1)
    BACKTEST_FIXTURE = "backtest_fixture"  # 回测固定基线 fixture (champion vs challenger · Phase A.1)
    GENERIC = "generic"  # 通用 (默认 180 天)


# DP4 PM 拍板 · freshness SLA (天)
FRESHNESS_SLA_DAYS: dict[ClaimType, int] = {
    ClaimType.NEWS: 180,
    ClaimType.FINANCIAL: 120,
    ClaimType.PENALTY: 365,
    ClaimType.POLICY: 365,
    ClaimType.CASE_STUDY: 730,
    ClaimType.BUSINESS_CHANGE: 730,
    ClaimType.BID: 90,
    ClaimType.RECRUIT: 60,
    ClaimType.LEGAL: 365,
    ClaimType.FUNDING: 365,
    ClaimType.LOAN_SAMPLE: 365,        # Phase A.1 RFC ratify · 信贷周期 12 月
    ClaimType.BACKTEST_FIXTURE: 730,   # Phase A.1 RFC ratify · 完整信贷周期 2y
    ClaimType.GENERIC: 180,
}


def _parse_date(date_input: Any) -> Optional[datetime]:
    """容纳多种日期格式 · 返 datetime (UTC) 或 None."""
    if date_input is None:
        return None
    if isinstance(date_input, datetime):
        return date_input.astimezone(timezone.utc) if date_input.tzinfo else date_input
    if isinstance(date_input, str):
        s = date_input.strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        # ISO 8601 fallback
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
    return None


def compute_freshness_days(
    evidence_date: Any,
    *,
    reference_date: Optional[datetime] = None,
) -> Optional[int]:
    """计算 evidence 距今天数 · 缺 evidence_date 返 None."""
    parsed = _parse_date(evidence_date)
    if parsed is None:
        return None
    ref = reference_date or datetime.now()
    if parsed.tzinfo and not ref.tzinfo:
        ref = ref.replace(tzinfo=parsed.tzinfo)
    elif ref.tzinfo and not parsed.tzinfo:
        parsed = parsed.replace(tzinfo=ref.tzinfo)
    delta = ref - parsed
    return max(delta.days, 0)


def compute_recency_weight(freshness_days: Optional[int]) -> float:
    """Recency 加权 (per R3 final 共识).

    < 30 天: 1.0
    < 180 天: 0.7
    < 365 天: 0.4
    < 730 天: 0.2
    其他: 0.05
    缺数据: 0.0 (不可用)
    """
    if freshness_days is None:
        return 0.0
    if freshness_days < 30:
        return 1.0
    if freshness_days < 180:
        return 0.7
    if freshness_days < 365:
        return 0.4
    if freshness_days < 730:
        return 0.2
    return 0.05


def classify_freshness(freshness_days: Optional[int]) -> str:
    """分类 freshness band · 用于 UI 显示."""
    if freshness_days is None:
        return "unknown"
    if freshness_days < 30:
        return "fresh"  # 鲜
    if freshness_days < 180:
        return "recent"  # 近期
    if freshness_days < 365:
        return "aging"  # 老化
    if freshness_days < 730:
        return "stale"  # 过期
    return "very_stale"  # 极久


def validate_evidence_freshness(
    *,
    evidence_date: Any,
    claim_type: ClaimType = ClaimType.GENERIC,
    reference_date: Optional[datetime] = None,
) -> dict[str, Any]:
    """校验单条 evidence 是否合时效.

    Args:
        evidence_date: 证据事件发生时间
        claim_type: 证据 claim 类型 (决定 SLA)
        reference_date: 参考时间 (默认 now)

    Returns:
        {
            'is_stale': bool · 是否超 SLA,
            'is_missing_date': bool · 是否缺 evidence_date,
            'freshness_days': int | None,
            'sla_days': int,
            'recency_weight': float,
            'classification': str,
            'block_as_core_claim': bool,  # 是否禁作核心理由
        }
    """
    fd = compute_freshness_days(evidence_date, reference_date=reference_date)
    sla = FRESHNESS_SLA_DAYS[claim_type]
    weight = compute_recency_weight(fd)
    classification = classify_freshness(fd)
    is_missing = fd is None
    is_stale = (fd is not None) and (fd > sla)

    # 核心 claim 阻断: 缺日期 OR 超 SLA OR weight < 0.4
    block_as_core = is_missing or is_stale or weight < 0.4

    return {
        "is_stale": is_stale,
        "is_missing_date": is_missing,
        "freshness_days": fd,
        "sla_days": sla,
        "recency_weight": weight,
        "classification": classification,
        "block_as_core_claim": block_as_core,
        "claim_type": claim_type.value,
    }


def validate_evidence_chain(
    evidences: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """校验整 evidence chain 是否合产品级 freshness 要求.

    Args:
        evidences: list of {evidence_date, claim_type, ...}

    Returns:
        {
            'all_valid': bool,
            'core_count': int (能作核心理由的 evidence 数),
            'stale_count': int,
            'missing_date_count': int,
            'avg_recency_weight': float,
            'block_reason': str | None,
            'per_evidence': [validate result list],
        }
    """
    items = list(evidences)
    per_results = []
    core_count = 0
    stale_count = 0
    missing_count = 0
    total_weight = 0.0

    for ev in items:
        ct_raw = ev.get("claim_type", "generic")
        try:
            ct = ClaimType(ct_raw)
        except ValueError:
            ct = ClaimType.GENERIC
        res = validate_evidence_freshness(
            evidence_date=ev.get("evidence_date"),
            claim_type=ct,
        )
        per_results.append(res)
        if not res["block_as_core_claim"]:
            core_count += 1
        if res["is_stale"]:
            stale_count += 1
        if res["is_missing_date"]:
            missing_count += 1
        total_weight += res["recency_weight"]

    n = max(len(items), 1)
    avg_weight = round(total_weight / n, 3)

    block_reason: Optional[str] = None
    if not items:
        block_reason = "无 evidence · 不可信"
    elif core_count == 0:
        block_reason = (
            f"0 条 evidence 可作核心理由 · "
            f"过期 {stale_count} · 缺日期 {missing_count} · 全部 stale 或无日期"
        )

    return {
        "all_valid": block_reason is None and stale_count == 0,
        "core_count": core_count,
        "stale_count": stale_count,
        "missing_date_count": missing_count,
        "total_count": len(items),
        "avg_recency_weight": avg_weight,
        "block_reason": block_reason,
        "per_evidence": per_results,
    }


__all__ = [
    "ClaimType",
    "FRESHNESS_SLA_DAYS",
    "compute_freshness_days",
    "compute_recency_weight",
    "classify_freshness",
    "validate_evidence_freshness",
    "validate_evidence_chain",
]
