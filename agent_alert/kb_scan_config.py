# -*- coding: utf-8 -*-
"""Agent4 (贷中预警) KB 扫描偏好配置 (D.5 共享底座).

由 ``shared.kb_scan.bootstrap_scanners()`` 自动调用 init() · 不在此手工 import。

domain 命名: ``agent_alert.<capability>`` · 调用方走 ``ScannerRouter().scan(...)``。
"""
from __future__ import annotations

from shared.kb_scan.router import register_preference


def init() -> None:
    """注册 Agent4 所有 domain 的扫描偏好链."""
    register_preference(
        "agent_alert.batch_loan_scan",
        ["alert_customer"],  # 单一 scanner · 暂无 fallback (KB 缺时 ok=False)
    )
