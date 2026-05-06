"""Sprint 6 D3 · 千人千面 segment 路由 + 金字塔产品适配

per xlsx v2 2.1+3.1 verbatim "5-10 类细分场景话术库 + 资产配置金字塔 (产品 → 风险等级 → 客群 静态映射)"

输入:
- candidate_profile: AI 画像 dict (含 annual_revenue / yoy_growth / tags / market_share)

输出:
- segment: { id, name, description, talking_point_template, ... }
- pyramid_tier: { tier_id, tier_name, risk_level, products[] }
- recommended_products: list[dict] · 客群 + 金字塔交集
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEGMENTS_PATH = PROJECT_ROOT / "data" / "customer_segments.json"
PYRAMID_PATH = PROJECT_ROOT / "data" / "product_pyramid.json"

_segments_cache: dict[str, Any] | None = None
_pyramid_cache: dict[str, Any] | None = None


def _load_segments() -> dict[str, Any]:
    global _segments_cache
    if _segments_cache is None:
        _segments_cache = json.loads(SEGMENTS_PATH.read_text(encoding="utf-8"))
    return _segments_cache


def _load_pyramid() -> dict[str, Any]:
    global _pyramid_cache
    if _pyramid_cache is None:
        _pyramid_cache = json.loads(PYRAMID_PATH.read_text(encoding="utf-8"))
    return _pyramid_cache


def _match_segment(profile: dict) -> dict[str, Any]:
    """按 criteria 优先级 match 客群 · fallback default_segment_id."""
    config = _load_segments()
    revenue = profile.get("annual_revenue") or 0
    growth = profile.get("yoy_growth") or 0
    market_share = profile.get("market_share") or 0
    export_ratio = profile.get("export_revenue_ratio") or 0
    tags = set(profile.get("tags") or [])

    for segment in config["segments"]:
        criteria = segment.get("criteria") or {}

        if "annual_revenue_gte" in criteria and revenue < criteria["annual_revenue_gte"]:
            continue
        if "annual_revenue_lt" in criteria and revenue >= criteria["annual_revenue_lt"]:
            continue
        if "annual_revenue_range" in criteria:
            lo, hi = criteria["annual_revenue_range"]
            if not (lo <= revenue <= hi):
                continue
        if "yoy_growth_gte" in criteria and growth < criteria["yoy_growth_gte"]:
            continue
        if "market_share_gte" in criteria and market_share < criteria["market_share_gte"]:
            continue
        if "export_revenue_ratio_gte" in criteria and export_ratio < criteria["export_revenue_ratio_gte"]:
            continue
        if "tags_any" in criteria:
            if not (set(criteria["tags_any"]) & tags):
                continue
        if "stage" in criteria:
            stage = profile.get("stage")
            if stage and stage not in criteria["stage"]:
                continue

        return segment

    # fallback
    default_id = config.get("default_segment_id", "segment_growth")
    for s in config["segments"]:
        if s["id"] == default_id:
            return s
    return config["segments"][0]


def _match_pyramid_tier(segment: dict) -> dict[str, Any]:
    """按 segment 找适配 tier · 优先 core 兼容多 segment."""
    pyramid = _load_pyramid()
    sid = segment["id"]
    matched_tiers = [t for t in pyramid["tiers"] if sid in t.get("target_segments", [])]
    if not matched_tiers:
        # fallback core tier
        core = next((t for t in pyramid["tiers"] if t["tier_id"] == "tier_core"), None)
        return core or pyramid["tiers"][0]
    # 选第一 matched (config 内顺序就是优先级)
    return matched_tiers[0]


def route_candidate(profile: dict) -> dict[str, Any]:
    """主入口 · 输入 candidate profile · 输出 segment + tier + 推荐产品 list.

    Sprint 6 D3-D4 ship · BE12 personal_insight 调用此 router 决定 talking_point template + product fit.
    """
    segment = _match_segment(profile)
    tier = _match_pyramid_tier(segment)
    products = list(tier.get("products", []))
    return {
        "segment": {
            "id": segment["id"],
            "name": segment["name"],
            "description": segment["description"],
            "talking_point_template": segment.get("talking_point_template"),
            "rate_band_offset": segment.get("rate_band_offset", 0),
            "amount_ceiling_multiplier": segment.get("amount_ceiling_multiplier", 1.0),
        },
        "pyramid_tier": {
            "tier_id": tier["tier_id"],
            "tier_name": tier["tier_name"],
            "risk_level": tier["risk_level"],
        },
        "recommended_products": products,
    }


__all__ = ["route_candidate"]
