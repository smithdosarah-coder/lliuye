# -*- coding: utf-8 -*-
"""对公评分模型 — 四维加权（财务 35% / 行业 15% / 经营 25% / 担保 25%）

对应 PRD 附录 A.1。
确定性计算：分段线性插值 + 子项加权，无 LLM 调用。
与现有 risk_classifier.py 是互补关系：v1.0 的 LLM 驱动评估可作为高级解读入口，
这里提供可审计、可重现的数值评分，作为 Dashboard 的骨架。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .risk_appetite_config import RiskAppetiteConfig


@dataclass
class CorporateScoringResult:
    financial_score: int = 0
    industry_score: int = 0
    operational_score: int = 0
    guarantee_score: int = 0
    composite_score: int = 0
    risk_grade: str = "D"
    sub_scores: dict = field(default_factory=dict)  # Phase B.2.1 hotfix · int dict (frontend 渲染需 number)
    sub_details: dict = field(default_factory=dict)  # Phase B.2.1 hotfix · dict detail (decision_graph evidence 用)
    industry_peer_gap: dict = field(default_factory=dict)
    amount_methods: dict = field(default_factory=dict)  # 四种额度测算结果

    def to_dict(self) -> dict:
        return asdict(self)


def _interp(x: float, points: list[tuple[float, float]]) -> float:
    """分段线性插值；points 要求按 x 升序"""
    if not points:
        return 50.0
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if x0 <= x <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return 50.0


# 分段插值表：x（指标值）→ y（0-100 评分）
SCORE_CURVES = {
    # 财务
    "debt_ratio": [(0.20, 95), (0.40, 85), (0.55, 70), (0.70, 50), (0.85, 25), (1.00, 5)],
    "revenue_growth": [(-0.30, 10), (-0.10, 40), (0.00, 55), (0.10, 70), (0.25, 85), (0.50, 95)],
    "net_margin": [(-0.10, 5), (0.00, 35), (0.03, 55), (0.06, 72), (0.10, 85), (0.20, 95)],
    "current_ratio": [(0.5, 15), (1.0, 50), (1.5, 75), (2.0, 88), (3.0, 95)],
    "ar_turnover_days": [(30, 95), (60, 85), (90, 70), (120, 55), (180, 30), (365, 10)],
    "cashflow_quality": [(-0.5, 10), (0.0, 45), (0.05, 65), (0.15, 82), (0.30, 95)],  # ocf/revenue
    # 行业
    "prosperity_index": [(30, 20), (50, 50), (65, 72), (80, 90)],
    "policy_sensitivity": [(0.0, 90), (0.3, 75), (0.6, 55), (0.8, 35), (1.0, 20)],
    "cyclicality": {"low": 85, "medium": 65, "high": 45},
    # 经营
    "established_years": [(1, 30), (3, 60), (5, 75), (10, 88), (20, 95)],
    "revenue_scale": [(1000, 30), (10000, 55), (30000, 72), (100000, 88), (500000, 95)],  # 万
    "cashflow_coverage": [(-1, 10), (0, 35), (1, 65), (2, 82), (5, 95)],
    "customer_concentration": [(0.0, 90), (0.2, 80), (0.4, 60), (0.6, 40), (0.8, 20)],
    # 担保
    "coverage_ratio": [(0.0, 10), (0.5, 40), (1.0, 68), (1.5, 82), (2.5, 95)],
    "guarantor_strength_score": [(0, 10), (30, 30), (50, 55), (70, 78), (90, 92)],
}


class CorporateScoringModel:
    """对公四维评分模型"""

    DEFAULT_WEIGHTS = {
        "financial": 0.35,
        "industry": 0.15,
        "operational": 0.25,
        "guarantee": 0.25,
    }

    GRADE_THRESHOLDS = [(80, "A"), (65, "B"), (50, "C"), (0, "D")]

    def __init__(self, appetite: RiskAppetiteConfig | None = None):
        self.appetite = appetite or RiskAppetiteConfig.default("corporate")

    # ------------------------------------------------------------------
    # 子项评分
    # ------------------------------------------------------------------

    def _score_financial(self, f: dict) -> tuple[int, dict]:
        # §3.1 反模式修复：所有比率/派生指标在 feature_extractor 一处通过
        # financial_analyzer 算齐，本方法只读消费 + 分段插值，不再现场算 ratio。
        sub = {
            "资产负债率": _interp(f.get("financial.debt_ratio", 0.5), SCORE_CURVES["debt_ratio"]),
            "营收增长率": _interp(f.get("financial.revenue_growth", 0), SCORE_CURVES["revenue_growth"]),
            "净利率": _interp(f.get("financial.net_margin", 0), SCORE_CURVES["net_margin"]),
            "流动比率": _interp(f.get("financial.current_ratio", 1.0), SCORE_CURVES["current_ratio"]),
            "应收账款周转": _interp(f.get("financial.ar_turnover_days", 90), SCORE_CURVES["ar_turnover_days"]),
            "现金流质量": _interp(f.get("financial.ocf_to_revenue", 0) or 0, SCORE_CURVES["cashflow_quality"]),
        }
        weights = {"资产负债率": 0.25, "营收增长率": 0.20, "净利率": 0.15,
                   "流动比率": 0.15, "应收账款周转": 0.10, "现金流质量": 0.15}
        score = sum(sub[k] * weights[k] for k in sub)
        return int(round(score)), {k: int(round(v)) for k, v in sub.items()}

    def _score_industry(self, f: dict) -> tuple[int, dict]:
        cyc = f.get("industry.cyclicality", "medium")
        sub = {
            "行业景气度": _interp(f.get("industry.prosperity_index", 60), SCORE_CURVES["prosperity_index"]),
            "政策敏感性": _interp(f.get("industry.policy_sensitivity", 0.4), SCORE_CURVES["policy_sensitivity"]),
            "周期性": SCORE_CURVES["cyclicality"].get(cyc, 65),
            "黑名单": 5 if f.get("industry.in_blacklist") else 90,
        }
        weights = {"行业景气度": 0.35, "政策敏感性": 0.25, "周期性": 0.25, "黑名单": 0.15}
        score = sum(sub[k] * weights[k] for k in sub)
        return int(round(score)), {k: int(round(v)) for k, v in sub.items()}

    def _score_operational(self, f: dict) -> tuple[int, dict]:
        sub = {
            "成立年限": _interp(f.get("operational.established_years", 3), SCORE_CURVES["established_years"]),
            "营收规模": _interp(f.get("operational.revenue_scale", 0), SCORE_CURVES["revenue_scale"]),
            "现金流覆盖": _interp(f.get("operational.cashflow_coverage", 0.5), SCORE_CURVES["cashflow_coverage"]),
            "客户集中度": _interp(f.get("operational.customer_concentration", 0.2), SCORE_CURVES["customer_concentration"]),
            "员工规模": _interp(max(f.get("operational.employee_count", 0), 1),
                              [(5, 30), (20, 55), (50, 70), (100, 82), (500, 92)]),
        }
        weights = {"成立年限": 0.20, "营收规模": 0.20, "现金流覆盖": 0.25,
                   "客户集中度": 0.20, "员工规模": 0.15}
        score = sum(sub[k] * weights[k] for k in sub)
        return int(round(score)), {k: int(round(v)) for k, v in sub.items()}

    def _score_guarantee(self, f: dict) -> tuple[int, dict]:
        coverage = f.get("guarantee.coverage_ratio", 0)
        has = f.get("guarantee.has_any_collateral", 0)
        if not has:
            return 15, {"有无担保": 15}
        type_score = 80 if "房产" in (f.get("guarantee.collateral_type") or "") else 60
        if not (f.get("guarantee.collateral_type") or ""):
            type_score = 40
        sub = {
            "覆盖率": _interp(coverage, SCORE_CURVES["coverage_ratio"]),
            "担保物类型": type_score,
            "保证人实力": _interp(f.get("guarantee.guarantor_strength_score", 50),
                                SCORE_CURVES["guarantor_strength_score"]),
            "组合完整性": f.get("guarantee.combination_completeness", 0.5) * 100,
        }
        weights = {"覆盖率": 0.40, "担保物类型": 0.25, "保证人实力": 0.20, "组合完整性": 0.15}
        score = sum(sub[k] * weights[k] for k in sub)
        return int(round(score)), {k: int(round(v)) for k, v in sub.items()}

    # ------------------------------------------------------------------
    # 额度测算（4 种方法，返回万元）
    # ------------------------------------------------------------------

    def _estimate_amounts(self, f: dict, composite: int) -> dict:
        revenue = f.get("financial.revenue", 0) or 0  # 万
        net_assets = f.get("financial.net_assets", 0) or 0
        ocf = f.get("financial.operating_cash_flow", 0) or 0
        collateral_value = f.get("guarantee.collateral_value", 0) or 0
        term_months = f.get("request.term_months", 12) or 12

        # 评级系数
        if composite >= 80:
            coef_rev, leverage, cov_mult, col_rate = 0.15, 0.60, 2.0, 0.70
        elif composite >= 65:
            coef_rev, leverage, cov_mult, col_rate = 0.10, 0.40, 1.5, 0.60
        elif composite >= 50:
            coef_rev, leverage, cov_mult, col_rate = 0.06, 0.25, 1.0, 0.50
        else:
            coef_rev, leverage, cov_mult, col_rate = 0.03, 0.10, 0.5, 0.40

        m_revenue = revenue * coef_rev
        m_netasset = net_assets * leverage
        m_cashflow = ocf * cov_mult * (36 / max(term_months, 12))
        m_collateral = collateral_value * col_rate

        return {
            "revenue_method": round(max(m_revenue, 0), 1),
            "netasset_method": round(max(m_netasset, 0), 1),
            "cashflow_method": round(max(m_cashflow, 0), 1),
            "collateral_method": round(max(m_collateral, 0), 1),
        }

    # ------------------------------------------------------------------
    def _grade(self, composite: int) -> str:
        thresholds = self.appetite.grade_thresholds or self.GRADE_THRESHOLDS
        for cutoff, grade in thresholds:
            if composite >= cutoff:
                return grade
        return "D"

    def score(self, features: dict) -> CorporateScoringResult:
        fin_score, fin_sub = self._score_financial(features)
        ind_score, ind_sub = self._score_industry(features)
        ope_score, ope_sub = self._score_operational(features)
        guar_score, guar_sub = self._score_guarantee(features)

        w = self.appetite.dimension_weights or self.DEFAULT_WEIGHTS
        total_w = sum(w.values()) or 1.0
        composite = (
            fin_score * w.get("financial", 0.35)
            + ind_score * w.get("industry", 0.15)
            + ope_score * w.get("operational", 0.25)
            + guar_score * w.get("guarantee", 0.25)
        ) / total_w
        composite_int = int(round(composite))

        # 同业分位差
        peer_gap = {
            "debt_ratio_gap": features.get("financial.debt_ratio", 0)
                - features.get("industry.debt_ratio_median", 0),
            "net_margin_gap": features.get("financial.net_margin", 0)
                - features.get("industry.net_margin_median", 0),
            "revenue_growth_gap": features.get("financial.revenue_growth", 0)
                - features.get("industry.revenue_growth_median", 0),
            "ar_turnover_gap": features.get("financial.ar_turnover_days", 0)
                - features.get("industry.ar_turnover_days_median", 0),
        }

        amounts = self._estimate_amounts(features, composite_int)

        return CorporateScoringResult(
            financial_score=fin_score,
            industry_score=ind_score,
            operational_score=ope_score,
            guarantee_score=guar_score,
            composite_score=composite_int,
            risk_grade=self._grade(composite_int),
            # Phase B.2.1 hotfix (PM 2026-05-10) · sub_scores 必须是 int (frontend 雷达图渲染需 number)
            sub_scores={
                "financial": fin_score,
                "industry": ind_score,
                "operational": ope_score,
                "guarantee": guar_score,
            },
            # detail dict (decision_graph evidence chain 用)
            sub_details={
                "financial": fin_sub,
                "industry": ind_sub,
                "operational": ope_sub,
                "guarantee": guar_sub,
            },
            industry_peer_gap=peer_gap,
            amount_methods=amounts,
        )
