# -*- coding: utf-8 -*-
"""shared.entity_resolver.candidate_helpers 单测.

per candidate-identity-contract.md §6 · 6 agent emit 时必填 id 字段的 wrapper.
"""
from __future__ import annotations

import pytest

from shared.entity_resolver import (
    ensure_candidate_id,
    ensure_list_unique_ids,
    verify_candidate_ids,
)


class TestEnsureCandidateId:
    def test_adds_id_when_missing(self):
        c = {"name": "腾讯", "uscc": "91440300708461136T"}
        ensure_candidate_id(c, idx=0)
        assert c["id"] == "uscc_91440300708461136T"

    def test_preserves_existing_id(self):
        c = {"name": "X", "uscc": "Y", "id": "manual_id_42"}
        ensure_candidate_id(c, idx=0)
        assert c["id"] == "manual_id_42"

    def test_overrides_regression_id_object(self):
        # "[object Object]" 是 regression · 必覆盖
        c = {"name": "腾讯", "uscc": "91440300708461136T", "id": "[object Object]"}
        ensure_candidate_id(c, idx=0)
        assert c["id"] == "uscc_91440300708461136T"

    def test_overrides_regression_id_text(self):
        c = {"name": "腾讯", "id": "未获取"}
        ensure_candidate_id(c, idx=2)
        assert c["id"] != "未获取"
        assert c["id"].startswith("name_")

    def test_idx_fallback_when_empty(self):
        c = {}
        ensure_candidate_id(c, idx=7)
        assert c["id"] == "cand_007"

    def test_custom_field_names(self):
        c = {"company_name": "腾讯", "credit_code": "91440300708461136T"}
        ensure_candidate_id(c, idx=0, name_field="company_name", uscc_field="credit_code")
        assert c["id"] == "uscc_91440300708461136T"


class TestEnsureListUniqueIds:
    def test_all_ids_filled(self):
        cands = [
            {"name": "腾讯", "uscc": "91440300708461136T"},
            {"name": "阿里巴巴"},
            {},
        ]
        ensure_list_unique_ids(cands)
        assert cands[0]["id"] == "uscc_91440300708461136T"
        assert cands[1]["id"].startswith("name_")
        assert cands[2]["id"] == "cand_002"

    def test_unique_within_list(self):
        cands = [{"name": f"公司 {i}"} for i in range(10)]
        ensure_list_unique_ids(cands)
        ids = [c["id"] for c in cands]
        assert len(set(ids)) == 10

    def test_duplicate_collision_resolved(self):
        # 2 条同 name (normalize 后相同) · 第 2 条加 _idx 后缀
        cands = [
            {"name": "腾讯有限公司"},
            {"name": "腾讯股份有限公司"},  # normalize 后都是 "腾讯"
        ]
        ensure_list_unique_ids(cands)
        ids = [c["id"] for c in cands]
        assert len(set(ids)) == 2  # 全 unique
        assert ids[1].endswith("_1")  # 后缀 _1


class TestVerifyCandidateIds:
    def test_all_clean(self):
        cands = [
            {"id": "uscc_91440300708461136T"},
            {"id": "name_abc123def456"},
            {"id": "cand_002"},
        ]
        assert verify_candidate_ids(cands) == []

    def test_missing_id_flagged(self):
        cands = [{"name": "X"}]
        violations = verify_candidate_ids(cands)
        assert len(violations) == 1
        assert "缺 id" in violations[0]

    def test_regression_placeholder_flagged(self):
        cands = [
            {"id": "未获取"},
            {"id": "[object Object]"},
            {"id": "null"},
            {"id": "undefined"},
        ]
        violations = verify_candidate_ids(cands)
        assert len(violations) == 4

    def test_duplicate_flagged(self):
        cands = [{"id": "x"}, {"id": "x"}]
        violations = verify_candidate_ids(cands)
        assert len(violations) == 1
        assert "重复" in violations[0]

    def test_non_string_flagged(self):
        cands = [{"id": 42}]
        violations = verify_candidate_ids(cands)
        assert len(violations) == 1
        assert "不是 str" in violations[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
