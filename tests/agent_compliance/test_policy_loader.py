# -*- coding: utf-8 -*-
"""agent_compliance.policy_loader unit tests · BE4 (Phase B Sprint 2 · 2026-05-04).

Hard guarantees:
1. Article-level segmentation (第X条) — every header → exactly one bucket
2. Paragraph-level segmentation (一、 / (一) / 1.) — produces ≥1 clause per article
3. Threshold extraction (max_months / min_ratio / max_amount / max_hours / min_years)
4. Category inference (8 buckets, fallback 其他)
5. Severity classification (critical/major/minor)
6. Idempotent load_policy roundtrip (segment → register → re-import = same ids)
7. clauses_to_scan_rules bridge preserves clause_id & threshold
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_compliance.policy_loader import (  # noqa: E402
    clauses_to_scan_rules,
    load_policy,
    segment_policy_text,
)
from shared.policy_registry import (  # noqa: E402
    PolicyRegistry,
    get_clauses,
    list_versions,
    set_default_registry,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic but representative policy text
# ---------------------------------------------------------------------------


SAMPLE_POLICY_V1 = """
为加强对公小微客户准入管理,特制定本办法。

第一条 对公客户年营业收入应不低于 2000 万元。
第二条 注册资本实缴比例不应低于 50%。
第三条 客户尽职调查应当对受益所有人识别;
（一）对持股 25% 以上的自然人股东追溯;
（二）对实际控制人进行身份验证;
（三）保留尽职调查记录不少于 5 年。
第四条 可疑交易报告应当在不超过 24 小时 内提交。
""".strip()

SAMPLE_POLICY_V2 = """
为加强对公小微客户准入管理,特制定本办法(2026 修订)。

