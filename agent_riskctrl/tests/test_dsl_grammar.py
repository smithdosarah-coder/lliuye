# -*- coding: utf-8 -*-
"""Q-054 C1 · DSL grammar 单测 · 覆盖 OR / 嵌套 / time_window / NOT 四类。

Grammar 优先级表 v1 (rule_engine.py module docstring 顶部冻结):
    1. ()   显式分组 (LLM 直出嵌套 group)
    2. NOT  unary prefix (right-assoc)  必须正好 1 child
    3. AND  binary left-assoc           隐式默认
    4. OR   binary left-assoc

歧义 case (LLM 出 dict 严格遵守 · 本测试集 fixture 直接验):
    - A AND B OR C  = (A AND B) OR C   (AND > OR)
    - A OR B AND C  = A OR (B AND C)
    - NOT A AND B   = (NOT A) AND B    (NOT > AND)
    - NOT (A OR B)  = NOT (A OR B)     (括号显式)

per §3.1 确定性: LLM 出树 dict · Python 求值 (本文件验)
per Q-054 风险 #3: OR/NOT 歧义 → grammar 优先级表先冻 + parser fixture 各覆盖 ≥ 2 case
"""
from __future__ import annotations

import pytest

from agent_riskctrl.rule_engine import (
    RuleCondition,
    RuleExpression,
    RuleSet,
    StrategyRule,
    _describe_expression,
    apply_expression,
    apply_rule,
    apply_ruleset,
    parse_expression_dict,
    parse_natural_language_rules,
)


# ===========================================================================
# Helper builders (fixture readability)
# ===========================================================================


def cond(field: str, op: str, value, time_window: str | None = None) -> RuleExpression:
    return RuleExpression(
        type="condition", field=field, operator=op, value=value, time_window=time_window
    )


def grp(op: str, *children: RuleExpression) -> RuleExpression:
    return RuleExpression(type="group", op=op, children=list(children))


# ===========================================================================
# Class 1 · OR · ≥ 2 fixture (per Q-054 C1)
# ===========================================================================


class TestOR:
    def test_or_two_branches_left_hit(self):
        """OR · 左分支命中 → True."""
        expr = grp(
            "OR",
            cond("debt_ratio", ">", 0.7),
            cond("days_past_due", ">=", 30),
        )
        assert apply_expression(expr, {"debt_ratio": 0.85, "days_past_due": 0}) is True

    def test_or_two_branches_right_hit(self):
        """OR · 右分支命中 → True (左分支 False 不阻断)."""
        expr = grp(
            "OR",
            cond("debt_ratio", ">", 0.7),
            cond("days_past_due", ">=", 30),
        )
        assert apply_expression(expr, {"debt_ratio": 0.3, "days_past_due": 45}) is True

    def test_or_two_branches_all_miss(self):
        """OR · 全 miss → False."""
        expr = grp(
            "OR",
            cond("debt_ratio", ">", 0.7),
            cond("days_past_due", ">=", 30),
        )
        assert apply_expression(expr, {"debt_ratio": 0.3, "days_past_due": 0}) is False

    def test_or_three_children(self):
        """OR · 三 child · 任一命中即 True (短路)."""
        expr = grp(
            "OR",
            cond("industry_l1", "==", "房地产"),
            cond("industry_l1", "==", "教培"),
            cond("industry_l1", "==", "互金"),
        )
        record = {"industry_l1": "互金"}
        assert apply_expression(expr, record) is True

    def test_or_empty_children_returns_false(self):
        """OR · 空 children 视为 False (per spec)."""
        expr = grp("OR")
        assert apply_expression(expr, {"debt_ratio": 0.9}) is False


# ===========================================================================
# Class 2 · 嵌套 · ≥ 2 fixture (per Q-054 C1)
# ===========================================================================


