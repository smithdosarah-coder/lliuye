# -*- coding: utf-8 -*-
"""shared.evidence_drawer 单测 · 共性架构 #2."""
from __future__ import annotations

import pytest

from shared.evidence_drawer import Evidence, EvidenceDrawer, default_drawer


@pytest.fixture
def drawer():
    return EvidenceDrawer()


class TestAttach:
    def test_returns_evidence_id(self, drawer):
        eid = drawer.attach(
            claim_id="c1",
            source="gsxt:91440300708461136T",
            anchor="cell=B2",
            snippet="腾讯科技 注册资本 800万",
            source_tier=2,
        )
        assert eid.startswith("ev_")
        assert len(eid) == len("ev_") + 16

    def test_dedup_same_source_and_hash(self, drawer):
        eid1 = drawer.attach(
            claim_id="c1", source="x", anchor="a", snippet="一样的话",
            source_tier=1,
        )
        eid2 = drawer.attach(
            claim_id="c1", source="x", anchor="b", snippet="一样的话",
            source_tier=1,
        )
        assert eid1 == eid2

    def test_no_dedup_across_claims(self, drawer):
        eid1 = drawer.attach(
            claim_id="c1", source="x", anchor="a", snippet="一样",
            source_tier=1,
        )
        eid2 = drawer.attach(
            claim_id="c2", source="x", anchor="a", snippet="一样",
            source_tier=1,
        )
        assert eid1 != eid2

    def test_invalid_tier_raises(self, drawer):
        with pytest.raises(ValueError):
            drawer.attach(claim_id="c", source="x", anchor="a", snippet="s", source_tier=5)
        with pytest.raises(ValueError):
            drawer.attach(claim_id="c", source="x", anchor="a", snippet="s", source_tier=0)

    def test_required_fields(self, drawer):
        with pytest.raises(ValueError):
            drawer.attach(claim_id="", source="x", anchor="a", snippet="s", source_tier=1)
        with pytest.raises(ValueError):
            drawer.attach(claim_id="c", source="", anchor="a", snippet="s", source_tier=1)

    def test_confidence_clamped(self, drawer):
        eid = drawer.attach(
            claim_id="c", source="x", anchor="a", snippet="s",
            source_tier=1, confidence=2.5,
        )
        assert drawer.get_evidence(eid).confidence == 1.0

    def test_snippet_truncated(self, drawer):
        long = "x" * 3000
        eid = drawer.attach(
            claim_id="c", source="x", anchor="a", snippet=long,
            source_tier=1,
        )
        assert len(drawer.get_evidence(eid).snippet) == 2048

    def test_default_retrieved_at_today(self, drawer):
        eid = drawer.attach(
            claim_id="c", source="x", anchor="a", snippet="s", source_tier=1,
        )
        ev = drawer.get_evidence(eid)
        # ISO YYYY-MM-DD · 10 字符
        assert len(ev.retrieved_at) == 10
        assert ev.retrieved_at[4] == "-"


class TestList:
    def test_list_evidence_in_attach_order(self, drawer):
        ids = []
        for i in range(3):
            ids.append(drawer.attach(
                claim_id="c",
                source=f"src_{i}",
                anchor=f"a_{i}",
                snippet=f"text_{i}",
                source_tier=1,
            ))
        items = drawer.list_evidence("c")
        assert [ev.evidence_id for ev in items] == ids

    def test_list_unknown_claim_empty(self, drawer):
        assert drawer.list_evidence("nope") == []


class TestDrawerPayload:
    def test_payload_empty(self, drawer):
        payload = drawer.to_drawer_payload("nope")
        assert payload["claim_id"] == "nope"
        assert payload["evidence_count"] == 0
        assert payload["min_tier"] is None
        assert payload["items"] == []

    def test_payload_tier_distribution(self, drawer):
        for src, tier in [("a", 1), ("b", 2), ("c", 4), ("d", 4)]:
            drawer.attach(claim_id="c1", source=src, anchor="x", snippet=src, source_tier=tier)
        payload = drawer.to_drawer_payload("c1")
        assert payload["evidence_count"] == 4
        assert payload["min_tier"] == 1
        assert payload["tier_distribution"] == {1: 1, 2: 1, 4: 2}
        assert len(payload["items"]) == 4


class TestVerifyClaimsHaveEvidence:
    def test_all_clean(self, drawer):
        for cid in ["c1", "c2"]:
            drawer.attach(claim_id=cid, source="x", anchor="a", snippet=cid, source_tier=2)
        assert drawer.verify_claims_have_evidence(["c1", "c2"]) == []

    def test_missing_evidence_flagged(self, drawer):
        drawer.attach(claim_id="c1", source="x", anchor="a", snippet="x", source_tier=1)
        violations = drawer.verify_claims_have_evidence(["c1", "c_no_evidence"])
        assert len(violations) == 1
        assert "c_no_evidence" in violations[0]

    def test_min_count_enforced(self, drawer):
        drawer.attach(claim_id="c1", source="x", anchor="a", snippet="x", source_tier=1)
        # 阈值 ≥ 2 · c1 仅 1 条
        violations = drawer.verify_claims_have_evidence(["c1"], min_evidence_count=2)
        assert len(violations) == 1
        assert "1 条证据" in violations[0]

    def test_tier_threshold_enforced(self, drawer):
        # 最高权威是 tier 4 · 但 max_tier_allowed=3 → 拒
        drawer.attach(claim_id="c1", source="web", anchor="a", snippet="x", source_tier=4)
        violations = drawer.verify_claims_have_evidence(["c1"], max_tier_allowed=3)
        assert len(violations) == 1
        assert "tier=4" in violations[0]


class TestStats:
    def test_stats_empty(self, drawer):
        s = drawer.stats()
        assert s["total_evidence"] == 0
        assert s["total_claims"] == 0

    def test_stats_after_attach(self, drawer):
        drawer.attach(claim_id="c1", source="x", anchor="a", snippet="x", source_tier=1)
        drawer.attach(claim_id="c1", source="y", anchor="a", snippet="y", source_tier=4)
        drawer.attach(claim_id="c2", source="z", anchor="a", snippet="z", source_tier=2)
        s = drawer.stats()
        assert s["total_evidence"] == 3
        assert s["total_claims"] == 2
        assert s["tier_distribution"][1] == 1
        assert s["tier_distribution"][2] == 1
        assert s["tier_distribution"][4] == 1


class TestDefaultDrawer:
    def test_singleton(self):
        d1 = default_drawer()
        d2 = default_drawer()
        assert d1 is d2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
