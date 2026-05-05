# -*- coding: utf-8 -*-
"""agent_riskctrl.psi — re-export shim.

V2 fix (codex review bhwi951pd major 3) · 实际实装在 `psi_monthly.py` ·
本 shim 提供 `agent_riskctrl.psi` import path 兼容 (commit message + 文档
若引用 'psi.py' 时不破).

实际 module: ``agent_riskctrl.psi_monthly`` · 见该文件 docstring.
"""
from __future__ import annotations

from agent_riskctrl.psi_monthly import (  # noqa: F401
    PSI_GREEN,
    PSI_YELLOW,
    MonthlyTrendPoint,
    PSIRecord,
    compute_monthly_trend,
    compute_psi_by_month,
    format_psi_summary,
    format_trend_report,
    psi_severity,
    write_psi_jsonl,
)

__all__ = [
    "MonthlyTrendPoint",
    "PSIRecord",
    "PSI_GREEN",
    "PSI_YELLOW",
    "compute_monthly_trend",
    "compute_psi_by_month",
    "format_psi_summary",
    "format_trend_report",
    "psi_severity",
    "write_psi_jsonl",
]
