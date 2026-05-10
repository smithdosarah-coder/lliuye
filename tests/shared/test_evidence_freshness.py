# -*- coding: utf-8 -*-
"""shared.evidence_freshness 单测.

Phase A.1 hotfix · per RFC freshness-claim-loan-sample (ratified 2026-05-09).
覆盖 LOAN_SAMPLE (365d) + BACKTEST_FIXTURE (730d) 两个新加 ClaimType.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from shared.evidence_freshness import (
    FRESHNESS_SLA_DAYS,
    ClaimType,
    classify_freshness,
    compute_freshness_days,
    compute_recency_weight,
    validate_evidence_freshness,
)


REF = datetime(2026, 5, 9)


class TestNewClaimTypeRegistered:
    def test_loan_sample_in_enum(self):
        assert ClaimType.LOAN_SAMPLE.value == "loan_sample"

    def test_backtest_fixture_in_enum(self):
        assert ClaimType.BACKTEST_FIXTURE.value == "backtest_fixture"

    def test_loan_sample_sla_365(self):
        assert FRESHNESS_SLA_DAYS[ClaimType.LOAN_SAMPLE] == 365

    def test_backtest_fixture_sla_730(self):
        assert FRESHNESS_SLA_DAYS[ClaimType.BACKTEST_FIXTURE] == 730

    def test_string_lookup_works(self):
        # consumer (riskctrl) 可能用 string 查 enum
        assert ClaimType("loan_sample") == ClaimType.LOAN_SAMPLE
        assert ClaimType("backtest_fixture") == ClaimType.BACKTEST_FIXTURE

    def test_existing_claim_types_unchanged(self):
        # 兼容性 verify · 现 11 ClaimType + GENERIC SLA 不变
        assert FRESHNESS_SLA_DAYS[ClaimType.NEWS] == 180
        assert FRESHNESS_SLA_DAYS[ClaimType.FINANCIAL] == 120
        assert FRESHNESS_SLA_DAYS[ClaimType.PENALTY] == 365
        assert FRESHNESS_SLA_DAYS[ClaimType.GENERIC] == 180


class TestLoanSampleFreshness:
    """LOAN_SAMPLE · 365d SLA · 信贷周期 12 月 · riskctrl backtest 用."""

    def test_30_days_old_is_fresh(self):
        d = (REF - timedelta(days=30)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.LOAN_SAMPLE, reference_date=REF,
        )
        assert not result["is_stale"]
        assert result["sla_days"] == 365
        assert not result["block_as_core_claim"]
        assert result["recency_weight"] >= 0.4  # < 180d → 0.7

    def test_90_days_old_is_fresh(self):
        d = (REF - timedelta(days=90)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.LOAN_SAMPLE, reference_date=REF,
        )
        assert not result["is_stale"]
        assert not result["block_as_core_claim"]

    def test_at_sla_boundary_365d_is_stale(self):
        # > 365d → stale (严格 > sla)
        d = (REF - timedelta(days=400)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.LOAN_SAMPLE, reference_date=REF,
        )
        assert result["is_stale"]
        assert result["block_as_core_claim"]

    def test_just_under_sla_is_ok_but_aged(self):
        # 364d · 边缘 ok (in SLA · aging band · weight 0.4)
        d = (REF - timedelta(days=364)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.LOAN_SAMPLE, reference_date=REF,
        )
        assert not result["is_stale"]
        assert result["recency_weight"] == 0.4

    def test_3y_old_is_very_stale(self):
        d = (REF - timedelta(days=1095)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.LOAN_SAMPLE, reference_date=REF,
        )
        assert result["is_stale"]
        assert result["classification"] == "very_stale"
        assert result["recency_weight"] == 0.05


class TestBacktestFixtureFreshness:
    """BACKTEST_FIXTURE · 730d SLA · 完整信贷周期 2y · 容忍长."""

    def test_18_months_is_fresh(self):
        # 18 月 = 540d · 仍 < 730d SLA
        d = (REF - timedelta(days=540)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.BACKTEST_FIXTURE, reference_date=REF,
        )
        assert not result["is_stale"]
        assert result["sla_days"] == 730

    def test_at_2y_boundary_ok(self):
        # 729d · 边缘 ok
        d = (REF - timedelta(days=729)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.BACKTEST_FIXTURE, reference_date=REF,
        )
        assert not result["is_stale"]

    def test_3y_old_is_stale(self):
        d = (REF - timedelta(days=1095)).date().isoformat()
        result = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.BACKTEST_FIXTURE, reference_date=REF,
        )
        assert result["is_stale"]
        assert result["block_as_core_claim"]

    def test_loan_sample_vs_backtest_fixture_at_540d(self):
        # 540d · BACKTEST_FIXTURE 仍 fresh · LOAN_SAMPLE 已 stale
        d = (REF - timedelta(days=540)).date().isoformat()
        loan = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.LOAN_SAMPLE, reference_date=REF,
        )
        fixture = validate_evidence_freshness(
            evidence_date=d, claim_type=ClaimType.BACKTEST_FIXTURE, reference_date=REF,
        )
        assert loan["is_stale"]
        assert not fixture["is_stale"]


class TestRiskctrlBacktestScenario:
    """end-to-end · 模拟 riskctrl backtest 消费 7500 行 mock loans.csv (按 80/20 分层)."""

    def test_distribution_80_20_passes_majority(self):
        # 假设 80% < 365d · 20% in 365-1095d
        # → fresh count ≈ 80% · stale count ≈ 20%
        # 需 stale_mask.mean() < 30% 才不 warn (per RFC §1 backtest stale check)
        evidences = [
            {"evidence_date": (REF - timedelta(days=200)).date().isoformat(),
             "claim_type": "loan_sample"}
            for _ in range(80)
        ] + [
            {"evidence_date": (REF - timedelta(days=600)).date().isoformat(),
             "claim_type": "loan_sample"}
            for _ in range(20)
        ]
        from shared.evidence_freshness import validate_evidence_chain
        result = validate_evidence_chain(evidences)
        # 20% stale · < 30% warn 阈值
        assert result["stale_count"] == 20
        assert result["stale_count"] / result["total_count"] == 0.2

    def test_missing_sample_date_blocks_core_claim(self):
        # 历史数据缺 sample_date · 不可作核心 claim (per CLAUDE.md §3.5.1 第 6 原则)
        result = validate_evidence_freshness(
            evidence_date=None, claim_type=ClaimType.LOAN_SAMPLE,
        )
        assert result["is_missing_date"]
        assert result["block_as_core_claim"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
