# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_champion_challenger.py — BE8.5 双 model 对比 unit tests."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agent_riskctrl.champion_challenger import (
    ChampionChallengerResult,
    compare_champion_challenger,
    format_cc_report,
)
from agent_riskctrl.rule_engine import RuleCondition, RuleSet, StrategyRule


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOANS_CSV = PROJECT_ROOT / "data" / "mock" / "agent2-samples" / "loans.csv"


def _make_ruleset(threshold: float, rule_id: str = "R001",
                  action: str = "reject") -> RuleSet:
    return RuleSet(rules=[
        StrategyRule(
            rule_id=rule_id, name=f"debt_ratio_{threshold}",
            priority=1, action=action,
            conditions=[RuleCondition(
                field="debt_ratio", operator=">", value=threshold,
            )],
        ),
    ])


# ===========================================================================
# 真跑 loans.csv subset
# ===========================================================================


@pytest.fixture(scope="module")
def loans_sample():
    if not LOANS_CSV.exists():
        pytest.skip(f"loans.csv 缺 {LOANS_CSV}")
    df = pd.read_csv(LOANS_CSV, encoding="utf-8")
    return df.head(500)


class TestRealCompare:
    def test_basic_comparison(self, loans_sample):
        champion = _make_ruleset(0.7)   # 严格 · 拒得多
        challenger = _make_ruleset(0.9)  # 宽松 · 拒得少
        res = compare_champion_challenger(loans_sample, champion, challenger)
        assert isinstance(res, ChampionChallengerResult)
        assert res.n_records == 500
        # challenger 阈值高 · 通过率应高于 champion
        assert (res.challenger_business["pass_rate"]
                >= res.champion_business["pass_rate"])

    def test_winner_decision_present(self, loans_sample):
        champion = _make_ruleset(0.7)
        challenger = _make_ruleset(0.9)
        res = compare_champion_challenger(loans_sample, champion, challenger)
        assert res.winner in ("champion", "challenger", "tie")

    def test_business_compare_keys(self, loans_sample):
        champion = _make_ruleset(0.5)
        challenger = _make_ruleset(0.8)
        res = compare_champion_challenger(loans_sample, champion, challenger)
        bc = res.business_compare
        for key in ("pass_rate_delta_pp", "reject_rate_delta_pp",
                    "bad_rate_delta_pp", "profit_delta_wan",
                    "profit_delta_pct", "recommendation", "reasons"):
            assert key in bc

    def test_format_report_markdown(self, loans_sample):
        champion = _make_ruleset(0.7)
        challenger = _make_ruleset(0.9)
        res = compare_champion_challenger(loans_sample, champion, challenger)
        out = format_cc_report(res)
        assert "Champion" in out
        assert "Challenger" in out
        assert "结论" in out
        assert "%" in out

    def test_to_dict_serializable(self, loans_sample):
        champion = _make_ruleset(0.7)
        challenger = _make_ruleset(0.9)
        res = compare_champion_challenger(loans_sample, champion, challenger)
        d = res.to_dict()
        # 关键字段全在
        for key in ("champion_ks", "challenger_ks", "ks_delta",
                    "winner", "winner_reasons", "risk_flags",
                    "champion_business", "challenger_business",
                    "business_compare"):
            assert key in d


# ===========================================================================
# Synthetic data · winner decision logic
# ===========================================================================


def _synthetic_df(n: int = 200) -> pd.DataFrame:
    """生成可控样本 · 半好半坏."""
    rows = []
    for i in range(n):
        if i < n // 2:
            rows.append({"debt_ratio": 0.3, "loan_amount_wan": 100,
                         "days_past_due": 0})
        else:
            rows.append({"debt_ratio": 0.85, "loan_amount_wan": 100,
                         "days_past_due": 60})
    return pd.DataFrame(rows)


class TestWinnerLogic:
    def test_challenger_wins_when_better_ks_and_profit(self):
        df = _synthetic_df()
        # champion 阈值高 0.95 · 几乎不拒 · 坏账暴露
        champion = _make_ruleset(0.95)
        # challenger 阈值 0.8 · 拒掉所有坏样本 · KS 提升
        challenger = _make_ruleset(0.8)
        res = compare_champion_challenger(df, champion, challenger)
        # challenger 应在统计层有优势
        assert res.challenger_ks >= res.champion_ks

    def test_tie_when_identical_rulesets(self):
        df = _synthetic_df()
        rs = _make_ruleset(0.7)
        res = compare_champion_challenger(df, rs, rs)
        assert res.winner == "tie"
        assert abs(res.ks_delta) < 0.001

    def test_risk_flag_when_pass_rate_drops_significantly(self):
        df = _synthetic_df()
        # champion 几乎不拒 (0.99) · challenger 拒一半 (0.5)
        # → challenger 通过率↓ ≥ 5pp · 触 risk_flag
        champion = _make_ruleset(0.99)
        challenger = _make_ruleset(0.5)
        res = compare_champion_challenger(df, champion, challenger)
        # 若通过率 delta < -5pp 必有 flag
        if res.business_compare.get("pass_rate_delta_pp", 0) < -5.0:
            assert any("通过率下降" in f for f in res.risk_flags)


# ===========================================================================
# Edge
# ===========================================================================


class TestEdge:
    def test_empty_df(self):
        df = pd.DataFrame([{"debt_ratio": 0.5, "days_past_due": 0}]).iloc[0:0]
        rs = _make_ruleset(0.7)
        res = compare_champion_challenger(df, rs, rs)
        assert res.n_records == 0

    def test_label_column_missing_kept_running(self):
        df = pd.DataFrame([
            {"debt_ratio": 0.5, "loan_amount_wan": 100},
            {"debt_ratio": 0.9, "loan_amount_wan": 200},
        ])
        rs = _make_ruleset(0.7)
        # label column 不存在 · KS 应 0 + meta 标 reason · 不抛
        res = compare_champion_challenger(df, rs, rs)
        assert res.champion_ks == 0.0
        assert "reason" in res.champion_ks_meta


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
