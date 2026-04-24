# -*- coding: utf-8 -*-
"""回测域 —— CSV 样本装载、单策略回测、多策略对比。"""

from __future__ import annotations

import pandas as pd

from ..backtesting import (
    BacktestResult,
    compare_strategies as _compare_strategies,
    load_csv_data as _load_csv_data,
    run_backtest as _run_backtest,
)


def backtest_load_csv(file_path: str) -> pd.DataFrame:
    """加载 CSV 样本文件（回测域：数据装载入口）。"""
    return _load_csv_data(file_path)


def backtest_run(*args, **kwargs) -> BacktestResult:
    """对单个 RuleSet 跑历史回测，产出 KS/通过率/坏账率（回测域：主入口）。

    透传参数到底层 `run_backtest(ruleset, df, label_col=..., per_rule=...)`。
    """
    return _run_backtest(*args, **kwargs)


def backtest_compare_strategies(*args, **kwargs):
    """并列比较多个策略（回测域：策略对比入口）。"""
    return _compare_strategies(*args, **kwargs)
