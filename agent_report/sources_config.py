# -*- coding: utf-8 -*-
"""Agent6 (信贷报告) 源偏好。

domain:
- law_citation: 报告正文引用法律法规（只信官方 flk.npc.gov.cn）
- company_lookup: 企业背景补充（akshare 研报 > tavily）
"""
from __future__ import annotations

from shared.sources.router import register_preference


def init() -> None:
    register_preference(
        "agent_report.law_citation",
        ["flk_npc"],
    )
    register_preference(
        "agent_report.company_lookup",
        ["akshare", "tavily"],
    )
