# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_psi_monthly.py — BE8.6+8.7 PSI 月度 + 分月趋势 unit tests."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from agent_riskctrl.psi_monthly import (
    PSI_GREEN,
    PSI_YELLOW,
    compute_monthly_trend,
    compute_psi_by_month,
    format_psi_summary,
    format_trend_report,
    psi_severity,
    write_psi_jsonl,
)
from agent_riskctrl.rule_engine import RuleCondition, RuleSet, StrategyRule


def _synthetic_monthly_df(months_drift: bool = False) -> pd.DataFrame:
    """生成 3 月 × 100 sample · drift=True 时 2025-03 debt_ratio 飘高."""
    rows = []
    for month, drift in [
        ("2025-01", 0.0),
        ("2025-02", 0.0),
        ("2025-03", 0.3 if months_drift else 0.0),
    ]:
        for i in range(100):
            base_debt = 0.4 + (i / 1000.0)  # 0.4-0.5
            rows.append({
                "originated_month": month,
                "debt_ratio": base_debt + drift,
                "loan_amount_wan": 100,
                "credit_score": 700,
                "days_past_due": 0 if i < 80 else 60,
            })
    return pd.DataFrame(rows)


# ===========================================================================
# psi_severity
# ===========================================================================


def test_psi_severity_stable():
    assert psi_severity(0.05) == "stable"


def test_psi_severity_drift():
    assert psi_severity(0.15) == "drift"


def test_psi_severity_severe():
    assert psi_severity(0.30) == "severe_drift"


def test_psi_severity_boundaries():
    assert psi_severity(PSI_GREEN) == "drift"   # >= 0.10
    assert psi_severity(PSI_YELLOW) == "severe_drift"  # >= 0.25


# ===========================================================================
# compute_psi_by_month
# ===========================================================================


class TestPSIByMonth:
    def test_no_drift_when_stable(self):
        df = _synthetic_monthly_df(months_drift=False)
        records = compute_psi_by_month(
            df, baseline_month="2025-01",
            feature_cols=["debt_ratio", "credit_score"],
        )
        # 三月都 stable
        for r in records:
            assert r.severity == "stable", (
                f"unexpected severity: {r.feature} {r.target_month} "
                f"PSI={r.psi}"
            )

    def test_drift_detected_when_present(self):
        df = _synthetic_monthly_df(months_drift=True)
        records = compute_psi_by_month(
            df, baseline_month="2025-01",
            feature_cols=["debt_ratio"],
        )
        mar_record = [r for r in records if r.target_month == "2025-03"]
        assert mar_record
        # debt_ratio 全偏移 0.3 · PSI 应该很大
        assert mar_record[0].psi > PSI_GREEN

    def test_baseline_month_excluded(self):
        df = _synthetic_monthly_df()
        records = compute_psi_by_month(df, baseline_month="2025-01")
        for r in records:
            assert r.target_month != "2025-01"

    def test_auto_feature_selection(self):
        df = _synthetic_monthly_df()
        records = compute_psi_by_month(df, baseline_month="2025-01")
        features = {r.feature for r in records}
        # days_past_due / loan_id / month_col 应被排除
        assert "days_past_due" not in features
        assert "originated_month" not in features
        # debt_ratio 数值列应在
        assert "debt_ratio" in features

    def test_empty_df(self):
        df = pd.DataFrame([{"originated_month": "2025-01", "debt_ratio": 0.5}]).iloc[0:0]
        assert compute_psi_by_month(df, "2025-01") == []

    def test_missing_month_col(self):
        df = pd.DataFrame([{"debt_ratio": 0.5}])
        assert compute_psi_by_month(df, "2025-01", month_col="ghost") == []

    def test_baseline_month_not_in_data(self):
        df = _synthetic_monthly_df()
        # baseline 月不存在 · 返空
        assert compute_psi_by_month(df, "1999-01") == []


# ===========================================================================
# write_psi_jsonl
# ===========================================================================


