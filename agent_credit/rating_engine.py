# -*- coding: utf-8 -*-
"""Agent2 授信决策辅助 - A-E信用评级引擎

基于风险评估综合评分，计算信用评级、建议额度和置信度。
"""

from __future__ import annotations

import re
from typing import Callable
from pydantic import BaseModel, Field

from .risk_classifier import RiskAssessment
from .prompts import SYSTEM_RATING


# ---------------------------------------------------------------------------
# 评级标准
# ---------------------------------------------------------------------------

RATING_CRITERIA = {
    "A": {"label": "优秀", "min": 80, "max": 100, "limit_pct": 0.30,
           "desc": "财务优秀，经营稳健，可正常授信"},
    "B": {"label": "良好", "min": 60, "max": 79,  "limit_pct": 0.20,
           "desc": "财务良好，经营基本稳定，正常授信"},
    "C": {"label": "一般", "min": 40, "max": 59,  "limit_pct": 0.10,
           "desc": "财务一般，经营有波动，谨慎授信"},
    "D": {"label": "关注", "min": 20, "max": 39,  "limit_pct": 0.05,
           "desc": "财务较差，经营波动大，严格控制"},
    "E": {"label": "高危", "min": 0,  "max": 19,  "limit_pct": 0.00,
           "desc": "财务严重恶化，建议拒绝授信"},
}


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class CreditRating(BaseModel):
    """信用评级结果"""
    rating: str = ""                            # A/B/C/D/E
    rating_label: str = ""                      # 优秀/良好/一般/关注/高危
    score: float = 0.0                          # 综合评分（来自风险评估）
    positive_factors: list[str] = Field(default_factory=list)   # 正面因素
    negative_factors: list[str] = Field(default_factory=list)   # 负面因素
    suggested_limit: str = ""                   # 建议授信额度
    confidence: float = 0.0                     # 评级置信度 0.0-1.0


# ---------------------------------------------------------------------------
# 评分 -> 评级
# ---------------------------------------------------------------------------

def _score_to_rating(score: float) -> tuple[str, str]:
    """将综合评分映射为信用评级"""
    for rating, criteria in RATING_CRITERIA.items():
        if criteria["min"] <= score <= criteria["max"]:
            return rating, criteria["label"]
    if score >= 80:
        return "A", "优秀"
    return "E", "高危"


def _extract_revenue_amount(profile_text: str) -> float | None:
    """从画像文本中提取营收金额（万元）"""
    for pattern in [
        r"(?:营[业收]收入|最近营收)[：:]*\s*([\d,.]+)\s*(?:万|万元)",
        r"([\d,.]+)\s*万元.*?营[业收]收入",
    ]:
        m = re.search(pattern, profile_text or "")
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except (ValueError, TypeError):
                continue
    return None


def _extract_asset_amount(materials: str) -> float | None:
    """从材料中提取资产总额（万元）"""
    for pattern in [
        r"资产总[额计][：:]*\s*([\d,.]+)\s*(?:万|万元)",
        r"总资产[：:]*\s*([\d,.]+)\s*(?:万|万元)",
    ]:
        m = re.search(pattern, materials or "")
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except (ValueError, TypeError):
                continue
    return None


# ---------------------------------------------------------------------------
# 建议额度计算
# ---------------------------------------------------------------------------

def suggest_credit_limit(
    rating: str,
    revenue: float | None = None,
    assets: float | None = None,
) -> str:
    """基于评级和企业规模建议授信额度

    计算逻辑：
    - 以营收为基准，按评级系数计算上限
    - 如果有资产数据，取营收和资产计算结果的较小值
    - E级不建议授信
    """
    criteria = RATING_CRITERIA.get(rating, RATING_CRITERIA["E"])
    limit_pct = criteria["limit_pct"]

    if rating == "E" or limit_pct <= 0:
        return "不建议授信"

    if revenue is None and assets is None:
        return (f"建议按{rating}级标准控制额度"
                f"（需补充营收/资产数据以计算具体金额）")

    limits = []
    if revenue is not None and revenue > 0:
        rev_limit = revenue * limit_pct
        limits.append(rev_limit)
    if assets is not None and assets > 0:
        asset_limit = assets * limit_pct * 0.5  # 资产系数更保守
        limits.append(asset_limit)

    if not limits:
        return f"建议按{rating}级标准控制额度"

    suggested = min(limits)
    # 格式化输出
    if suggested >= 10000:
        return f"{suggested / 10000:.1f}亿元"
    elif suggested >= 1:
        return f"{suggested:.0f}万元"
    else:
        return f"{suggested:.2f}万元"


# ---------------------------------------------------------------------------
# 评级置信度计算
# ---------------------------------------------------------------------------

def _calculate_confidence(risk_assessment: RiskAssessment) -> float:
    """根据维度信息完整性计算评级置信度"""
    if not risk_assessment.dimensions:
        return 0.2

    info_count = 0
    total = len(risk_assessment.dimensions)
    for dim in risk_assessment.dimensions:
        # 有实质性证据（不是"信息不足"类）
        has_evidence = (
            dim.evidence
            and "信息不足" not in dim.evidence
            and "未获取" not in dim.evidence
        )
        if has_evidence:
            info_count += 1
        # 有多个具体因素
        has_factors = (
            len(dim.key_factors) >= 2
            and not any("信息不足" in f for f in dim.key_factors)
        )
        if has_factors:
            info_count += 0.5

    ratio = info_count / (total * 1.5) if total > 0 else 0
    # 映射到 0.3-0.95 区间
    confidence = 0.3 + ratio * 0.65
    return round(min(confidence, 0.95), 2)


# ---------------------------------------------------------------------------
# 核心函数：计算信用评级
# ---------------------------------------------------------------------------

def calculate_rating(
    risk_assessment: RiskAssessment,
    profile_text: str = "",
    materials: str = "",
    llm_json_func: Callable | None = None,
) -> CreditRating:
    """基于风险评估计算信用评级

    Args:
        risk_assessment: 5维风险评估结果
        profile_text: 企业画像文本（用于提取营收）
        materials: 企业材料全文（用于提取资产）
        llm_json_func: BaseAgent.llm_json 函数引用（可选，用于LLM增强）

    Returns:
        CreditRating 评级结果
    """
    score = risk_assessment.overall_score
    rating, label = _score_to_rating(score)

    # 提取正面/负面因素
    positive = []
    negative = []
    for dim in risk_assessment.dimensions:
        if dim.score >= 70:
            positive.append(
                f"{dim.name}表现{dim.level}（{dim.score}分）"
            )
        elif dim.score < 50:
            negative.append(
                f"{dim.name}评估为{dim.level}（{dim.score}分）"
            )
        for factor in dim.key_factors:
            if dim.score >= 60:
                positive.append(factor)
            elif dim.score < 40:
                negative.append(factor)

    # 去重，保留前几条
    positive = list(dict.fromkeys(positive))[:5]
    negative = list(dict.fromkeys(negative))[:5]

    # 计算建议额度
    revenue = _extract_revenue_amount(profile_text)
    assets = _extract_asset_amount(materials)
    limit_str = suggest_credit_limit(rating, revenue, assets)

    # 置信度
    confidence = _calculate_confidence(risk_assessment)

    return CreditRating(
        rating=rating,
        rating_label=label,
        score=score,
        positive_factors=positive,
        negative_factors=negative,
        suggested_limit=limit_str,
        confidence=confidence,
    )
