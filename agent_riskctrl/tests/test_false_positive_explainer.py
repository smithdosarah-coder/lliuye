# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_false_positive_explainer.py — BE8.8 误杀解释 unit tests."""
from __future__ import annotations

import pandas as pd
import pytest

from agent_riskctrl.false_positive_explainer import (
    FalsePositive,
    explain_false_positives,
    format_fp_summary,
    identify_false_positives,
)
from agent_riskctrl.rule_engine import RuleCondition, RuleSet, StrategyRule


def _make_ruleset() -> RuleSet:
    """高负债 reject 规则 · 用于触 FP."""
    return RuleSet(rules=[
        StrategyRule(
            rule_id="R001", name="高负债拒绝",
            priority=1, action="reject",
            conditions=[RuleCondition(field="debt_ratio", operator=">", value=0.7)],
        ),
    ])


def _df_with_fp() -> pd.DataFrame:
    """高负债但实际未逾期的客户 (true FP) + 高负债且实际逾期 (true positive)."""
    return pd.DataFrame([
        # 真 FP: 高负债 + 未逾期
        {"loan_id": "L00001", "debt_ratio": 0.85, "credit_score": 750,
         "monthly_income_cny": 30000, "days_past_due": 0},
        {"loan_id": "L00002", "debt_ratio": 0.75, "credit_score": 700,
         "monthly_income_cny": 25000, "days_past_due": 5},
        # 真 TP: 高负债 + 逾期
        {"loan_id": "L00003", "debt_ratio": 0.9, "credit_score": 500,
         "monthly_income_cny": 5000, "days_past_due": 60},
        # 低负债 · 不命中规则 · 不进 FP 名单
        {"loan_id": "L00004", "debt_ratio": 0.4, "credit_score": 800,
         "monthly_income_cny": 50000, "days_past_due": 0},
    ])


# ===========================================================================
# identify_false_positives (确定性 · 不走 LLM)
# ===========================================================================


