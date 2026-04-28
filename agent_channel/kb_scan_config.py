# -*- coding: utf-8 -*-
"""Agent1 (全渠道) KB 扫描偏好配置 (D.5 共享底座).

domain:
- ``agent_channel.candidate_enrich`` — 单候选丰富 (radar / dims / products / pitch)
"""
from __future__ import annotations

from shared.kb_scan.router import register_preference


def init() -> None:
    register_preference(
        "agent_channel.candidate_enrich",
        ["channel_signal"],
    )
