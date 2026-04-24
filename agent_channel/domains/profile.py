# -*- coding: utf-8 -*-
"""企业画像域 —— 理想画像抽取 + 工商补全 + Top 候选富化。"""

from __future__ import annotations

from ..profile_extractor import ProfileExtractor
from ..realtime_stream import (
    _enrich_top_companies as _enrich_top_companies_impl,
    _fetch_qcc_info as _fetch_qcc_info_impl,
)


def profile_extract_ideal_from_kb(kb, llm_caller=None):
    """从知识库抽取理想企业画像（企业画像域：IdealProfile 主入口）。

    薄包装 `ProfileExtractor(llm_caller).extract(kb)`。
    """
    return ProfileExtractor(llm_caller=llm_caller).extract(kb)


def profile_fetch_qcc_info(company_name: str, tavily_key: str) -> dict:
    """企查查侧工商基础信息（企业画像域：工商补全）。"""
    return _fetch_qcc_info_impl(company_name, tavily_key)


def profile_enrich_top_companies(top_companies: list[dict], tags: list[dict]) -> list[dict]:
    """对 Top 候选企业富化（企业画像域：候选富化）。"""
    return _enrich_top_companies_impl(top_companies, tags)
