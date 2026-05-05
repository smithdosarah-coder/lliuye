# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_business_metrics.py — BE6.4 双轨业务指标 unit tests."""
from __future__ import annotations

import pytest

from agent_riskctrl.business_metrics import (
    DEFAULT_CONFIG,
    BusinessMetricsConfig,
    calculate_business_metrics,
    compare_business_metrics,
    format_business_summary,
    format_compare_summary,
)


# ===========================================================================
# calculate_business_metrics
# ===========================================================================


class TestCalc:
    def test_basic(self):
        bt = {"total_records": 1000, "approved": 200, "rejected": 100,
              "manual_review": 50}
        m = calculate_business_metrics(bt, bad_rate=0.05)
        # 通过 = approved + no_hit (no_hit = 1000-200-100-50=650) = 850
        assert m["pass_count"] == 850
        assert m["pass_rate"] == 0.85
        assert m["reject_rate"] == 0.10
        assert m["review_rate"] == 0.05
        assert m["bad_rate"] == 0.05

    def test_profit_positive_when_low_bad_rate(self):
        bt = {"total_records": 100, "approved": 50, "rejected": 0,
              "manual_review": 0}
        # bad_rate=0 · NIM=3.5% · profit = 100 × 100 × 0.035 = 350 万
        m = calculate_business_metrics(bt, bad_rate=0.0)
        assert m["profit_total_wan"] == pytest.approx(350.0, rel=1e-3)

    def test_profit_negative_when_bad_rate_high(self):
        bt = {"total_records": 100, "approved": 50, "rejected": 0,
              "manual_review": 0}
        # bad_rate 高于 NIM/LGD = 3.5/60 = 5.83% · 利润为负
        m = calculate_business_metrics(bt, bad_rate=0.10)
        assert m["profit_total_wan"] < 0

    def test_actual_avg_loan_overrides_default(self):
        bt = {"total_records": 100, "approved": 100, "rejected": 0,
              "manual_review": 0}
        m = calculate_business_metrics(
            bt, avg_loan_amount_wan_actual=500.0, bad_rate=0.0,
        )
        # 100 × 500 × 0.035 = 1750 万
        assert m["profit_total_wan"] == pytest.approx(1750.0, rel=1e-3)
        assert m["avg_loan_amount_wan"] == 500.0

    def test_zero_total(self):
        m = calculate_business_metrics({"total_records": 0, "approved": 0,
                                        "rejected": 0, "manual_review": 0})
        assert m["pass_rate"] == 0.0
        assert m["profit_total_wan"] == 0.0

    def test_no_bad_rate_assumes_zero(self):
        m = calculate_business_metrics({"total_records": 100, "approved": 100,
                                        "rejected": 0, "manual_review": 0})
        assert m["bad_rate"] == 0.0

    def test_custom_config(self):
        # 提高 NIM 到 5% · 同样数据利润↑
        cfg = BusinessMetricsConfig(nim_default=0.05)
        bt = {"total_records": 100, "approved": 100, "rejected": 0,
              "manual_review": 0}
        m = calculate_business_metrics(bt, config=cfg, bad_rate=0.0)
        # 100 × 100 × 0.05 = 500 万
        assert m["profit_total_wan"] == pytest.approx(500.0, rel=1e-3)
        assert m["nim"] == 0.05

    def test_no_hit_counted_as_pass(self):
        # 30 命中 (10 reject + 20 manual) · 70 未命中 (no_hit) · approve=0
        # 通过 = 0 + 70 = 70 (no_hit 视作通过 · 没规则拦)
        bt = {"total_records": 100, "approved": 0, "rejected": 10,
              "manual_review": 20}
        m = calculate_business_metrics(bt)
        assert m["pass_count"] == 70


# ===========================================================================
# compare_business_metrics
# ===========================================================================


class TestCompare:
    def test_adopt_when_profit_up_bad_down(self):
        before = {"pass_rate": 0.85, "reject_rate": 0.10, "bad_rate": 0.05,
                  "profit_total_wan": 100.0}
        after = {"pass_rate": 0.83, "reject_rate": 0.12, "bad_rate": 0.03,
                 "profit_total_wan": 150.0}
        cmp = compare_business_metrics(before, after)
        assert cmp["recommendation"] == "adopt"
        assert cmp["profit_delta_wan"] == 50.0
        assert cmp["bad_rate_delta_pp"] == -2.0

    def test_reject_when_profit_down_bad_up(self):
        before = {"pass_rate": 0.85, "reject_rate": 0.10, "bad_rate": 0.05,
                  "profit_total_wan": 100.0}
        after = {"pass_rate": 0.90, "reject_rate": 0.05, "bad_rate": 0.07,
                 "profit_total_wan": 80.0}
        cmp = compare_business_metrics(before, after)
        assert cmp["recommendation"] == "reject"

    def test_review_when_mixed(self):
        before = {"pass_rate": 0.85, "bad_rate": 0.05, "profit_total_wan": 100.0,
                  "reject_rate": 0.10}
        after = {"pass_rate": 0.90, "bad_rate": 0.07, "profit_total_wan": 110.0,
                 "reject_rate": 0.05}
        cmp = compare_business_metrics(before, after)
        assert cmp["recommendation"] == "review"

    def test_pp_unit_correct(self):
        # 5% → 7% delta = +2 pp (NOT 0.02)
        before = {"bad_rate": 0.05, "pass_rate": 0.85, "reject_rate": 0.10,
                  "profit_total_wan": 100.0}
        after = {"bad_rate": 0.07, "pass_rate": 0.83, "reject_rate": 0.12,
                 "profit_total_wan": 100.0}
        cmp = compare_business_metrics(before, after)
        assert cmp["bad_rate_delta_pp"] == pytest.approx(2.0, abs=0.01)


# ===========================================================================
# Format
# ===========================================================================


class TestFormat:
    def test_summary_renders(self):
        bt = {"total_records": 1000, "approved": 200, "rejected": 100,
              "manual_review": 50}
        m = calculate_business_metrics(bt, bad_rate=0.05)
        out = format_business_summary(m)
        assert "通过率" in out
        assert "%" in out
        assert "万元" in out

    def test_compare_summary_adopt(self):
        before = {"pass_rate": 0.85, "reject_rate": 0.10, "bad_rate": 0.05,
                  "profit_total_wan": 100.0}
        after = {"pass_rate": 0.83, "reject_rate": 0.12, "bad_rate": 0.03,
                 "profit_total_wan": 150.0}
        cmp = compare_business_metrics(before, after)
        out = format_compare_summary(cmp)
        assert "建议采纳" in out
        assert "+50.00" in out  # profit delta


# ===========================================================================
# Default config sanity
# ===========================================================================


def test_default_config_immutable():
    # frozen=True dataclass · 不能改字段
    with pytest.raises((AttributeError, Exception)):
        DEFAULT_CONFIG.nim_default = 0.99  # type: ignore[misc]


def test_default_values_within_industry_range():
    # 国有大行 NIM 通常 1.5-3.5% · LGD 通常 50-70%
    assert 0.01 <= DEFAULT_CONFIG.nim_default <= 0.05
    assert 0.4 <= DEFAULT_CONFIG.lgd_default <= 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
