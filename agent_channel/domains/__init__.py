# -*- coding: utf-8 -*-
"""Agent1 获客 · 工具域入口（CLAUDE.md §3.2）

四个子域：信号搜索 / 企业画像 / 匹配评分 / 产品推荐。
`realtime_stream.py` 的 6 阶段流式编排保留在 `agent_channel.agent.ChannelMatchAgent`
（跨域协作走编排层，不在域内互调）。
"""

from .signal_search import (
    signal_search_stream,
    signal_generate_queries,
    signal_parse_intent,
    signal_extract_from_text,
    signal_aggregate_by_company,
)
from .profile import (
    profile_extract_ideal_from_kb,
    profile_fetch_qcc_info,
    profile_enrich_top_companies,
)
from .match_score import (
    match_score_calculate,
    match_score_rank_recommendations,
    match_lookalike_find,
    match_tags_build,
    match_score_and_rank_signals,
)
from .product_recommend import (
    product_recommend_by_rules,
    product_recommend_from_signals,
    product_pitch_generate,
    product_pitch_fallback,
)

__all__ = [
    # 信号搜索域
    "signal_search_stream",
    "signal_generate_queries",
    "signal_parse_intent",
    "signal_extract_from_text",
    "signal_aggregate_by_company",
    # 企业画像域
    "profile_extract_ideal_from_kb",
    "profile_fetch_qcc_info",
    "profile_enrich_top_companies",
    # 匹配评分域
    "match_score_calculate",
    "match_score_rank_recommendations",
    "match_lookalike_find",
    "match_tags_build",
    "match_score_and_rank_signals",
    # 产品推荐域
    "product_recommend_by_rules",
    "product_recommend_from_signals",
    "product_pitch_generate",
    "product_pitch_fallback",
]
