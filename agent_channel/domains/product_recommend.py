# -*- coding: utf-8 -*-
"""产品推荐域 —— 规则匹配 + 信号驱动推荐 + 切入话术生成。"""

from __future__ import annotations

from ..channel_rules import match_channels as _match_channels
from ..realtime_stream import (
    _fallback_pitch as _fallback_pitch_impl,
    _generate_pitch as _generate_pitch_impl,
    _recommend_products as _recommend_products_impl,
)


def product_recommend_by_rules(company_info: dict) -> list[dict]:
    """基于渠道规则库推荐产品（产品推荐域：规则命中）。"""
    return _match_channels(company_info)


def product_recommend_from_signals(signals: list[dict]) -> list[str]:
    """基于信号画像推荐 Top3 产品（产品推荐域：信号驱动）。"""
    return _recommend_products_impl(signals)


def product_pitch_generate(llm, item: dict) -> str:
    """LLM 生成切入话术（产品推荐域：话术主路径）。"""
    return _generate_pitch_impl(llm, item)


def product_pitch_fallback(item: dict) -> str:
    """模板兜底话术（产品推荐域：无 LLM 时的降级）。"""
    return _fallback_pitch_impl(item)
