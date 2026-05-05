# -*- coding: utf-8 -*-
"""Agent4 Alert · Signal quality scoring (BE5 · Phase B Sprint 2 · 2026-05-04).

三件套确定性计算 · 不调 LLM · 给 evidence_pipeline / scan_engine 消费:

1. freshness_score(observed_at, ref=None) -> int
   日衰减: 当天=100 · -10/day · clamp [0, 100]

2. lookup_source_confidence(source_type | source_label) -> str
   3 档枚举 high / med / low · 表落 data/mock/workspace/alert/source_confidence.json

3. classify_signal_kind(rule_id, route=None) -> str
   细粒度信号 kind (legal/financial/business/industry/related_party/internal_policy)
   from rule_id prefix (LAW/FIN/BIZ/IND/REL/POL · per cross_matcher rule taxonomy)

4. compute_evidence_confidence(freshness, source_confidence) -> float
   合并 0-1 confidence · evidence_pipeline.py EvidenceItem.confidence 用

设计:
- 100% 确定性 (CLAUDE.md §3.1) · 无 LLM 现场算
- 100% 结构推断 (CLAUDE.md §12) · 不依赖关键词黑名单
- source_confidence 表是数据非代码 · 加新源走表更新 · 不改逻辑
- 与 §3.7 active rules 兼容 · 不破 Q-040/Q-041

为什么有这层 (BE5 价值):
- 现 evidence_pipeline.py 静态写 confidence=0.75/0.5 (第 56/67 行) · 不区分时效与源
- signal_diversity baseline=0.0 因为 trigger_reasons 永远 1 个 enum (test_trigger_reasons.py:47)
- 把 rule_id prefix → kind 暴露成 signal_kinds 字段 (HitItem.extras) · 评估 ≥ 2 自然到位
- freshness × source_confidence 让旧/低置信信号自然降权 · 给客户经理 actionable 排序
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_CONFIDENCE_PATH = (
    PROJECT_ROOT / "data" / "mock" / "workspace" / "alert" / "source_confidence.json"
)


# ---------------------------------------------------------------------------
# 1. Freshness score
# ---------------------------------------------------------------------------


_FRESHNESS_DECAY_PER_DAY: int = 10  # -10/day
_FRESHNESS_MAX: int = 100
_FRESHNESS_MIN: int = 0


def _coerce_to_date(value: Any) -> date | None:
    """容忍多种入参形态 → date · 失败返 None."""
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
        # ISO 8601 first
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        # 常见中文 / 简化格式 2024-01-31, 2024/01/31, 20240131
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(s[: len(fmt) + 4 if fmt == "%Y" else len(s)], fmt).date()
            except ValueError:
                continue
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
        >>> freshness_score(date(2026, 5, 4), ref=date(2026, 5, 4))
        100
        >>> freshness_score(date(2026, 5, 1), ref=date(2026, 5, 4))
        70
        >>> freshness_score("2026-04-20", ref=date(2026, 5, 4))
        0
        >>> freshness_score(None)
        0
        >>> freshness_score("2026-05-10", ref=date(2026, 5, 4))  # future date
        100
    """
    obs = _coerce_to_date(observed_at)
    if obs is None:
        return _FRESHNESS_MIN

    ref_date = _coerce_to_date(ref) or datetime.now().date()
    delta_days = (ref_date - obs).days

    if delta_days <= 0:
        # 未来 (clock skew / future-dated event) · clamp 当天
        return _FRESHNESS_MAX

    raw = _FRESHNESS_MAX - _FRESHNESS_DECAY_PER_DAY * delta_days
    return max(_FRESHNESS_MIN, min(_FRESHNESS_MAX, raw))


# ---------------------------------------------------------------------------
# 2. Source confidence lookup
# ---------------------------------------------------------------------------


SourceConfidence = Literal["high", "med", "low"]
_DEFAULT_CONFIDENCE: SourceConfidence = "med"


def _load_source_confidence_table() -> dict[str, dict[str, Any]]:
    """读 source_confidence.json · 失败返空表 (silent fail · 调用走 default 'med')."""
    try:
        raw = SOURCE_CONFIDENCE_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        logger.warning("source_confidence.json load failed (%s) · fallback to defaults", e)
        return {}

    table: dict[str, dict[str, Any]] = {}
    entries = data.get("entries", []) if isinstance(data, dict) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key", "")).strip().lower()
        if not key:
            continue
        table[key] = entry
    return table


@lru_cache(maxsize=1)
def _cached_table() -> dict[str, dict[str, Any]]:
    return _load_source_confidence_table()


def reload_source_confidence_table() -> None:
    """测试用 · 显式 invalidate cache."""
    _cached_table.cache_clear()


def _normalize_lookup_key(value: str) -> str:
    """清洗输入用于查表 · lower + 去空白."""
    return re.sub(r"\s+", "", value.strip().lower())


