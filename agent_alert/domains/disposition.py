# -*- coding: utf-8 -*-
"""处置建议域 —— 红灯客户配处置建议 + 台账 Excel 导出。"""

from __future__ import annotations

from ..alert_engine import AlertReport
from ..disposition import DispositionPlan, generate_disposition as _generate_disposition
from ..ledger_exporter import export_ledger_excel as _export_ledger_excel


def disposition_generate_plan(alert_report: AlertReport) -> DispositionPlan:
    """为单份预警报告生成处置建议（处置建议域：方案生成）。"""
    return _generate_disposition(alert_report)


def disposition_export_ledger(*args, **kwargs) -> str:
    """导出预警台账 Excel（处置建议域：持久化）。"""
    return _export_ledger_excel(*args, **kwargs)
