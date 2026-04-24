# -*- coding: utf-8 -*-
"""信号搜索域 —— 中标 / 专精特新 / 专利 / 扩产 / 获奖 5 路并行 + 信号聚合。

编排入口仍在 `agent_channel.agent.ChannelMatchAgent`（走跨域 glue）；本域只暴露原子能力。
"""

from __future__ import annotations

from typing import Iterator

from ..lead_finder import generate_search_queries as _generate_search_queries
from ..realtime_stream import (
    _aggregate_by_company as _aggregate_by_company_impl,
    _extract_signal as _extract_signal_impl,
    _parse_intent as _parse_intent_impl,
    run_channel_search_stream as _run_channel_search_stream,
)


def signal_search_stream(*args, **kwargs) -> Iterator[dict]:
    """主流式搜索入口 —— 返回逐阶段事件迭代器（信号搜索域：主入口）。

    透传到底层 `run_channel_search_stream(company_info, api_key, llm, ...)`。
    """
    return _run_channel_search_stream(*args, **kwargs)


def signal_generate_queries(ideal, max_queries: int = 4) -> list[str]:
    """理想画像 → 搜索词集合（信号搜索域：检索式生成）。"""
    return _generate_search_queries(ideal, max_queries=max_queries)


def signal_parse_intent(llm, query: str) -> list[dict]:
    """自然语言 → 结构化意图标签（信号搜索域：意图解析）。"""
    return _parse_intent_impl(llm, query)


def signal_extract_from_text(*args, **kwargs) -> dict | None:
    """从搜索结果文本提取单条结构化信号（信号搜索域：信号抽取）。"""
    return _extract_signal_impl(*args, **kwargs)


def signal_aggregate_by_company(signals: list[dict]) -> dict[str, dict]:
    """按企业名聚合信号，产出候选企业→信号时间线字典（信号搜索域：聚合）。"""
    return _aggregate_by_company_impl(signals)