def lookup_source_confidence(
    source_type: str = "",
    source_label: str = "",
    source_url: str = "",
) -> SourceConfidence:
    """3 档枚举 high / med / low · 优先级 source_type > source_label > source_url.

    Args:
        source_type:  域名 type (e.g. "gov", "media", "social", "court", "corp_registry")
        source_label: 人话 label (e.g. "央行", "财新", "微博")
        source_url:   URL 全文 (从 URL 域名兜底匹配 · e.g. ".gov.cn" → high)

    Returns:
        Literal["high", "med", "low"] · 任意输入查不到 → "med" (default)

    示例:
        lookup_source_confidence(source_type="gov") -> "high"
        lookup_source_confidence(source_label="央行") -> "high"
        lookup_source_confidence(source_url="http://www.pbc.gov.cn/...") -> "high"
        lookup_source_confidence("") -> "med"  # default
    """
    table = _cached_table()
    if not table:
        return _DEFAULT_CONFIDENCE

    candidates: list[str] = []
    if source_type:
        candidates.append(_normalize_lookup_key(source_type))
    if source_label:
        candidates.append(_normalize_lookup_key(source_label))

    for key in candidates:
        if key and key in table:
            level = str(table[key].get("confidence", _DEFAULT_CONFIDENCE)).lower()
            if level in ("high", "med", "low"):
                return level  # type: ignore[return-value]

    if source_url:
        url_lower = source_url.lower()
        for key, entry in table.items():
            domain_hints = entry.get("domain_hints") or []
            for hint in domain_hints:
                if isinstance(hint, str) and hint and hint.lower() in url_lower:
                    level = str(entry.get("confidence", _DEFAULT_CONFIDENCE)).lower()
                    if level in ("high", "med", "low"):
                        return level  # type: ignore[return-value]

    return _DEFAULT_CONFIDENCE


# ---------------------------------------------------------------------------
# 3. Signal kind classifier (rule_id prefix → fine-grained kind)
# ---------------------------------------------------------------------------


SIGNAL_KIND_LEGAL = "legal_signal"          # LAW-* (court records / judicial)
SIGNAL_KIND_FINANCIAL = "financial_signal"  # FIN-* (revenue/profit/leverage)
SIGNAL_KIND_BUSINESS = "business_signal"    # BIZ-* (corp changes / cessation)
SIGNAL_KIND_INDUSTRY = "industry_signal"    # IND-* (industry trends)
SIGNAL_KIND_RELATED = "related_party_signal"  # REL-* (related party)
SIGNAL_KIND_INTERNAL = "internal_policy"    # POL-* (internal rule)
SIGNAL_KIND_OTHER = "other_signal"          # unmapped prefix · 兜底

_PREFIX_TO_KIND: dict[str, str] = {
    "LAW": SIGNAL_KIND_LEGAL,
    "FIN": SIGNAL_KIND_FINANCIAL,
    "BIZ": SIGNAL_KIND_BUSINESS,
    "IND": SIGNAL_KIND_INDUSTRY,
    "REL": SIGNAL_KIND_RELATED,
    "POL": SIGNAL_KIND_INTERNAL,
}

ALL_SIGNAL_KINDS: tuple[str, ...] = (
    SIGNAL_KIND_LEGAL,
    SIGNAL_KIND_FINANCIAL,
    SIGNAL_KIND_BUSINESS,
    SIGNAL_KIND_INDUSTRY,
    SIGNAL_KIND_RELATED,
    SIGNAL_KIND_INTERNAL,
    SIGNAL_KIND_OTHER,
)


def classify_signal_kind(rule_id: str, route: str | None = None) -> str:
    """从 rule_id 前缀推断 fine-grained signal kind.

    Args:
        rule_id: e.g. "LAW-002" / "FIN-001" / "POL-001"
        route:   "external" / "internal" · 用作 fallback 给无前缀 / 异常 rule_id

    Returns:
        SIGNAL_KIND_* 之一 · unmapped → SIGNAL_KIND_OTHER (or _INTERNAL if route="internal")

    设计:
        - 100% 结构推断 · 不读关键词 (CLAUDE.md §12)
        - 与 cross_matcher rule taxonomy 1:1 · LAW/FIN/BIZ/IND/REL/POL
        - 暴露在 HitItem.extras["signal_kinds"] · 用于 signal_diversity 评估
    """
    rid = (rule_id or "").strip().upper()
    prefix = rid.split("-", 1)[0] if "-" in rid else rid[:3]
    kind = _PREFIX_TO_KIND.get(prefix)
    if kind:
        return kind
    if route == "internal":
        return SIGNAL_KIND_INTERNAL
    return SIGNAL_KIND_OTHER