class TestNested:
    def test_nested_and_inside_or(self):
        """(A AND B) OR C · 验 AND 优先级 > OR 通过显式嵌套表达.

        Case 1: A=True, B=True, C=False → AND 命中 → OR True
        """
        expr = grp(
            "OR",
            grp(
                "AND",
                cond("debt_ratio", ">", 0.5),
                cond("query_count_3m", ">", 5),
            ),
            cond("days_past_due", ">=", 30),
        )
        record = {"debt_ratio": 0.7, "query_count_3m": 8, "days_past_due": 0}
        assert apply_expression(expr, record) is True

    def test_nested_and_inside_or_only_outer_hits(self):
        """(A AND B) OR C · A 命中 B 不命中 → AND False · C 命中 → OR True."""
        expr = grp(
            "OR",
            grp(
                "AND",
                cond("debt_ratio", ">", 0.5),
                cond("query_count_3m", ">", 5),
            ),
            cond("days_past_due", ">=", 30),
        )
        record = {"debt_ratio": 0.7, "query_count_3m": 2, "days_past_due": 45}
        assert apply_expression(expr, record) is True

    def test_nested_or_inside_and(self):
        """(A OR B) AND (C OR D) · 双 OR 子树 · 都命中至少一支 → True."""
        expr = grp(
            "AND",
            grp("OR", cond("industry_l1", "==", "房地产"), cond("industry_l1", "==", "教培")),
            grp("OR", cond("debt_ratio", ">", 0.7), cond("days_past_due", ">=", 30)),
        )
        record = {"industry_l1": "教培", "debt_ratio": 0.4, "days_past_due": 60}
        assert apply_expression(expr, record) is True

    def test_nested_or_inside_and_one_branch_miss(self):
        """(A OR B) AND (C OR D) · 第二支全 miss → AND False."""
        expr = grp(
            "AND",
            grp("OR", cond("industry_l1", "==", "房地产"), cond("industry_l1", "==", "教培")),
            grp("OR", cond("debt_ratio", ">", 0.7), cond("days_past_due", ">=", 30)),
        )
        record = {"industry_l1": "教培", "debt_ratio": 0.3, "days_past_due": 5}
        assert apply_expression(expr, record) is False

    def test_three_level_nested(self):
        """三层嵌套 NOT(AND(OR(A, B), C)) · 内层 OR 命中 + AND 命中 + 外 NOT 翻转 → False."""
        inner_or = grp("OR", cond("industry_l1", "==", "房地产"), cond("industry_l1", "==", "互金"))
        and_node = grp("AND", inner_or, cond("debt_ratio", ">", 0.5))
        expr = grp("NOT", and_node)
        record = {"industry_l1": "互金", "debt_ratio": 0.8}
        # inner_or True · debt > 0.5 True → AND True → NOT False
        assert apply_expression(expr, record) is False


# ===========================================================================
# Class 3 · time_window · ≥ 2 fixture (per Q-054 C1 · 反 §3.1 LLM 现场算窗口)
# ===========================================================================


class TestTimeWindow:
    def test_time_window_last_30d_hit(self):
        """last_30d · field 重写为 query_count_last_30d · 命中."""
        expr = cond("query_count", ">", 5, time_window="last_30d")
        record = {"query_count_last_30d": 10, "query_count": 1}
        assert apply_expression(expr, record) is True

    def test_time_window_last_30d_miss(self):
        """last_30d · 阈值未达 → False (即使无窗口的 query_count 命中也不算)."""
        expr = cond("query_count", ">", 5, time_window="last_30d")
        record = {"query_count_last_30d": 3, "query_count": 100}
        assert apply_expression(expr, record) is False

    def test_time_window_last_90d_ge_op(self):
        """last_90d · >= 操作符 · 命中."""
        expr = cond("complaint_count", ">=", 3, time_window="last_90d")
        record = {"complaint_count_last_90d": 3}
        assert apply_expression(expr, record) is True

    def test_time_window_invalid_pattern_silent_reject(self):
        """非法 pattern (e.g. '30 days' / 'last_30days' / '30d') → 静默拒 False."""
        # 不让 LLM 现场算窗口 · parser 严格 ^last_\d+d$ pattern
        record = {"query_count_30 days": 10, "query_count_last_30days": 10, "query_count_30d": 10}
        for bad in ("30 days", "last_30days", "30d", "last30d", "LAST_30D"):
            expr = cond("query_count", ">", 5, time_window=bad)
            assert apply_expression(expr, record) is False, f"bad pattern {bad!r} 应静默拒"

    def test_time_window_field_not_in_record(self):
        """合法 pattern · 但 record 无对应预聚合列 → False (字段不存在)."""
        expr = cond("query_count", ">", 5, time_window="last_30d")
        record = {"query_count": 100}  # 无 query_count_last_30d
        assert apply_expression(expr, record) is False


