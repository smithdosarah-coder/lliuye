# -*- coding: utf-8 -*-
"""Agent2 授信决策辅助 - 5维风险分类器

对企业进行财务风险、经营风险、行业风险、管理风险、担保风险五个维度的
量化评估，每个维度输出评分(1-100)、等级、关键因素和证据。
"""

from __future__ import annotations

import json
from typing import Callable
from pydantic import BaseModel, Field

from .prompts import SYSTEM_RISK_ASSESS


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class RiskDimension(BaseModel):
    """单维度风险评估结果"""
    name: str = ""                              # 维度名称
    score: int = 50                             # 评分 1-100
    level: str = ""                             # 等级描述（如"良好"）
    key_factors: list[str] = Field(default_factory=list)  # 关键风险因素
    evidence: str = ""                          # 评估证据（引用材料原文/数据）


class RiskAssessment(BaseModel):
    """5维风险综合评估结果"""
    dimensions: list[RiskDimension] = Field(default_factory=list)
    overall_score: float = 0.0                  # 加权综合评分
    summary: str = ""                           # 综合风险摘要


# ---------------------------------------------------------------------------
# 维度定义与权重
# ---------------------------------------------------------------------------

RISK_DIMENSIONS = [
    {"name": "财务风险", "weight": 0.30},
    {"name": "经营风险", "weight": 0.25},
    {"name": "行业风险", "weight": 0.15},
    {"name": "管理风险", "weight": 0.15},
    {"name": "担保风险", "weight": 0.15},
]

SCORE_LEVELS = [
    (80, 100, "优秀"),
    (60, 79, "良好"),
    (40, 59, "一般"),
    (20, 39, "关注"),
    (0, 19, "高危"),
]


def _score_to_level(score: int) -> str:
    """将评分映射为等级描述"""
    for low, high, label in SCORE_LEVELS:
        if low <= score <= high:
            return label
    return "未知"


def _calculate_overall(dimensions: list[RiskDimension]) -> float:
    """按权重计算综合评分"""
    if not dimensions:
        return 0.0
    total = 0.0
    weight_sum = 0.0
    for dim in dimensions:
        for cfg in RISK_DIMENSIONS:
            if cfg["name"] == dim.name:
                total += dim.score * cfg["weight"]
                weight_sum += cfg["weight"]
                break
    return round(total / weight_sum, 1) if weight_sum > 0 else 0.0


# ---------------------------------------------------------------------------
# 默认评估（LLM 不可用时的兜底）
# ---------------------------------------------------------------------------

def _default_assessment(profile_text: str, materials: str) -> RiskAssessment:
    """基于关键词的简单规则评估，作为LLM不可用时的兜底"""
    combined = (profile_text or "") + "\n" + (materials or "")
    dims = []
    for cfg in RISK_DIMENSIONS:
        score = 50  # 默认中等
        factors = ["信息不足，采用保守评分"]
        evidence = "未获取到充分的评估材料"

        if cfg["name"] == "财务风险":
            if "亏损" in combined or "净利润为负" in combined:
                score = 30
                factors = ["存在亏损迹象"]
                evidence = "材料中提及亏损相关内容"
            elif "盈利" in combined or "净利润" in combined:
                score = 65
                factors = ["有盈利记录"]
                evidence = "材料中提及盈利相关内容"

        elif cfg["name"] == "经营风险":
            if "订单" in combined or "在手项目" in combined:
                score = 65
                factors = ["有在手订单/项目"]
                evidence = "材料中提及订单或项目信息"

        elif cfg["name"] == "行业风险":
            if "政策支持" in combined or "新兴" in combined:
                score = 70
                factors = ["行业受政策支持"]
                evidence = "材料中提及政策利好信息"

        elif cfg["name"] == "管理风险":
            if "涉诉" in combined or "处罚" in combined:
                score = 35
                factors = ["存在涉诉或处罚记录"]
                evidence = "材料中提及法律或合规问题"

        elif cfg["name"] == "担保风险":
            if "抵押" in combined or "担保" in combined:
                score = 60
                factors = ["有担保安排"]
                evidence = "材料中提及担保相关内容"

        dims.append(RiskDimension(
            name=cfg["name"],
            score=score,
            level=_score_to_level(score),
            key_factors=factors,
            evidence=evidence,
        ))

    overall = _calculate_overall(dims)
    return RiskAssessment(
        dimensions=dims,
        overall_score=overall,
        summary=f"基于有限材料的保守评估，综合评分 {overall} 分。"
                f"建议补充更多材料以获得更准确的评估结果。",
    )


# ---------------------------------------------------------------------------
# 核心函数：LLM 驱动的风险分类
# ---------------------------------------------------------------------------

def classify_risks(
    profile_text: str,
    materials: str,
    llm_json_func: Callable | None = None,
) -> RiskAssessment:
    """执行5维风险评估

    Args:
        profile_text: 企业画像上下文文本
        materials: 企业材料全文（截断后）
        llm_json_func: BaseAgent.llm_json 函数引用

    Returns:
        RiskAssessment 完整评估结果
    """
    if llm_json_func is None:
        return _default_assessment(profile_text, materials)

    user_prompt = f"""请对以下企业进行5维风险评估。

## 企业画像
{profile_text or '（未提供）'}

## 企业材料
{materials[:12000] if materials else '（未提供）'}

请严格按照5个维度（财务风险、经营风险、行业风险、管理风险、担保风险）逐一评估，
每个维度给出score(1-100整数)、level、key_factors(list)和evidence。
最后给出overall_score（加权综合分）和summary。"""

    try:
        result = llm_json_func(
            SYSTEM_RISK_ASSESS,
            user_prompt,
            model_class=RiskAssessment,
            retries=3,
        )
        if isinstance(result, RiskAssessment):
            # 确保等级和综合分正确
            for dim in result.dimensions:
                dim.level = _score_to_level(dim.score)
            result.overall_score = _calculate_overall(result.dimensions)
            return result
        # 如果返回的是 dict（model_class 解析失败时的降级）
        if isinstance(result, dict):
            return RiskAssessment.model_validate(result)
    except Exception:
        pass

    return _default_assessment(profile_text, materials)
