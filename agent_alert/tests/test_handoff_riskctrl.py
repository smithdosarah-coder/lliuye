# -*- coding: utf-8 -*-
"""Agent4 BE9.3 · handoff_riskctrl.py 锁盘测试 (Phase B Sprint 2 · 2026-05-04).

锁定 (per docs/contracts/agent-handoff-schemas.md v1.1 §6.4):
- build_pattern_proposal cluster → payload schema 完整
- 必字段 schema_version="1.0" / source/target_agent / intent_type
- affected_clients < 3 → ValueError (§6.4 触发条件硬线)
- proposal_type 启发式 (跨行业大 → new_rule · 否则 rule_update)
- signal_features 涵盖 rule/kind/industry/tier
- urgency_score 透传 cluster
- is_proposal_valid 全方位校验
- fixture data/mock/handoff/agent4-to-2-pattern.json 形态符合 spec
- E2E: alert_clusterer → handoff_riskctrl 链路通
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_alert.alert_clusterer import compute_clusters
from agent_alert.handoff_riskctrl import (
    INTENT_TYPE,
    MIN_AFFECTED_CLIENTS,
    SCHEMA_VERSION,
    SOURCE_AGENT,
    TARGET_AGENT,
    build_pattern_proposal,
    build_proposals_for_clusters,
    is_proposal_valid,
)


# ---------------------------------------------------------------------------
# build_pattern_proposal · 单 cluster
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_cluster():
    return {
        "pattern_id": "PTN-test1234",
        "affected_clients": ["C1", "C2", "C3"],
        "common_rules": ["LAW-001", "FIN-002"],
        "common_kinds": ["legal_signal", "financial_signal"],
        "industries": ["光伏"],
        "tier_distribution": {"red": 2, "yellow": 1},
        "urgency_score": 65,
        "cluster_label": "3 客户共触发 legal_signal+financial_signal · LAW-001+FIN-002",
        "evidence_pointers": [
            {"client_id": "C1", "score": 0.9, "top_rule": "LAW-001", "tier": "red"},
            {"client_id": "C2", "score": 0.85, "top_rule": "LAW-001", "tier": "red"},
            {"client_id": "C3", "score": 0.55, "top_rule": "FIN-002", "tier": "yellow"},
        ],
    }


class TestBuildPatternProposal:
    def test_required_keys_all_present(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        for k in (
            "schema_version", "intent_type", "source_agent", "target_agent",
            "pattern_id", "pattern_description", "affected_clients",
            "signal_features", "proposal_type", "urgency_score", "generated_at",
        ):
            assert k in p, f"missing required key {k}"

    def test_schema_version_locked(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        assert p["schema_version"] == "1.0"

    def test_source_target_locked(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        assert p["source_agent"] == "alert"
        assert p["target_agent"] == "riskctrl"
        assert p["intent_type"] == "pattern_to_rule_proposal"

    def test_pattern_id_propagated(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        assert p["pattern_id"] == "PTN-test1234"

    def test_affected_clients_propagated(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        assert p["affected_clients"] == ["C1", "C2", "C3"]

    def test_urgency_propagated(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        assert p["urgency_score"] == 65

    def test_signal_features_cover_rules(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        rule_features = [f for f in p["signal_features"] if f["feature_type"] == "matched_rule"]
        assert len(rule_features) == 2
        values = {f["value"] for f in rule_features}
        assert values == {"LAW-001", "FIN-002"}

    def test_signal_features_cover_kinds(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        kind_features = [f for f in p["signal_features"] if f["feature_type"] == "signal_kind"]
        values = {f["value"] for f in kind_features}
        assert values == {"legal_signal", "financial_signal"}

    def test_signal_features_include_tier_dist(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        tier_features = [f for f in p["signal_features"] if f["feature_type"] == "tier_distribution"]
        assert len(tier_features) == 1
        assert tier_features[0]["value"] == {"red": 2, "yellow": 1}

    def test_proposal_type_default_single_industry(self, sample_cluster):
        # 单行业 + size 3 < 5 → "rule_update"
        p = build_pattern_proposal(sample_cluster)
        assert p["proposal_type"] == "rule_update"

    def test_proposal_type_cross_industry_large(self):
        # 多行业 + size ≥ 5 → "new_rule" 启发
        cluster = {
            "pattern_id": "PTN-cross",
            "affected_clients": [f"C{i}" for i in range(5)],
            "common_rules": ["IND-001"],
            "common_kinds": ["industry_signal"],
            "industries": ["光伏", "汽车零部件", "钢铁"],
            "tier_distribution": {"red": 3, "yellow": 2},
            "urgency_score": 80,
            "cluster_label": "5 客户...",
            "evidence_pointers": [],
        }
        p = build_pattern_proposal(cluster)
        assert p["proposal_type"] == "new_rule"

    def test_proposal_type_explicit_override(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster, proposal_type="new_rule")
        assert p["proposal_type"] == "new_rule"


# ---------------------------------------------------------------------------
# Validation · §6.4 触发条件硬线
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_pattern_id_raises(self):
        cluster = {"pattern_id": "", "affected_clients": ["C1", "C2", "C3"]}
        with pytest.raises(ValueError, match="pattern_id"):
            build_pattern_proposal(cluster)

    def test_below_min_size_raises(self):
        cluster = {
            "pattern_id": "PTN-x",
            "affected_clients": ["C1", "C2"],  # < 3
        }
        with pytest.raises(ValueError, match="6.4"):
            build_pattern_proposal(cluster)

    def test_min_size_enforced(self):
        # spec §6.4 触发条件 ≥ 3
        assert MIN_AFFECTED_CLIENTS == 3


# ---------------------------------------------------------------------------
# build_proposals_for_clusters · 批量处理
# ---------------------------------------------------------------------------


class TestBuildProposalsForClusters:
    def test_skip_too_small(self, sample_cluster):
        small_cluster = {**sample_cluster, "affected_clients": ["C1", "C2"]}
        proposals = build_proposals_for_clusters([sample_cluster, small_cluster])
        assert len(proposals) == 1  # 只 sample_cluster 满足 min_size
        assert proposals[0]["pattern_id"] == "PTN-test1234"

    def test_sort_by_urgency_desc(self):
        c1 = {
            "pattern_id": "PTN-low", "affected_clients": ["a", "b", "c"],
            "common_rules": [], "common_kinds": [], "industries": [],
            "tier_distribution": {}, "urgency_score": 30,
            "cluster_label": "low", "evidence_pointers": [],
        }
        c2 = {
            "pattern_id": "PTN-high", "affected_clients": ["x", "y", "z"],
            "common_rules": [], "common_kinds": [], "industries": [],
            "tier_distribution": {}, "urgency_score": 80,
            "cluster_label": "high", "evidence_pointers": [],
        }
        proposals = build_proposals_for_clusters([c1, c2])
        assert proposals[0]["urgency_score"] == 80
        assert proposals[1]["urgency_score"] == 30

    def test_empty_input(self):
        assert build_proposals_for_clusters([]) == []


# ---------------------------------------------------------------------------
# is_proposal_valid · 消费侧防御
# ---------------------------------------------------------------------------


class TestIsProposalValid:
    def test_valid_proposal(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        assert is_proposal_valid(p) is True

    def test_missing_required_key_invalid(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        del p["pattern_id"]
        assert is_proposal_valid(p) is False

    def test_wrong_schema_version_invalid(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        p["schema_version"] = "0.9"
        assert is_proposal_valid(p) is False

    def test_wrong_source_agent_invalid(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        p["source_agent"] = "channel"
        assert is_proposal_valid(p) is False

    def test_wrong_proposal_type_invalid(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        p["proposal_type"] = "garbage"
        assert is_proposal_valid(p) is False

    def test_urgency_out_of_range_invalid(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        p["urgency_score"] = 150
        assert is_proposal_valid(p) is False

    def test_too_few_affected_invalid(self, sample_cluster):
        p = build_pattern_proposal(sample_cluster)
        p["affected_clients"] = ["A", "B"]  # < 3
        assert is_proposal_valid(p) is False

    def test_non_dict_invalid(self):
        assert is_proposal_valid("not-a-dict") is False  # type: ignore[arg-type]
        assert is_proposal_valid([]) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Fixture · data/mock/handoff/agent4-to-2-pattern.json 形态
# ---------------------------------------------------------------------------


def test_fixture_file_exists():
    p = Path("data/mock/handoff/agent4-to-2-pattern.json")
    assert p.is_file(), "fixture 不存在 · spec §6.4 要求 v1.1 placeholder"


def test_fixture_passes_validation():
    p = Path("data/mock/handoff/agent4-to-2-pattern.json")
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert is_proposal_valid(payload), "fixture 不符合 §6.4 schema"


def test_fixture_schema_compliance():
    p = Path("data/mock/handoff/agent4-to-2-pattern.json")
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["source_agent"] == "alert"
    assert payload["target_agent"] == "riskctrl"
    assert payload["intent_type"] == "pattern_to_rule_proposal"
    assert len(payload["affected_clients"]) >= 3


# ---------------------------------------------------------------------------
# E2E · alert_clusterer → handoff_riskctrl 链路
# ---------------------------------------------------------------------------


def test_e2e_clusterer_to_handoff():
    """端到端: 从 batch_scan-shape hits → cluster → handoff payload."""
    # 模拟 batch_scan aggregate_hits 形态 (BE9.1 输出)
    hits = [
        {
            "client_id": f"E2E-{i}",
            "company_name": f"测试公司{i}",
            "matched_rules": ["IND-001", "LAW-001"],
            "signal_kinds": ["industry_signal", "legal_signal"],
            "tier": "red" if i < 2 else "yellow",
            "score": 0.7 + 0.05 * i,
            "industry": "光伏",
            "scenario_key": "demo",
        }
        for i in range(4)
    ]

    clusters = compute_clusters(hits)
    assert len(clusters) == 1  # 全 hit 同 signature → 1 cluster

    proposals = build_proposals_for_clusters(clusters)
    assert len(proposals) == 1
    p = proposals[0]
    assert is_proposal_valid(p)
    assert len(p["affected_clients"]) == 4
    assert "industry_signal" in [
        f["value"] for f in p["signal_features"] if f["feature_type"] == "signal_kind"
    ]
