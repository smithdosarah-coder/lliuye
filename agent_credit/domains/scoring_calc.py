# -*- coding: utf-8 -*-
"""评分计算域 —— 对公 / 对私双模型。

PB#2 cleanup (2026-05-06): 删除 scoring_calc_rating / scoring_calc_limit 2 wrapper ·
透传的 rating_engine.py 已 git rm (pre-existing ImportError 死代码).
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