# ===========================================================================
# Class 4 · NOT · ≥ 2 fixture (per Q-054 C1)
# ===========================================================================


class TestNOT:
    def test_not_condition_inverts_true_to_false(self):
        """NOT (industry == '房地产') · record industry='房地产' → 内 True → NOT False."""
        expr = grp("NOT", cond("industry_l1", "==", "房地产"))
        assert apply_expression(expr, {"industry_l1": "房地产"}) is False

    def test_not_condition_inverts_false_to_true(self):
        """NOT (industry == '房地产') · record industry='制造' → 内 False → NOT True."""
        expr = grp("NOT", cond("industry_l1", "==", "房地产"))
        assert apply_expression(expr, {"industry_l1": "制造"}) is True

    def test_not_and_combo_priority(self):
        """NOT A AND B = (NOT A) AND B · 验 NOT > AND 优先级.

        record A=true B=true: (NOT True) AND True = False AND True = False
        """
        expr = grp(
            "AND",
            grp("NOT", cond("blacklisted", "==", "yes")),
            cond("debt_ratio", "<", 0.5),
        )
        # blacklisted=yes (NOT True → False) AND debt 0.3<0.5 True → False
        record_a = {"blacklisted": "yes", "debt_ratio": 0.3}
        assert apply_expression(expr, record_a) is False

        # blacklisted=no (NOT False → True) AND debt 0.3<0.5 True → True
        record_b = {"blacklisted": "no", "debt_ratio": 0.3}
        assert apply_expression(expr, record_b) is True

    def test_not_group_or_de_morgan(self):
        """NOT (A OR B) · 仅当 A 和 B 都 False 时 NOT True (De Morgan)."""
        expr = grp(
            "NOT",
            grp("OR", cond("days_past_due", ">=", 30), cond("debt_ratio", ">", 0.7)),
        )
        # 两个内 condition 都 False → OR False → NOT True
        assert apply_expression(expr, {"days_past_due": 0, "debt_ratio": 0.3}) is True
        # 任一 True → OR True → NOT False
        assert apply_expression(expr, {"days_past_due": 60, "debt_ratio": 0.3}) is False

    def test_not_with_zero_or_multiple_children_returns_false(self):
        """NOT 必须正好 1 child · 0 / 2+ → False (语义违反)."""
        # 0 child
        expr_zero = RuleExpression(type="group", op="NOT", children=[])
        assert apply_expression(expr_zero, {"x": 1}) is False
        # 2 children
        expr_two = RuleExpression(
            type="group",
            op="NOT",
            children=[
                cond("x", ">", 0),
                cond("y", ">", 0),
            ],
        )
        assert apply_expression(expr_two, {"x": 1, "y": 1}) is False


# ===========================================================================
# parse_expression_dict (LLM dict → RuleExpression)
# ===========================================================================


