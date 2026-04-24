# -*- coding: utf-8 -*-
"""Agent2 授信决策辅助 - 审批建议引擎

基于信用评级和风险评估，生成审批决策建议（通过/谨慎/拒绝）、
附加条件和风险缓释措施。
"""

from __future__ import annotations

from typing import Callable
from pydantic import BaseModel, Field

from .risk_classifier import RiskAssessment
from .rating_engine import CreditRating
from .prompts import SYSTEM_APPROVAL


# ---------------------------------------------------------------------------
# Pydantic 模型
# ---------------------------------------------------------------------------

class ApprovalDecision(BaseModel):
    """审批决策建议"""
    decision: str = ""                          # 建议通过 / 建议谨慎 / 建议拒绝
    conditions: list[str] = Field(default_factory=list)         # 附加条件
    risk_mitigations: list[str] = Field(default_factory=list)   # 风险缓释措施
    explanation: str = ""                       # 决策说明（可解释性输出）


# ---------------------------------------------------------------------------
# 规则驱动的审批决策
# ---------------------------------------------------------------------------

def _rule_based_approval(
    rating: CreditRating,
    risk_assessment: RiskAssessment,
) -> ApprovalDecision:
    """基于规则生成审批决策（LLM兜底方案）"""

    r = rating.rating
    score = rating.score

    if r in ("A", "B") and score >= 60:
        decision = "建议通过"
        conditions = []
        mitigations = []

        if r == "B":
            conditions.append(
                "建议定期跟踪企业经营情况，每半年复查一次"
            )
        if rating.negative_factors:
            conditions.append(
                f"关注以下风险点：{'、'.join(rating.negative_factors[:2])}"
            )

        # 检查各维度是否有低分项
        for dim in risk_assessment.dimensions:
            if dim.score < 50:
                conditions.append(
                    f"{dim.name}评分偏低（{dim.score}分），建议加强监控"
                )
                mitigations.append(
                    f"针对{dim.name}制定专项风控措施"
                )

        explanation = (
            f"企业信用评级为{r}级（{rating.rating_label}），"
            f"综合评分{score:.1f}分。"
            f"整体风险可控，建议按正常流程审批。"
        )
        if rating.positive_factors:
            explanation += (
                f"主要优势：{'、'.join(rating.positive_factors[:3])}。"
            )

        return ApprovalDecision(
            decision=decision,
            conditions=conditions,
            risk_mitigations=mitigations,
            explanation=explanation,
        )

    elif r == "C" and score >= 40:
        conditions = [
            "建议增加担保措施（追加抵押物或引入第三方保证）",
            "授信期限建议控制在1年以内",
            "建议适当降低授信额度",
            "每季度定期复查企业经营状况",
        ]
        mitigations = [
            "加强贷后管理频率",
            "设置财务指标预警阈值",
        ]
        for dim in risk_assessment.dimensions:
            if dim.score < 40:
                mitigations.append(
                    f"针对{dim.name}（{dim.score}分）制定专项监控方案"
                )

        explanation = (
            f"企业信用评级为C级（一般），综合评分{score:.1f}分。"
            f"存在一定风险因素，建议在附加条件下谨慎审批。"
        )
        if rating.negative_factors:
            explanation += (
                f"主要风险点：{'、'.join(rating.negative_factors[:3])}。"
            )

        return ApprovalDecision(
            decision="建议谨慎",
            conditions=conditions,
            risk_mitigations=mitigations,
            explanation=explanation,
        )

    else:  # D or E
        conditions = []
        mitigations = []

        if r == "D":
            decision = "建议拒绝"
            conditions.append(
                "如确需授信，须提供全额担保并经上级审批"
            )
            mitigations.append("仅限短期、有明确还款来源的授信")
            mitigations.append("要求企业提交经营改善计划")
        else:
            decision = "建议拒绝"
            mitigations.append(
                "建议持续关注企业状况，待风险缓释后再议"
            )

        explanation = (
            f"企业信用评级为{r}级（{rating.rating_label}），"
            f"综合评分{score:.1f}分。风险水平较高，不建议授信。"
        )
        if rating.negative_factors:
            explanation += (
                f"核心风险：{'、'.join(rating.negative_factors[:3])}。"
            )

        return ApprovalDecision(
            decision=decision,
            conditions=conditions,
            risk_mitigations=mitigations,
            explanation=explanation,
        )


# ---------------------------------------------------------------------------
# 核心函数：生成审批建议
# ---------------------------------------------------------------------------

def generate_approval(
    rating: CreditRating,
    risk_assessment: RiskAssessment,
    profile_text: str = "",
    llm_chat_func: Callable[[str, str], str] | None = None,
) -> ApprovalDecision:
    """生成审批决策建议

    先用规则引擎生成基础决策，再用LLM增强决策说明的可解释性。

    Args:
        rating: 信用评级结果
        risk_assessment: 5维风险评估结果
        profile_text: 企业画像文本
        llm_chat_func: BaseAgent.llm_chat 函数引用（可选）

    Returns:
        ApprovalDecision 审批决策建议
    """
    # 规则引擎生成基础决策
    decision = _rule_based_approval(rating, risk_assessment)

    # LLM 增强决策说明
    if llm_chat_func is not None:
        dim_summary = "\n".join(
            f"- {d.name}：{d.score}分（{d.level}），"
            f"关键因素：{'、'.join(d.key_factors[:2])}"
            for d in risk_assessment.dimensions
        )
        user_prompt = f"""请基于以下评估结果，给出详细的审批决策说明。

## 信用评级
评级：{rating.rating}级（{rating.rating_label}），综合评分：{rating.score:.1f}
建议额度：{rating.suggested_limit}

## 各维度评估
{dim_summary}

## 风险摘要
{risk_assessment.summary}

## 企业画像
{profile_text[:3000] if profile_text else '（未提供）'}

## 初步决策
决策：{decision.decision}
附加条件：{'、'.join(decision.conditions) if decision.conditions else '无'}

请给出300字以内的审批决策说明，要求：
1. 明确表达审批态度
2. 引用具体评估数据和依据
3. 说明主要风险考量
4. 如有附加条件，解释条件设置的合理性"""

        try:
            llm_explanation = llm_chat_func(SYSTEM_APPROVAL, user_prompt)
            if llm_explanation and len(llm_explanation) > 30:
                decision.explanation = llm_explanation[:800]
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
            pass  # 保持规则引擎的说明

    return decision
