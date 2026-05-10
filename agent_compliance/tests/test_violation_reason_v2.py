# -*- coding: utf-8 -*-
"""ViolationReason v2 schema · ALL IN Phase B step 4 (2026-05-09).

新增 8th 必填字段 clause_text_hash (红线 #8) + freshness 三字段
(evidence_date / freshness_days / staleness_passed).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from agent_compliance.violation_schema import (
    CLAUSE_HASH_PREFIX_HEX,
    POLICY_FRESHNESS_SLA_DAYS,
    ViolationReason,
    build_violation_reason,
    compute_clause_text_hash,
    compute_freshness,
)


# ---------------------------------------------------------------------------
# clause_text_hash 计算 (红线 #8)
# ---------------------------------------------------------------------------


def test_compute_clause_text_hash_returns_16_hex():
    h = compute_clause_text_hash("第六条 个人消费贷款期限不得超过 12 个月。")
    assert len(h) == CLAUSE_HASH_PREFIX_HEX == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_clause_text_hash_deterministic():
    text = "第三条 联合贷款本行出资比例不得低于 30%。"
    assert compute_clause_text_hash(text) == compute_clause_text_hash(text)


def test_compute_clause_text_hash_changes_when_text_changes():
    a = compute_clause_text_hash("第六条 期限不得超过 12 个月。")
    b = compute_clause_text_hash("第六条 期限不得超过 24 个月。")
    assert a != b


def test_compute_clause_text_hash_empty_returns_empty():
    assert compute_clause_text_hash("") == ""
    assert compute_clause_text_hash("   ") == ""


def test_violation_reason_rejects_empty_hash():
    with pytest.raises(Exception):
        ViolationReason(
            policy_id="POL-001",
            policy_version="VER-001",
            clause_id="CL-001",
            conflict_field="期限",
            business_excerpt="loan months=18",
            policy_excerpt="期限不得超过 12 个月",
            confidence=1.0,
            clause_text_hash="",  # 空 · 应拒
        )


def test_violation_reason_rejects_invalid_hash_format():
    with pytest.raises(Exception):
        ViolationReason(
            policy_id="POL-001",
            policy_version="VER-001",
            clause_id="CL-001",
            conflict_field="期限",
            business_excerpt="loan months=18",
            policy_excerpt="期限不得超过 12 个月",
            confidence=1.0,
            clause_text_hash="ZZZ-not-hex",  # 非 hex · 应拒
        )


def test_violation_reason_rejects_wrong_length_hash():
    with pytest.raises(Exception):
        ViolationReason(
            policy_id="POL-001",
            policy_version="VER-001",
            clause_id="CL-001",
            conflict_field="期限",
            business_excerpt="loan months=18",
            policy_excerpt="期限不得超过 12 个月",
            confidence=1.0,
            clause_text_hash="abc123",  # 6 hex · 应拒 (要 16)
        )


# ---------------------------------------------------------------------------
# freshness 计算
# ---------------------------------------------------------------------------


def test_compute_freshness_within_sla():
    today = date.today().isoformat()
    ev = (date.today() - timedelta(days=30)).isoformat()
    days, passed = compute_freshness(ev, today)
    assert days == 30
    assert passed is True


def test_compute_freshness_exceeds_sla():
    today = date.today().isoformat()
    ev = (date.today() - timedelta(days=400)).isoformat()
    days, passed = compute_freshness(ev, today)
    assert days == 400
    assert passed is False


def test_compute_freshness_at_sla_boundary():
    today = date.today().isoformat()
    ev = (date.today() - timedelta(days=POLICY_FRESHNESS_SLA_DAYS)).isoformat()
    days, passed = compute_freshness(ev, today)
    assert days == POLICY_FRESHNESS_SLA_DAYS
    assert passed is True  # 恰 365d 视作通过 (含 boundary)


def test_compute_freshness_no_evidence_date_passes():
    """无 evidence_date 时容错通过 · -1 表示不可计算."""
    today = date.today().isoformat()
    days, passed = compute_freshness("", today)
    assert days == -1
    assert passed is True


def test_compute_freshness_invalid_date_format_passes():
    """parse 失败容错通过 (不抛异常)."""
    days, passed = compute_freshness("not-a-date", date.today().isoformat())
    assert days == -1
    assert passed is True


# ---------------------------------------------------------------------------
# build_violation_reason · 端到端 8 字段 + freshness 真填
# ---------------------------------------------------------------------------


def _registry_rule(policy_excerpt: str = "期限不得超过 12 个月") -> dict:
    return {
        "rule_id": "POL-001",
        "policy_id": "POL-CBIRC-2026-018",
        "version_id": "VER-2026-04-08",
        "clause_id": "CL-006-期限",
        "article": "第六条",
        "category": "期限",
        "condition": policy_excerpt,
        "policy_excerpt": policy_excerpt,
        "threshold": {"max_months": 12},
        "severity_hint": "critical",
    }


def _violate_event() -> dict:
    return {
        "event_id": "LN20251108",
        "event_type": "loan",
        "fields": {"months": 18, "amount": 100000, "purpose": "consumer"},
    }


def _hard_rule_cell() -> dict:
    return {
        "status": "violate",
        "evidence": "months=18 超阈值 max_months=12",
        "match_reason": "事件 LN20251108 months=18 > 上限 12",
    }


def test_build_violation_reason_fills_all_8_fields():
    reason = build_violation_reason(
        rule=_registry_rule(),
        event=_violate_event(),
        cell=_hard_rule_cell(),
        policy_meta={"effective_date": "2026-04-08", "title": "消费金融管理办法"},
    )
    assert reason is not None
    d = reason.to_dict()
    # 7 原字段
    assert d["policy_id"].startswith("POL-")
    assert d["policy_version"].startswith("VER-")
    assert d["clause_id"].startswith("CL-")
    assert d["conflict_field"]
    assert d["business_excerpt"]
    assert d["policy_excerpt"]
    assert 0 <= d["confidence"] <= 1
    # 8th + freshness
    assert len(d["clause_text_hash"]) == 16
    assert d["evidence_date"] == "2026-04-08"
    assert d["retrieved_at"]  # default today
    assert isinstance(d["freshness_days"], int)
    assert isinstance(d["staleness_passed"], bool)


def test_build_violation_reason_hard_rule_confidence_is_one():
    reason = build_violation_reason(
        rule=_registry_rule(),
        event=_violate_event(),
        cell=_hard_rule_cell(),
        policy_meta={"effective_date": "2026-04-08"},
    )
    assert reason is not None
    assert reason.confidence == 1.0


def test_build_violation_reason_freshness_within_sla():
    """policy_meta.effective_date 在 365d 内 · staleness_passed=True."""
    recent = (date.today() - timedelta(days=30)).isoformat()
    reason = build_violation_reason(
        rule=_registry_rule(),
        event=_violate_event(),
        cell=_hard_rule_cell(),
        policy_meta={"effective_date": recent},
    )
    assert reason is not None
    assert reason.staleness_passed is True
    assert reason.freshness_days == 30


def test_build_violation_reason_freshness_exceeds_sla():
    """policy_meta.effective_date 超 365d · staleness_passed=False (政策过期 · UI 应警示)."""
    stale = (date.today() - timedelta(days=400)).isoformat()
    reason = build_violation_reason(
        rule=_registry_rule(),
        event=_violate_event(),
        cell=_hard_rule_cell(),
        policy_meta={"effective_date": stale},
    )
    assert reason is not None
    assert reason.staleness_passed is False
    assert reason.freshness_days == 400


def test_build_violation_reason_no_policy_excerpt_returns_none():
    """红线 #8: 政策原文真为空 · 拒绝构造 (clause_text_hash 不能造)."""
    rule = _registry_rule(policy_excerpt="")
    rule["condition"] = ""  # 也清掉 fallback
    reason = build_violation_reason(
        rule=rule,
        event=_violate_event(),
        cell=_hard_rule_cell(),
        policy_meta={"effective_date": "2026-04-08"},
    )
    assert reason is None


