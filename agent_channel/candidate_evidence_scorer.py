# -*- coding: utf-8 -*-
"""Agent1 候选企业证据评分器 — Phase B Sprint 3 BE1 (2026-05-05).

per CLAUDE.md §3.1 (确定性 vs 概率性) + §3.5 #5 (环境边界 · 内部 mock 不替 Agent 外搜):
- 确定性评分 0-100 (Python · 不让 LLM 现场算 score)
- 证据链 schema (出处 file/URL/段落 ID · 每条 score 必带 evidence)
- 4 维度 (industry / scale / region / signal) · 各权重明确

输出消费者:
- agent_channel/api.py /api/channel/run → 在 enrich 阶段后给 LLM 做 grounded 推荐
- LLM 见 score + evidence_chain · 不 hallucinate

per Q-052 #2 永不 multi-tenant + Q-041 4 字段 metadata (industry/geo/scale/similarity):
- score 输入候选 dict 必含 4 字段 (per §3.7.2)
- score 输出 add `evidence_score: int` + `evidence_chain: list[dict]`
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict


# 评分维度权重 (per Agent1 v4.0 信号驱动搜索 + Q-041 4 字段)
EVIDENCE_WEIGHTS: dict[str, float] = {
    "industry":    0.30,  # 行业匹配 (vs 已成交客户内源 KB)
    "scale":       0.25,  # 规模匹配 (vs 银行准入额度区间)
    "region":      0.20,  # 地域匹配 (vs RM 辖区)
    "signal":      0.25,  # 外部信号 (招标 / 招聘 / 项目 / 政策契合)
}

# 分档基础分
TIER_SCORE: dict[str, int] = {
    "high":    90,  # 强匹配
    "medium":  60,  # 中匹配
    "low":     30,  # 弱匹配
    "none":    0,   # 无证据
}


class EvidenceItem(TypedDict, total=False):
    """单条证据 schema · 必含 source / quote / location."""

    source: str           # 来源类型 ("internal_kb" / "tavily" / "akshare" / "qcc" / "policy_db")
    source_url: str       # 出处 URL (live source · 内源 KB 走 file path)
    file: str             # 文件路径 (内源 KB · e.g. "data/channel_kb/seed_companies.jsonl")
    paragraph_id: str     # 段落 ID (e.g. "p3" / "row-12" / "section-2.1")
    quote: str            # 原文引用 (≤ 200 char)
    fetched_at: str       # ISO 时间戳 (live source 必填)
    confidence: float     # 0-1 来源可信度 (e.g. 内源 KB 0.95 · Tavily 0.7)


class DimensionScore(TypedDict):
    """单维度评分输出."""

    dimension: Literal["industry", "scale", "region", "signal"]
    tier: Literal["high", "medium", "low", "none"]
    base_score: int       # 来自 TIER_SCORE
    weight: float         # 来自 EVIDENCE_WEIGHTS
    weighted: float       # base_score * weight
    evidence: list[EvidenceItem]  # 该维度的证据 list (≥ 1 条 if tier != "none")


class CandidateEvidenceScore(TypedDict):
    """完整候选评分输出 schema."""

    candidate_id: str
    candidate_name: str
    total_score: int                              # 0-100
    dimensions: list[DimensionScore]              # 4 维度详情
    evidence_chain: list[EvidenceItem]            # 全部 evidence (flat · 给 LLM grounded)
    metadata: dict[str, Any]                      # Q-041 4 字段: industry/geo/scale/similarity


def _score_industry(
    candidate: dict[str, Any],
    internal_kb_companies: list[dict[str, Any]],
) -> tuple[Literal["high", "medium", "low", "none"], list[EvidenceItem]]:
    """行业维度评分 · 比对候选行业 vs 内源已成交客户行业分布."""
    cand_industry = (candidate.get("industry") or "").strip()
    if not cand_industry:
        return "none", []

    matched = [
        c for c in internal_kb_companies
        if cand_industry in (c.get("industry") or "")
        or (c.get("industry") or "") in cand_industry
    ]

    if len(matched) >= 5:
        tier: Literal["high", "medium", "low", "none"] = "high"
    elif len(matched) >= 2:
        tier = "medium"
    elif len(matched) >= 1:
        tier = "low"
    else:
        tier = "none"

    evidence: list[EvidenceItem] = []
    if matched:
        sample = matched[0]
        evidence.append({
            "source": "internal_kb",
            "file": "data/channel_kb/seed_companies.jsonl",
            "paragraph_id": f"row-{sample.get('row_id', '?')}",
            "quote": (
                f"已成交客户 {sample.get('name', 'unknown')} 行业为"
                f" {sample.get('industry', 'unknown')} · 与候选 {cand_industry} 匹配 "
                f"(共 {len(matched)} 条相似)"
            ),
            "confidence": 0.95,
        })
    return tier, evidence


def _score_scale(
    candidate: dict[str, Any],
    internal_kb_companies: list[dict[str, Any]],
) -> tuple[Literal["high", "medium", "low", "none"], list[EvidenceItem]]:
    """规模维度评分 · 比对候选规模 vs 内源 KB 准入区间."""
    cand_scale = (candidate.get("scale") or "").strip()
    if not cand_scale:
        return "none", []

    # KB 已成交客户的规模分档分布
    scale_dist: dict[str, int] = {}
    for c in internal_kb_companies:
        s = (c.get("scale") or "").strip()
        if s:
            scale_dist[s] = scale_dist.get(s, 0) + 1

    cand_count = scale_dist.get(cand_scale, 0)
    total_kb = sum(scale_dist.values())

    if total_kb == 0:
        return "none", []

    proportion = cand_count / total_kb if total_kb else 0
    if proportion >= 0.30:
        tier: Literal["high", "medium", "low", "none"] = "high"
    elif proportion >= 0.10:
        tier = "medium"
    elif cand_count > 0:
        tier = "low"
    else:
        tier = "none"

    evidence: list[EvidenceItem] = [{
        "source": "internal_kb",
        "file": "data/channel_kb/seed_companies.jsonl",
        "paragraph_id": "scale-aggregate",
        "quote": (
            f"内源 KB {total_kb} 已成交客户中 · 规模 {cand_scale} 占比 "
            f"{proportion:.1%} ({cand_count} 条) · "
            f"分档评级 {tier}"
        ),
        "confidence": 0.95,
    }] if cand_count > 0 else []
    return tier, evidence


def _score_region(
    candidate: dict[str, Any],
    rm_region: str,
) -> tuple[Literal["high", "medium", "low", "none"], list[EvidenceItem]]:
    """地域维度评分 · 候选 geo 字段 vs RM 辖区."""
    cand_geo = (candidate.get("geo") or candidate.get("region") or "").strip()
    if not cand_geo:
        return "none", []

    rm = (rm_region or "").strip()
    if not rm:
        return "low", [{
            "source": "config",
            "paragraph_id": "rm-region-missing",
            "quote": f"RM 辖区未配置 · 候选 geo {cand_geo} 给基础分 (low)",
            "confidence": 0.5,
        }]

    if cand_geo == rm or cand_geo in rm or rm in cand_geo:
        tier: Literal["high", "medium", "low", "none"] = "high"
        quote = f"候选 geo {cand_geo!r} 与 RM 辖区 {rm!r} 完全匹配"
    else:
        tier = "medium"
        quote = f"候选 geo {cand_geo!r} 不在 RM 辖区 {rm!r} · 但同省/同区域可触达"

    return tier, [{
        "source": "rm_config",
        "paragraph_id": "rm-region",
        "quote": quote,
        "confidence": 0.90,
    }]


def _score_signal(
    candidate: dict[str, Any],
) -> tuple[Literal["high", "medium", "low", "none"], list[EvidenceItem]]:
    """外部信号维度评分 · 候选已抓取的招标/招聘/项目/政策信号数."""
    signals = candidate.get("signals") or []
    if not signals:
        return "none", []

    n = len(signals)
    if n >= 4:
        tier: Literal["high", "medium", "low", "none"] = "high"
    elif n >= 2:
        tier = "medium"
    else:
        tier = "low"

    evidence: list[EvidenceItem] = []
    for sig in signals[:3]:
        evidence.append({
            "source": sig.get("source", "tavily"),
            "source_url": sig.get("url", ""),
            "paragraph_id": sig.get("signal_type", "unknown"),
            "quote": (sig.get("title") or sig.get("snippet") or "")[:200],
            "fetched_at": sig.get("fetched_at", ""),
            "confidence": 0.70,
        })
    return tier, evidence


def score_candidate(
    candidate: dict[str, Any],
    internal_kb_companies: list[dict[str, Any]] | None = None,
    rm_region: str = "",
) -> CandidateEvidenceScore:
    """对单个候选企业打分 0-100 + 输出证据链.

    Args:
        candidate: 候选企业 dict · 必含 Q-041 4 字段 (industry/geo/scale/similarity) +
                   可选 signals: list[dict] (外部抓取的招标/招聘/项目/政策信号)
        internal_kb_companies: 内源已成交客户 KB list (default empty · 实际从 data/channel_kb/ 加载)
        rm_region: RM 辖区 (e.g. "华东" / "上海")

    Returns:
        CandidateEvidenceScore · 含 total_score (0-100) + 4 维度详情 + evidence_chain.

    确定性: 全 Python 计算 · 不调 LLM (per §3.1).
    """
    kb = internal_kb_companies or []

    industry_tier, industry_ev = _score_industry(candidate, kb)
    scale_tier, scale_ev = _score_scale(candidate, kb)
    region_tier, region_ev = _score_region(candidate, rm_region)
    signal_tier, signal_ev = _score_signal(candidate)

    dimensions: list[DimensionScore] = []
    total_weighted = 0.0
    full_evidence: list[EvidenceItem] = []

    for dim_name, tier, ev in [
        ("industry", industry_tier, industry_ev),
        ("scale", scale_tier, scale_ev),
        ("region", region_tier, region_ev),
        ("signal", signal_tier, signal_ev),
    ]:
        base = TIER_SCORE[tier]
        weight = EVIDENCE_WEIGHTS[dim_name]
        weighted = base * weight
        total_weighted += weighted
        dimensions.append({
            "dimension": dim_name,  # type: ignore[typeddict-item]
            "tier": tier,
            "base_score": base,
            "weight": weight,
            "weighted": weighted,
            "evidence": ev,
        })
        full_evidence.extend(ev)

    total_score = max(0, min(100, int(round(total_weighted))))

    return {
        "candidate_id": candidate.get("candidate_id", candidate.get("id", "unknown")),
        "candidate_name": candidate.get("name", "unknown"),
        "total_score": total_score,
        "dimensions": dimensions,
        "evidence_chain": full_evidence,
        "metadata": {
            "industry":    candidate.get("industry", ""),
            "geo":         candidate.get("geo") or candidate.get("region", ""),
            "scale":       candidate.get("scale", ""),
            "similarity":  candidate.get("similarity", 0.0),
        },
    }


def score_candidates(
    candidates: list[dict[str, Any]],
    internal_kb_companies: list[dict[str, Any]] | None = None,
    rm_region: str = "",
) -> list[CandidateEvidenceScore]:
    """批量评分 + 按 total_score 降序排."""
    out = [
        score_candidate(c, internal_kb_companies, rm_region)
        for c in candidates
    ]
    out.sort(key=lambda x: x["total_score"], reverse=True)
    return out
