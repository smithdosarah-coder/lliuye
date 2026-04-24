# -*- coding: utf-8 -*-
"""红线检查域 —— 规则引擎 v2 + 风险维度分类 + 风险偏好配置。

确定性判定层（CLAUDE.md §3.1）：不让 LLM 现场算红线。

注：`risk_classifier` 的 import 下沉到函数体内，避开 `SYSTEM_RISK_ASSESS` 缺失
的 pre-existing bug（code-urgent 地盘）。
"""

from __future__ import annotations

from ..risk_appetite_config import RiskAppetiteConfig
from ..rule_engine_v2 import RedLineHit, RuleEngineV2


def redline_check_classify(*args, **kwargs):
    """风险维度分类（红线检查域：维度判定）。

    透传到 `risk_classifier.classify_risks(...)`。
    """
    from ..risk_classifier import classify_risks
    return classify_risks(*args, **kwargs)


def redline_check_rules_v2(features: dict, segment: str = "corporate",
                            appetite: RiskAppetiteConfig | None = None) -> list[RedLineHit]:
    """跑规则引擎 v2 出红线命中列表（红线检查域：规则引擎入口）。"""
    return RuleEngineV2(appetite=appetite).check(features, segment)


def redline_check_appetite_load(client_id: str = "", segment: str = "corporate") -> RiskAppetiteConfig:
    """按板块加载风险偏好配置（红线检查域：配置加载）。"""
    return RiskAppetiteConfig.load(client_id=client_id, segment=segment)
