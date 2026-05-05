# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_unit_normalizer.py — BE6.2 单位归一 unit tests."""
from __future__ import annotations

import pytest

from agent_riskctrl.dsl_field_dict import (
    DTYPE_AMOUNT_CNY,
    DTYPE_AMOUNT_WAN,
    DTYPE_AMOUNT_YI,
    DTYPE_BPS,
    DTYPE_PERCENT,
    DTYPE_RATIO,
)
from agent_riskctrl.unit_normalizer import (
    UNIT_AMOUNT_CNY,
    UNIT_AMOUNT_WAN,
    UNIT_AMOUNT_YI,
    UNIT_BPS,
    UNIT_PERCENT,
    UNIT_RAW,
    normalize_for_field,
    normalize_to_dtype,
    parse_human_value,
)


# ===========================================================================
# parse_human_value
# ===========================================================================


class TestParse:
    def test_pure_number(self):
        p = parse_human_value("0.74")
        assert p.value == 0.74 and p.source_unit == UNIT_RAW

    def test_int_input(self):
        p = parse_human_value(8000)
        assert p.value == 8000.0 and p.source_unit == UNIT_RAW

    def test_yi_chinese(self):
        p = parse_human_value("1.5亿")
        assert p.value == 1.5 and p.source_unit == UNIT_AMOUNT_YI

    def test_yi_with_yuan(self):
        p = parse_human_value("1.5亿元")
        assert p.value == 1.5 and p.source_unit == UNIT_AMOUNT_YI

    def test_wan_chinese(self):
        p = parse_human_value("300万")
        assert p.value == 300.0 and p.source_unit == UNIT_AMOUNT_WAN

    def test_wan_with_yuan(self):
        p = parse_human_value("300万元")
        assert p.value == 300.0 and p.source_unit == UNIT_AMOUNT_WAN

    def test_percent(self):
        p = parse_human_value("80%")
        assert p.value == 80.0 and p.source_unit == UNIT_PERCENT

    def test_bps(self):
        p = parse_human_value("50bps")
        assert p.value == 50.0 and p.source_unit == UNIT_BPS

    def test_bps_chinese(self):
        p = parse_human_value("50 基点")
        assert p.value == 50.0 and p.source_unit == UNIT_BPS

    def test_thousand_separator(self):
        p = parse_human_value("19,031 元")
        assert p.value == 19031.0 and p.source_unit == UNIT_AMOUNT_CNY

    def test_chinese_comma(self):
        p = parse_human_value("19，031 元")
        assert p.value == 19031.0

    def test_negative(self):
        p = parse_human_value("-5%")
        assert p.value == -5.0 and p.source_unit == UNIT_PERCENT

    def test_no_number(self):
        p = parse_human_value("hello")
        assert p.value is None and p.error

    def test_empty_string(self):
        p = parse_human_value("")
        assert p.value is None and p.error == "empty input"

    def test_none_input(self):
        p = parse_human_value(None)  # type: ignore[arg-type]
        assert p.value is None


# ===========================================================================
# Amount conversions
# ===========================================================================


class TestAmount:
    def test_yi_to_cny(self):
        r = normalize_to_dtype("1.5亿", DTYPE_AMOUNT_CNY)
        assert r.value == 150_000_000.0 and not r.error

    def test_yi_to_wan(self):
        r = normalize_to_dtype("1.5亿", DTYPE_AMOUNT_WAN)
        assert r.value == 15000.0

    def test_yi_to_yi(self):
        r = normalize_to_dtype("1.5亿", DTYPE_AMOUNT_YI)
        assert r.value == 1.5

    def test_wan_to_cny(self):
        r = normalize_to_dtype("300万", DTYPE_AMOUNT_CNY)
        assert r.value == 3_000_000.0

    def test_wan_to_yi(self):
        r = normalize_to_dtype("5000万", DTYPE_AMOUNT_YI)
        assert r.value == 0.5

    def test_cny_to_wan(self):
        r = normalize_to_dtype("8000元", DTYPE_AMOUNT_WAN)
        assert r.value == 0.8

    def test_amount_rejects_percent(self):
        r = normalize_to_dtype("80%", DTYPE_AMOUNT_CNY)
        assert r.value is None and "金额字段不能接受" in r.error

    def test_raw_assumed_target_unit(self):
        # 无后缀输入 → 假设已在目标单位
        r = normalize_to_dtype("300", DTYPE_AMOUNT_WAN)
        assert r.value == 300.0
        assert r.warnings  # 警告 ambiguous


