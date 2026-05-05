# -*- coding: utf-8 -*-
"""Agent4 BE5 · agent_alert/signal_quality.py 锁盘测试.

锁定:
- freshness_score 4 boundary (today=100 / 3d=70 / 10d=0 / 11d=0 / future=100 / None=0)
- lookup_source_confidence 优先级 type > label > url + default 'med'
- classify_signal_kind 6 prefix → 6 kind + unknown 兜底
- compute_evidence_confidence floor + max 边界
- quality_bundle 一站集成
- infer_signal_kinds 去重 + deterministic 顺序
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from agent_alert.signal_quality import (
    ALL_SIGNAL_KINDS,
    SIGNAL_KIND_BUSINESS,
    SIGNAL_KIND_FINANCIAL,
    SIGNAL_KIND_INDUSTRY,
    SIGNAL_KIND_INTERNAL,
    SIGNAL_KIND_LEGAL,
    SIGNAL_KIND_OTHER,
    SIGNAL_KIND_RELATED,
    classify_signal_kind,
    compute_evidence_confidence,
    freshness_score,
    infer_signal_kinds,
    lookup_source_confidence,
    quality_bundle,
    reload_source_confidence_table,
)


# ---------------------------------------------------------------------------
# freshness_score
# ---------------------------------------------------------------------------


class TestFreshnessScore:
    def test_today_returns_max(self):
        ref = date(2026, 5, 4)
        assert freshness_score(ref, ref=ref) == 100

    def test_3_day_old_decay_30(self):
        assert freshness_score(date(2026, 5, 1), ref=date(2026, 5, 4)) == 70

    def test_10_day_old_returns_zero(self):
        assert freshness_score(date(2026, 4, 24), ref=date(2026, 5, 4)) == 0

    def test_11_day_old_clamps_zero(self):
        assert freshness_score(date(2026, 4, 23), ref=date(2026, 5, 4)) == 0

    def test_future_clamps_max(self):
        # clock skew · 未来事件 clamp 为当天
        assert freshness_score(date(2026, 5, 10), ref=date(2026, 5, 4)) == 100

    def test_none_returns_zero(self):
        assert freshness_score(None) == 0

    def test_iso_string(self):
        assert freshness_score("2026-05-01", ref=date(2026, 5, 4)) == 70

    def test_iso_with_z(self):
        assert freshness_score("2026-05-01T10:00:00Z", ref=date(2026, 5, 4)) == 70

    def test_slash_format(self):
        assert freshness_score("2026/05/01", ref=date(2026, 5, 4)) == 70

    def test_compact_format(self):
        assert freshness_score("20260501", ref=date(2026, 5, 4)) == 70

    def test_datetime_input(self):
        assert freshness_score(datetime(2026, 5, 1, 23, 59), ref=date(2026, 5, 4)) == 70

    def test_invalid_string_returns_zero(self):
        assert freshness_score("not-a-date") == 0

    def test_empty_string_returns_zero(self):
        assert freshness_score("") == 0

    def test_default_ref_is_today(self):
        # 用真 today 算 · 当天 = 100
        assert freshness_score(datetime.now().date()) == 100


# ---------------------------------------------------------------------------
# lookup_source_confidence
# ---------------------------------------------------------------------------


class TestLookupSourceConfidence:
    @pytest.fixture(autouse=True)
    def _reset_cache(self):
        # 每个 test 重新加载 · 避免上下游污染
        reload_source_confidence_table()

    def test_court_high(self):
        assert lookup_source_confidence(source_type="court") == "high"

    def test_pbc_label_high(self):
        assert lookup_source_confidence(source_label="央行") == "high"

    def test_url_domain_match_high(self):
        assert lookup_source_confidence(source_url="http://www.pbc.gov.cn/news") == "high"

    def test_weibo_label_low(self):
        assert lookup_source_confidence(source_label="微博") == "low"

    def test_caixin_med(self):
        assert lookup_source_confidence(source_label="财新") == "med"

    def test_unknown_returns_default_med(self):
        assert lookup_source_confidence(source_type="unknown_xyz") == "med"

    def test_empty_returns_default_med(self):
        assert lookup_source_confidence() == "med"

    def test_priority_type_over_url(self):
        # type 命中应优先于 url
        result = lookup_source_confidence(
            source_type="court",
            source_url="http://weibo.com/some-post",
        )
        assert result == "high"

    def test_url_domain_hint_low(self):
        assert lookup_source_confidence(source_url="https://weibo.com/u/123") == "low"

    def test_court_url_hint(self):
        # wenshu.court.gov.cn 必须命中 court entry → high
        result = lookup_source_confidence(
            source_url="https://wenshu.court.gov.cn/case/12345",
        )
        assert result == "high"


# ---------------------------------------------------------------------------
# classify_signal_kind
# ---------------------------------------------------------------------------


class TestClassifySignalKind:
    def test_law_to_legal(self):
        assert classify_signal_kind("LAW-001") == SIGNAL_KIND_LEGAL
        assert classify_signal_kind("LAW-002") == SIGNAL_KIND_LEGAL

    def test_fin_to_financial(self):
        assert classify_signal_kind("FIN-001") == SIGNAL_KIND_FINANCIAL

    def test_biz_to_business(self):
        assert classify_signal_kind("BIZ-002") == SIGNAL_KIND_BUSINESS

    def test_ind_to_industry(self):
        assert classify_signal_kind("IND-001") == SIGNAL_KIND_INDUSTRY

    def test_rel_to_related(self):
        assert classify_signal_kind("REL-001") == SIGNAL_KIND_RELATED

    def test_pol_to_internal(self):
        assert classify_signal_kind("POL-001") == SIGNAL_KIND_INTERNAL

    def test_unknown_prefix_other(self):
        assert classify_signal_kind("XYZ-001") == SIGNAL_KIND_OTHER

    def test_internal_route_fallback(self):
        # 异常 rule_id 但 route=internal · 走 internal 兜底
        assert classify_signal_kind("XYZ-999", route="internal") == SIGNAL_KIND_INTERNAL

    def test_external_route_falls_to_other(self):
        assert classify_signal_kind("XYZ-999", route="external") == SIGNAL_KIND_OTHER

    def test_lowercase_prefix(self):
        # 容错 lowercase
        assert classify_signal_kind("law-001") == SIGNAL_KIND_LEGAL

    def test_empty_returns_other(self):
        assert classify_signal_kind("") == SIGNAL_KIND_OTHER


# ---------------------------------------------------------------------------
# infer_signal_kinds (跨 hit 聚合)
# ---------------------------------------------------------------------------


class TestInferSignalKinds:
    def test_three_distinct_kinds(self):
        hits = [
            {"rule_id": "LAW-001", "route": "external"},
            {"rule_id": "FIN-002", "route": "external"},
            {"rule_id": "POL-001", "route": "internal"},
        ]
        result = infer_signal_kinds(hits)
        assert set(result) == {
            SIGNAL_KIND_LEGAL,
            SIGNAL_KIND_FINANCIAL,
            SIGNAL_KIND_INTERNAL,
        }
        # diversity ≥ 2 · BE5 解锁 signal_diversity blocker
        assert len(set(result)) >= 2

    def test_dedup(self):
        hits = [
            {"rule_id": "LAW-001"},
            {"rule_id": "LAW-002"},
            {"rule_id": "LAW-003"},
        ]
        assert infer_signal_kinds(hits) == [SIGNAL_KIND_LEGAL]

    def test_empty_returns_empty(self):
        assert infer_signal_kinds([]) == []

    def test_deterministic_order(self):
        # 顺序按 ALL_SIGNAL_KINDS 全局枚举
        hits = [
            {"rule_id": "POL-001"},
            {"rule_id": "LAW-001"},
            {"rule_id": "FIN-001"},
        ]
        result = infer_signal_kinds(hits)
        # FIN 在 POL 之前 · LAW 在 FIN 之前 (per ALL_SIGNAL_KINDS)
        assert result.index(SIGNAL_KIND_LEGAL) < result.index(SIGNAL_KIND_FINANCIAL)
        assert result.index(SIGNAL_KIND_FINANCIAL) < result.index(SIGNAL_KIND_INTERNAL)

    def test_obj_attribute_input(self):
        # 容忍非 dict (RuleHit-like obj)
        class _Hit:
            def __init__(self, rid, route):
                self.rule_id = rid
                self.route = route

        hits = [_Hit("LAW-001", "external"), _Hit("POL-001", "internal")]
        result = infer_signal_kinds(hits)
        assert SIGNAL_KIND_LEGAL in result
        assert SIGNAL_KIND_INTERNAL in result


# ---------------------------------------------------------------------------
# compute_evidence_confidence
# ---------------------------------------------------------------------------


class TestComputeEvidenceConfidence:
    def test_high_full_freshness(self):
        assert compute_evidence_confidence(100, "high") == 0.95

    def test_high_zero_freshness(self):
        assert compute_evidence_confidence(0, "high") == 0.475

    def test_low_zero_freshness_floor(self):
        # 0.45 × 0.5 = 0.225 > floor 0.10
        assert compute_evidence_confidence(0, "low") == 0.225

    def test_floor_kicks_in(self):
        # 极低输入 · floor 兜底
        assert compute_evidence_confidence(0, "low", floor=0.30) == 0.30

    def test_clamps_max_at_one(self):
        # base 不会超 0.95 · 但确保 cap 安全
        result = compute_evidence_confidence(100, "high")
        assert 0.0 <= result <= 1.0

    def test_invalid_level_falls_to_med(self):
        # 不识别 level 当 med 处理
        result = compute_evidence_confidence(100, "garbage")
        assert result == compute_evidence_confidence(100, "med")

    def test_freshness_clamped_negative(self):
        # 负 freshness 视作 0
        assert compute_evidence_confidence(-50, "high") == 0.475

    def test_freshness_clamped_over_max(self):
        # 超 100 视作 100
        assert compute_evidence_confidence(150, "high") == 0.95


# ---------------------------------------------------------------------------
# quality_bundle (一站集成)
# ---------------------------------------------------------------------------


class TestQualityBundle:
    def test_full_bundle(self):
        bundle = quality_bundle(
            rule_id="LAW-002",
            route="external",
            observed_at="2026-05-01",
            source_type="court",
            ref_date=date(2026, 5, 4),
        )
        assert bundle["freshness_score"] == 70
        assert bundle["source_confidence"] == "high"
        assert bundle["signal_kind"] == "legal_signal"
        assert 0.0 < bundle["confidence"] <= 1.0

    def test_internal_rule_bundle(self):
        bundle = quality_bundle(
            rule_id="POL-001",
            route="internal",
            observed_at=date(2026, 5, 4),
            source_type="internal_policy",
            ref_date=date(2026, 5, 4),
        )
        assert bundle["freshness_score"] == 100
        assert bundle["source_confidence"] == "high"
        assert bundle["signal_kind"] == "internal_policy"
        assert bundle["confidence"] == 0.95

    def test_unknown_rule_bundle(self):
        bundle = quality_bundle(
            rule_id="",
            observed_at=None,
            source_type="",
        )
        assert bundle["freshness_score"] == 0
        assert bundle["source_confidence"] == "med"
        assert bundle["signal_kind"] == "other_signal"
        # default med + freshness 0 → 0.7 × 0.5 = 0.35
        assert bundle["confidence"] >= 0.10
