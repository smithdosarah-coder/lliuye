# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_dsl_field_dict.py — BE6.1 字段字典 unit tests."""
from __future__ import annotations

import pytest

from agent_riskctrl.dsl_field_dict import (
    DTYPE_AMOUNT_WAN,
    DTYPE_PERCENT,
    DTYPE_RATIO,
    FIELD_DICT,
    format_field_dict_for_prompt,
    format_for_business,
    get_field_spec,
    validate_value,
)


# ===========================================================================
# get_field_spec · 别名 + 大小写
# ===========================================================================


def test_get_field_spec_canonical():
    spec = get_field_spec("debt_ratio")
    assert spec is not None
    assert spec.business_name == "资产负债率"


def test_get_field_spec_alias_chinese():
    spec = get_field_spec("负债率")
    assert spec is not None and spec.name == "debt_ratio"


def test_get_field_spec_alias_english():
    spec = get_field_spec("loan_amount")
    assert spec is not None and spec.name == "loan_amount_wan"


def test_get_field_spec_case_insensitive():
    assert get_field_spec("DEBT_RATIO") is get_field_spec("debt_ratio")
    assert get_field_spec("ROE") is get_field_spec("roe")


def test_get_field_spec_unknown():
    assert get_field_spec("not_a_field") is None
    assert get_field_spec("") is None


# ===========================================================================
# validate_value · hard / soft / categorical
# ===========================================================================


def test_validate_unknown_field():
    res = validate_value("ghost_field", 1.0)
    assert res.valid is False
    assert "未在 FIELD_DICT 注册" in res.message


def test_validate_categorical_ok():
    res = validate_value("scale", "小型")
    assert res.valid is True
    assert res.warning is False


def test_validate_categorical_invalid():
    res = validate_value("scale", "巨型")
    assert res.valid is False
    assert "不在允许枚举内" in res.message


def test_validate_numeric_within_soft():
    res = validate_value("debt_ratio", 0.4)
    assert res.valid is True
    assert res.warning is False


def test_validate_numeric_warns_above_soft():
    # debt_ratio soft_max=0.9, hard_max=5
    res = validate_value("debt_ratio", 1.5)
    assert res.valid is True
    assert res.warning is True
    assert "高于业务常见上界" in res.message


def test_validate_numeric_rejects_above_hard():
    res = validate_value("debt_ratio", 100)
    assert res.valid is False
    assert "高于 hard_max" in res.message


def test_validate_numeric_rejects_below_hard():
    res = validate_value("applicant_age", 5)  # hard_min=18
    assert res.valid is False
    assert "低于 hard_min" in res.message


def test_validate_numeric_non_numeric_input():
    res = validate_value("rate_pct", "not_a_number")
    assert res.valid is False
    assert "不能转数值" in res.message


# ===========================================================================
# format_for_business · 业务可读
# ===========================================================================


def test_format_ratio_to_percent():
    # 0.74 → 74%
    out = format_for_business("debt_ratio", 0.74)
    assert "74%" in out
    assert "资产负债率" in out


def test_format_percent_keeps_decimal():
    out = format_for_business("rate_pct", 6.61)
    assert "6.61%" in out
    assert "利率" in out


def test_format_amount_wan_with_separator():
    out = format_for_business("loan_amount_wan", 313.98)
    assert "313.98" in out
    assert "万元" in out


def test_format_amount_cny_with_thousand_separator():
    out = format_for_business("monthly_income_cny", 19031)
    assert "19,031" in out
    assert "元" in out


def test_format_categorical_passthrough():
    out = format_for_business("scale", "小型")
    assert "企业规模" in out
    assert "小型" in out


def test_format_unknown_field_fallback():
    # 未注册字段应 fallback 不抛
    out = format_for_business("ghost", 42)
    assert "ghost" in out and "42" in out


# ===========================================================================
# format_field_dict_for_prompt · LLM prompt 注入
# ===========================================================================


def test_prompt_fragment_contains_all_fields():
    md = format_field_dict_for_prompt()
    # 抽样 5 字段必须在 markdown 内
    for f in ("debt_ratio", "loan_amount_wan", "industry_l1", "rate_pct", "credit_score"):
        assert f"`{f}`" in md
    # 表头存在
    assert "| 字段 |" in md


def test_prompt_fragment_subset():
    md = format_field_dict_for_prompt(fields=["debt_ratio", "rate_pct"])
    assert "`debt_ratio`" in md
    assert "`rate_pct`" in md
    assert "`loan_amount_wan`" not in md


def test_prompt_fragment_unknown_field_skipped():
    md = format_field_dict_for_prompt(fields=["debt_ratio", "ghost_field"])
    assert "`debt_ratio`" in md
    assert "ghost_field" not in md


# ===========================================================================
# Sanity · FIELD_DICT 完整性
# ===========================================================================


def test_field_dict_aliases_no_collision():
    """两字段不能共享同一别名 (case-insensitive)."""
    seen: dict[str, str] = {}
    for spec in FIELD_DICT.values():
        keys = [spec.name.lower()] + [a.lower() for a in spec.aliases]
        for k in keys:
            assert k not in seen or seen[k] == spec.name, (
                f"alias collision: '{k}' on {spec.name} vs {seen[k]}"
            )
            seen[k] = spec.name


def test_field_dict_categorical_has_allowed_values():
    """所有 categorical 字段必须列 allowed_values."""
    from agent_riskctrl.dsl_field_dict import DTYPE_CATEGORICAL
    for spec in FIELD_DICT.values():
        if spec.dtype == DTYPE_CATEGORICAL:
            assert spec.allowed_values, f"{spec.name} categorical 缺 allowed_values"


def test_field_dict_csv_columns_covered():
    """data/mock/agent2-samples/loans.csv 28 字段必须全在 FIELD_DICT (除 loan_id)."""
    # loan_id 是主键 · 非 DSL 字段 · 跳
    csv_columns = [
        "applicant_age", "marriage", "education", "job_tenure_months",
        "monthly_income_cny", "company_age_years", "industry_l1", "scale",
        "region", "current_ratio", "debt_ratio", "roe", "revenue_yoy",
        "net_margin", "loan_amount_wan", "term_months", "rate_pct",
        "collateral_type", "purpose", "credit_score", "past_overdue_count_1y",
        "current_overdue_count", "guarantee_times_1y", "query_times_3m",
        "bank_balance_stddev_3m", "large_debit_count_1m",
        "cross_province_count_1m", "days_past_due",
    ]
    missing = [c for c in csv_columns if c not in FIELD_DICT]
    assert not missing, f"FIELD_DICT 缺字段: {missing}"


# ===========================================================================
# Edge: business_direction enum
# ===========================================================================


def test_business_direction_values():
    allowed = {"higher_better", "lower_better", "neutral"}
    for spec in FIELD_DICT.values():
        assert spec.business_direction in allowed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
