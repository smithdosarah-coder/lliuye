# -*- coding: utf-8 -*-
"""评分计算域 —— 对公 / 对私双模型 + 评级 + 额度建议。

注：`rating_engine` 的 import 下沉到函数体内，避开 `risk_classifier` 上游
`SYSTEM_RISK_ASSESS` 缺失的预先存在问题（code-urgent 地盘，非本 worker 修）。
"""

from __future__ import annotations

from ..risk_appetite_config import RiskAppetiteConfig
from ..scoring_model_corporate import CorporateScoringModel, CorporateScoringResult
from ..scoring_model_retail import RetailScoringModel, RetailScoringResult


def scoring_calc_corporate(features: dict, appetite: RiskAppetiteConfig | None = None) -> CorporateScoringResult:
    """对公信贷四维评分（评分计算域：对公模型）。"""
    return CorporateScoringModel(appetite=appetite).score(features)


def scoring_calc_retail(features: dict, appetite: RiskAppetiteConfig | None = None) -> RetailScoringResult:
    """对私信贷四维评分（评分计算域：对私模型）。"""
    return RetailScoringModel(appetite=appetite).score(features)


def scoring_calc_rating(*args, **kwargs):
    """综合评分 → 信用评级（评分计算域：评级映射）。

    透传到 `rating_engine.calculate_rating(...)`。
    """
    from ..rating_engine import calculate_rating
    return calculate_rating(*args, **kwargs)


def scoring_calc_limit(*args, **kwargs):
    """基于评分/画像建议授信额度（评分计算域：额度建议）。

    透传到 `rating_engine.suggest_credit_limit(...)`。
    """
    from ..rating_engine import suggest_credit_limit
    return suggest_credit_limit(*args, **kwargs)
