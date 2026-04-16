# -*- coding: utf-8 -*-
"""Agent3 (授信决策) 源偏好。

domain:
- profile: 企业画像补充（聚合源 akshare 的研报 > 通用搜索 tavily）
- industry_benchmark: 行业对标（akshare 行业板块 > tavily 泛搜）
"""
from __future__ import annotations

from shared.sources.router import register_preference


def init() -> None:
    register_preference(
        "agent_credit.profile",
        ["akshare", "tavily"],
    )
    register_preference(
        "agent_credit.industry_benchmark",
        ["akshare", "tavily"],
    )
