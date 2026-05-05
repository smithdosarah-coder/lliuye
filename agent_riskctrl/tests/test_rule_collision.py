# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_rule_collision.py — BE6.3 互斥/遮蔽 unit tests."""
from __future__ import annotations

import pytest

from agent_riskctrl.rule_collision import (
    analyze_collisions,
    detect_action_contradictions,
    detect_dead_rules,
    detect_priority_shadows,
)
from agent_riskctrl.rule_engine import RuleCondition, RuleSet, StrategyRule


def _mk_rule(rid: str, prio: int, action: str, field: str, op: str, val) -> StrategyRule:
    return StrategyRule(
        rule_id=rid, name=f"rule {rid}", priority=prio, action=action,
        conditions=[RuleCondition(field=field, operator=op, value=val)],
    )


# ===========================================================================
# Shadow detection
# ===========================================================================


class TestShadow:
    def test_gt_shadow(self):
        # high: debt>0.5 (prio=1), low: debt>0.7 (prio=5) → low shadowed
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.5),
            _mk_rule("R005", 5, "reject", "debt_ratio", ">", 0.7),
        ])
        shadows = detect_priority_shadows(rs)
        assert len(shadows) == 1
        assert shadows[0].shadowed_rule_id == "R005"
        assert shadows[0].shadowing_rule_id == "R001"

    def test_lt_shadow(self):
        # high: age<25 (prio=1), low: age<20 (prio=5) → low shadowed
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "applicant_age", "<", 25),
            _mk_rule("R005", 5, "reject", "applicant_age", "<", 20),
        ])
        shadows = detect_priority_shadows(rs)
        assert len(shadows) == 1
        assert shadows[0].shadowed_rule_id == "R005"

    def test_eq_shadow(self):
        # 同值同 op · 高优先级吃掉低优先级
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "industry_l1", "==", "房地产业"),
            _mk_rule("R005", 5, "approve", "industry_l1", "==", "房地产业"),
        ])
        shadows = detect_priority_shadows(rs)
        assert len(shadows) == 1
        assert shadows[0].shadowed_rule_id == "R005"

    def test_no_shadow_when_disjoint(self):
        # debt>0.8 (prio=1) 不 shadow debt>0.5 (prio=5)
        # 因为高 rule 命中区间窄 (>0.8) · 不包住低 rule (>0.5)
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.8),
            _mk_rule("R005", 5, "reject", "debt_ratio", ">", 0.5),
        ])
        shadows = detect_priority_shadows(rs)
        assert len(shadows) == 0

    def test_alias_shadow(self):
        # 用别名"负债率" + 规范名"debt_ratio" 也应 detect
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "负债率", ">", 0.5),
            _mk_rule("R005", 5, "reject", "debt_ratio", ">", 0.7),
        ])
        shadows = detect_priority_shadows(rs)
        assert len(shadows) == 1

    def test_no_shadow_different_field(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.5),
            _mk_rule("R005", 5, "reject", "rate_pct", ">", 0.7),
        ])
        assert detect_priority_shadows(rs) == []

    def test_no_shadow_different_op(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.5),
            _mk_rule("R005", 5, "reject", "debt_ratio", "<", 0.3),
        ])
        assert detect_priority_shadows(rs) == []

    def test_skip_multi_condition_rules(self):
        # 复合 AND 当前跳过 (conservative)
        rs = RuleSet(rules=[
            StrategyRule(
                rule_id="R001", name="m1", priority=1, action="reject",
                conditions=[
                    RuleCondition(field="debt_ratio", operator=">", value=0.5),
                    RuleCondition(field="rate_pct", operator=">", value=10),
                ],
            ),
            _mk_rule("R005", 5, "reject", "debt_ratio", ">", 0.7),
        ])
        # multi-cond rule 不参与 shadow 分析
        assert detect_priority_shadows(rs) == []


# ===========================================================================
# Contradiction detection
# ===========================================================================


class TestContradiction:
    def test_basic_contradiction(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "industry_l1", "==", "房地产业"),
            _mk_rule("R002", 5, "approve", "industry_l1", "==", "房地产业"),
        ])
        cs = detect_action_contradictions(rs)
        assert len(cs) == 1
        assert cs[0].winner_rule_id == "R001"

    def test_winner_by_priority(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 10, "reject", "scale", "==", "微型"),
            _mk_rule("R002", 1, "approve", "scale", "==", "微型"),
        ])
        cs = detect_action_contradictions(rs)
        assert cs[0].winner_rule_id == "R002"  # prio=1 winner

    def test_no_contradiction_same_action(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "scale", "==", "微型"),
            _mk_rule("R002", 5, "reject", "scale", "==", "小型"),
        ])
        assert detect_action_contradictions(rs) == []

    def test_no_contradiction_different_field(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "scale", "==", "微型"),
            _mk_rule("R002", 5, "approve", "industry_l1", "==", "金融业"),
        ])
        assert detect_action_contradictions(rs) == []

    def test_manual_review_not_contradiction(self):
        # reject vs manual_review 不算冲突 (都是非通过)
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "scale", "==", "微型"),
            _mk_rule("R002", 5, "manual_review", "scale", "==", "微型"),
        ])
        assert detect_action_contradictions(rs) == []


# ===========================================================================
# Dead rule detection
# ===========================================================================


class TestDeadRule:
    def test_dead_rule_detected(self):
        # debt>1000 在所有样本里都不命中
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 1000),
        ])
        records = [{"debt_ratio": 0.5}, {"debt_ratio": 0.8}]
        dead = detect_dead_rules(rs, records)
        assert len(dead) == 1 and dead[0].rule_id == "R001"

    def test_alive_rule_not_reported(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.7),
        ])
        records = [{"debt_ratio": 0.5}, {"debt_ratio": 0.8}]
        dead = detect_dead_rules(rs, records)
        assert dead == []

    def test_empty_records_returns_empty(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.7),
        ])
        assert detect_dead_rules(rs, []) == []


# ===========================================================================
# Integration analyze_collisions
# ===========================================================================


class TestAnalyze:
    def test_full_report_static(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.5),
            _mk_rule("R005", 5, "reject", "debt_ratio", ">", 0.7),  # shadowed
            _mk_rule("R010", 10, "approve", "debt_ratio", ">", 0.7),  # contradicts R001
        ])
        rep = analyze_collisions(rs)
        assert rep.has_issues
        assert rep.total_rules == 3
        assert rep.total_fields_covered == 1
        assert len(rep.shadows) >= 1
        assert len(rep.contradictions) >= 1

    def test_dynamic_dead_rules(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 1000),
        ])
        records = [{"debt_ratio": 0.5}]
        rep = analyze_collisions(rs, records=records)
        assert len(rep.dead_rules) == 1

    def test_clean_ruleset(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.8),
        ])
        rep = analyze_collisions(rs)
        assert not rep.has_issues

    def test_to_dict(self):
        rs = RuleSet(rules=[
            _mk_rule("R001", 1, "reject", "debt_ratio", ">", 0.5),
            _mk_rule("R005", 5, "reject", "debt_ratio", ">", 0.7),
        ])
        rep = analyze_collisions(rs)
        d = rep.to_dict()
        assert "shadows" in d
        assert d["has_issues"] is True
        assert d["total_rules"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
