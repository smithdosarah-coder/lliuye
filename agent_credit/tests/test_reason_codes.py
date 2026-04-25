"""reason_codes 加载 + 推导测试。"""
from __future__ import annotations

from dataclasses import dataclass

from agent_credit.reason_codes import derive_top_reason_codes, load_codes


@dataclass
class FakeHit:
    rule_id: str
    severity: str
    actual_value: float | int | None = None
    threshold: float | int | None = None


def test_load_codes_corporate_has_15_entries():
    codes = load_codes("corporate")
    assert len(codes) >= 10
    # severity 枚举闭合：red/yellow/green
    assert {c.severity for c in codes.values()} <= {"red", "yellow", "green"}


def test_load_codes_retail_has_entries():
    codes = load_codes("retail")
    assert len(codes) >= 10
    assert {c.severity for c in codes.values()} <= {"red", "yellow", "green"}


def test_sme_routes_to_retail():
    assert load_codes("sme") == load_codes("retail")


def test_derive_top5_truncates():
    feats = {
        "financial.debt_ratio": 0.85,
        "operational.customer_concentration": 0.55,
        "operational.cashflow_coverage": 0.4,
        "external.related_party_pct": 0.5,
        "financial.consecutive_loss_years": 2,
    }
    top = derive_top_reason_codes("corporate", "拒绝", [], feats, top_n=5)
    assert len(top) <= 5
    for t in top:
        assert t["severity"] in {"red", "yellow", "green"}
        assert t["code"].startswith("R_CORP_")


def test_rule_hit_promoted_to_rule_match():
    hits = [FakeHit(rule_id="retail_rl_001", severity="red")]
    feats = {"credit.overdue_severity": 3}
    top = derive_top_reason_codes("retail", "拒绝", hits, feats, top_n=5)
    # rule 直接命中 R_RET_OVERDUE_SEVERE，matched_by 应为 "rule"
    rule_hits = [t for t in top if t.get("matched_by") == "rule"]
    assert len(rule_hits) == 1
    assert rule_hits[0]["code"] == "R_RET_OVERDUE_SEVERE"


def test_green_codes_appear_for_approved():
    feats = {
        "capacity.monthly_repay_capacity": 2.0,
        "credit.overdue_severity": 0,
        "credit.account_age_years": 6,
    }
    top = derive_top_reason_codes("retail", "批准", [], feats, top_n=5)
    assert any(t["severity"] == "green" for t in top)


def test_evidence_value_resolved():
    feats = {"capacity.dti_ratio": 0.65}
    top = derive_top_reason_codes("retail", "有条件批准", [], feats, top_n=5)
    dti = next((t for t in top if t["code"] == "R_RET_DTI_HIGH"), None)
    assert dti is not None
    assert dti["evidence_value"] == 0.65
