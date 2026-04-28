# -*- coding: utf-8 -*-
"""Agent5 (合规) KB 扫描偏好配置 (D.5 共享底座).

domain:
- ``agent_compliance.policy_scan`` — 扫描新政策候选清单
"""
from __future__ import annotations

from shared.kb_scan.router import register_preference


def init() -> None:
    register_preference(
        "agent_compliance.policy_scan",
        ["compliance_policy"],
    )