def test_build_violation_reason_falls_back_to_condition_when_no_excerpt():
    """rule.policy_excerpt 缺 但 condition 有 · 用 condition 算 hash."""
    rule = _registry_rule()
    del rule["policy_excerpt"]  # 仅留 condition
    reason = build_violation_reason(
        rule=rule,
        event=_violate_event(),
        cell=_hard_rule_cell(),
        policy_meta={"effective_date": "2026-04-08"},
    )
    assert reason is not None
    # hash 来自 condition · 与 _registry_rule 默认 excerpt 一致 (因为 default 文本相同)
    expected = compute_clause_text_hash("期限不得超过 12 个月")
    assert reason.clause_text_hash == expected


def test_build_violation_reason_no_policy_meta_uses_today():
    """无 policy_meta · evidence_date='' · freshness_days=-1 · staleness_passed=True 容错."""
    reason = build_violation_reason(
        rule=_registry_rule(),
        event=_violate_event(),
        cell=_hard_rule_cell(),
    )
    assert reason is not None
    assert reason.evidence_date == ""
    assert reason.freshness_days == -1
    assert reason.staleness_passed is True


def test_violation_reason_to_dict_has_all_new_fields():
    """to_dict() 序列化全新字段 · SSE 真到 frontend 必经路径."""
    reason = build_violation_reason(
        rule=_registry_rule(),
        event=_violate_event(),
        cell=_hard_rule_cell(),
        policy_meta={"effective_date": "2026-04-08"},
    )
    d = reason.to_dict()
    expected_keys = {
        "policy_id", "policy_version", "clause_id",
        "conflict_field", "business_excerpt", "policy_excerpt",
        "confidence", "clause_text_hash", "review_reason",
        "evidence_date", "retrieved_at", "freshness_days", "staleness_passed",
    }
    assert expected_keys.issubset(d.keys())
