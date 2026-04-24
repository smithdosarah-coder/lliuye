# -*- coding: utf-8 -*-
"""Agent3 授信 · 工具域入口（CLAUDE.md §3.2）

四个子域：画像消费 / 评分计算（对公+对私双模型） / 红线检查 / 案例召回。
编排层保留在 `agent_credit.decision_engine.DecisionEngine`（跨域 glue 不在域内做）。
"""

from .profile_consume import (
    profile_consume_features,
    profile_consume_enhance,
)
from .scoring_calc import (
    scoring_calc_corporate,
    scoring_calc_retail,
    scoring_calc_rating,
    scoring_calc_limit,
)
from .redline_check import (
    redline_check_classify,
    redline_check_rules_v2,
    redline_check_appetite_load,
)
from .case_retrieve import (
    case_retrieve_similar,
)

__all__ = [
    # 画像消费域
    "profile_consume_features",
    "profile_consume_enhance",
    # 评分计算域
    "scoring_calc_corporate",
    "scoring_calc_retail",
    "scoring_calc_rating",
    "scoring_calc_limit",
    # 红线检查域
    "redline_check_classify",
    "redline_check_rules_v2",
    "redline_check_appetite_load",
    # 案例召回域
    "case_retrieve_similar",
]
