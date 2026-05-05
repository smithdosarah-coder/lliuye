# -*- coding: utf-8 -*-
"""agent_compliance.violation_schema unit tests · BE4 (Phase B Sprint 2 · 2026-05-04).

Hard guarantees:
1. All 7 mandatory fields must be populated · None of them empty
2. Excerpts truncated to EXCERPT_MAX_CHARS (300) at boundary
3. confidence ∈ [0.0, 1.0]; out-of-range raises ValidationError
4. policy_id / policy_version / clause_id prefix sanity (POL-/VER-/CL-)
5. build_violation_reason returns None when triplet is missing
6. confidence: hard-rule = 1.0, LLM violate = 0.7, override always wins
7. derive_conflict_field uses cell.evidence first, then threshold map
8. review_reason is single-sentence narrative (deterministic; no LLM)
9. is_complete catches malformed payloads
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_compliance.violation_schema import (  # noqa: E402
    EXCERPT_MAX_CHARS,
    ViolationReason,
    build_violation_reason,
    derive_conflict_field,
    derive_review_reason,
)


# ---------------------------------------------------------------------------
# 1. Schema invariants
# ---------------------------------------------------------------------------


def _ok_reason_dict(**overrides) -> dict:
    base = {
        "policy_id": "POL-abcdef0123456789",
        "policy_version": "VER-abcdef0123456789",
        "clause_id": "CL-abcdef0123456789",
        "conflict_field": "营业收入",
        "business_excerpt": "客户A年营业收入 1500 万元",
        "policy_excerpt": "对公客户年营业收入应不低于 2000 万元",
        "confidence": 1.0,
    }
    base.update(overrides)
    return base


def test_seven_fields_round_trip():
    reason = ViolationReason.model_validate(_ok_reason_dict())
    d = reason.to_dict()
    for k in ("policy_id", "policy_version", "clause_id", "conflict_field",
              "business_excerpt", "policy_excerpt", "confidence"):
        assert d[k]
    assert "review_reason" in d


def test_excerpt_bounded_at_300():
    long_text = "x" * 500
    reason = ViolationReason.model_validate(_ok_reason_dict(
        business_excerpt=long_text,
        policy_excerpt=long_text,
    ))
    assert len(reason.business_excerpt) <= EXCERPT_MAX_CHARS
    assert len(reason.policy_excerpt) <= EXCERPT_MAX_CHARS
    # Trailing ellipsis preserved when truncated
    assert reason.business_excerpt.endswith("…")


def test_confidence_out_of_range_raises():
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(confidence=1.5))
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(confidence=-0.1))


def test_id_prefix_required():
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(policy_id="bad-id"))
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(policy_version="VVV-x"))
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(clause_id="CLAUSE-x"))


def test_empty_required_field_raises():
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(conflict_field=""))
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(business_excerpt="   "))
    with pytest.raises(Exception):
        ViolationReason.model_validate(_ok_reason_dict(policy_excerpt=""))


def test_is_complete_helper():
    assert ViolationReason.is_complete(_ok_reason_dict()) is True
    assert ViolationReason.is_complete({"policy_id": "POL-x"}) is False
    assert ViolationReason.is_complete("not a dict") is False
    assert ViolationReason.is_complete(None) is False


# ---------------------------------------------------------------------------
# 2. derive_conflict_field
# ---------------------------------------------------------------------------


def test_derive_conflict_field_uses_cell_evidence():
    rule = {"category": "客户准入", "threshold": {}}
    event = {}
    cell = {"evidence": "amount_wan=1500 低于阈值 min_amount_wan=2000"}
    cf = derive_conflict_field(rule, event, cell)
    assert cf == "金额(万元)"


def test_derive_conflict_field_unknown_field_passes_through():
    rule = {"category": "其他", "threshold": {}}
    cell = {"evidence": "weird_metric=42 低于阈值"}
    cf = derive_conflict_field(rule, {}, cell)
    assert cf == "weird_metric"


def test_derive_conflict_field_falls_back_to_threshold_map():
    rule = {"category": "客户准入", "threshold": {"min_amount_wan": 2000}}
    cf = derive_conflict_field(rule, {}, None)
    assert cf == "金额(万元)"


def test_derive_conflict_field_falls_back_to_category():
    rule = {"category": "信息披露", "threshold": {}}
    cf = derive_conflict_field(rule, {}, None)
    assert cf == "信息披露"


def test_derive_conflict_field_default_when_all_empty():
    rule = {}
    cf = derive_conflict_field(rule, {}, None)
    assert cf == "合规阈值"


# ---------------------------------------------------------------------------
# 3. derive_review_reason — single-sentence narrative
# ---------------------------------------------------------------------------


def test_derive_review_reason_format():
    reason = ViolationReason.model_validate(_ok_reason_dict())
    rr = derive_review_reason(reason)
    assert "营业收入 不符合" in rr
    assert "abcdef01" in rr  # short clause id
    assert "「" in rr and "」" in rr
    assert "置信度 1.00" in rr
    # Deterministic: same input → same output
    assert derive_review_reason(reason) == rr


def test_derive_review_reason_handles_dict():
    rr = derive_review_reason(_ok_reason_dict())
    assert "营业收入 不符合" in rr
    assert "置信度" in rr


def test_derive_review_reason_invalid_input():
    assert derive_review_reason("nonsense") == ""
    assert derive_review_reason(None) == ""


# ---------------------------------------------------------------------------
# 4. build_violation_reason
# ---------------------------------------------------------------------------


def _rule(threshold=None, **overrides):
    base = {
        "rule_id": "CL-abcdef0123456789",
        "clause_id": "CL-abcdef0123456789",
        "policy_id": "POL-abcdef0123456789",
        "version_id": "VER-abcdef0123456789",
        "article": "第一条",
        "category": "客户准入",
        "condition": "对公客户年营业收入应不低于 2000 万元。",
        "policy_excerpt": "对公客户年营业收入应不低于 2000 万元。",
        "threshold": threshold or {"min_amount_wan": 2000.0},
        "severity_hint": "major",
    }
    base.update(overrides)
    return base


def _event(fields=None, **overrides):
    base = {
        "event_id": "EVT-001",
        "event_type": "loan_review",
        "fields": fields or {"raw": "客户 A 年营业收入 1500 万元", "amount_wan": 1500},
    }
    base.update(overrides)
    return base


def test_build_violation_reason_hard_rule_confidence_1():
    cell = {
        "status": "violate",
        "evidence": "amount_wan=1500 低于阈值 min_amount_wan=2000",
        "match_reason": "amount_wan 低于下限",
    }
    reason = build_violation_reason(rule=_rule(), event=_event(), cell=cell)
    assert reason is not None
    assert reason.confidence == 1.0
    assert reason.policy_id.startswith("POL-")
    assert reason.review_reason


def test_build_violation_reason_llm_violate_confidence_07():
    cell = {
        "status": "violate",
        "evidence": "LLM judged this fails the rule",
        "match_reason": "客户营收远低于门槛",
    }
    reason = build_violation_reason(rule=_rule(), event=_event(), cell=cell)
    assert reason is not None
    assert reason.confidence == 0.7


def test_build_violation_reason_default_confidence_05():
    """No cell → 0.5 default."""
    reason = build_violation_reason(rule=_rule(), event=_event(), cell=None)
    assert reason is not None
    assert reason.confidence == 0.5


def test_build_violation_reason_override_wins():
    cell = {"status": "violate", "evidence": "超阈值"}
    reason = build_violation_reason(
        rule=_rule(), event=_event(), cell=cell,
        confidence_override=0.42,
    )
    assert reason.confidence == 0.42


def test_build_violation_reason_returns_none_without_id_triplet():
    bad_rule = _rule(rule_id="POL-001", clause_id="POL-001")  # no CL- prefix
    bad_rule.pop("clause_id", None)
    bad_rule["clause_id"] = "RULE-bad"
    reason = build_violation_reason(rule=bad_rule, event=_event(), cell=None)
    assert reason is None


def test_build_violation_reason_returns_none_when_excerpts_empty():
    rule = _rule()
    rule["condition"] = ""
    rule["policy_excerpt"] = ""
    reason = build_violation_reason(rule=rule, event=_event(), cell=None)
    assert reason is None


def test_build_violation_reason_excerpt_from_event_fallback():
    """Event with key=value fields produces a friendly excerpt."""
    event = _event(fields={"customer_id": "X", "amount_wan": 1500})
    reason = build_violation_reason(rule=_rule(), event=event, cell=None)
    assert reason is not None
    assert "customer_id" in reason.business_excerpt
    assert "amount_wan" in reason.business_excerpt


def test_build_violation_reason_clamps_override():
    cell = {"status": "violate"}
    r1 = build_violation_reason(rule=_rule(), event=_event(),
                                cell=cell, confidence_override=10.0)
    r2 = build_violation_reason(rule=_rule(), event=_event(),
                                cell=cell, confidence_override=-5.0)
    assert r1.confidence == 1.0
    assert r2.confidence == 0.0