class TestParseExpressionDict:
    def test_parse_condition_leaf(self):
        d = {"type": "condition", "field": "debt_ratio", "operator": ">", "value": 0.7}
        expr = parse_expression_dict(d)
        assert expr is not None
        assert expr.type == "condition"
        assert expr.field == "debt_ratio"
        assert expr.operator == ">"
        assert expr.value == 0.7
        assert expr.time_window is None

    def test_parse_condition_with_time_window(self):
        d = {
            "type": "condition",
            "field": "query_count",
            "operator": ">",
            "value": 5,
            "time_window": "last_30d",
        }
        expr = parse_expression_dict(d)
        assert expr is not None
        assert expr.time_window == "last_30d"

    def test_parse_group_or(self):
        d = {
            "type": "group",
            "op": "or",  # lowercase · parser uppercase 化
            "children": [
                {"type": "condition", "field": "x", "operator": ">", "value": 1},
                {"type": "condition", "field": "y", "operator": "<", "value": 0},
            ],
        }
        expr = parse_expression_dict(d)
        assert expr is not None
        assert expr.type == "group"
        assert expr.op == "OR"
        assert len(expr.children) == 2

    def test_parse_nested_group(self):
        d = {
            "type": "group",
            "op": "AND",
            "children": [
                {
                    "type": "group",
                    "op": "OR",
                    "children": [
                        {"type": "condition", "field": "a", "operator": ">", "value": 1},
                        {"type": "condition", "field": "b", "operator": "<", "value": 0},
                    ],
                },
                {"type": "condition", "field": "c", "operator": "==", "value": "x"},
            ],
        }
        expr = parse_expression_dict(d)
        assert expr is not None
        assert expr.type == "group"
        assert expr.op == "AND"
        assert len(expr.children) == 2
        assert expr.children[0].op == "OR"

    def test_parse_invalid_input_returns_none(self):
        assert parse_expression_dict(None) is None
        assert parse_expression_dict("not_a_dict") is None
        assert parse_expression_dict({"type": "unknown"}) is None
        assert parse_expression_dict({}) is None

    def test_parse_group_with_bad_child_drops_silently(self):
        """bad child 解析失败 → 丢弃 · 不阻断整树."""
        d = {
            "type": "group",
            "op": "OR",
            "children": [
                {"type": "condition", "field": "x", "operator": ">", "value": 1},
                "not_a_dict",  # bad
                {"type": "condition", "field": "y", "operator": "<", "value": 0},
            ],
        }
        expr = parse_expression_dict(d)
        assert expr is not None
        assert len(expr.children) == 2  # bad child 被丢


# ===========================================================================
# parse_natural_language_rules · LLM dict 含 expression 字段
# ===========================================================================


class TestParseLLMRulesWithExpression:
    def test_llm_rule_with_expression_field(self):
        """LLM rule item 含 expression → StrategyRule.expression 非空."""
        llm = {
            "rules": [
                {
                    "rule_id": "R001",
                    "name": "复合规则",
                    "expression": {
                        "type": "group",
                        "op": "OR",
                        "children": [
                            {"type": "condition", "field": "debt_ratio", "operator": ">", "value": 0.7},
                            {"type": "condition", "field": "days_past_due", "operator": ">=", "value": 30},
                        ],
                    },
                    "action": "reject",
                    "priority": 1,
                }
            ]
        }
        rs = parse_natural_language_rules(llm)
        assert len(rs.rules) == 1
        rule = rs.rules[0]
        assert rule.expression is not None
        assert rule.expression.op == "OR"
        assert len(rule.expression.children) == 2

    def test_llm_rule_legacy_conditions_only(self):
        """Backward compat: rule item 仅 conditions · expression=None · 走 legacy AND."""
        llm = {
            "rules": [
                {
                    "rule_id": "R001",
                    "name": "legacy",
                    "conditions": [{"field": "debt_ratio", "operator": ">", "value": 0.5}],
                    "action": "reject",
                }
            ]
        }
        rs = parse_natural_language_rules(llm)
        assert rs.rules[0].expression is None
        assert len(rs.rules[0].conditions) == 1


