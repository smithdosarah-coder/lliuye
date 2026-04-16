# -*- coding: utf-8 -*-
"""对私评分卡模型（FICO-式，300-850）

对应 PRD 第 6.6 节 + 附录 A.2 + mock_data/scorecard_weights.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .risk_appetite_config import RiskAppetiteConfig

_WEIGHTS_PATH = Path(__file__).parent / "mock_data" / "scorecard_weights.json"


def _load_weights() -> dict:
    try:
        with open(_WEIGHTS_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


@dataclass
class RetailScoringResult:
    fico_score: int = 500
    grade: str = "拒绝"
    sub_scores: dict = field(default_factory=dict)     # {category: {var: score}}
    category_scores: dict = field(default_factory=dict)  # {category: int}
    approved_limit_cap: float = 0.0     # 万元，档位允许上限
    rate_tier: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _lookup_score(value: Any, rule: Any) -> float:
    """按 score_maps 规则查分数。
    rule 可能是 list[[x,y],...]（分段插值）或 dict（直接映射）"""
    if isinstance(rule, list):
        if not rule:
            return 600
        pts = [(float(p[0]), float(p[1])) for p in rule]
        try:
            x = float(value or 0)
        except (TypeError, ValueError):
            return 600
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]
        for i in range(1, len(pts)):
            x0, y0 = pts[i - 1]
            x1, y1 = pts[i]
            if x0 <= x <= x1:
                if x1 == x0:
                    return y1
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return 600
    if isinstance(rule, dict):
        key = str(value)
        if key in rule:
            return float(rule[key])
        # 特殊值
        if value in rule:
            return float(rule[value])
        return float(rule.get("", 650))
    return 600


# 特征键 → score_map 键 的映射（4 大类）
FEATURE_TO_VAR = {
    "repayment_capacity": {
        "monthly_income_stability": "capacity.monthly_income_stability",
        "dti_ratio": "capacity.dti_ratio",
        "avg_balance_6m": "capacity.avg_balance_6m",
        "monthly_income_level": "capacity.monthly_income",
        "monthly_repay_capacity": "capacity.monthly_repay_capacity",
        "cash_surplus": "capacity.cash_surplus",
    },
    "repayment_willingness": {
        "query_count_24m": "credit.query_count_24m",
        "overdue_history": "credit.overdue_history",
        "cc_utilization": "credit.card_utilization",
        "credit_history_length": "credit.account_age_years",
        "social_security_months": "stability.social_security_months",
    },
    "stability": {
        "years_in_job": "stability.years_in_job",
        "years_at_address": "stability.years_at_address",
        "marital_status": "stability.marital_status",
        "education": "stability.education",
        "housing_type": "stability.housing_type",
        "age": "stability.age",
    },
    "collateral": {
        "collateral_type": "collateral.type",
        "ltv": "collateral.ltv",
        "title_verified": "collateral.title_verified",
        "mortgage_count": "collateral.mortgage_count",
        "valuation_source": "collateral.valuation_source",
    },
}


class RetailScoringModel:
    """对私评分卡模型"""

    DEFAULT_CATEGORY_WEIGHTS = {
        "repayment_capacity": 0.30,
        "repayment_willingness": 0.25,
        "stability": 0.25,
        "collateral": 0.20,
    }

    def __init__(self, appetite: RiskAppetiteConfig | None = None):
        self.appetite = appetite or RiskAppetiteConfig.default("retail")
        self._raw = _load_weights()
        self.sub_var_weights = self._raw.get("sub_variable_weights", {}) or {}
        self.score_maps = self._raw.get("score_maps", {}) or {}
        self.grade_thresholds = self._raw.get("grade_thresholds") or [
            [800, "优", "LPR-10BP", 500],
            [760, "中优", "LPR", 300],
            [700, "良好", "LPR+20BP", 100],
            [680, "边界（人工复核）", "LPR+50BP", 50],
            [0, "拒绝", None, 0],
        ]

    def _category_score(self, features: dict, category: str) -> tuple[int, dict]:
        mapping = FEATURE_TO_VAR.get(category, {})
        weights = self.sub_var_weights.get(category, {})
        sub = {}
        total = 0.0
        weight_sum = 0.0
        for sub_var, feat_key in mapping.items():
            value = features.get(feat_key)
            score_map = self.score_maps.get(sub_var)
            if score_map is None:
                continue
            s = _lookup_score(value, score_map)
            sub[sub_var] = int(round(s))
            w = weights.get(sub_var, 0)
            total += s * w
            weight_sum += w
        score = int(round(total / weight_sum)) if weight_sum else 600
        return score, sub

    def _pick_grade(self, fico: int) -> tuple[str, str | None, float]:
        for row in self.grade_thresholds:
            cutoff = row[0]
            grade = row[1]
            rate = row[2] if len(row) > 2 else None
            cap = float(row[3]) if len(row) > 3 and row[3] is not None else 0.0
            if fico >= cutoff:
                return grade, rate, cap
        return "拒绝", None, 0.0

    def score(self, features: dict) -> RetailScoringResult:
        cat_w = self.appetite.dimension_weights or self.DEFAULT_CATEGORY_WEIGHTS
        cat_scores = {}
        sub_scores = {}
        total_w = sum(cat_w.values()) or 1.0
        weighted_sum = 0.0
        for cat in cat_w:
            s, sub = self._category_score(features, cat)
            cat_scores[cat] = s
            sub_scores[cat] = sub
            weighted_sum += s * cat_w[cat]

        fico = int(round(weighted_sum / total_w))
        fico = max(300, min(850, fico))
        grade, rate_tier, cap = self._pick_grade(fico)

        return RetailScoringResult(
            fico_score=fico,
            grade=grade,
            sub_scores=sub_scores,
            category_scores=cat_scores,
            approved_limit_cap=cap,
            rate_tier=rate_tier or "",
        )
