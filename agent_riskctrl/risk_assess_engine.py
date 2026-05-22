# -*- coding: utf-8 -*-
"""agent_riskctrl.risk_assess_engine — 客户风险评级引擎 (W1 Phase D · 2026-05-21).

Per codex R3 R3.2 #3 (user ack 2026-05-21):

新业务方向 · "客户风险评级" (vs 旧 DSL 业务回测)·
旧 DSL ``/dsl_gen`` + ``/backtest`` endpoint 全保留 (backward compat) ·
本模块仅提供新 ``/risk_assess`` endpoint 实现.

输出 (per codex R3 R3.2 #3 ack):
- 评级: 低 / 中 / 高 (3 段)
- Top risks: 命中维度的具体风险描述 list
- 缓释 (mitigations): 针对 top risks 的对策建议
- 后审周期 (review_cycle_months): 12 / 6 / 3 (低/中/高)

7 维 (codex R3 R3.2 #3 ack):
- credit (信用)              · 履约历史 / overdue / PD
- financial (财务)           · 债务率 / 流动比 / 杠杆
- transaction (交易)         · 流水 / 频率 / 净流入
- industry (行业)            · 景气 / 周期 / policy risk
- guarantee (担保)           · 抵质押 / 保证人
- concentration (集中度)     · 客户集中度 / 行业集中度
- negative_sentiment_judicial · 诉讼 / 处罚 / 舆情

实现 (per 刘野 CLAUDE.md §3.1 + R3 R3.2 #3 ack):

- **加权 risk model 确定性出分** (不让 LLM 算分 · 防幻觉)
  · 各维度 0-100 分 · 加权汇总 → composite_risk_score
  · risk_grade = 低 / 中 / 高 (composite < 30 / 30-60 / > 60)
  · 维度数据来源: canonical client_metadata + decision_context + credit_terms
- **LLM 写理由** (温度 0 · 仅生成自然语言 reasoning · 不改分)
  · LLM 不可用 (key 缺 / 调用 fail) → 模板兜底 reasoning · data_source=mock_fallback
- **deterministic + auditable**: 同 input → 同 output (固定权重)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 7-dim definition (codex R3 R3.2 #3 ack)
# ---------------------------------------------------------------------------


DIMENSIONS: list[dict[str, Any]] = [
    {
        "id": "credit",
        "label": "信用",
        "weight": 0.20,
        "factors": ["履约历史", "逾期记录", "PD 评级"],
    },
    {
        "id": "financial",
        "label": "财务",
        "weight": 0.18,
        "factors": ["资产负债率", "流动比", "杠杆"],
    },
    {
        "id": "transaction",
        "label": "交易",
        "weight": 0.12,
        "factors": ["流水稳定性", "交易频率", "净流入"],
    },
    {
        "id": "industry",
        "label": "行业",
        "weight": 0.12,
        "factors": ["景气度", "周期阶段", "政策风险"],
    },
    {
        "id": "guarantee",
        "label": "担保",
        "weight": 0.12,
        "factors": ["抵质押覆盖率", "保证人资质"],
    },
    {
        "id": "concentration",
        "label": "集中度",
        "weight": 0.10,
        "factors": ["客户集中度", "行业集中度", "地域集中度"],
    },
    {
        "id": "negative_sentiment_judicial",
        "label": "舆情司法",
        "weight": 0.16,
        "factors": ["诉讼记录", "行政处罚", "负面舆情"],
    },
]


# Sum of weights MUST = 1.0 (deterministic guarantee)
_TOTAL_WEIGHT = sum(d["weight"] for d in DIMENSIONS)
assert abs(_TOTAL_WEIGHT - 1.0) < 0.001, f"DIMENSIONS weights sum != 1.0 · got {_TOTAL_WEIGHT}"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class RiskAssessResult:
    """客户风险评级结果 · 共形 decision_context-schema 7-dim score_breakdown."""

    composite_risk_score: float  # 0-100 (越高 = 风险越高 · 与 credit 评分反向)
    risk_grade: str  # "低" / "中" / "高"
    dimension_scores: dict[str, float]  # 7-dim raw scores (0-100)
    top_risks: list[dict[str, str]]  # [{dimension, factor, description, severity}, ...]
    mitigations: list[str]  # 针对 top_risks 的缓释建议
    review_cycle_months: int  # 12 / 6 / 3
    reasoning: str  # LLM 或 template 生成
    confidence: float  # 0-1
    data_source: str  # "live" / "mock_fallback"


# ---------------------------------------------------------------------------
# Deterministic scoring (per dim · canonical input → 0-100 score)
# ---------------------------------------------------------------------------


def _score_credit_dim(client_metadata: dict, decision_context: Optional[dict]) -> float:
    """信用维度评分 · 基于 PD / overdue 历史.

    Score 含义: 越高 = 风险越高 (与 credit Agent 评分反向 · per risk model convention).

    数据来源:
    - decision_context.score_breakdown.repayment_history (credit 已算) → 反转
    - client_metadata.CREDIT_OVERDUE_RECORD (字符串叙述 → 关键词命中)
    - client_metadata.CLIENT_PD_RATING (PD 评级 1-9 · 9 最差)
    """
    # 优先复用 credit Agent 已算的 repayment_history (反转 100 - x)
    if decision_context:
        bd = decision_context.get("score_breakdown") or {}
        rh = bd.get("repayment_history")
        if rh is not None:
            try:
                return max(0.0, min(100.0, 100.0 - float(rh)))
            except (ValueError, TypeError):
                pass

    # Fallback: PD rating + overdue keyword
    pd_rating = client_metadata.get("CLIENT_PD_RATING") or client_metadata.get("CREDIT_PD_RATING")
    if pd_rating:
        try:
            pd_val = int(str(pd_rating).strip())
            # PD 1 (最好) → 10 分 · PD 9 (最差) → 90 分
            return max(0.0, min(100.0, 10.0 + (pd_val - 1) * 10.0))
        except (ValueError, TypeError):
            pass

    overdue = str(
        client_metadata.get("CREDIT_OVERDUE_RECORD")
        or client_metadata.get("CLIENT_OVERDUE_RECORD")
        or ""
    )
    if any(kw in overdue for kw in ("无", "未发生", "0 次")):
        return 15.0  # 低风险
    if any(kw in overdue for kw in ("严重", "60 天以上", "90 天以上", "M3+")):
        return 80.0  # 高风险
    if any(kw in overdue for kw in ("逾期", "M1", "M2", "30 天")):
        return 50.0  # 中风险
    return 35.0  # 默认 (信息不足 · 偏中低)


def _score_financial_dim(client_metadata: dict, decision_context: Optional[dict]) -> float:
    """财务维度 · 资产负债率 / 流动比 / 杠杆."""
    # 复用 credit financial_health (反转)
    if decision_context:
        bd = decision_context.get("score_breakdown") or {}
        fh = bd.get("financial_health")
        if fh is not None:
            try:
                return max(0.0, min(100.0, 100.0 - float(fh)))
            except (ValueError, TypeError):
                pass

    # Fallback: debt_ratio if present
    debt_ratio = client_metadata.get("CLIENT_DEBT_RATIO") or client_metadata.get("DEBT_RATIO")
    if debt_ratio:
        try:
            val = float(str(debt_ratio).replace("%", "").strip())
            # 负债率 0%→0 · 50%→50 · 90%+→90+
            if val <= 1.0:
                val = val * 100  # 0-1 区间转 %
            return max(0.0, min(100.0, val))
        except (ValueError, TypeError):
            pass

    return 40.0  # 默认中低


def _score_transaction_dim(client_metadata: dict, material_facts: Optional[dict]) -> float:
    """交易维度 · 流水 / 频率 / 净流入."""
    if material_facts:
        cf = str(material_facts.get("FINANCIAL_CASH_FLOW_DESC") or "")
        if any(kw in cf for kw in ("充足", "稳定", "正常")):
            return 25.0
        if any(kw in cf for kw in ("不足", "紧张", "断流", "负流入")):
            return 70.0
    return 40.0


def _score_industry_dim(client_metadata: dict) -> float:
    """行业维度 · 景气 / 周期 / 政策."""
    industry = str(
        client_metadata.get("CLIENT_INDUSTRY_FULL")
        or client_metadata.get("CLIENT_INDUSTRY_CODE")
        or ""
    )
    # 简化分类 (生产应接行业景气 KB)
    high_risk_keywords = ["房地产", "教培", "金融", "P2P", "网贷", "采矿", "煤炭"]
    if any(kw in industry for kw in high_risk_keywords):
        return 70.0
    medium_keywords = ["制造业", "建筑", "餐饮", "零售"]
    if any(kw in industry for kw in medium_keywords):
        return 45.0
    return 30.0  # 默认低风险 (科技/医疗/农业等)


def _score_guarantee_dim(credit_terms: Optional[dict], material_facts: Optional[dict]) -> float:
    """担保维度 · 抵质押 / 保证人."""
    guarantee_method = ""
    if credit_terms:
        guarantee_method = str(credit_terms.get("GUARANTEE_METHOD") or "")
    if material_facts and not guarantee_method:
        guarantee_method = str(material_facts.get("GUARANTEE_DESCRIPTION") or "")

    if "抵押" in guarantee_method or "质押" in guarantee_method:
        return 20.0  # 强担保
    if "保证" in guarantee_method:
        return 45.0  # 一般担保
    if "信用" in guarantee_method or "无担保" in guarantee_method:
        return 70.0  # 弱担保
    return 50.0


def _score_concentration_dim(material_facts: Optional[dict]) -> float:
    """集中度维度 · 客户集中度 / 行业集中度."""
    if material_facts:
        concentration_desc = str(material_facts.get("CUSTOMER_CONCENTRATION_DESC") or "")
        if any(kw in concentration_desc for kw in ("分散", "多元化")):
            return 25.0
        if any(kw in concentration_desc for kw in ("单一", "高度集中", "大于 50%")):
            return 75.0
    return 40.0  # 默认中等


def _score_negative_dim(client_metadata: dict, decision_context: Optional[dict]) -> float:
    """舆情司法维度 · 诉讼 / 处罚 / 负面."""
    # 优先复用 decision_context.negative_judicial (credit 已算 · 反转)
    if decision_context:
        bd = decision_context.get("score_breakdown") or {}
        nj = bd.get("negative_judicial")
        if nj is not None:
            try:
                return max(0.0, min(100.0, 100.0 - float(nj)))
            except (ValueError, TypeError):
                pass

        # 红线触发 → 高风险信号
        redlines = decision_context.get("redlines_triggered") or []
        if any("lawsuit" in str(r).lower() or "penalty" in str(r).lower() or "judicial" in str(r).lower()
               for r in redlines):
            return 80.0

    legal_desc = str(
        client_metadata.get("CLIENT_LEGAL_RISK_DESC")
        or client_metadata.get("CLIENT_LAWSUIT_RECORD")
        or ""
    )
    if any(kw in legal_desc for kw in ("无", "未发生", "0 起")):
        return 15.0
    if any(kw in legal_desc for kw in ("重大", "未决", "悬而未决", "败诉")):
        return 75.0
    if any(kw in legal_desc for kw in ("诉讼", "起诉", "处罚")):
        return 50.0
    return 25.0


# ---------------------------------------------------------------------------
# Top risks + mitigations (deterministic · per dim threshold)
# ---------------------------------------------------------------------------


_HIGH_RISK_THRESHOLD = 60.0


def _build_top_risks(
    dimension_scores: dict[str, float],
    client_metadata: dict,
) -> list[dict[str, str]]:
    """从 dim_scores 派生 top_risks (deterministic) · 按 score 降序取前 3."""
    sorted_dims = sorted(
        DIMENSIONS, key=lambda d: -dimension_scores.get(d["id"], 0.0),
    )
    top_risks: list[dict[str, str]] = []
    for dim in sorted_dims:
        score = dimension_scores.get(dim["id"], 0.0)
        if score < _HIGH_RISK_THRESHOLD or len(top_risks) >= 3:
            break

        severity = "高" if score >= 75 else "中"
        if dim["id"] == "credit":
            desc = f"信用风险偏高 (评分 {score:.0f})· 历史履约记录欠佳"
        elif dim["id"] == "financial":
            desc = f"财务风险偏高 (评分 {score:.0f})· 杠杆 / 负债率超阈"
        elif dim["id"] == "transaction":
            desc = f"交易风险偏高 (评分 {score:.0f})· 流水稳定性不足"
        elif dim["id"] == "industry":
            industry = client_metadata.get("CLIENT_INDUSTRY_FULL", "")
            desc = f"行业风险偏高 (评分 {score:.0f})· {industry} 行业景气下行"
        elif dim["id"] == "guarantee":
            desc = f"担保风险偏高 (评分 {score:.0f})· 抵质押覆盖不足"
        elif dim["id"] == "concentration":
            desc = f"集中度风险偏高 (评分 {score:.0f})· 客户/行业过度集中"
        else:
            desc = f"舆情司法风险偏高 (评分 {score:.0f})· 诉讼/处罚记录"

        top_risks.append({
            "dimension": dim["id"],
            "dimension_label": dim["label"],
            "score": round(score, 1),
            "severity": severity,
            "description": desc,
        })
    return top_risks


def _build_mitigations(top_risks: list[dict[str, str]]) -> list[str]:
    """每条 top_risk 配 1-2 条缓释建议 (deterministic template)."""
    mitigations: list[str] = []
    for risk in top_risks:
        dim_id = risk["dimension"]
        if dim_id == "credit":
            mitigations.append("调高利率 50-100bp · 缩短贷款期限至 6 个月内")
        elif dim_id == "financial":
            mitigations.append("要求补充财务报表 · 增加保证人或抵押物")
        elif dim_id == "transaction":
            mitigations.append("增加交易流水监控频率 · 设置异常告警阈值")
        elif dim_id == "industry":
            mitigations.append("行业敞口限额管控 · 跟踪行业景气月度变化")
        elif dim_id == "guarantee":
            mitigations.append("追加抵质押覆盖率至 130%+ · 评估保证人代偿能力")
        elif dim_id == "concentration":
            mitigations.append("敞口分散化 · 单户敞口控制在总资产 5% 以内")
        else:
            mitigations.append("加密司法/舆情监测 · 设置自动预警 · 必要时启动催收")
    return mitigations


# ---------------------------------------------------------------------------
# Compose: weighted aggregate + grade + cycle
# ---------------------------------------------------------------------------


def _grade_and_cycle(composite_score: float) -> tuple[str, int]:
    """评级 + 后审周期 (低/中/高 · 12/6/3 月)."""
    if composite_score < 30:
        return "低", 12
    if composite_score < 60:
        return "中", 6
    return "高", 3


def _build_template_reasoning(
    result_partial: dict[str, Any],
    client_name: str,
) -> str:
    """LLM 不可用时的模板 reasoning · deterministic · 不假装 LLM 输出."""
    grade = result_partial["risk_grade"]
    score = result_partial["composite_risk_score"]
    top = result_partial["top_risks"]
    cycle = result_partial["review_cycle_months"]

    parts = [
        f"客户 {client_name or '未命名'} 综合风险评级 {grade} · 综合风险分 {score:.1f}/100 ·"
        f" 后审周期 {cycle} 个月。",
    ]
    if top:
        risks_str = "、".join(f"{r['dimension_label']}({r['severity']})" for r in top)
        parts.append(f"主要风险点: {risks_str}。")
    parts.append("[模板兜底 reasoning · 非 LLM 生成 · 建议人工复核]")
    return "".join(parts)


def _build_llm_reasoning_prompt(
    composite_score: float,
    risk_grade: str,
    dim_scores: dict[str, float],
    top_risks: list[dict],
    mitigations: list[str],
    client_metadata: dict,
) -> tuple[str, str]:
    """构 (system, user) prompt · LLM 仅写理由 · 不改分."""
    system = (
        "你是银行风控评级专家 · 基于已计算好的 7 维评分 + Top 风险 + 缓释建议 ·"
        "用 100-300 字写一段决策理由 (中文)。"
        "禁止: (1) 改变 score/verdict/grade · 完全照搬数值; (2) 编造数据 ·"
        "无数据的字段直接说 '数据不足'; (3) 兜底 '可能/大概'。"
        "结构: 1 句总评 · 2-3 句 top risk 分析 · 1 句后续建议。"
    )
    client_name = client_metadata.get("CLIENT_FULL_NAME", "")
    industry = client_metadata.get("CLIENT_INDUSTRY_FULL", "")
    dim_str = " · ".join(
        f"{d['label']}{dim_scores.get(d['id'], 0):.0f}"
        for d in DIMENSIONS
    )
    top_str = " / ".join(
        f"{r['dimension_label']}({r['severity']})" for r in top_risks
    ) or "无明显高风险维度"
    miti_str = "、".join(mitigations) or "维持现有管控"

    user = (
        f"客户: {client_name or '未提供'}\n"
        f"行业: {industry or '未提供'}\n"
        f"综合风险分: {composite_score:.1f}/100 · 评级 {risk_grade}\n"
        f"7 维评分: {dim_str}\n"
        f"Top risks: {top_str}\n"
        f"缓释建议: {miti_str}\n\n"
        "请写决策理由。"
    )
    return system, user


# ---------------------------------------------------------------------------
# Main entry · run_risk_assess
# ---------------------------------------------------------------------------


def run_risk_assess(
    *,
    client_metadata: dict,
    decision_context: Optional[dict] = None,
    credit_terms: Optional[dict] = None,
    material_facts: Optional[dict] = None,
    llm_caller: Optional[Callable[[str, str], str]] = None,
) -> RiskAssessResult:
    """主入口 · 计算客户风险评级 (deterministic 7 维 + LLM reasoning).

    Args:
        client_metadata: canonical client_metadata fields dict
        decision_context: credit Agent 决策结果 (optional · 提升 credit/financial 评分准确度)
        credit_terms: 授信条件 (optional · 用于 guarantee 评分)
        material_facts: 物料事实 (optional · 用于 transaction/concentration 评分)
        llm_caller: text caller (system, user) -> str · 返 "" → fallback template

    Returns:
        RiskAssessResult · 7 维 + 评级 + top risks + mitigations + reasoning + confidence

    确定性保证 (per 刘野 CLAUDE.md §3.1 + 证据支撑):
    - 同 input → 同 dim scores (固定权重 + 规则查表)
    - LLM 失败 → 模板兜底 + data_source=mock_fallback (不假装 live · 不静默兜底)
    """
    cm = client_metadata or {}
    dc = decision_context
    ct = credit_terms
    mf = material_facts

    # 7-dim scoring (deterministic)
    dim_scores = {
        "credit": _score_credit_dim(cm, dc),
        "financial": _score_financial_dim(cm, dc),
        "transaction": _score_transaction_dim(cm, mf),
        "industry": _score_industry_dim(cm),
        "guarantee": _score_guarantee_dim(ct, mf),
        "concentration": _score_concentration_dim(mf),
        "negative_sentiment_judicial": _score_negative_dim(cm, dc),
    }

    # Weighted composite
    composite_score = sum(
        dim_scores[d["id"]] * d["weight"] for d in DIMENSIONS
    )
    composite_score = max(0.0, min(100.0, composite_score))

    # Grade + cycle
    risk_grade, review_cycle = _grade_and_cycle(composite_score)

    # Top risks + mitigations
    top_risks = _build_top_risks(dim_scores, cm)
    mitigations = _build_mitigations(top_risks)

    # Reasoning · LLM 优先 · 失败模板兜底
    result_partial = {
        "composite_risk_score": composite_score,
        "risk_grade": risk_grade,
        "top_risks": top_risks,
        "review_cycle_months": review_cycle,
    }
    reasoning = ""
    data_source = "live"
    confidence = 0.85

    if llm_caller is not None:
        try:
            system, user = _build_llm_reasoning_prompt(
                composite_score, risk_grade, dim_scores,
                top_risks, mitigations, cm,
            )
            reasoning = llm_caller(system, user) or ""
        except Exception as exc:  # noqa: BLE001 · LLM 失败 silent fallback OK
            logger.warning(
                "[risk_assess] LLM reasoning failed · template fallback · err=%s",
                exc,
            )
            reasoning = ""

    if not reasoning.strip():
        reasoning = _build_template_reasoning(result_partial, cm.get("CLIENT_FULL_NAME", ""))
        data_source = "mock_fallback"
        confidence = 0.65  # 模板兜底 · 置信度降

    return RiskAssessResult(
        composite_risk_score=round(composite_score, 1),
        risk_grade=risk_grade,
        dimension_scores={k: round(v, 1) for k, v in dim_scores.items()},
        top_risks=top_risks,
        mitigations=mitigations,
        review_cycle_months=review_cycle,
        reasoning=reasoning,
        confidence=confidence,
        data_source=data_source,
    )


__all__ = [
    "DIMENSIONS",
    "RiskAssessResult",
    "run_risk_assess",
]