# ===========================================================================
# apply_rule dispatch · expression 优先 over conditions
# ===========================================================================


class TestApplyRuleDispatch:
    def test_expression_takes_precedence_over_conditions(self):
        """rule 同时给 expression 和 conditions · expression 优先."""
        rule = StrategyRule(
            rule_id="R001",
            name="t",
            # legacy AND-only · 单独跑会要求 industry='房地产' 才命中
            conditions=[RuleCondition(field="industry_l1", operator="==", value="房地产")],
            # expression: 任意 industry > 50% debt 即命中
            expression=cond("debt_ratio", ">", 0.5),
            action="reject",
        )
        record = {"industry_l1": "制造", "debt_ratio": 0.8}
        # 走 expression: debt 0.8 > 0.5 → True
        # 若走 conditions: industry != 房地产 → False
        assert apply_rule(rule, record) is True

    def test_legacy_conditions_when_no_expression(self):
        """expression=None · fallback conditions AND-only."""
        rule = StrategyRule(
            rule_id="R001",
            name="legacy",
            conditions=[
                RuleCondition(field="debt_ratio", operator=">", value=0.5),
                RuleCondition(field="days_past_due", operator=">=", value=30),
            ],
            action="reject",
        )
        # 都命中
        assert apply_rule(rule, {"debt_ratio": 0.8, "days_past_due": 60}) is True
        # 第二条 miss → AND False
        assert apply_rule(rule, {"debt_ratio": 0.8, "days_past_due": 0}) is False


# ===========================================================================
# apply_ruleset · hit_conditions 描述 (expression vs legacy)
# ===========================================================================


class TestApplyRulesetDescribe:
    def test_hit_conditions_for_expression_rule(self):
        """expression 命中 · hit_conditions 用 _describe_expression."""
        rule = StrategyRule(
            rule_id="R001",
            name="复合",
            expression=grp(
                "OR",
                cond("debt_ratio", ">", 0.7),
                cond("days_past_due", ">=", 30),
            ),
            action="reject",
            priority=1,
        )
        rs = RuleSet(rules=[rule])
        results = apply_ruleset(rs, [{"debt_ratio": 0.8, "days_past_due": 0}])
        assert results[0]["hit_rule_id"] == "R001"
        assert results[0]["action"] == "reject"
        # hit_conditions 应是 1 个 string · 描述了 OR 树
        hit = results[0]["hit_conditions"]
        assert len(hit) == 1
        assert "OR" in hit[0]
        assert "debt_ratio" in hit[0]

    def test_hit_conditions_for_legacy_rule(self):
        """legacy conditions 命中 · hit_conditions 维持原 list[str] 描述."""
        rule = StrategyRule(
            rule_id="R002",
            name="legacy",
            conditions=[RuleCondition(field="debt_ratio", operator=">", value=0.5)],
            action="reject",
            priority=1,
        )
        rs = RuleSet(rules=[rule])
        results = apply_ruleset(rs, [{"debt_ratio": 0.8}])
        assert results[0]["hit_rule_id"] == "R002"
        # legacy 描述: "field operator value" list
        assert results[0]["hit_conditions"] == ["debt_ratio > 0.5"]


# ===========================================================================
# _describe_expression · 命中说明可读性
# ===========================================================================


class TestDescribeExpression:
    def test_describe_condition_with_time_window(self):
        e = cond("query_count", ">", 5, time_window="last_30d")
        s = _describe_expression(e)
        assert "query_count[last_30d]" in s
        assert ">" in s

    def test_describe_not_group(self):
        e = grp("NOT", cond("industry_l1", "==", "房地产"))
        s = _describe_expression(e)
        assert s.startswith("NOT (")

    def test_describe_or_group(self):
        e = grp("OR", cond("a", ">", 1), cond("b", "<", 2))
        s = _describe_expression(e)
        assert " OR " in s
