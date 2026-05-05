# -*- coding: utf-8 -*-
"""Agent4 BE9.2 · alert_clusterer.py 锁盘测试 (Phase B Sprint 2 · 2026-05-04).

锁定:
- jaccard_set 算法正确 (含空集 boundary)
- 单 hit / 双 hit / 不到 min_size · 不返 cluster
- ≥ 3 客户共同 pattern · 返 cluster (per §6.4)
- 跨 industry 不同客户 · 仍 cluster (industries 透传不影响 jaccard)
- 不同 pattern 客户分开 cluster
- urgency_score 0-100 · red 多 / size 大 / 共同 rule 多都加权
- pattern_id 稳定 hash (相同 signature → 相同 id)
- threshold 调节 · 0.7 vs 0.85 不同结果
"""
from __future__ import annotations

import pytest

from agent_alert.alert_clusterer import (
    DEFAULT_JACCARD_THRESHOLD,
    DEFAULT_MIN_CLUSTER_SIZE,
    compute_clusters,
    compute_urgency_score,
)
from shared.similarity import jaccard_set


# ---------------------------------------------------------------------------
# jaccard_set boundaries
# ---------------------------------------------------------------------------


class TestJaccardSet:
    def test_full_overlap(self):
        assert jaccard_set({"a", "b"}, {"a", "b"}) == 1.0

    def test_no_overlap(self):
        assert jaccard_set({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        # |a∩b|=1, |a∪b|=3
        assert abs(jaccard_set({"a", "b"}, {"a", "c"}) - 1 / 3) < 1e-9

    def test_subset(self):
        # 2/3
        result = jaccard_set({"a", "b"}, {"a", "b", "c"})
        assert abs(result - 2 / 3) < 1e-9

    def test_both_empty_returns_zero(self):
        assert jaccard_set([], []) == 0.0

    def test_one_empty_returns_zero(self):
        assert jaccard_set({"a"}, []) == 0.0

    def test_list_input(self):
        assert jaccard_set(["a", "a", "b"], ["a", "b"]) == 1.0  # set dedup


# ---------------------------------------------------------------------------
# compute_clusters · 基础形态
# ---------------------------------------------------------------------------


class TestComputeClustersBasic:
    def test_empty_hits_returns_empty(self):
        assert compute_clusters([]) == []

    def test_single_hit_no_cluster(self):
        hits = [{"client_id": "C1", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]}]
        assert compute_clusters(hits) == []

    def test_two_matching_hits_below_min_size(self):
        # 默认 min_size=3 · 2 client 不成 cluster
        hits = [
            {"client_id": "C1", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]},
            {"client_id": "C2", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]},
        ]
        assert compute_clusters(hits) == []

    def test_three_identical_signature_cluster(self):
        hits = [
            {"client_id": "C1", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"], "tier": "red", "score": 0.9},
            {"client_id": "C2", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"], "tier": "red", "score": 0.85},
            {"client_id": "C3", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"], "tier": "yellow", "score": 0.6},
        ]
        clusters = compute_clusters(hits)
        assert len(clusters) == 1
        c = clusters[0]
        assert set(c["affected_clients"]) == {"C1", "C2", "C3"}
        assert c["common_rules"] == ["LAW-001"]
        assert c["common_kinds"] == ["legal_signal"]
        assert c["size"] == 3

    def test_pattern_id_stable_hash(self):
        # 相同 signature 必产相同 pattern_id (re-run 一致 · audit reproducible)
        hits1 = [
            {"client_id": f"A{i}", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]}
            for i in range(3)
        ]
        hits2 = [
            {"client_id": f"B{i}", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]}
            for i in range(3)
        ]
        c1 = compute_clusters(hits1)
        c2 = compute_clusters(hits2)
        assert c1[0]["pattern_id"] == c2[0]["pattern_id"]

    def test_urgency_in_range(self):
        hits = [
            {"client_id": f"C{i}", "matched_rules": ["LAW-001", "FIN-002"],
             "signal_kinds": ["legal_signal", "financial_signal"], "tier": "red"}
            for i in range(5)
        ]
        clusters = compute_clusters(hits)
        assert clusters[0]["urgency_score"] >= 0
        assert clusters[0]["urgency_score"] <= 100


# ---------------------------------------------------------------------------
# compute_clusters · 多模式分组
# ---------------------------------------------------------------------------


class TestMultiClusters:
    def test_two_distinct_patterns_two_clusters(self):
        # 3 客户共触 LAW · 3 客户共触 FIN · 应分 2 cluster
        hits = []
        for i in range(3):
            hits.append({
                "client_id": f"L{i}",
                "matched_rules": ["LAW-001", "LAW-002"],
                "signal_kinds": ["legal_signal"],
                "tier": "red",
            })
        for i in range(3):
            hits.append({
                "client_id": f"F{i}",
                "matched_rules": ["FIN-001"],
                "signal_kinds": ["financial_signal"],
                "tier": "yellow",
            })
        clusters = compute_clusters(hits)
        assert len(clusters) == 2
        ids_per_cluster = [set(c["affected_clients"]) for c in clusters]
        assert any(ids == {"L0", "L1", "L2"} for ids in ids_per_cluster)
        assert any(ids == {"F0", "F1", "F2"} for ids in ids_per_cluster)

    def test_no_cluster_when_threshold_too_high(self):
        # 全是单 rule 命中 · jaccard=1.0 · 但调阈值 1.01 (不可能) → 不 cluster
        # 实际测略低: {LAW-001} vs {LAW-001,FIN-001} = 1/2 < 0.7
        hits = [
            {"client_id": "C1", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]},
            {"client_id": "C2", "matched_rules": ["LAW-001", "FIN-001"], "signal_kinds": ["legal_signal", "financial_signal"]},
            {"client_id": "C3", "matched_rules": ["LAW-001", "FIN-001", "POL-001"],
             "signal_kinds": ["legal_signal", "financial_signal", "internal_policy"]},
        ]
        # 默认 0.7 阈值 · C1 vs C2 = jaccard(1/2.5)=0.4 · C2 vs C3 = jaccard(0.66) → C2-C3 union, C1 singleton
        # 结果: C2+C3 一个组 (size=2, < min=3) → 不返
        clusters = compute_clusters(hits)
        assert clusters == []  # no cluster meets min_size=3

    def test_cross_industry_clusters(self):
        # 同 pattern 跨 industry · industries 透传 (但不影响聚合)
        hits = [
            {"client_id": "A", "matched_rules": ["IND-001"], "signal_kinds": ["industry_signal"],
             "tier": "yellow", "industry": "光伏"},
            {"client_id": "B", "matched_rules": ["IND-001"], "signal_kinds": ["industry_signal"],
             "tier": "yellow", "industry": "光伏"},
            {"client_id": "C", "matched_rules": ["IND-001"], "signal_kinds": ["industry_signal"],
             "tier": "red", "industry": "光伏"},
            {"client_id": "D", "matched_rules": ["IND-001"], "signal_kinds": ["industry_signal"],
             "tier": "red", "industry": "汽车零部件"},
        ]
        clusters = compute_clusters(hits)
        assert len(clusters) == 1
        c = clusters[0]
        assert set(c["industries"]) == {"光伏", "汽车零部件"}
        assert len(c["affected_clients"]) == 4


