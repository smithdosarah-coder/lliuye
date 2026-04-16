# -*- coding: utf-8 -*-
"""Agent4 贷中风险预警 - 趋势分析器

从数据中提取财务指标时序数据，计算变化率、判断趋势方向、检测异常点。
"""

from __future__ import annotations

import math
import re
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class TrendItem(BaseModel):
    """单项趋势分析结果"""
    metric_name: str = ""               # 指标名称
    values: list[float] = Field(default_factory=list)  # 时序数值列表
    trend: str = "平稳"                 # 上升 / 下降 / 平稳
    change_rate: float = 0.0            # 变化率（百分比）
    risk_note: str = ""                 # 风险提示


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _safe_float(val: Any) -> Optional[float]:
    """安全地将值转换为浮点数"""
    if val is None:
        return None
    s = str(val).strip().replace(",", "").replace("万元", "").replace("万", "")
    s = s.replace("亿元", "").replace("亿", "").replace("%", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _extract_values(text: str, patterns: list[str]) -> list[float]:
    """从文本中按正则提取所有数值"""
    values: list[float] = []
    for pat in patterns:
        matches = re.findall(pat, text)
        for m in matches:
            v = _safe_float(m)
            if v is not None:
                values.append(v)
        if values:
            break
    return values


def _calc_trend(values: list[float]) -> tuple[str, float]:
    """根据数值列表计算趋势方向和变化率

    Returns:
        (trend, change_rate): trend为"上升"/"下降"/"平稳"，change_rate为百分比
    """
    if len(values) < 2:
        return "平稳", 0.0
    latest = values[-1]
    previous = values[-2]
    if previous == 0:
        if latest > 0:
            return "上升", 100.0
        elif latest < 0:
            return "下降", -100.0
        return "平稳", 0.0
    rate = (latest - previous) / abs(previous) * 100
    if rate > 5:
        return "上升", round(rate, 2)
    elif rate < -5:
        return "下降", round(rate, 2)
    return "平稳", round(rate, 2)


# ---------------------------------------------------------------------------
# 异常检测
# ---------------------------------------------------------------------------

def detect_anomalies(values: list[float]) -> list[dict]:
    """简单异常检测：偏离均值2倍标准差的数据点

    Args:
        values: 数值列表

    Returns:
        异常点列表，每项包含 index, value, deviation
    """
    if len(values) < 3:
        return []

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance) if variance > 0 else 0

    if std == 0:
        return []

    anomalies = []
    for i, v in enumerate(values):
        deviation = abs(v - mean) / std
        if deviation > 2.0:
            anomalies.append({
                "index": i,
                "value": v,
                "deviation": round(deviation, 2),
                "direction": "偏高" if v > mean else "偏低",
            })
    return anomalies


# ---------------------------------------------------------------------------
# 趋势分析入口
# ---------------------------------------------------------------------------

def analyze_financial_trends(data: dict) -> list[TrendItem]:
    """分析财务指标趋势

    Args:
        data: 企业数据字典（kb 格式）

    Returns:
        趋势分析结果列表
    """
    facts = data.get("facts", {}) or {}
    all_text = str(facts) + " " + str(data.get("tables", {}))
    results: list[TrendItem] = []

    # 定义要分析的指标及其提取模式
    metrics_config = [
        {
            "name": "营业收入",
            "patterns": [
                r"营[业收]收入[：:]*\s*([\d,.]+)\s*万",
                r"([\d,.]+)\s*万.*?营[业收]收入",
            ],
            "risk_check": lambda vals, rate: (
                "营收持续下降，经营状况恶化" if rate < -10
                else ("营收大幅增长，需关注增长质量" if rate > 50 else "")
            ),
        },
        {
            "name": "净利润",
            "patterns": [
                r"净利润[：:]*\s*([-\d,.]+)\s*万",
                r"([-\d,.]+)\s*万.*?净利润",
            ],
            "risk_check": lambda vals, rate: (
                "企业处于亏损状态" if (vals and vals[-1] < 0)
                else ("利润下降，盈利能力减弱" if rate < -10 else "")
            ),
        },
        {
            "name": "资产负债率",
            "patterns": [
                r"资产负债率[：:]*\s*([\d.]+)\s*%?",
            ],
            "risk_check": lambda vals, rate: (
                "资产负债率超过80%警戒线" if (vals and vals[-1] > 80)
                else ("资产负债率偏高，接近警戒线" if (vals and vals[-1] > 70) else "")
            ),
        },
        {
            "name": "流动比率",
            "patterns": [
                r"流动比率[：:]*\s*([\d.]+)",
            ],
            "risk_check": lambda vals, rate: (
                "流动比率低于1，短期偿债能力严重不足" if (vals and vals[-1] < 1)
                else ("流动比率偏低" if (vals and vals[-1] < 1.5) else "")
            ),
        },
        {
            "name": "经营性现金流",
            "patterns": [
                r"经营.*?现金.*?净[额量][：:]*\s*([-\d,.]+)\s*万",
            ],
            "risk_check": lambda vals, rate: (
                "经营性现金流为负，造血能力不足" if (vals and vals[-1] < 0) else ""
            ),
        },
    ]

    for cfg in metrics_config:
        values = _extract_values(all_text, cfg["patterns"])
        if not values:
            continue
        trend, change_rate = _calc_trend(values)

        # 检测异常
        anomalies = detect_anomalies(values)
        risk_note = cfg["risk_check"](values, change_rate)
        if anomalies and not risk_note:
            risk_note = f"检测到{len(anomalies)}个异常数据点"

        results.append(TrendItem(
            metric_name=cfg["name"],
            values=values,
            trend=trend,
            change_rate=change_rate,
            risk_note=risk_note,
        ))

    return results


# ---------------------------------------------------------------------------
# 格式化输出
# ---------------------------------------------------------------------------

def format_trend_report(trends: list[TrendItem]) -> str:
    """格式化趋势报告为 Markdown 表格

    Args:
        trends: 趋势分析结果列表

    Returns:
        Markdown 格式的趋势报告文本
    """
    if not trends:
        return "暂无足够的财务数据进行趋势分析。"

    trend_icon = {"上升": "📈", "下降": "📉", "平稳": "➡️"}
    lines = [
        "| 指标 | 最新值 | 变化率 | 趋势 | 风险提示 |",
        "|------|--------|--------|------|----------|",
    ]
    for t in trends:
        latest = f"{t.values[-1]:,.2f}" if t.values else "--"
        icon = trend_icon.get(t.trend, "")
        rate_str = f"{t.change_rate:+.1f}%" if t.change_rate != 0 else "--"
        note = t.risk_note or "正常"
        lines.append(f"| {t.metric_name} | {latest} | {rate_str} | {icon} {t.trend} | {note} |")

    return "\n".join(lines)
