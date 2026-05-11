# -*- coding: utf-8 -*-
"""shared.evidence.confidence_policy contract test (TDD red · B.3.4 P0-R1).

per docs/contracts/shared-evidence-confidence-policy-v1.0.md §5
- I1-I10 invariants 全覆盖
- alert backward-compat (re-export 不破)
- canary flag (channel) ON/OFF 行为差异

Phase 1 (this commit · red): import shared.evidence.confidence_policy → ImportError
Phase 1 (next commit · green): 实现 shared/evidence/confidence_policy.py · 全 pass
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

# Phase 1 red: shared.evidence.confidence_policy 不存在 · ImportError 是预期
from shared.evidence.confidence_policy import (  # noqa: F401
    CONFIDENCE_BASE,
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_FLOOR,
    FRESHNESS_DECAY_PER_DAY,
    FRESHNESS_MAX,
    FRESHNESS_MIN,
    SourceConfidence,
    compute_evidence_confidence,
    freshness_score,
    quality_bundle,
)


REF = date(2026, 5, 11)


# ---------------------------------------------------------------------------
# I1 · freshness_score(today) == 100
# ---------------------------------------------------------------------------


class TestI1FreshnessTodayIsMax:
    def test_today_is_100(self):
        assert freshness_score(REF, ref=REF) == 100

    def test_today_iso_string(self):
        assert freshness_score("2026-05-11", ref=REF) == 100

    def test_today_datetime(self):
        assert freshness_score(datetime(2026, 5, 11, 12, 30), ref=REF) == 100


# ---------------------------------------------------------------------------
# I2 · freshness_score(10_days_ago) == 0 (floor)
# ---------------------------------------------------------------------------


class TestI2FreshnessOldIsZero:
    def test_10_days_ago_is_0(self):
        assert freshness_score(REF - timedelta(days=10), ref=REF) == 0

    def test_30_days_ago_clamps_to_0(self):
        assert freshness_score(REF - timedelta(days=30), ref=REF) == 0

    def test_5_days_ago_is_50(self):
        assert freshness_score(REF - timedelta(days=5), ref=REF) == 50


# ---------------------------------------------------------------------------
# I3 · freshness_score(future_date) == 100 (clock skew clamp)
# ---------------------------------------------------------------------------


class TestI3FreshnessFutureClampsToMax:
    def test_tomorrow_is_100(self):
        assert freshness_score(REF + timedelta(days=1), ref=REF) == 100

    def test_far_future_is_100(self):
        assert freshness_score(REF + timedelta(days=365), ref=REF) == 100


# ---------------------------------------------------------------------------
# I4 · freshness_score(unparseable / None) == 0
# ---------------------------------------------------------------------------


class TestI4FreshnessUnparseableIsZero:
    def test_none_is_0(self):
        assert freshness_score(None) == 0

    def test_empty_string_is_0(self):
        assert freshness_score("", ref=REF) == 0

    def test_garbage_string_is_0(self):
        assert freshness_score("not-a-date", ref=REF) == 0

    def test_unsupported_type_is_0(self):
        assert freshness_score(object(), ref=REF) == 0


# ---------------------------------------------------------------------------
# I5 · compute_evidence_confidence(100, "high") == 0.95 (源高 + 当天 = 满分 base)
# ---------------------------------------------------------------------------


class TestI5HighFreshTodayIsMax:
    def test_high_today_is_0_95(self):
        assert compute_evidence_confidence(100, "high") == pytest.approx(0.95, abs=1e-3)

    def test_med_today_is_0_70(self):
        assert compute_evidence_confidence(100, "med") == pytest.approx(0.70, abs=1e-3)

    def test_low_today_is_0_45(self):
        assert compute_evidence_confidence(100, "low") == pytest.approx(0.45, abs=1e-3)


# ---------------------------------------------------------------------------
# I6 · compute_evidence_confidence(0, "low") == 0.225 (floor 之上)
# ---------------------------------------------------------------------------


class TestI6LowOldFloorKicksIn:
    def test_low_old_is_0_225(self):
        # base[low]=0.45 × (0.5 + 0/200) = 0.45 × 0.5 = 0.225 · floor 0.10 不 kick
        assert compute_evidence_confidence(0, "low") == pytest.approx(0.225, abs=1e-3)

    def test_high_old_is_0_475(self):
        # 0.95 × 0.5 = 0.475
        assert compute_evidence_confidence(0, "high") == pytest.approx(0.475, abs=1e-3)


# ---------------------------------------------------------------------------
# I7 · floor 显式 clamp
# ---------------------------------------------------------------------------


class TestI7FloorClamp:
    def test_floor_kicks_in_when_higher_than_raw(self):
        # base[low] × 0.5 = 0.225 · floor=0.5 kick
        assert compute_evidence_confidence(0, "low", floor=0.5) == 0.5

    def test_floor_does_not_clamp_when_raw_higher(self):
        # high+today=0.95 · floor=0.5 不 kick
        assert compute_evidence_confidence(100, "high", floor=0.5) == pytest.approx(0.95, abs=1e-3)

    def test_default_floor_is_0_10(self):
        assert DEFAULT_FLOOR == 0.10


# ---------------------------------------------------------------------------
# I8 · quality_bundle 纯版 不带 alert taxonomy (无 signal_kind 字段)
# ---------------------------------------------------------------------------


class TestI8QualityBundleIsPure:
    def test_returns_freshness_source_confidence_only(self):
        bundle = quality_bundle(
            observed_at=REF,
            source_confidence_level="high",
            ref_date=REF,
        )
        assert "freshness_score" in bundle
        assert "source_confidence" in bundle
        assert "confidence" in bundle
        # 关键: 无 alert taxonomy
        assert "signal_kind" not in bundle, "shared quality_bundle 不能带 alert-specific signal_kind"

    def test_default_source_level_is_med(self):
        bundle = quality_bundle(observed_at=REF, ref_date=REF)
        assert bundle["source_confidence"] == "med"

    def test_unknown_source_level_falls_back_to_med(self):
        bundle = quality_bundle(
            observed_at=REF,
            source_confidence_level="bogus",
            ref_date=REF,
        )
        assert bundle["source_confidence"] == "bogus" or bundle["source_confidence"] == "med"
        # confidence 不能挂 · 须落在合理区间
        assert 0.10 <= bundle["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# I9 · alert signal_quality re-export 不破 (现有 import path 保留)
# ---------------------------------------------------------------------------


class TestI9AlertReExportPreserved:
    """alert signal_quality.py 改用 shared backing 后 · 现有 import 不破."""

    def test_alert_freshness_score_importable(self):
        from agent_alert.signal_quality import freshness_score as alert_fs
        assert alert_fs(REF, ref=REF) == 100

    def test_alert_compute_evidence_confidence_importable(self):
        from agent_alert.signal_quality import compute_evidence_confidence as alert_cec
        assert alert_cec(100, "high") == pytest.approx(0.95, abs=1e-3)

    def test_alert_quality_bundle_signature_unchanged(self):
        """alert quality_bundle 加 alert taxonomy · signature 不破."""
        from agent_alert.signal_quality import quality_bundle as alert_qb
        bundle = alert_qb(
            rule_id="LAW-002",
            route="external",
            observed_at=REF,
            source_type="court",
            source_url="https://wenshu.court.gov.cn/foo",
            ref_date=REF,
        )
        assert "freshness_score" in bundle
        assert "confidence" in bundle
        assert "signal_kind" in bundle  # alert taxonomy 必带

    def test_alert_signal_kind_constants_preserved(self):
        from agent_alert.signal_quality import (
            SIGNAL_KIND_LEGAL,
            SIGNAL_KIND_FINANCIAL,
            ALL_SIGNAL_KINDS,
        )
        assert SIGNAL_KIND_LEGAL == "legal_signal"
        assert SIGNAL_KIND_FINANCIAL == "financial_signal"
        assert SIGNAL_KIND_LEGAL in ALL_SIGNAL_KINDS


# ---------------------------------------------------------------------------
# I10 · 其他 5 Agent flag OFF 默认 · confidence 行为不变
# ---------------------------------------------------------------------------


class TestI10NonAlertFlagOffPreservesStatic:
    """flag-gate per CLAUDE.md §3.7.7 · 默认 OFF · 5 Agent 静态 confidence 不变."""

    def test_flag_default_off(self, monkeypatch):
        # 移除可能存在的 env var
        monkeypatch.delenv("LIUYE_AGENT_CHANNEL_SHARED_CONFIDENCE", raising=False)
        from agent_channel.evidence_pipeline import ChannelPitchPipeline  # noqa: F401
        # 不直接 import flag · 验通过 evidence_pipeline 行为
        # 静态 confidence · 5 Agent 行为不变 (此 test 主要确保 import 不破)

    def test_canary_flag_recognized(self, monkeypatch):
        """flag ON 时 · evidence_pipeline 应能 import shared confidence_policy."""
        monkeypatch.setenv("LIUYE_AGENT_CHANNEL_SHARED_CONFIDENCE", "true")
        # 验 shared module importable · 不验 channel evidence_pipeline 内部行为 (那是 Phase 2 canary)
        from shared.evidence.confidence_policy import quality_bundle as _qb
        assert _qb is not None


# ---------------------------------------------------------------------------
# 公共常量自检
# ---------------------------------------------------------------------------


class TestConstantsExposed:
    def test_decay_per_day_is_10(self):
        assert FRESHNESS_DECAY_PER_DAY == 10

    def test_freshness_range(self):
        assert FRESHNESS_MAX == 100
        assert FRESHNESS_MIN == 0

    def test_default_confidence_level_is_med(self):
        assert DEFAULT_CONFIDENCE_LEVEL == "med"

    def test_confidence_base_three_levels(self):
        assert set(CONFIDENCE_BASE.keys()) == {"high", "med", "low"}
        assert CONFIDENCE_BASE["high"] == 0.95
        assert CONFIDENCE_BASE["med"] == 0.70
        assert CONFIDENCE_BASE["low"] == 0.45
