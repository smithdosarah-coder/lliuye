# -*- coding: utf-8 -*-
"""Unit tests for credit canonical input mapper (W1 Phase B).

Per codex R3 R3.4 W1 第 2 步 (credit canonical input adapter):

- canonical signature detection (含 ``client_metadata`` layer → canonical 路径)
- backward compat (raw payload 不含 ``client_metadata`` → passthrough 不变)
- CanonicalInput → DecisionRequestV4 shape mapping (stage_tab/report_json/materials/
  appetite_config/preset_name 全保留)
- stage_tab 推断: CLIENT_ID_NUMBER → retail · CLIENT_USCC → corporate
- amount/term 中文数字解析 ('5000 万元' → 5000.0 · '一年' → 12)
- financial_anchors deterministic mapping (无 LLM 抽数路径)
"""
from __future__ import annotations

import pytest

from liuye_service.adapters.credit import (
    _canonical_to_credit_input,
    _parse_amount_wan,
    _parse_term_months,
    _extract_financial_anchors,
)


class TestParseHelpers:
    """parse_amount_wan + parse_term_months · deterministic 解析 utility."""

    def test_amount_wan_chinese_unit(self):
        assert _parse_amount_wan("5000 万元") == 5000.0
        assert _parse_amount_wan("5000万") == 5000.0
        assert _parse_amount_wan("5000万元") == 5000.0

    def test_amount_wan_already_numeric(self):
        assert _parse_amount_wan(5000) == 5000.0
        assert _parse_amount_wan(5000.5) == 5000.5

    def test_amount_wan_with_comma(self):
        assert _parse_amount_wan("5,000 万元") == 5000.0

    def test_amount_wan_invalid(self):
        assert _parse_amount_wan(None) is None
        assert _parse_amount_wan("") is None
        assert _parse_amount_wan("not a number") is None

    def test_term_months_chinese_year(self):
        assert _parse_term_months("一年") == 12
        assert _parse_term_months("3 年") == 36
        assert _parse_term_months("两年") == 24

    def test_term_months_explicit_months(self):
        assert _parse_term_months("12 个月") == 12
        assert _parse_term_months("36 月") == 36

    def test_term_months_invalid(self):
        assert _parse_term_months(None) is None
        assert _parse_term_months("") is None
        assert _parse_term_months("abc") is None


class TestFinancialAnchors:
    """material_facts → financial_anchors deterministic mapping."""

    def test_retail_anchors(self):
        mf = {
            "CLIENT_MONTHLY_INCOME": "18000 元",
            "CLIENT_DSR": "33%",
            "CREDIT_OUTSTANDING_BALANCE": "45 万元",
            "CREDIT_OVERDUE_RECORD": "无",
        }
        anchors = _extract_financial_anchors(mf)
        assert anchors["monthly_income"] == "18000 元"
        assert anchors["dsr"] == "33%"
        assert anchors["debt_balance"] == "45 万元"
        assert anchors["overdue_status"] == "无"

    def test_empty_mf(self):
        assert _extract_financial_anchors({}) == {}

    def test_partial_anchors(self):
        mf = {"CREDIT_OVERDUE_RECORD": "无逾期"}
        anchors = _extract_financial_anchors(mf)
        assert anchors == {"overdue_status": "无逾期"}


