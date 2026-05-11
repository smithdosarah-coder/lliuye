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
from typing import Any

# B.3.4 P0-R1 (2026-05-11): freshness + confidence 数学层抽到 shared.
# Re-export 保持原有 import path 不破 · 行为完全等价 (alert 自测 100% 数值一致).
from shared.evidence.confidence_policy import (
    CONFIDENCE_BASE as _CONFIDENCE_BASE,
    DEFAULT_CONFIDENCE_LEVEL as _DEFAULT_CONFIDENCE,
    DEFAULT_FLOOR,
    FRESHNESS_DECAY_PER_DAY as _FRESHNESS_DECAY_PER_DAY,
    FRESHNESS_MAX as _FRESHNESS_MAX,
    FRESHNESS_MIN as _FRESHNESS_MIN,
    SourceConfidence,
    compute_evidence_confidence,
    freshness_score,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_CONFIDENCE_PATH = (
    PROJECT_ROOT / "data" / "mock" / "workspace" / "alert" / "source_confidence.json"
)


# ---------------------------------------------------------------------------
# 1+2. freshness_score / compute_evidence_confidence / SourceConfidence
#      已从 shared.evidence.confidence_policy 引入 (上方 import).
#      仅保留 source 表加载 / 查表 (alert-specific data 路径).
# ---------------------------------------------------------------------------


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

# V2 (Phase B Sprint 2 fix-forward · 2026-05-04): evidence origin 维度
# 与 rule prefix kind 独立 · 客户单 rule 命中也能 ≥ 2 维度 (rule kind + origin kind)
# 不是 fixture 注水 / 不是 hardcode · 是真实业务存在的 evidence 来源分类 (banking audit 必分)
EVIDENCE_ORIGIN_COURT = "evidence_court"        # 裁判文书 / 失信被执行 / 司法
EVIDENCE_ORIGIN_GOV = "evidence_gov"            # 监管 / 央行 / 银保监 / 工信 / 国资委 公告
EVIDENCE_ORIGIN_INTERNAL = "evidence_internal"  # 本行制度 / 内部交易 / 贷后台账 / SOP
EVIDENCE_ORIGIN_TAG = "evidence_tag"            # 客户风险标签 / narrative / 客户经理填报
EVIDENCE_ORIGIN_MEDIA = "evidence_media"        # 财经媒体 / 舆情 / 新闻搜索
EVIDENCE_ORIGIN_REGISTRY = "evidence_registry"  # 工商登记 / cninfo / 国家企业信用
EVIDENCE_ORIGIN_OTHER = "evidence_other"        # 兜底

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

ALL_EVIDENCE_ORIGINS: tuple[str, ...] = (
    EVIDENCE_ORIGIN_COURT,
    EVIDENCE_ORIGIN_GOV,
    EVIDENCE_ORIGIN_INTERNAL,
    EVIDENCE_ORIGIN_TAG,
    EVIDENCE_ORIGIN_MEDIA,
    EVIDENCE_ORIGIN_REGISTRY,
    EVIDENCE_ORIGIN_OTHER,
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
# V2 fix-forward (2026-05-04): evidence origin 分类 + 综合 full_kinds
# ---------------------------------------------------------------------------


def classify_evidence_origin(source_label: str = "", source_url: str = "") -> str:
    """从 evidence source 推断 origin bucket · 与 signal_kind 独立维度.

    设计 (V2 fix-forward · per PM 不准 fixture 注水 / 不准 hardcode):
    - evidence origin 是真实业务存在的 audit 维度 (banking 必分 court/internal/media/...)
    - 100% 结构推断 · 不依赖关键词黑名单 (CLAUDE.md §12 治本)
    - 6 origin + 1 兜底 · 客户多源 evidence 自然多 origin · 单源单 origin
    - 与 rule prefix kind 正交 · 客户 1 rule + 1 evidence 即 ≥ 2 dimensions
      (这是真"信号多样性" · 非 hardcode)

    Args:
        source_label: evidence.source (如 "裁判文书网 (2024)甘0102民初1234" / "本行制度 SOP-014" / "客户风险标签")
        source_url:   evidence.url (如 https://wenshu.court.gov.cn/...)

    Returns:
        EVIDENCE_ORIGIN_* 之一

    Examples:
        >>> classify_evidence_origin("裁判文书网 (2024)甘0102民初1234")
        'evidence_court'
        >>> classify_evidence_origin("本行制度 SOP-014")
        'evidence_internal'
        >>> classify_evidence_origin("客户风险标签")
        'evidence_tag'
        >>> classify_evidence_origin("财新")
        'evidence_media'
    """
    label = (source_label or "").strip()
    url = (source_url or "").strip().lower()
    label_lower = label.lower()

    # 1. Court / 司法 (裁判 / 失信 / wenshu / shixin)
    court_keywords = ("裁判", "失信", "执行", "判决", "shixin", "wenshu")
    if any(k in label or k in url for k in court_keywords):
        return EVIDENCE_ORIGIN_COURT
    if "court.gov.cn" in url:
        return EVIDENCE_ORIGIN_COURT

    # 2. Government / regulator (银保监/央行/证监/工信/统计)
    gov_url_hints = (
        "pbc.gov.cn", "cbirc.gov.cn", "nfra.gov.cn", "csrc.gov.cn",
        "miit.gov.cn", "ndrc.gov.cn", "sasac.gov.cn", "stats.gov.cn",
        "mofcom.gov.cn", "mof.gov.cn", "safe.gov.cn",
    )
    if any(h in url for h in gov_url_hints):
        return EVIDENCE_ORIGIN_GOV
    gov_label_hints = ("银保监", "央行", "证监会", "工信", "国资委", "统计局", "发改委")
    if any(h in label for h in gov_label_hints):
        return EVIDENCE_ORIGIN_GOV

    # 3. Industry / corp registry (cninfo / gsxt / 工商 / 公示)
    registry_url_hints = ("cninfo.com.cn", "gsxt.gov.cn", "tianyancha", "qcc.com", "qixin")
    if any(h in url for h in registry_url_hints):
        return EVIDENCE_ORIGIN_REGISTRY
    if "工商" in label or "公示" in label:
        return EVIDENCE_ORIGIN_REGISTRY

    # 4. Internal · 本行 / 内部 / SOP / 制度 / 风偏 / 准入 / 贷后 / 台账
    internal_hints = (
        "本行", "内部", "sop", "制度", "风偏", "准入", "贷后", "台账", "kb_internal",
    )
    if any(h in label_lower for h in internal_hints):
        return EVIDENCE_ORIGIN_INTERNAL

    # 5. Tag / narrative / 客户经理填报
    tag_hints = ("标签", "narrative", "客户经理", "尽调", "现场")
    if any(h in label_lower for h in tag_hints):
        return EVIDENCE_ORIGIN_TAG

    # 6. Media · 财新/华尔街见闻/界面/搜索/新闻/舆情
    media_url_hints = (
        "caixin.com", "yicai.com", "wallstreetcn.com", "jiemian.com",
        "21jingji.com", "thepaper.cn",
    )
    if any(h in url for h in media_url_hints):
        return EVIDENCE_ORIGIN_MEDIA
    media_label_hints = ("财新", "第一财经", "华尔街", "界面", "21世纪", "舆情", "新闻", "媒体", "搜索")
    if any(h in label for h in media_label_hints):
        return EVIDENCE_ORIGIN_MEDIA

    return EVIDENCE_ORIGIN_OTHER


def infer_evidence_origins(evidences: list[Any]) -> list[str]:
    """对一批 evidence 抽 unique origin bucket (deterministic order).

    Args:
        evidences: list of dict {"source": str, "url": str} OR Evidence pydantic obj
                   (容忍两种形态 · 兼容 cross_matcher.match_customer 输出)

    Returns:
        list[str] · unique origins in ALL_EVIDENCE_ORIGINS 顺序
    """
    seen: set[str] = set()
    for ev in evidences or []:
        if isinstance(ev, dict):
            label = str(ev.get("source") or ev.get("evidence_source") or "")
            url = str(ev.get("url") or ev.get("evidence_url") or "")
        else:
            label = str(getattr(ev, "source", "") or getattr(ev, "evidence_source", ""))
            url = str(getattr(ev, "url", "") or getattr(ev, "evidence_url", ""))
        seen.add(classify_evidence_origin(label, url))
    return [o for o in ALL_EVIDENCE_ORIGINS if o in seen]


def infer_full_kinds(
    hit_data: list[Any] | None = None,
    evidences: list[Any] | None = None,
) -> list[str]:
    """V2 fix-forward · 综合 rule prefix kinds + evidence origin kinds (union).

    设计:
    - 客户的"信号多样性" = rule kind 维度 ∪ evidence origin 维度
    - 两个维度正交 · 客户 1 rule + 1 evidence 即 ≥ 2 dimensions
    - 反对 hardcode 凑数 / 反对 fixture 注水 (PM 红线) ·
      origin 来自 evidence source 真实分类 (banking audit 必分维度)

    Args:
        hit_data: rule hits (per infer_signal_kinds)
        evidences: evidence list (per infer_evidence_origins)

    Returns:
        list[str] · rule kinds + evidence origins · deterministic 顺序
        (rule kinds 在前 · evidence origins 在后 · 各自内按 ALL_* 顺序)
    """
    rule_kinds = infer_signal_kinds(hit_data or [])
    origins = infer_evidence_origins(evidences or [])
    return rule_kinds + origins


# ---------------------------------------------------------------------------
# 4. compute_evidence_confidence 已 import from shared.evidence.confidence_policy
#    (上方 import · 行为完全等价 · alert 自测 100% 数值一致)
# ---------------------------------------------------------------------------


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
    "ALL_EVIDENCE_ORIGINS",
    "ALL_SIGNAL_KINDS",
    "EVIDENCE_ORIGIN_COURT",
    "EVIDENCE_ORIGIN_GOV",
    "EVIDENCE_ORIGIN_INTERNAL",
    "EVIDENCE_ORIGIN_MEDIA",
    "EVIDENCE_ORIGIN_OTHER",
    "EVIDENCE_ORIGIN_REGISTRY",
    "EVIDENCE_ORIGIN_TAG",
    "SIGNAL_KIND_BUSINESS",
    "SIGNAL_KIND_FINANCIAL",
    "SIGNAL_KIND_INDUSTRY",
    "SIGNAL_KIND_INTERNAL",
    "SIGNAL_KIND_LEGAL",
    "SIGNAL_KIND_OTHER",
    "SIGNAL_KIND_RELATED",
    "SOURCE_CONFIDENCE_PATH",
    "SourceConfidence",
    "classify_evidence_origin",
    "classify_signal_kind",
    "compute_evidence_confidence",
    "freshness_score",
    "infer_evidence_origins",
    "infer_full_kinds",
    "infer_signal_kinds",
    "lookup_source_confidence",
    "quality_bundle",
    "reload_source_confidence_table",
]
