# -*- coding: utf-8 -*-
"""shared.evidence.confidence_policy · 跨 Agent confidence 数学层 (B.3.4 P0-R1 · 2026-05-11)

per docs/contracts/shared-evidence-confidence-policy-v1.0.md v1.0

设计 (per CLAUDE.md §3.1 + §3.5.1 + §3.7.7 + R7 verdict):
- 抽 agent_alert/signal_quality.py 纯数学部分到 shared (freshness + confidence 公式)
- alert-specific taxonomy (LAW/FIN/BIZ rule prefix · evidence origin classifier ·
  source_confidence.json 表) 留 agent_alert/signal_quality.py local
- 确定性计算 · 100% 不调 LLM
- flag-gate 渐进 opt-in · 默认 OFF · 5 Agent 各自决定何时切

公共常量 + 函数:
- FRESHNESS_DECAY_PER_DAY / FRESHNESS_MAX / FRESHNESS_MIN
- DEFAULT_CONFIDENCE_LEVEL / DEFAULT_FLOOR / CONFIDENCE_BASE
- freshness_score(observed_at, ref=None) -> int [0, 100]
- compute_evidence_confidence(freshness, level, *, floor) -> float [floor, 1.0]
- quality_bundle(observed_at, source_confidence_level, ref_date) -> dict
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

__all__ = [
    "CONFIDENCE_BASE",
    "DEFAULT_CONFIDENCE_LEVEL",
    "DEFAULT_FLOOR",
    "FRESHNESS_DECAY_PER_DAY",
    "FRESHNESS_MAX",
    "FRESHNESS_MIN",
    "SourceConfidence",
    "compute_evidence_confidence",
    "freshness_score",
    "quality_bundle",
]


# ---------------------------------------------------------------------------
# 公共常量 (跨 Agent invariant)
# ---------------------------------------------------------------------------

SourceConfidence = Literal["high", "med", "low"]

FRESHNESS_DECAY_PER_DAY: int = 10  # -10/day
FRESHNESS_MAX: int = 100           # 当天 = 100
FRESHNESS_MIN: int = 0             # ≥ 10 天前 = 0

DEFAULT_CONFIDENCE_LEVEL: SourceConfidence = "med"
DEFAULT_FLOOR: float = 0.10        # 最低 confidence (避免 0 信号被吃掉)

CONFIDENCE_BASE: dict[str, float] = {
    "high": 0.95,
    "med": 0.70,
    "low": 0.45,
}


# ---------------------------------------------------------------------------
# 1. Freshness score (日衰减 · 0-100)
# ---------------------------------------------------------------------------


def _coerce_to_date(value: Any) -> date | None:
    """容忍多种入参形态 → date · 失败返 None.

    支持: date / datetime / int|float (epoch) / ISO 8601 str / 简化日期 str.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value)).date()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m"):
            try:
                return datetime.strptime(s[: len(fmt) + 4], fmt).date()
            except ValueError:
                continue
        try:
            return datetime.strptime(s[:4], "%Y").date()
        except ValueError:
            return None
    return None


def freshness_score(observed_at: Any, ref: Any = None) -> int:
    """日衰减 freshness · 0-100 · 当天=100 · -10/day · clamp [0, 100].

    Args:
        observed_at: 信号产生时间 (date / datetime / ISO str / epoch / None)
        ref:         参考"今天" · 默认 datetime.now().date()

    Returns:
        int [0, 100] · 0 = ≥ 10 天前 · 100 = 当天 · 不可解析 = 0

    Examples:
        >>> from datetime import date
        >>> freshness_score(date(2026, 5, 11), ref=date(2026, 5, 11))
        100
        >>> freshness_score(date(2026, 5, 1), ref=date(2026, 5, 11))
        0
        >>> freshness_score("2026-05-06", ref=date(2026, 5, 11))
        50
        >>> freshness_score(None)
        0
    """
    obs = _coerce_to_date(observed_at)
    if obs is None:
        return FRESHNESS_MIN

    ref_date = _coerce_to_date(ref) or datetime.now().date()
    delta_days = (ref_date - obs).days

    if delta_days <= 0:
        return FRESHNESS_MAX

    raw = FRESHNESS_MAX - FRESHNESS_DECAY_PER_DAY * delta_days
    return max(FRESHNESS_MIN, min(FRESHNESS_MAX, raw))


# ---------------------------------------------------------------------------
# 2. Combined evidence confidence (freshness × source_confidence → 0-1)
# ---------------------------------------------------------------------------


def compute_evidence_confidence(
    freshness: int,
    source_confidence: SourceConfidence | str,
    *,
    floor: float = DEFAULT_FLOOR,
) -> float:
    """合并 freshness × source_confidence → [floor, 1.0] confidence.

    公式: base[level] × (0.5 + freshness/200) · clamp [floor, 1.0]
    - high + freshness 100 → 0.95 × 1.0 = 0.95
    - high + freshness 0   → 0.95 × 0.5 = 0.475
    - med  + freshness 50  → 0.70 × 0.75 = 0.525
    - low  + freshness 100 → 0.45 × 1.0 = 0.45
    - low  + freshness 0   → 0.45 × 0.5 = 0.225 → max(floor=0.10, 0.225)

    Args:
        freshness:         freshness_score 输出 · 0-100 (越界自动 clamp)
        source_confidence: high / med / low · 不识别按 med 处理
        floor:             最低 confidence · 默认 0.10

    Returns:
        float [floor, 1.0]
    """
    level_str = str(source_confidence or DEFAULT_CONFIDENCE_LEVEL).strip().lower()
    base = CONFIDENCE_BASE.get(level_str, CONFIDENCE_BASE[DEFAULT_CONFIDENCE_LEVEL])
    f = max(FRESHNESS_MIN, min(FRESHNESS_MAX, int(freshness)))
    multiplier = 0.5 + (f / 200.0)
    raw = base * multiplier
    return max(floor, min(1.0, round(raw, 4)))


# ---------------------------------------------------------------------------
# 3. Quality bundle · 一站算 freshness + confidence (纯数学版 · 无 alert taxonomy)
# ---------------------------------------------------------------------------


def quality_bundle(
    *,
    observed_at: Any = None,
    source_confidence_level: SourceConfidence | str = DEFAULT_CONFIDENCE_LEVEL,
    ref_date: Any = None,
) -> dict[str, Any]:
    """一站算 freshness + confidence · 不带 alert-specific taxonomy.

    Args:
        observed_at:             信号时间 (date / str / epoch / None)
        source_confidence_level: high / med / low (调用方查表后传入)
        ref_date:                参考"今天" · 默认 today

    Returns:
        {
          "freshness_score": int 0-100,
          "source_confidence": "high" | "med" | "low" (or unrecognized as-is),
          "confidence": float [floor, 1.0],
        }

    注:
        - 不算 signal_kind (alert 才有 taxonomy · agent_alert/signal_quality.py)
        - 不查 source_confidence (各 Agent 表路径不同 · adapter 自己查后传 level)
        - 5 Agent 想 opt-in 调本函数 · 用 flag-gate (per CLAUDE.md §3.7.7)
    """
    f = freshness_score(observed_at, ref=ref_date)
    c = compute_evidence_confidence(f, source_confidence_level)
    level_str = str(source_confidence_level or DEFAULT_CONFIDENCE_LEVEL).strip().lower()
    return {
        "freshness_score": f,
        "source_confidence": level_str,
        "confidence": c,
    }
