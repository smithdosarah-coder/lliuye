# -*- coding: utf-8 -*-
"""风控策略指标计算

功能:
    calculate_ks               — KS统计量
    calculate_psi              — PSI稳定性指标
    calculate_confusion_matrix — 混淆矩阵 + 精确率/召回率/F1
    format_metrics_report      — 格式化指标报告
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ======================================================================
# KS 统计量
# ======================================================================

def calculate_ks(y_true: list, y_pred: list) -> float:
    """计算KS统计量（区分好坏客户的最大差异）。

    Args:
        y_true: 真实标签 (0/1)
        y_pred: 预测概率或分数

    Returns:
        KS值 (0~1)
    """
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    if len(y_true) == 0 or len(y_true) != len(y_pred):
        return 0.0

    # 按预测值降序排列
    order = np.argsort(-y_pred)
    y_true_sorted = y_true[order]

    n_pos = y_true_sorted.sum()
    n_neg = len(y_true_sorted) - n_pos

    if n_pos == 0 or n_neg == 0:
        return 0.0

    tpr_cumsum = np.cumsum(y_true_sorted) / n_pos
    fpr_cumsum = np.cumsum(1 - y_true_sorted) / n_neg

    ks = float(np.max(np.abs(tpr_cumsum - fpr_cumsum)))
    return round(ks, 4)


# ======================================================================
# AUC (V2 fix · BE6.4 codex review critical 1)
#   纯 numpy rank-based 实现 · 等价 sklearn roc_auc_score · 不引新 dep
#   公式: AUC = (sum_pos_ranks - n_pos*(n_pos+1)/2) / (n_pos * n_neg)
#   等价 Mann-Whitney U test · 平均处理 ties (rankdata average)
# ======================================================================


def _rankdata_average(arr: np.ndarray) -> np.ndarray:
    """numpy 实现 scipy.stats.rankdata(method='average') · 处理 ties."""
    sorter = np.argsort(arr, kind="mergesort")
    inv = np.empty_like(sorter)
    inv[sorter] = np.arange(len(arr))
    sorted_arr = arr[sorter]
    # 1-indexed ranks · 同值取平均
    n = len(arr)
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_arr[j + 1] == sorted_arr[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        ranks[i:j + 1] = avg_rank
        i = j + 1
    return ranks[inv]


def calculate_auc(y_true: list, y_pred: list) -> float:
    """计算 AUC (Area Under ROC Curve) · 等价 sklearn roc_auc_score.

    Args:
        y_true: 真实标签 (0/1)
        y_pred: 预测分数 (越高越坏 / risk score)

    Returns:
        AUC ∈ [0, 1] · 0.5 = 随机 · 1.0 = 完美区分
        edge: y_true 全同类 / 长度不一致 / 空 → 0.0
    """
    y_true_arr = np.array(y_true, dtype=float)
    y_pred_arr = np.array(y_pred, dtype=float)

    if len(y_true_arr) == 0 or len(y_true_arr) != len(y_pred_arr):
        return 0.0

    n_pos = float((y_true_arr == 1).sum())
    n_neg = float((y_true_arr == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.0

    ranks = _rankdata_average(y_pred_arr)
    sum_pos_ranks = float(ranks[y_true_arr == 1].sum())
    auc = (sum_pos_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return round(float(auc), 4)


# ======================================================================
# PSI 稳定性指标
# ======================================================================

def calculate_psi(expected: list, actual: list, bins: int = 10) -> float:
    """计算PSI (Population Stability Index) 稳定性指标。

    PSI < 0.1: 稳定
    0.1 <= PSI < 0.25: 轻微偏移
    PSI >= 0.25: 显著偏移

    Args:
        expected: 基准分布（训练集/上期）
        actual: 实际分布（验证集/当期）
        bins: 分箱数

    Returns:
        PSI值
    """
    expected = np.array(expected, dtype=float)
    actual = np.array(actual, dtype=float)

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # 用 expected 的分位数作为分箱边界
    breakpoints = np.percentile(expected, np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)

    # 计算各区间占比
    exp_counts = np.histogram(expected, bins=breakpoints)[0]
    act_counts = np.histogram(actual, bins=breakpoints)[0]

    # 转为占比（加小量避免除零）
    eps = 1e-6
    exp_pct = exp_counts / len(expected) + eps
    act_pct = act_counts / len(actual) + eps

    psi = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))
    return round(psi, 4)


# ======================================================================
# 混淆矩阵
# ======================================================================

def calculate_confusion_matrix(y_true: list, y_pred: list) -> dict:
    """计算混淆矩阵及精确率、召回率、F1。

    Args:
        y_true: 真实标签 (0/1 或 bool)
        y_pred: 预测标签 (0/1 或 bool)

    Returns:
        {
            "TP": int, "FP": int, "TN": int, "FN": int,
            "precision": float, "recall": float, "f1": float,
            "accuracy": float,
        }
    """
    y_true = [_to_bool(v) for v in y_true]
    y_pred = [_to_bool(v) for v in y_pred]

    n = min(len(y_true), len(y_pred))
    tp = fp = tn = fn = 0

    for i in range(n):
        if y_pred[i] and y_true[i]:
            tp += 1
        elif y_pred[i] and not y_true[i]:
            fp += 1
        elif not y_pred[i] and not y_true[i]:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    accuracy = (tp + tn) / n if n > 0 else 0.0

    return {
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }


def _to_bool(val: Any) -> bool:
    """将标签值统一转为布尔"""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val == 1
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "是", "bad", "违约", "逾期", "风险")


# ======================================================================
# 格式化指标报告
# ======================================================================

def format_metrics_report(metrics: dict) -> str:
    """将指标字典格式化为可读的Markdown报告。

    Args:
        metrics: 指标字典，可包含混淆矩阵、KS、PSI等

    Returns:
        Markdown格式的报告文本
    """
    lines = ["### 策略效果指标", ""]

    # 混淆矩阵
    if "TP" in metrics:
        lines.append("**混淆矩阵：**")
        lines.append("")
        lines.append("| | 预测风险 | 预测正常 |")
        lines.append("|------|----------|----------|")
        lines.append(
            f"| **实际风险** | TP={metrics['TP']} | FN={metrics.get('FN', 0)} |"
        )
        lines.append(
            f"| **实际正常** | FP={metrics['FP']} | TN={metrics.get('TN', 0)} |"
        )
        lines.append("")

    # 常规指标
    metric_labels = {
        "precision": "精确率",
        "recall": "召回率",
        "f1": "F1分数",
        "accuracy": "准确率",
        "ks": "KS统计量",
        "psi": "PSI稳定性",
    }

    displayed = []
    for key, label in metric_labels.items():
        if key in metrics:
            val = metrics[key]
            if isinstance(val, float):
                displayed.append(f"- **{label}**: {val:.4f}")
            else:
                displayed.append(f"- **{label}**: {val}")

    if displayed:
        lines.extend(displayed)
        lines.append("")

    # PSI解读
    if "psi" in metrics:
        psi_val = metrics["psi"]
        if psi_val < 0.1:
            lines.append("> PSI < 0.1，群体稳定性良好")
        elif psi_val < 0.25:
            lines.append("> 0.1 <= PSI < 0.25，存在轻微偏移，建议关注")
        else:
            lines.append("> PSI >= 0.25，群体显著偏移，建议重新校准策略")
        lines.append("")

    # KS解读
    if "ks" in metrics:
        ks_val = metrics["ks"]
        if ks_val >= 0.3:
            lines.append("> KS >= 0.3，策略区分能力较强")
        elif ks_val >= 0.2:
            lines.append("> 0.2 <= KS < 0.3，策略区分能力一般")
        else:
            lines.append("> KS < 0.2，策略区分能力较弱，建议优化")
        lines.append("")

    return "\n".join(lines)