class TestWriteJsonl:
    def test_writes_target_month_only(self, tmp_path):
        df = _synthetic_monthly_df(months_drift=True)
        records = compute_psi_by_month(
            df, baseline_month="2025-01",
            feature_cols=["debt_ratio", "credit_score"],
        )
        out = write_psi_jsonl(records, target_month="2025-03", out_dir=tmp_path)
        assert out.exists()
        # 读回 · 全是 2025-03
        with out.open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                assert rec["target_month"] == "2025-03"

    def test_jsonl_format_each_line_one_object(self, tmp_path):
        df = _synthetic_monthly_df()
        records = compute_psi_by_month(df, baseline_month="2025-01")
        out = write_psi_jsonl(records, "2025-02", out_dir=tmp_path)
        with out.open(encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        for line in lines:
            obj = json.loads(line)
            for key in ("target_month", "baseline_month", "feature",
                        "psi", "severity", "n_target", "n_baseline"):
                assert key in obj

    def test_dir_created(self, tmp_path):
        deep_dir = tmp_path / "psi" / "2025"
        df = _synthetic_monthly_df()
        records = compute_psi_by_month(df, "2025-01")
        out = write_psi_jsonl(records, "2025-02", out_dir=deep_dir)
        assert out.parent.exists()


# ===========================================================================
# compute_monthly_trend
# ===========================================================================


class TestTrend:
    def test_basic_trend(self):
        df = _synthetic_monthly_df()
        rs = RuleSet(rules=[
            StrategyRule(
                rule_id="R001", name="debt cap", priority=1, action="reject",
                conditions=[RuleCondition(field="debt_ratio", operator=">", value=0.7)],
            ),
        ])
        trend = compute_monthly_trend(df, rs)
        assert len(trend) == 3  # 3 months
        assert all(p.n_records == 100 for p in trend)

    def test_trend_keys_present(self):
        df = _synthetic_monthly_df()
        rs = RuleSet(rules=[
            StrategyRule(
                rule_id="R001", name="r", priority=1, action="reject",
                conditions=[RuleCondition(field="debt_ratio", operator=">", value=0.7)],
            ),
        ])
        trend = compute_monthly_trend(df, rs)
        for p in trend:
            assert hasattr(p, "ks")
            assert hasattr(p, "pass_rate")
            assert hasattr(p, "bad_rate")
            assert hasattr(p, "profit_total_wan")

    def test_psi_avg_injection(self):
        df = _synthetic_monthly_df(months_drift=True)
        psi_records = compute_psi_by_month(
            df, "2025-01", feature_cols=["debt_ratio"],
        )
        rs = RuleSet(rules=[
            StrategyRule(
                rule_id="R001", name="r", priority=1, action="reject",
                conditions=[RuleCondition(field="debt_ratio", operator=">", value=0.7)],
            ),
        ])
        trend = compute_monthly_trend(df, rs, psi_records=psi_records)
        # 2025-01 是基线 · psi_avg = 0
        # 2025-03 应有非零 PSI
        m1 = [p for p in trend if p.month == "2025-01"][0]
        m3 = [p for p in trend if p.month == "2025-03"][0]
        assert m1.psi_avg == 0.0
        assert m3.psi_avg > 0


# ===========================================================================
# Format
# ===========================================================================


class TestFormat:
    def test_trend_report(self):
        df = _synthetic_monthly_df()
        rs = RuleSet(rules=[
            StrategyRule(
                rule_id="R001", name="r", priority=1, action="reject",
                conditions=[RuleCondition(field="debt_ratio", operator=">", value=0.7)],
            ),
        ])
        trend = compute_monthly_trend(df, rs)
        out = format_trend_report(trend)
        assert "分月趋势" in out
        assert "2025-01" in out
        assert "通过率" in out

    def test_trend_report_empty(self):
        out = format_trend_report([])
        assert "为空" in out

    def test_psi_summary(self):
        df = _synthetic_monthly_df(months_drift=True)
        records = compute_psi_by_month(
            df, "2025-01", feature_cols=["debt_ratio"],
        )
        out = format_psi_summary(records)
        assert "PSI 月度漂移监控" in out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
