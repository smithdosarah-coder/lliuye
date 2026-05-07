# -*- coding: utf-8 -*-
"""红线检查域 —— 规则引擎 v2 + 风险偏好配置。

确定性判定层（CLAUDE.md §3.1）：不让 LLM 现场算红线。

PB#2 cleanup (2026-05-06): 删除 redline_check_classify wrapper · 透传的
risk_classifier.py 已 git rm (pre-existing ImportError 死代码).
"""

from __future__ import annotations

from ..risk_appetite_config import RiskAppetiteConfig
from ..rule_engine_v2 import RedLineHit, RuleEngineV2


def redline_check_rules_v2(features: dict, segment: str = "corporate",
                            appetite: RiskAppetiteConfig | None = None) -> list[RedLineHit]:
    """跑规则引擎 v2 出红线命中列表（红线检查域：规则引擎入口）。"""
    return RuleEngineV2(appetite=appetite).check(features, segment)


def redline_check_appetite_load(client_id: str = "", segment: str = "corporate") -> RiskAppetiteConfig:
    """按板块加载风险偏好配置（红线检查域：配置加载）。"""
    return RiskAppetiteConfig.load(client_id=client_id, segment=segment)
