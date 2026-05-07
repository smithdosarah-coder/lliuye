# -*- coding: utf-8 -*-
"""agent_channel.signal_density — Q-054 第 5 维度 candidate metadata.

候选企业近 90 天动态信号密度 0-1 分 · per Q-054 R3 v2 P0 mesh + CLAUDE.md §3.1 / §3.5.1 #6.

3 层算法:
  L1 freshness (确定性 · Python): signal_type → ClaimType → recency_weight
  L2 salience  (概率性 · LLM 可选): 走 shared.llm_caller · LLM 仅打 0-1 分
  L3 aggregate (确定性 · Python): clamp01(sum(L1 * L2) / SIGNAL_DENSITY_NORMALIZATION_DIVISOR)

硬线:
  - LLM 仅打 0-1 显著性 · 不算频次 (per §3.1)
  - LLM 越界 → 单 signal salience=0 + reason="llm_out_of_range"
                + 冻结 prompt 版本写 evidence/llm_out_of_range_<date>.md (Q-054 risk)
  - LLM 不可达 → static prior fallback + reason="llm_unavailable" · 不阻整流
  - 不破 Q-041 4 字段 · 仅 additive 加 signal_density / signal_density_reason

字段填不了 → signal_density=0.0 + signal_density_reason="未能自动填写: <cause>"

使用:
    from agent_channel.signal_density import compute_signal_density

    result = compute_signal_density(item, llm=llm_caller_or_none)
    # → {"signal_density": 0.42, "signal_density_reason": ""}
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from shared.evidence_freshness import (
    ClaimType,
    compute_freshness_days,
    compute_recency_weight,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 模块级常量
# ============================================================================

# 归一化分母 · 3 个满分信号 (recency_w=1.0 × salience=1.0) 即 signal_density=1.0
# 业务依据: 1 条满分信号 ≈ 0.33 (远未到首抓阈值) · 3 条满分 = 客户经理首抓信号
SIGNAL_DENSITY_NORMALIZATION_DIVISOR: float = 3.0

# 90 天硬窗口 (per Q-054 · align freshness SLA · 窗口外 recency_weight 极低)
WINDOW_DAYS: int = 90

# signal_type → ClaimType (per shared.evidence_freshness.FRESHNESS_SLA_DAYS)
# 10 种 signal_type 来自 agent_channel.realtime_stream._SIGNAL_TYPE_TO_KEY
SIGNAL_TYPE_TO_CLAIM: dict[str, ClaimType] = {
    "biz":         ClaimType.BUSINESS_CHANGE,  # 工商变更 730d
    "bidding":     ClaimType.BID,              # 招投标 90d
    "growth":      ClaimType.FUNDING,          # 扩产 / 融资 365d
    "legal":       ClaimType.LEGAL,            # 司法 365d
    "tax":         ClaimType.FINANCIAL,        # 税务 120d
    "recruit":     ClaimType.RECRUIT,          # 招聘 60d
    "news":        ClaimType.NEWS,             # 新闻 180d
    "recognition": ClaimType.NEWS,             # 专精特新名单 → 资讯 180d
    "award":       ClaimType.NEWS,             # 获奖 180d
    "tech":        ClaimType.NEWS,             # 技术突破 180d
    "social":      ClaimType.NEWS,             # 社交舆情 180d
}

# 静态 salience prior 表 · LLM 不可达时 fallback (per §3.1 确定性兜底)
# 业务依据: 客户经理"现在该打哪通电话"优先级 ·
#   biz 股权 / 法人 / 注资 = 决策含金量最高 · social 噪声多
STATIC_SALIENCE_PRIOR: dict[str, float] = {
    "biz":         0.85,
    "bidding":     0.70,
    "growth":      0.65,
    "legal":       0.55,
    "tax":         0.50,
    "tech":        0.45,
    "recognition": 0.45,
    "award":       0.40,
    "recruit":     0.35,
    "news":        0.30,
    "social":      0.20,
}

# 未识别 signal_type 的兜底 salience
UNKNOWN_SALIENCE: float = 0.30


# ============================================================================
# 公开 API
# ============================================================================

def signal_type_to_claim_type(signal_type: str) -> ClaimType:
    """signal_type → ClaimType · 未识别返 GENERIC (180d SLA · per shared.evidence_freshness)."""
    return SIGNAL_TYPE_TO_CLAIM.get((signal_type or "").strip(), ClaimType.GENERIC)


def compute_signal_salience(
    signal: dict,
    *,
    llm: Optional[Any] = None,
) -> tuple[float, str]:
    """单 signal 的 salience score 0-1.

    优先 LLM (走 shared.llm_caller · step 2 接) · fallback static prior.

    Args:
        signal: dict with signal_type / signal_title / signal_detail
        llm:    LLMCaller 实例 or None · None 直 fallback static prior

    Returns:
        (salience ∈ [0, 1], reason)
        reason 非空时表示走了 fallback 路径
        (e.g. "llm_unavailable" / "llm_out_of_range" / "llm_invalid_response")
    """
    # Step 2 接 LLM 路径 · 当前 step 1 直 fallback static prior
    if llm is None:
        return _static_salience(signal), ""
    # LLM 路径在 step 2 commit 加 · 这里 placeholder 暂走 static
    return _static_salience(signal), ""


def _static_salience(signal: dict) -> float:
    """静态 prior 表 · 按 signal_type 返 prior 值 · 越界 clamp 到 [0, 1]."""
    stype = (signal.get("signal_type") or "").strip()
    val = STATIC_SALIENCE_PRIOR.get(stype, UNKNOWN_SALIENCE)
    return _clamp01(val)


def _clamp01(x: float) -> float:
    """clamp [0, 1] · 防 prior 表 / LLM 误差越界."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def compute_signal_density(
    item: dict,
    *,
    llm: Optional[Any] = None,
    reference_date: Optional[datetime] = None,
) -> dict:
    """主入口 · 单候选企业 signal_density 0-1.

    Args:
        item: enriched candidate dict · item["signals"] = list of signal dict
              每 signal 含 signal_type / signal_date (YYYY-MM-DD) / signal_title / signal_detail
        llm:  LLMCaller 实例 or None · None → 静态 prior fallback
        reference_date: datetime · 测试可注入固定时间 · 默认 now

    Returns:
        {
            "signal_density": float ∈ [0, 1],  (4 位精度)
            "signal_density_reason": str (空 = 正常 · 非空 = 降级原因合并),
        }

    设计:
      L1: per-signal recency_weight (Python · per shared.evidence_freshness)
      L2: per-signal salience (LLM or static prior · step 2 接 LLM)
      L3: clamp01(sum(L1 × L2) / SIGNAL_DENSITY_NORMALIZATION_DIVISOR)

    Edge cases:
      - signals 空 → 0.0 + reason="未能自动填写: no_signals"
      - 全 signal 缺 signal_date → recency_w=0 → density=0 + reason="missing_dates"
      - LLM 不可达 / 越界 / 异常 → 单 signal fallback static + reason 合并
    """
    signals = item.get("signals") or []
    if not signals:
        return {
            "signal_density": 0.0,
            "signal_density_reason": "未能自动填写: no_signals",
        }

    reasons: list[str] = []
    total_weight: float = 0.0
    valid_dates = 0

    for sig in signals:
        # L1: freshness recency_weight (确定性 · Python)
        evidence_date = sig.get("signal_date") or sig.get("evidence_date") or ""
        fd = compute_freshness_days(evidence_date, reference_date=reference_date)
        if fd is not None:
            valid_dates += 1
        recency_w = compute_recency_weight(fd)

        # L2: salience (概率性 · 当前 step 1 仅 static · step 2 加 LLM)
        salience, reason = compute_signal_salience(sig, llm=llm)
        if reason:
            reasons.append(reason)

        total_weight += recency_w * salience

    density = min(1.0, total_weight / SIGNAL_DENSITY_NORMALIZATION_DIVISOR)
    density = round(_clamp01(density), 4)

    if valid_dates == 0:
        # 所有 signal 缺 signal_date · density 不可信 · 标降级
        return {
            "signal_density": 0.0,
            "signal_density_reason": "未能自动填写: missing_dates",
        }

    # reason 合并 · 保留 evidence (不去重 · 多 LLM 失败 = 多 evidence)
    reason_str = ", ".join(reasons) if reasons else ""
    return {
        "signal_density": density,
        "signal_density_reason": reason_str,
    }


__all__ = [
    "SIGNAL_DENSITY_NORMALIZATION_DIVISOR",
    "WINDOW_DAYS",
    "SIGNAL_TYPE_TO_CLAIM",
    "STATIC_SALIENCE_PRIOR",
    "UNKNOWN_SALIENCE",
    "signal_type_to_claim_type",
    "compute_signal_salience",
    "compute_signal_density",
]