# ---------------------------------------------------------------------------
# urgency_score · 加权逻辑
# ---------------------------------------------------------------------------


class TestUrgencyScore:
    def test_size_weight_increasing(self):
        s_3 = compute_urgency_score(size=3, tier_dist={"yellow": 3}, common_rules_count=1)
        s_10 = compute_urgency_score(size=10, tier_dist={"yellow": 10}, common_rules_count=1)
        assert s_10 > s_3

    def test_red_heavier_than_yellow(self):
        s_red = compute_urgency_score(size=3, tier_dist={"red": 3}, common_rules_count=1)
        s_yel = compute_urgency_score(size=3, tier_dist={"yellow": 3}, common_rules_count=1)
        assert s_red > s_yel

    def test_more_common_rules_higher(self):
        s_1 = compute_urgency_score(size=3, tier_dist={"red": 3}, common_rules_count=1)
        s_3 = compute_urgency_score(size=3, tier_dist={"red": 3}, common_rules_count=3)
        assert s_3 > s_1

    def test_max_capped_100(self):
        # 超大 cluster + all red + 多 rule
        s = compute_urgency_score(size=100, tier_dist={"red": 100}, common_rules_count=10)
        assert s == 100

    def test_min_zero(self):
        s = compute_urgency_score(size=3, tier_dist={"green": 3}, common_rules_count=0)
        assert 0 <= s <= 30


# ---------------------------------------------------------------------------
# Pattern_id stability + cluster label
# ---------------------------------------------------------------------------


class TestClusterMetadata:
    def test_pattern_id_format(self):
        hits = [
            {"client_id": f"C{i}", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]}
            for i in range(3)
        ]
        clusters = compute_clusters(hits)
        assert clusters[0]["pattern_id"].startswith("PTN-")
        assert len(clusters[0]["pattern_id"]) == len("PTN-12345678")

    def test_cluster_label_human_readable(self):
        hits = [
            {"client_id": f"C{i}", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"], "tier": "red"}
            for i in range(3)
        ]
        clusters = compute_clusters(hits)
        label = clusters[0]["cluster_label"]
        assert "3 客户" in label
        assert "legal_signal" in label

    def test_evidence_pointers_one_per_client(self):
        hits = [
            {"client_id": f"C{i}", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"],
             "tier": "red", "score": 0.5 + 0.1 * i, "company_name": f"公司{i}"}
            for i in range(3)
        ]
        clusters = compute_clusters(hits)
        ptrs = clusters[0]["evidence_pointers"]
        assert len(ptrs) == 3
        for p in ptrs:
            assert "client_id" in p
            assert "score" in p
            assert "top_rule" in p


# ---------------------------------------------------------------------------
# Threshold tuning
# ---------------------------------------------------------------------------


class TestThresholdTuning:
    def test_default_threshold_07(self):
        assert DEFAULT_JACCARD_THRESHOLD == 0.7

    def test_default_min_size_3(self):
        # per agent-handoff-schemas §6.4
        assert DEFAULT_MIN_CLUSTER_SIZE == 3

    def test_relaxed_threshold_more_clusters(self):
        # 同样 hits · 阈值 0.3 vs 0.9 → 0.3 多 cluster
        hits = [
            {"client_id": "A", "matched_rules": ["R1", "R2"], "signal_kinds": ["k1"]},
            {"client_id": "B", "matched_rules": ["R1", "R3"], "signal_kinds": ["k1"]},
            {"client_id": "C", "matched_rules": ["R1"], "signal_kinds": ["k1", "k2"]},
        ]
        c_loose = compute_clusters(hits, threshold=0.3)
        c_strict = compute_clusters(hits, threshold=0.95)
        # loose 至少能成 1 cluster · strict 不必
        assert len(c_loose) >= len(c_strict)

    def test_min_size_2_allows_pairs(self):
        hits = [
            {"client_id": "A", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]},
            {"client_id": "B", "matched_rules": ["LAW-001"], "signal_kinds": ["legal_signal"]},
        ]
        c = compute_clusters(hits, min_size=2)
        assert len(c) == 1
