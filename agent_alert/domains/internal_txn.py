# -*- coding: utf-8 -*-
"""内部交易域 —— 对照内部制度，扫流水异常 / 财务趋势 / 经营指标。"""

from __future__ import annotations

from typing import Any

from ..alert_engine import AlertReport, evaluate_alerts as _evaluate_alerts
from ..trend_analyzer import (
    TrendItem,
    analyze_financial_trends as _analyze_financial_trends,
    detect_anomalies as _detect_anomalies,
)


def internal_txn_evaluate(data: dict, profile=None, search_text: str = "") -> AlertReport:
    """跑 11 条内部指标检查（内部交易域：指标扫描主入口）。"""
    return _evaluate_alerts(data, profile=profile, search_text=search_text)


def internal_txn_analyze_trends(data: dict) -> list[TrendItem]:
    """财务趋势分析（内部交易域：趋势抽取）。"""
    return _analyze_financial_trends(data)


def internal_txn_detect_anomalies(values: list[float]) -> list[dict]:
    """时序异常点检测（内部交易域：原子工具）。"""
    return _detect_anomalies(values)
