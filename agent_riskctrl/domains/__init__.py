# -*- coding: utf-8 -*-
"""Agent2 风控 · 工具域入口（CLAUDE.md §3.2）

三个子域按 `<域>_<动作>` 命名；底层实现保留在 `agent_riskctrl/{rule_engine,backtesting,metrics}.py`
（未被跨域直接调用，只通过本子包重导出）。
"""

from .dsl_gen import (
    dsl_gen_parse_from_llm,
    dsl_gen_apply_rule,
    dsl_gen_apply_ruleset,
)
from .backtest import (
    backtest_load_csv,
    backtest_run,
    backtest_compare_strategies,
)
from .metrics_analyze import (
    metrics_analyze_ks,
    metrics_analyze_psi,
    metrics_analyze_confusion,
    metrics_analyze_format_report,
)

__all__ = [
    # DSL 生成域
    "dsl_gen_parse_from_llm",
    "dsl_gen_apply_rule",
    "dsl_gen_apply_ruleset",
    # 回测域
    "backtest_load_csv",
    "backtest_run",
    "backtest_compare_strategies",
    # 指标分析域
    "metrics_analyze_ks",
    "metrics_analyze_psi",
    "metrics_analyze_confusion",
    "metrics_analyze_format_report",
]
