# -*- coding: utf-8 -*-
"""指标分析域 —— KS / PSI / 混淆矩阵 / 报表格式化。"""

from __future__ import annotations

from ..metrics import (
    calculate_confusion_matrix as _calculate_confusion_matrix,
    calculate_ks as _calculate_ks,
    calculate_psi as _calculate_psi,
    format_metrics_report as _format_metrics_report,
)


def metrics_analyze_ks(y_true: list, y_pred: list) -> float:
    """KS 值（指标分析域：区分度）。"""
    return _calculate_ks(y_true, y_pred)


def metrics_analyze_psi(expected: list, actual: list, bins: int = 10) -> float:
    """PSI（Population Stability Index · 指标分析域：稳定性）。"""
    return _calculate_psi(expected, actual, bins=bins)


def metrics_analyze_confusion(y_true: list, y_pred: list) -> dict:
    """混淆矩阵 + 衍生指标（指标分析域：准召分解）。"""
    return _calculate_confusion_matrix(y_true, y_pred)


def metrics_analyze_format_report(metrics: dict) -> str:
    """Markdown 格式化回测指标报告（指标分析域：可读输出）。"""
    return _format_metrics_report(metrics)
