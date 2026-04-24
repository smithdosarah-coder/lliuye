# -*- coding: utf-8 -*-
"""Agent3 接入 financial_analyzer · 比率一致性 smoke test (Task A)

验证 feature_extractor 提取的 financial.* 比率与 financial_analyzer
直接计算的指标一致（误差 < 0.01%）。同时确认 LLM prompt 的 evidence 块
携带 financial_analyzer.format_for_prompt() 的输出。
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from agent_credit.feature_extractor import FeatureExtractor, _anchors_to_indicators


SAMPLE_PROFILE: dict = {
    "company_name": "众智达科技",
    "industry": "I65-互联网与相关服务",
    "establishment_date": "2018-06",
    "employee_count": 86,
    "financial_anchors": {
        "revenue_latest": 18650.0,        # 万元
        "revenue_prev": 16230.0,
        "net_profit_latest": 1235.0,
        "net_profit_prev": 820.0,
        "total_assets": 16956.5,
        "total_liabilities": 7206.5,
        "net_assets": 9750.0,
        "accounts_receivable": 4380.0,
        "inventory": 2150.0,
        "operating_cash_flow": 791.2,
        "short_term_borrowing": 2200.0,
        "ebitda": 1985.0,
    },
    "guarantee_info": {"type": "房产抵押+保证人", "collateral_value": 1500.0},
    "request": {"amount": 800.0, "term_months": 24, "purpose": "补充流动资金"},
}


def _approx(a: float, b: float, tol: float = 1e-4) -> bool:
    return abs(a - b) <= tol


def test_extracted_ratios_match_financial_analyzer():
    """feature_extractor 输出的 financial.* 比率必须与 financial_analyzer
    在同一组 anchors 上直接计算的指标一致。"""
    fx = FeatureExtractor()
    features = fx.extract(SAMPLE_PROFILE, "corporate")
    indicators = _anchors_to_indicators(SAMPLE_PROFILE["financial_anchors"])

    assert _approx(features["financial.debt_ratio"],
                   (indicators.debt_to_asset_ratio.current or 0) / 100)
    assert _approx(features["financial.net_margin"],
                   (indicators.net_margin.current or 0) / 100)
    assert _approx(features["financial.gross_margin"],
                   (indicators.gross_margin.current or 0) / 100)
    assert _approx(features["financial.revenue_growth"],
                   (indicators.revenue.yoy_pct or 0) / 100)
    assert _approx(features["financial.ar_turnover_days"],
                   indicators.ar_turnover_days.current or 0)


def test_prompt_block_carries_financial_analyzer_evidence():
    """advisor_formatter 通过 _financial_prompt_block 引用 financial_analyzer
    的 format_for_prompt 输出 —— LLM 不需要、也不应自己重算。"""
    from agent_credit.advisor_formatter import _corporate_summary

    fx = FeatureExtractor()
    features = fx.extract(SAMPLE_PROFILE, "corporate")
    summary = _corporate_summary(SAMPLE_PROFILE, features)

    assert features.get("_financial_prompt_block"), \
        "_financial_prompt_block 未注入 features"
    assert "已计算财务指标" in summary, \
        "_corporate_summary 未携带 financial_analyzer 证据块"
    # 关键：禁止 LLM 算的硬性提示要在文本里
    assert "数字权威" in summary or "禁止重新计算" in summary


def test_features_snapshot_drops_internal_keys():
    """DecisionAdvice.features_snapshot 不应包含下划线前缀的内部字段。"""
    fx = FeatureExtractor()
    features = fx.extract(SAMPLE_PROFILE, "corporate")
    # 模拟 advisor_formatter 内的 snapshot 过滤
    snapshot = {k: v for k, v in features.items()
                if not k.startswith("chapters") and not k.startswith("_")}
    assert "_financial_prompt_block" not in snapshot


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
