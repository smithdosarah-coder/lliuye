# -*- coding: utf-8 -*-
"""Agent5 (合规)源偏好。

domain:
- policy_scan: 扫描新政策（gov.cn/PBC 官方优先，法规库兜底，tavily 降级）
- law_lookup: 精准法律法规检索（法规库 > tavily）
"""
from __future__ import annotations

from shared.sources.router import register_preference


def init() -> None:
    register_preference(
        "agent_compliance.policy_scan",
        ["gov_cn", "pbc_gov", "flk_npc", "tavily"],
    )
    register_preference(
        "agent_compliance.law_lookup",
        ["flk_npc", "tavily"],
    )
