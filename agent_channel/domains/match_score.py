# -*- coding: utf-8 -*-
"""匹配评分域 —— 信号密度打分 + look-alike 相似度 + 匹配标签。"""

from __future__ import annotations

from ..lead_finder import LookAlikeMatcher
from ..realtime_stream import (
    _build_match_tags as _build_match_tags_impl,
    _score_and_rank as _score_and_rank_impl,
)
from ..scoring import (
    calculate_match_score as _calculate_match_score,
    rank_recommendations as _rank_recommendations,
)


def match_score_calculate(company_info: dict, channel: dict) -> int:
    """企业 × 渠道的匹配度打分（匹配评分域：原子评分）。"""
    return _calculate_match_score(company_info, channel)


def match_score_rank_recommendations(company_info: dict, *args, **kwargs):
    """对候选渠道列表按匹配度排序（匹配评分域：排序）。"""
    return _rank_recommendations(company_info, *args, **kwargs)


def match_lookalike_find(candidates, ideal, anchors, *, top_anchor_k: int = 3,
                          profile_weight: float = 0.6, anchor_weight: float = 0.4):
    """基于理想画像 + 种子企业做 look-alike 相似度召回（匹配评分域：类似企业发现）。

    透传到 `LookAlikeMatcher(...).match_all_against_ideal(candidates, ideal, anchors, top_anchor_k)`。
    """
    matcher = LookAlikeMatcher(profile_weight=profile_weight, anchor_weight=anchor_weight)
    return matcher.match_all_against_ideal(
        candidates, ideal, anchors, top_anchor_k=top_anchor_k,
    )


def match_tags_build(item: dict, tags: list[dict]) -> list[dict]:
    """为单条候选构建匹配标签（匹配评分域：标签化解释）。"""
    return _build_match_tags_impl(item, tags)


def match_score_and_rank_signals(company_map: dict[str, dict]) -> list[dict]:
    """把按企业聚合后的信号 map 按密度/时新性打分+排序（匹配评分域：信号侧排序）。"""
    return _score_and_rank_impl(company_map)
