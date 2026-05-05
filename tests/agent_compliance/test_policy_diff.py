# -*- coding: utf-8 -*-
"""agent_compliance.policy_diff unit tests · BE4 (Phase B Sprint 2 · 2026-05-04).

Hard guarantees:
1. Identical clause sets → 0 diffs (or all unchanged when include_unchanged)
2. Pure addition is detected as "add"
3. Pure deletion is detected as "delete"
4. Same (article, paragraph_index) with text edit → "change" + similarity < 1
5. Fuzzy relocation (article changed, text mostly intact) → "change" with
   old_clause_id != new_clause_id
6. Below-threshold similarity → "delete" + "add" (not "change")
7. ndiff hunks present on "change" rows
8. summarize_diff counters match
9. diff_versions reads from registry
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_compliance.policy_diff import (  # noqa: E402
    ClauseDiff,
    diff_clauses,
    diff_versions,
    summarize_diff,
)
from agent_compliance.policy_loader import load_policy  # noqa: E402
from shared.policy_registry import PolicyRegistry, set_default_registry  # noqa: E402


# ---------------------------------------------------------------------------
# Inline fixtures (don't depend on registry)
# ---------------------------------------------------------------------------


def _c(cid, article, idx, text):
    return {
        "clause_id": cid,
        "article": article,
        "paragraph_index": idx,
        "text": text,
    }


# ---------------------------------------------------------------------------
# 1. Equality / unchanged
# ---------------------------------------------------------------------------


def test_identical_sets_default_no_diffs():
    src = [_c("A", "第一条", 0, "对公客户年营业收入应不低于 2000 万元。")]
    dst = [_c("A", "第一条", 0, "对公客户年营业收入应不低于 2000 万元。")]
    diffs = diff_clauses(src, dst)
    assert diffs == []


def test_identical_sets_with_include_unchanged():
    src = [_c("A", "第一条", 0, "营业收入 2000 万元。")]
    dst = [_c("A", "第一条", 0, "营业收入 2000 万元。")]
    diffs = diff_clauses(src, dst, include_unchanged=True)
    assert len(diffs) == 1
    assert diffs[0].diff_type == "unchanged"
    assert diffs[0].similarity == 1.0


# ---------------------------------------------------------------------------
# 2. Add / delete
# ---------------------------------------------------------------------------


def test_pure_addition_is_add():
    src: list[dict] = []
    dst = [_c("X", "第一条", 0, "新增条款。")]
    diffs = diff_clauses(src, dst)
    assert len(diffs) == 1
    assert diffs[0].diff_type == "add"
    assert diffs[0].new_clause_id == "X"
    assert diffs[0].old_clause_id is None
    assert diffs[0].similarity == 0.0


def test_pure_deletion_is_delete():
    src = [_c("Y", "第一条", 0, "废止条款。")]
    dst: list[dict] = []
    diffs = diff_clauses(src, dst)
    assert len(diffs) == 1
    assert diffs[0].diff_type == "delete"
    assert diffs[0].old_clause_id == "Y"
    assert diffs[0].new_clause_id is None


# ---------------------------------------------------------------------------
# 3. Change with similarity < 1.0
# ---------------------------------------------------------------------------


def test_threshold_tightening_is_change():
    src = [_c("A", "第一条", 0, "对公客户年营业收入应不低于 2000 万元。")]
    dst = [_c("B", "第一条", 0, "对公客户年营业收入应不低于 3000 万元。")]
    diffs = diff_clauses(src, dst)
    assert len(diffs) == 1
    d = diffs[0]
    assert d.diff_type == "change"
    assert 0.0 < d.similarity < 1.0
    assert d.old_clause_id == "A"
    assert d.new_clause_id == "B"
    assert d.old_article == d.new_article == "第一条"
    # ndiff hunks are present
    assert d.hunks
    assert any("- " in h or "+ " in h for h in d.hunks)


def test_change_keeps_paragraph_index_pairing():
    """第三条 paragraph (二) edited → still pairs by (article,idx)."""
    src = [
        _c("A1", "第三条", 0, "尽职调查应当对受益所有人识别。"),
        _c("A2", "第三条", 1, "对持股 25% 以上的自然人股东追溯。"),
    ]
    dst = [
        _c("B1", "第三条", 0, "尽职调查应当对受益所有人识别。"),
        _c("B2", "第三条", 1, "对持股 20% 以上的自然人股东追溯。"),  # 25 → 20
    ]
    diffs = diff_clauses(src, dst)
    # idx 0 unchanged (omitted by default), idx 1 changed
    changes = [d for d in diffs if d.diff_type == "change"]
    assert len(changes) == 1
    assert changes[0].old_clause_id == "A2"
    assert changes[0].new_clause_id == "B2"


# ---------------------------------------------------------------------------
# 4. Fuzzy relocation across articles
# ---------------------------------------------------------------------------


def test_fuzzy_relocation_is_change():
    """Same content, different article — fuzzy path catches it."""
    src = [_c("A", "第三条", 1, "对持股 25% 以上的自然人股东追溯尽职调查。")]
    dst = [_c("B", "第四条", 0, "对持股 25% 以上的自然人股东追溯尽职调查。")]
    diffs = diff_clauses(src, dst)
    # Both keys differ, but content identical → fuzzy match
    assert len(diffs) == 1
    d = diffs[0]
    assert d.diff_type == "change"
    assert d.old_article == "第三条"
    assert d.new_article == "第四条"
    assert d.similarity == pytest.approx(1.0)


def test_below_threshold_is_separate_add_and_delete():
    """Two unrelated clauses → no change row, both add+delete."""
    src = [_c("A", "第一条", 0, "营业收入门槛 2000 万元。")]
    dst = [_c("B", "第二条", 0, "可疑交易报告 24 小时内提交。")]
    diffs = diff_clauses(src, dst, fuzzy_threshold=0.55)
    types = sorted(d.diff_type for d in diffs)
    assert types == ["add", "delete"]


# ---------------------------------------------------------------------------
# 5. summarize_diff
# ---------------------------------------------------------------------------


def test_summarize_diff_counters():
    diffs = [
        ClauseDiff("add", None, "x", "", "第一条", "", "n", 0.0),
        ClauseDiff("delete", "y", None, "第二条", "", "o", "", 0.0),
        ClauseDiff("change", "z1", "z2", "第三条", "第三条", "old", "new", 0.5),
        ClauseDiff("change", "z3", "z4", "第四条", "第四条", "old", "new2", 0.7),
        ClauseDiff("unchanged", "w1", "w2", "第五条", "第五条", "same", "same", 1.0),
    ]
    summary = summarize_diff(diffs)
    assert summary["add"] == 1
    assert summary["delete"] == 1
    assert summary["change"] == 2
    assert summary["unchanged"] == 1
    assert summary["total"] == 5
    assert summary["avg_similarity"] == pytest.approx(0.6)


def test_summarize_empty():
    summary = summarize_diff([])
    assert summary["total"] == 0
    assert summary["avg_similarity"] == 0.0


# ---------------------------------------------------------------------------
# 6. diff_versions reads from registry
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_registry(tmp_path):
    db = tmp_path / "policies.sqlite"
    reg = PolicyRegistry(db)
    set_default_registry(reg)
    yield reg
    set_default_registry(None)


SAMPLE_V1 = """
第一条 对公客户年营业收入应不低于 2000 万元。
第二条 注册资本实缴比例不应低于 50%。
第四条 可疑交易报告应当在不超过 24 小时 内提交。
""".strip()

SAMPLE_V2 = """
第一条 对公客户年营业收入应不低于 3000 万元。
第二条 注册资本实缴比例不应低于 50%。
第四条 可疑交易报告应当在不超过 12 小时 内提交。
第五条 严禁与未通过 KYC 的客户开展业务。
""".strip()


def test_diff_versions_e2e(tmp_registry):
    r1 = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_V1,
        effective_date="2026-01-01",
    )
    r2 = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_V2,
        effective_date="2026-05-01",
    )
    diffs = diff_versions(r1.version_id, r2.version_id)
    summary = summarize_diff(diffs)

    # Articles 1, 4 changed (threshold tightening)
    # Article 2 unchanged → omitted by default
    # Article 5 added
    assert summary["add"] == 1, summary
    assert summary["change"] >= 2, summary  # at least 第一条 and 第四条
    assert summary["delete"] == 0, summary

    # The added clause is 第五条
    added = [d for d in diffs if d.diff_type == "add"]
    assert added[0].new_article == "第五条"
    assert "严禁" in added[0].new_text


def test_diff_versions_idempotent_on_same_version(tmp_registry):
    r = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_V1,
        effective_date="2026-01-01",
    )
    diffs = diff_versions(r.version_id, r.version_id)
    # Same version → no rows by default (all unchanged)
    assert diffs == []
    diffs_inc = diff_versions(
        r.version_id, r.version_id, include_unchanged=True,
    )
    assert all(d.diff_type == "unchanged" for d in diffs_inc)


def test_to_dict_round_trip():
    d = ClauseDiff("change", "A", "B", "第一条", "第一条",
                   "old text", "new text", 0.83, hunks=["- old", "+ new"])
    blob = d.to_dict()
    assert blob["diff_type"] == "change"
    assert blob["similarity"] == 0.83
    assert blob["hunks"] == ["- old", "+ new"]