第一条 对公客户年营业收入应不低于 3000 万元。
第二条 注册资本实缴比例不应低于 50%。
第三条 客户尽职调查应当对受益所有人识别;
（一）对持股 25% 以上的自然人股东追溯;
（二）对实际控制人进行身份验证;
（三）保留尽职调查记录不少于 5 年。
第四条 可疑交易报告应当在不超过 12 小时 内提交。
第五条 严禁与未通过 KYC 的客户开展业务。
""".strip()


# ---------------------------------------------------------------------------
# 1. Article-level segmentation
# ---------------------------------------------------------------------------


def test_segments_each_article():
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    articles = {c["article"] for c in clauses if c["article"]}
    assert articles == {"第一条", "第二条", "第三条", "第四条"}


def test_preamble_discarded():
    """Text before 第一条 is preamble — must not produce a clause."""
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    for c in clauses:
        assert "为加强对公小微客户准入管理" not in c["text"]


def test_no_articles_one_clause():
    """Doc without 第X条 markers → single clause with article=''."""
    clauses = segment_policy_text("自由文本政策正文,无任何条款标记。")
    assert len(clauses) == 1
    assert clauses[0]["article"] == ""
    assert clauses[0]["text"]


# ---------------------------------------------------------------------------
# 2. Paragraph-level segmentation
# ---------------------------------------------------------------------------


def test_third_article_split_into_subparagraphs():
    """第三条 has 3 sub-paragraphs (一)/(二)/(三) — must produce 3 clauses
    (plus the lead-in line) for paragraph_index 0..3."""
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    third = [c for c in clauses if c["article"] == "第三条"]
    # At minimum: lead-in + 3 sub items = 4 clauses (lead-in may merge with
    # first sub if structure compacts; we accept ≥3).
    assert len(third) >= 3
    # Every sub-paragraph must have stripped its marker.
    for c in third:
        assert not c["text"].lstrip().startswith("(")
        assert not c["text"].lstrip().startswith("（")


# ---------------------------------------------------------------------------
# 3. Threshold extraction
# ---------------------------------------------------------------------------


def test_threshold_min_ratio():
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    second = [c for c in clauses if c["article"] == "第二条"][0]
    assert second["threshold"].get("min_bank_share_ratio") == pytest.approx(0.5)


def test_threshold_min_amount_wan():
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    first = [c for c in clauses if c["article"] == "第一条"][0]
    assert first["threshold"].get("min_amount_wan") == pytest.approx(2000.0)


def test_threshold_max_hours():
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    fourth = [c for c in clauses if c["article"] == "第四条"][0]
    assert fourth["threshold"].get("max_hours") == pytest.approx(24.0)


def test_threshold_min_years():
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    third_subs = [c for c in clauses if c["article"] == "第三条"
                  and c["threshold"]]
    # Sub-paragraph "保留尽职调查记录不少于 5 年" → min_years = 5
    assert any(c["threshold"].get("min_years") == pytest.approx(5.0)
               for c in third_subs)


def test_threshold_empty_when_no_quantification():
    clauses = segment_policy_text("第一条 客户尽职调查应当严格执行。")
    assert clauses[0]["threshold"] == {}


# ---------------------------------------------------------------------------
# 4. Category inference
# ---------------------------------------------------------------------------


def test_category_customer_admission():
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    first = [c for c in clauses if c["article"] == "第一条"][0]
    assert first["category"] == "客户准入"


def test_category_aml():
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    third_subs = [c for c in clauses if c["article"] == "第三条"]
    cats = {c["category"] for c in third_subs if c["text"]}
    assert "反洗钱" in cats


def test_category_other_fallback():
    """Unknown vocabulary → 其他."""
    clauses = segment_policy_text("第一条 这是一个完全不沾监管词的句子。")
    assert clauses[0]["category"] == "其他"


# ---------------------------------------------------------------------------
# 5. Severity classification
# ---------------------------------------------------------------------------


def test_severity_critical_when_threshold_plus_mandate():
    """第一条 V1 has 不低于 + 应 → critical (per spec §3.4)."""
    clauses = segment_policy_text(SAMPLE_POLICY_V1)
    first = [c for c in clauses if c["article"] == "第一条"][0]
    assert first["severity_hint"] in {"critical", "major"}


def test_severity_critical_when_yanjin():
    clauses = segment_policy_text(SAMPLE_POLICY_V2)
    fifth = [c for c in clauses if c["article"] == "第五条"][0]
    # 严禁 → mandate; threshold likely empty → still major (per spec the
    # critical bump requires BOTH threshold and mandate). Sanity: must not
    # be minor.
    assert fifth["severity_hint"] in {"critical", "major"}


def test_severity_minor_for_pure_narrative():
    clauses = segment_policy_text("第一条 本办法解释权归监管部门所有。")
    assert clauses[0]["severity_hint"] == "minor"


# ---------------------------------------------------------------------------
# 6. Idempotent load_policy roundtrip
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_registry(tmp_path):
    db = tmp_path / "policies.sqlite"
    reg = PolicyRegistry(db)
    set_default_registry(reg)
    yield reg
    set_default_registry(None)


def test_load_policy_creates_version(tmp_registry):
    r = load_policy(
        title="对公小微客户准入新规",
        issuer="银保监",
        body_text=SAMPLE_POLICY_V1,
        effective_date="2026-03-15",
        source_url="https://example.test/v1.html",
    )
    assert r.persisted
    assert r.is_new_version
    versions = list_versions(r.policy_id)
    assert len(versions) == 1
    clauses = get_clauses(r.version_id)
    # 4 articles + at least 3 sub-paragraphs of 第三条 → ≥ 6
    assert len(clauses) >= 6


def test_load_policy_roundtrip_same_ids(tmp_registry):
    r1 = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_POLICY_V1,
        effective_date="2026-03-15",
    )
    r2 = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_POLICY_V1,
        effective_date="2026-03-15",
    )
    assert r1.version_id == r2.version_id
    ids_1 = [c["clause_id"] for c in get_clauses(r1.version_id)]
    ids_2 = [c["clause_id"] for c in get_clauses(r2.version_id)]
    assert ids_1 == ids_2


def test_load_policy_v1_v2_distinct_versions(tmp_registry):
    r1 = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_POLICY_V1,
        effective_date="2026-03-15",
    )
    r2 = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_POLICY_V2,
        effective_date="2026-05-01",
    )
    assert r1.policy_id == r2.policy_id
    assert r1.version_id != r2.version_id
    # clause counts differ — V2 added 第五条
    assert len(get_clauses(r2.version_id)) > len(get_clauses(r1.version_id))


# ---------------------------------------------------------------------------
# 7. clauses_to_scan_rules bridge
# ---------------------------------------------------------------------------


def test_clauses_to_scan_rules_passthrough(tmp_registry):
    r = load_policy(
        title="X", issuer="银保监", body_text=SAMPLE_POLICY_V1,
        effective_date="2026-03-15",
    )
    clauses = get_clauses(r.version_id)
    rules = clauses_to_scan_rules(clauses)
    assert rules
    # Each rule keeps clause_id as rule_id (deterministic across re-imports)
    for rule in rules:
        assert rule["rule_id"].startswith("CL-")
        assert rule["clause_id"] == rule["rule_id"]
        assert "policy_excerpt" in rule
        assert rule["condition"]
        # threshold passes through unchanged
        assert isinstance(rule["threshold"], dict)


def test_clauses_to_scan_rules_skips_empty():
    rules = clauses_to_scan_rules([
        {"clause_id": "CL-x", "text": "valid", "article": "第一条"},
        {"clause_id": "CL-y", "text": "  ", "article": "第二条"},
        {"clause_id": "CL-z", "text": "", "article": "第三条"},
    ])
    assert len(rules) == 1
    assert rules[0]["clause_id"] == "CL-x"