# ===========================================================================
# Percent / Ratio / BPS
# ===========================================================================


class TestPercent:
    def test_percent_passthrough(self):
        r = normalize_to_dtype("80%", DTYPE_PERCENT)
        assert r.value == 80.0 and not r.warnings

    def test_bps_to_percent(self):
        r = normalize_to_dtype("50bps", DTYPE_PERCENT)
        assert r.value == 0.5

    def test_ambiguous_ratio_to_percent(self):
        r = normalize_to_dtype("0.8", DTYPE_PERCENT)
        assert r.value == 80.0 and r.warnings  # warn

    def test_raw_above_one_kept(self):
        # >1 raw 给 percent → 直接当 percent
        r = normalize_to_dtype("8.5", DTYPE_PERCENT)
        assert r.value == 8.5

    def test_negative_percent(self):
        r = normalize_to_dtype("-5%", DTYPE_PERCENT)
        assert r.value == -5.0


class TestRatio:
    def test_ratio_passthrough(self):
        r = normalize_to_dtype("0.74", DTYPE_RATIO)
        assert r.value == 0.74

    def test_percent_to_ratio(self):
        r = normalize_to_dtype("80%", DTYPE_RATIO)
        assert r.value == 0.8

    def test_bps_to_ratio(self):
        r = normalize_to_dtype("50bps", DTYPE_RATIO)
        assert abs(r.value - 0.005) < 1e-9

    def test_ambiguous_percent_to_ratio(self):
        r = normalize_to_dtype("80", DTYPE_RATIO)
        assert r.value == 0.8 and r.warnings


class TestBPS:
    def test_bps_passthrough(self):
        r = normalize_to_dtype("50bps", DTYPE_BPS)
        assert r.value == 50.0

    def test_percent_to_bps(self):
        r = normalize_to_dtype("0.5%", DTYPE_BPS)
        assert r.value == 50.0

    def test_ambiguous_ratio_to_bps(self):
        r = normalize_to_dtype("0.005", DTYPE_BPS)
        assert r.value == 50.0 and r.warnings


# ===========================================================================
# normalize_for_field (integration with FIELD_DICT)
# ===========================================================================


class TestForField:
    def test_loan_amount_wan_field_with_yi_input(self):
        # field is amount_wan, input '1.5亿' → 15000 万
        r = normalize_for_field("loan_amount_wan", "1.5亿")
        assert r.value == 15000.0

    def test_loan_amount_alias(self):
        r = normalize_for_field("贷款金额", "300万")
        assert r.value == 300.0

    def test_debt_ratio_field_percent_input(self):
        # field is ratio · input '80%' → 0.8
        r = normalize_for_field("debt_ratio", "80%")
        assert r.value == 0.8

    def test_rate_pct_field_bps_input(self):
        # field is percent · input '50bps' → 0.5%
        r = normalize_for_field("rate_pct", "50bps")
        assert r.value == 0.5

    def test_unknown_field(self):
        r = normalize_for_field("ghost", "100%")
        assert r.value is None and "未在 FIELD_DICT 注册" in r.error

    def test_categorical_field_passthrough(self):
        # categorical 字段没单位 · raw 透传
        r = normalize_for_field("scale", "小型")
        # 'no number found' is acceptable for categorical · value None but error fills
        assert r.value is None
        assert r.error  # 'no number found' for non-numeric str


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdge:
    def test_zero(self):
        r = normalize_to_dtype("0", DTYPE_RATIO)
        assert r.value == 0

    def test_one_to_ratio(self):
        # 1 是 ratio 的边界 · 不触发 ambiguous heuristic (≤1 当 ratio)
        r = normalize_to_dtype("1", DTYPE_RATIO)
        assert r.value == 1.0 and not r.warnings

    def test_large_yi(self):
        r = normalize_to_dtype("100亿", DTYPE_AMOUNT_CNY)
        assert r.value == 10_000_000_000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