class TestIdentify:
    def test_basic_fp(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        assert len(fps) == 2  # L00001 + L00002
        loan_ids = {fp.loan_id for fp in fps}
        assert loan_ids == {"L00001", "L00002"}

    def test_true_positive_excluded(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        ids = {fp.loan_id for fp in fps}
        assert "L00003" not in ids  # 真坏账 不算 FP

    def test_no_hit_excluded(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        ids = {fp.loan_id for fp in fps}
        assert "L00004" not in ids  # 未命中规则

    def test_manual_review_not_counted(self):
        df = _df_with_fp()
        # manual_review action 不算 FP (不是 reject)
        rs = RuleSet(rules=[
            StrategyRule(
                rule_id="R001", name="高负债转人工",
                priority=1, action="manual_review",
                conditions=[RuleCondition(field="debt_ratio", operator=">", value=0.7)],
            ),
        ])
        fps = identify_false_positives(df, rs)
        assert fps == []

    def test_key_features_filled(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        assert "debt_ratio" in fps[0].key_features

    def test_label_column_missing(self):
        df = pd.DataFrame([{"debt_ratio": 0.85, "loan_id": "L1"}])
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        assert fps == []

    def test_empty_df(self):
        df = pd.DataFrame([{"debt_ratio": 0.5, "days_past_due": 0}]).iloc[0:0]
        rs = _make_ruleset()
        assert identify_false_positives(df, rs) == []


# ===========================================================================
# explain_false_positives · LLM 注入 + fallback
# ===========================================================================


class FakeCaller:
    """Fake LLMCaller for tests · 不真调网络."""
    def __init__(self, return_text: str = "test reason from fake LLM"):
        self.return_text = return_text
        self.calls: list[tuple[str, str]] = []

    def simple_chat(self, system: str, user: str,
                    temperature: float | None = None,
                    api_key: str = "",
                    user_id: str | None = None) -> str:
        self.calls.append((system, user))
        return self.return_text


class FailingCaller:
    """Caller 永远失败."""
    def simple_chat(self, *args, **kwargs):
        raise RuntimeError("fake LLM down")


class EmptyCaller:
    """Caller 返空."""
    def simple_chat(self, *args, **kwargs) -> str:
        return ""


class TestExplain:
    def test_llm_called_for_top_n(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        fake = FakeCaller("规则阈值过严 · 客户征信分高")
        out = explain_false_positives(fps, max_explain=2, llm_caller=fake)
        assert len(out) == 2
        for r in out:
            assert r["reason_source"] == "llm"
            assert "规则阈值过严" in r["reason"]
        assert len(fake.calls) == 2

    def test_skip_over_limit_uses_fallback(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        fake = FakeCaller("LLM reason")
        # max_explain=1 · 第二条应 skipped_over_limit
        out = explain_false_positives(fps, max_explain=1, llm_caller=fake)
        sources = [r["reason_source"] for r in out]
        assert sources[0] == "llm"
        assert sources[1] == "skipped_over_limit"

    def test_llm_failure_falls_back(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        out = explain_false_positives(
            fps, max_explain=10, llm_caller=FailingCaller(),
        )
        for r in out:
            assert r["reason_source"] == "fallback_on_error"
            assert "LLM 解释不可用" in r["reason"]

    def test_empty_llm_response_falls_back(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        out = explain_false_positives(
            fps, max_explain=10, llm_caller=EmptyCaller(),
        )
        for r in out:
            assert r["reason_source"] == "fallback"

    def test_no_caller_fallback(self):
        # caller=None + LLMCaller import fail · 都退 no_llm
        # (test env shared.llm_caller 一般可 import · 走 LLM 真路径会失败 in test → fallback_on_error)
        # 这里只验 caller 注入 None 时 不抛
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        # 注入 None · 真 LLM 在 test env 没 key · 应触 fallback_on_error
        out = explain_false_positives(fps, max_explain=10, llm_caller=None)
        for r in out:
            # 任何 fallback 来源都接受 · 关键是不抛 + 有 reason
            assert r["reason"]
            assert r["reason_source"] in (
                "fallback", "fallback_on_error", "no_llm", "llm",
            )

    def test_empty_fp_list(self):
        assert explain_false_positives([], max_explain=5) == []


# ===========================================================================
# Format
# ===========================================================================


class TestFormat:
    def test_summary_renders(self):
        df = _df_with_fp()
        rs = _make_ruleset()
        fps = identify_false_positives(df, rs)
        out = explain_false_positives(
            fps, max_explain=2, llm_caller=FakeCaller("test reason"),
        )
        md = format_fp_summary(out)
        assert "误杀个案解释" in md
        assert "L00001" in md
        assert "test reason" in md

    def test_summary_empty(self):
        md = format_fp_summary([])
        assert "未发现误杀" in md


# ===========================================================================
# §3.1 红线: LLM 不算 KS · 仅给 reason
# ===========================================================================


def test_module_does_not_compute_ks():
    """本模块不应直接调用 calculate_ks (§3.1 LLM 不算 KS)."""
    import inspect

    from agent_riskctrl import false_positive_explainer as mod

    src = inspect.getsource(mod)
    # 不应直接 import calculate_ks 也不 compute_ks
    assert "calculate_ks" not in src
    assert "compute_strategy_ks" not in src


def test_no_legacy_llm_import():
    """红线: 本模块不能新增 legacy LLMClient 直连.

    V2 fix (codex review critical 2): forbidden string 用 concat build ·
    避免 DIFF guard 扫 production import 时误报 test 文件本身命中
    (test self-check literal vs production code import 区分).
    """
    import inspect

    from agent_riskctrl import false_positive_explainer as mod

    src = inspect.getsource(mod)
    # build forbidden literal via concat · 不在 test 源文件留 raw match string
    forbidden_import = "from llm" + " import " + "LLMClient"
    forbidden_call = "LLMClient" + "("
    assert forbidden_import not in src, (
        f"production module 不允许 {forbidden_import}"
    )
    assert forbidden_call not in src, (
        f"production module 不允许 直接构造 {forbidden_call}"
    )
    # 用 shared/llm_caller (允许)
    assert "shared.llm_caller" in src


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