def infer_signal_kinds(hit_data: list[dict[str, Any]]) -> list[str]:
    """对一批 hit dict 抽 unique signal kinds (deterministic order).

    Args:
        hit_data: list of {"rule_id": str, "route": Optional[str]} dict
                  (容忍 RuleHit obj 通过 .__dict__ 也能跑 · 但建议提前转 dict)

    Returns:
        list[str] · unique kinds in deterministic order (per ALL_SIGNAL_KINDS 顺序)
    """
    seen: set[str] = set()
    for h in hit_data:
        if isinstance(h, dict):
            rid = str(h.get("rule_id", ""))
            route = h.get("route")
        else:
            rid = str(getattr(h, "rule_id", ""))
            route = getattr(h, "route", None)
        kind = classify_signal_kind(rid, route)
        seen.add(kind)
    # deterministic order per ALL_SIGNAL_KINDS
    return [k for k in ALL_SIGNAL_KINDS if k in seen]


# ---------------------------------------------------------------------------
# 4. Combined evidence confidence
# ---------------------------------------------------------------------------


_CONFIDENCE_BASE: dict[str, float] = {
    "high": 0.95,
    "med": 0.70,
    "low": 0.45,
}


def compute_evidence_confidence(
    freshness: int,
    source_confidence: SourceConfidence | str,
    *,
    floor: float = 0.10,
) -> float:
    """合并 freshness × source_confidence → 0-1 evidence.confidence.

    Args:
        freshness:         freshness_score 输出 · 0-100
        source_confidence: high / med / low · 不识别按 med 处理
        floor:             最低 confidence (避免 0 · 维持下游 evidence 必有)

    Returns:
        float [floor, 1.0] · = base[level] × (0.5 + freshness/200)
        - source high + freshness 100  → 0.95
        - source high + freshness 0    → 0.475
        - source low  + freshness 100  → 0.45
        - source low  + freshness 0    → 0.225 → max(floor, 0.225)

    设计:
        - freshness 占 50% 权 · 旧信号自动降权 (per BE5 spec)
        - source 占 50% 权 · gov 永远高于社媒 (per BE5 spec)
        - floor 兜底 · 避免完全 0 信号被吃掉 → 还有理由进入 trigger_reasons
    """
    level_str = str(source_confidence or _DEFAULT_CONFIDENCE).strip().lower()
    base = _CONFIDENCE_BASE.get(level_str, _CONFIDENCE_BASE[_DEFAULT_CONFIDENCE])
    f = max(_FRESHNESS_MIN, min(_FRESHNESS_MAX, int(freshness)))
    multiplier = 0.5 + (f / 200.0)  # 0.5 ~ 1.0
    raw = base * multiplier
    return max(floor, min(1.0, round(raw, 4)))


# ---------------------------------------------------------------------------
# 5. Public bundle helper · evidence_pipeline.py 一站消费入口
# ---------------------------------------------------------------------------


def quality_bundle(
    *,
    rule_id: str = "",
    route: str | None = None,
    observed_at: Any = None,
    source_type: str = "",
    source_label: str = "",
    source_url: str = "",
    ref_date: Any = None,
) -> dict[str, Any]:
    """一站算 freshness + source_confidence + signal_kind + confidence.

    Returns dict (snake_case · evidence_pipeline 直接 spread 到 EvidenceItem.meta):
        {
          "freshness_score": int 0-100,
          "source_confidence": "high" | "med" | "low",
          "signal_kind": str,
          "confidence": float 0-1,
        }

    用法:
        bundle = quality_bundle(
            rule_id="LAW-002",
            route="external",
            observed_at=hit.evidence_meta.get("published_at"),
            source_type="court",
            source_url=hit.evidence_url,
        )
        EvidenceItem(... confidence=bundle["confidence"], meta=bundle)
    """
    freshness = freshness_score(observed_at, ref=ref_date)
    source_conf = lookup_source_confidence(
        source_type=source_type,
        source_label=source_label,
        source_url=source_url,
    )
    kind = classify_signal_kind(rule_id, route)
    conf = compute_evidence_confidence(freshness, source_conf)
    return {
        "freshness_score": freshness,
        "source_confidence": source_conf,
        "signal_kind": kind,
        "confidence": conf,
    }


__all__ = [
    "ALL_SIGNAL_KINDS",
    "SIGNAL_KIND_BUSINESS",
    "SIGNAL_KIND_FINANCIAL",
    "SIGNAL_KIND_INDUSTRY",
    "SIGNAL_KIND_INTERNAL",
    "SIGNAL_KIND_LEGAL",
    "SIGNAL_KIND_OTHER",
    "SIGNAL_KIND_RELATED",
    "SOURCE_CONFIDENCE_PATH",
    "SourceConfidence",
    "classify_signal_kind",
    "compute_evidence_confidence",
    "freshness_score",
    "infer_signal_kinds",
    "lookup_source_confidence",
    "quality_bundle",
    "reload_source_confidence_table",
]
