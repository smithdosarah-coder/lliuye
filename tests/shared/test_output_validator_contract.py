# -*- coding: utf-8 -*-
"""shared.output_validator contract test (TDD red · B.3.4 P0-R1).

per docs/contracts/shared-output-validator-v1.0.md §5
- I1-I6 invariants 全覆盖
- factory + 5 Agent shim 行为等价测

Phase 1 (this commit · red): import shared.output_validator → ImportError
Phase 1 (next commit · green): 实现 shared/output_validator.py · 全 pass
"""
from __future__ import annotations

import pytest

# Phase 1 red: shared.output_validator 不存在 · ImportError 是预期
from shared.output_validator import (  # noqa: F401
    OutputValidator,
    make_output_validator,
)
from shared.qc import PlaceholderViolation


# ---------------------------------------------------------------------------
# I1 · validate_text("") 不抛异常
# ---------------------------------------------------------------------------


class TestI1EmptyStringIsClean:
    def test_empty_string_no_raise(self):
        v = make_output_validator("agent_alert")
        v.validate_text("")  # 不抛

    def test_none_treated_as_empty(self):
        v = make_output_validator("agent_alert")
        v.validate_text(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# I2 · validate_text(text_with_placeholder) 抛 PlaceholderViolation · agent 字段 = adapter agent_id
# ---------------------------------------------------------------------------


class TestI2PlaceholderRaises:
    def test_placeholder_raises_violation(self):
        v = make_output_validator("agent_credit")
        with pytest.raises(PlaceholderViolation) as exc_info:
            v.validate_text("决策摘要：客户 {COMPANY_NAME} 申请 {AMOUNT} 万")
        # agent 字段 钉死 = factory 传入的 agent_id
        assert getattr(exc_info.value, "agent", None) == "agent_credit"

    def test_each_agent_id_propagates(self):
        for aid in (
            "agent_alert",
            "agent_channel",
            "agent_compliance",
            "agent_credit",
            "agent_riskctrl",
        ):
            v = make_output_validator(aid)
            assert v.agent_id == aid

    def test_assert_clean_alias_behaves_same(self):
        v = make_output_validator("agent_alert")
        with pytest.raises(PlaceholderViolation):
            v.assert_clean("placeholder {COMPANY_NAME}")


# ---------------------------------------------------------------------------
# I3 · soft_clean 递归 dict / list / str
# ---------------------------------------------------------------------------


class TestI3SoftCleanRecursive:
    def test_soft_clean_dict_replaces_placeholder(self):
        v = make_output_validator("agent_channel")
        cleaned, hits = v.soft_clean({
            "name": "客户 {COMPANY_NAME}",
            "score": 88,
            "nested": {"summary": "申请 {AMOUNT} 万"},
        })
        assert "{COMPANY_NAME}" not in str(cleaned["name"])
        assert "{AMOUNT}" not in str(cleaned["nested"]["summary"])
        assert len(hits) >= 2

    def test_soft_clean_list_recursive(self):
        v = make_output_validator("agent_channel")
        cleaned, hits = v.soft_clean([
            "无占位符",
            "有 {COMPANY_NAME}",
            ["更深 {AMOUNT}"],
        ])
        assert len(hits) >= 2
        assert isinstance(cleaned, list)

    def test_soft_clean_clean_str_unchanged(self):
        v = make_output_validator("agent_alert")
        cleaned, hits = v.soft_clean("纯净文本无占位符")
        assert cleaned == "纯净文本无占位符"
        assert hits == []


# ---------------------------------------------------------------------------
# I4 · soft_clean 非 str/dict/list 类型原样返回 (int/float/None/bool)
# ---------------------------------------------------------------------------


class TestI4PreservesNonStr:
    def test_int_unchanged(self):
        v = make_output_validator("agent_credit")
        cleaned, hits = v.soft_clean(42)
        assert cleaned == 42
        assert hits == []

    def test_float_unchanged(self):
        v = make_output_validator("agent_credit")
        cleaned, hits = v.soft_clean(3.14)
        assert cleaned == 3.14

    def test_none_unchanged(self):
        v = make_output_validator("agent_credit")
        cleaned, hits = v.soft_clean(None)
        assert cleaned is None

    def test_bool_unchanged(self):
        v = make_output_validator("agent_credit")
        cleaned, hits = v.soft_clean(True)
        assert cleaned is True

    def test_mixed_dict_preserves_non_str(self):
        v = make_output_validator("agent_credit")
        cleaned, hits = v.soft_clean({
            "score": 88,
            "ratio": 0.85,
            "active": True,
            "value": None,
            "name": "{COMPANY_NAME}",
        })
        assert cleaned["score"] == 88
        assert cleaned["ratio"] == 0.85
        assert cleaned["active"] is True
        assert cleaned["value"] is None
        assert "{COMPANY_NAME}" not in str(cleaned["name"])


# ---------------------------------------------------------------------------
# I5 · hit_kinds 顺序 = 遍历顺序 · 同 kind 重复入列
# ---------------------------------------------------------------------------


class TestI5HitKindsOrderAndDuplicates:
    def test_hit_kinds_not_deduped(self):
        v = make_output_validator("agent_alert")
        cleaned, hits = v.soft_clean([
            "{COMPANY_NAME}",
            "{COMPANY_NAME}",
            "{COMPANY_NAME}",
        ])
        assert len(hits) == 3  # 重复 · 不去重

    def test_hit_kinds_traversal_order(self):
        v = make_output_validator("agent_alert")
        cleaned, hits = v.soft_clean({
            "first": "{COMPANY_NAME}",
            "second_list": ["{AMOUNT}", "{INDUSTRY}"],
        })
        # dict insertion order + list left→right
        assert len(hits) >= 3


# ---------------------------------------------------------------------------
# I6 · 5 Agent shim public symbols (production import 不破)
# ---------------------------------------------------------------------------


class TestI6AgentShimPublicSymbols:
    """5 Agent thin shim 必须保留 public symbols · 不破 production import."""

    @pytest.mark.parametrize("agent_id,module_path", [
        ("agent_alert", "agent_alert.output_validator"),
        ("agent_channel", "agent_channel.output_validator"),
        ("agent_compliance", "agent_compliance.output_validator"),
        ("agent_credit", "agent_credit.output_validator"),
        ("agent_riskctrl", "agent_riskctrl.output_validator"),
    ])
    def test_agent_module_exports_required_symbols(self, agent_id, module_path):
        import importlib

        mod = importlib.import_module(module_path)
        assert hasattr(mod, "AGENT"), f"{module_path} 缺 AGENT 常量"
        assert mod.AGENT == agent_id, f"{module_path}.AGENT != {agent_id}"
        assert hasattr(mod, "validate_text"), f"{module_path} 缺 validate_text"
        assert hasattr(mod, "soft_clean"), f"{module_path} 缺 soft_clean"
        assert hasattr(mod, "PlaceholderViolation"), f"{module_path} 缺 PlaceholderViolation re-export"


# ---------------------------------------------------------------------------
# 行为等价 · 同输入 → 5 Agent factory 输出相同 (除 agent_id)
# ---------------------------------------------------------------------------


class TestBehaviorEquivalenceAcrossAgents:
    """除 agent 字段外 · 5 Agent 行为完全等价 (这是 extract 的核心 invariant)."""

    SAMPLE_PAYLOAD = {
        "title": "决策摘要",
        "body": "客户 {COMPANY_NAME} 申请 {AMOUNT} 万",
        "score": 88,
        "tags": ["{INDUSTRY}", "净值"],
    }

    def test_soft_clean_same_output_across_agents(self):
        results = []
        for aid in (
            "agent_alert",
            "agent_channel",
            "agent_compliance",
            "agent_credit",
            "agent_riskctrl",
        ):
            v = make_output_validator(aid)
            cleaned, hits = v.soft_clean(self.SAMPLE_PAYLOAD)
            results.append((cleaned, sorted(hits)))

        # 全部相同
        first = results[0]
        for r in results[1:]:
            assert r == first, "5 Agent soft_clean 行为不等价 · 这破 I6"