class TestCanonicalToCreditInput:
    """`_canonical_to_credit_input` 主 mapper · backward compat + canonical 两条路径."""

    def test_backward_compat_raw_payload(self):
        """Raw payload (无 ``client_metadata`` key) → passthrough 不变 · backward compat."""
        raw = {
            "stage_tab": "corporate",
            "report_json": {"header": {"subject_name": "鼎盛"}},
            "mock": False,
        }
        result = _canonical_to_credit_input(raw)
        assert result == raw

    def test_backward_compat_preserves_legacy_fields(self):
        """Raw payload 含 legacy 字段 (provider/api_key/parent_tool_call_id) → 透传."""
        raw = {
            "stage_tab": "retail",
            "report_json": None,
            "preset_name": "trade_eval_v1",
            "provider": "anthropic",
            "api_key": "sk-xxx",
            "parent_tool_call_id": "tc_report_v16_pipeline",
        }
        result = _canonical_to_credit_input(raw)
        assert result["stage_tab"] == "retail"
        assert result["preset_name"] == "trade_eval_v1"
        assert result["provider"] == "anthropic"
        assert result["parent_tool_call_id"] == "tc_report_v16_pipeline"

    def test_canonical_corporate(self):
        """Canonical 含 CLIENT_USCC → 推断 corporate · report_json header 全字段 mapping."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "鼎盛商贸有限公司",
                "CLIENT_USCC": "91310000XXXXXXXXXX",
                "CLIENT_INDUSTRY_FULL": "批发和零售业-批发业",
                "CLIENT_INDUSTRY_CODE": "F51",
                "CLIENT_LOCATION_CITY": "上海",
                "CLIENT_ESTABLISHMENT_DATE": "2015年3月15日",
                "CLIENT_REGISTERED_CAPITAL": "2000 万元",
                "CLIENT_EMPLOYEE_COUNT": "350 人",
                "CLIENT_OPERATING_YEARS": "8 年",
            },
            "credit_terms": {
                "CREDIT_AMOUNT": "5000 万元",
                "CREDIT_PERIOD": "一年",
                "CREDIT_PURPOSE": "经营周转",
            },
            "material_facts": {
                "BUSINESS_HISTORY_DESC": "8 年深耕",
            },
        }
        result = _canonical_to_credit_input(canonical)
        assert result["stage_tab"] == "corporate"
        assert result["mock"] is False
        rj = result["report_json"]
        # Header full mapping
        assert rj["header"]["subject_name"] == "鼎盛商贸有限公司"
        assert rj["header"]["uscc"] == "91310000XXXXXXXXXX"
        assert rj["header"]["industry"] == "批发和零售业-批发业"
        assert rj["header"]["industry_code"] == "F51"
        assert rj["header"]["location"] == "上海"
        assert rj["header"]["registered_capital"] == "2000 万元"
        assert rj["header"]["employee_count"] == "350 人"
        # Term parsing
        assert rj["header"]["applied_amount_wan"] == 5000.0
        assert rj["header"]["applied_term_months"] == 12
        assert rj["header"]["applied_product"] == "经营周转"
        # business_line
        assert rj["business_line"] == "corporate"
        # 3-layer passthrough into report_json
        assert rj["client_metadata"]["CLIENT_FULL_NAME"] == "鼎盛商贸有限公司"
        assert rj["credit_terms"]["CREDIT_AMOUNT"] == "5000 万元"
        assert rj["material_facts"]["BUSINESS_HISTORY_DESC"] == "8 年深耕"

    def test_canonical_retail(self):
        """Canonical 含 CLIENT_ID_NUMBER (无 USCC) → 推断 retail."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "李四",
                "CLIENT_ID_NUMBER": "310101199001010011",
                "CLIENT_MARITAL_STATUS": "已婚",
                "CLIENT_HOUSEHOLD_INCOME": "30 万元",
            },
            "credit_terms": {
                "CREDIT_AMOUNT": "30 万元",
                "CREDIT_PERIOD": "24 个月",
                "REPAYMENT_METHOD": "等额本息",
                "GUARANTEE_METHOD": "抵押",
            },
            "material_facts": {
                "CLIENT_MONTHLY_INCOME": "18000 元",
                "CLIENT_DSR": "33%",
                "CREDIT_OUTSTANDING_BALANCE": "45 万元",
                "REPAYMENT_ABILITY_ASSESSMENT": "DSR 合理 · 有还款能力",
            },
        }
        result = _canonical_to_credit_input(canonical)
        assert result["stage_tab"] == "retail"
        rj = result["report_json"]
        assert rj["header"]["subject_name"] == "李四"
        assert rj["header"]["applied_amount_wan"] == 30.0
        assert rj["header"]["applied_term_months"] == 24
        # financial_anchors deterministic mapping
        assert rj["financial_anchors"]["monthly_income"] == "18000 元"
        assert rj["financial_anchors"]["dsr"] == "33%"
        assert rj["financial_anchors"]["debt_balance"] == "45 万元"
        assert rj["financial_anchors"]["repayment_assessment"] == "DSR 合理 · 有还款能力"

    def test_canonical_passthrough_overrides_inference(self):
        """Canonical passthrough 含 explicit stage_tab → 不走推断."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "测试客户",
                "CLIENT_USCC": "91XXXXXXXXX",
            },
            "stage_tab": "small_business",  # explicit · 推翻 corporate 推断
            "provider": "anthropic",
            "mock": True,
        }
        result = _canonical_to_credit_input(canonical)
        assert result["stage_tab"] == "small_business"
        assert result["provider"] == "anthropic"
        assert result["mock"] is True

    def test_canonical_upstream_report_json_merge(self):
        """若 caller 透传 report_json (Agent6 handoff)· canonical 让位 + merge."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "鼎盛",
                "CLIENT_USCC": "91XXX",
            },
            "report_json": {
                "header": {
                    "subject_name": "Agent6 透传名 (overrides canonical)",
                    "extra_field": "from upstream",
                },
                "agent6_extra": "preserved",
            },
        }
        result = _canonical_to_credit_input(canonical)
        rj = result["report_json"]
        # Upstream wins on overlap
        assert rj["header"]["subject_name"] == "Agent6 透传名 (overrides canonical)"
        # Upstream extras preserved
        assert rj["agent6_extra"] == "preserved"

    def test_canonical_invalid_fallback_raw(self):
        """canonical 含 ``client_metadata`` 但 pydantic 验证 fail (e.g. CLIENT_FULL_NAME 缺)·
        fallback raw passthrough (不 raise · backward compat)."""
        canonical = {
            "client_metadata": {
                # CLIENT_FULL_NAME 缺 · pydantic 必 raise · mapper fallback raw
                "CLIENT_USCC": "91XXX",
            },
            "stage_tab": "corporate",
        }
        result = _canonical_to_credit_input(canonical)
        # fallback path: 原 raw payload 透传 · stage_tab 保留
        assert result["stage_tab"] == "corporate"

    def test_canonical_small_business_default(self):
        """无 CLIENT_USCC + 无 CLIENT_ID_NUMBER → 默认 small_business."""
        canonical = {
            "client_metadata": {
                "CLIENT_FULL_NAME": "小微企业 A",
            },
        }
        result = _canonical_to_credit_input(canonical)
        assert result["stage_tab"] == "small_business"

    def test_non_dict_returns_empty(self):
        assert _canonical_to_credit_input(None) == {}  # type: ignore[arg-type]
        assert _canonical_to_credit_input("not a dict") == {}  # type: ignore[arg-type]
