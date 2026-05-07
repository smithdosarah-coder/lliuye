# -*- coding: utf-8 -*-
"""风控策略规则引擎 — 规则DSL定义、解析、执行

核心模型:
    RuleCondition   — 单个条件 (field operator value · legacy AND-only)
    RuleExpression  — 嵌套表达式 (AND/OR/NOT + condition leaf · 支持 time_window)
    StrategyRule    — 一条策略规则 (legacy conditions list 或 新 expression 树)
    RuleSet         — 规则集合

安全原则: 操作符用固定映射，不使用 eval()

Grammar 优先级表 (本 lane 冻结 · v1 · per Q-054 C1 · 防 OR/NOT 歧义):
    优先级 (低数字 = 高优):
      1. ()    显式分组 · 优先级最高 (用嵌套 group 表达 · LLM dict 出树)
      2. NOT   一元前缀 · right-associative · 必须正好 1 child
      3. AND   二元 · left-associative · 隐式默认 (兼容现有 conditions list)
      4. OR    二元 · left-associative

    歧义 case (LLM 出 dict 时必须严格遵守):
      - A AND B OR C  = (A AND B) OR C   (AND > OR)
      - A OR B AND C  = A OR (B AND C)
      - NOT A AND B   = (NOT A) AND B    (NOT > AND)
      - NOT (A OR B)  = NOT (A OR B)     (括号显式)

    LLM 不消费自然语言 grammar · 直出嵌套 dict (RuleExpression schema) · Python parser 读 dict 求值
    per §3.1 确定性 vs 概率性: LLM 出树 (概率性) · Python 求值 (确定性) · 不让 LLM 现场判定布尔逻辑

Time window 语义:
    condition leaf 上的 modifier · 合法 pattern: ^last_\\d+d$ (e.g. last_30d/last_90d/last_365d)
    求值时 effective_field = f"{field}_{tw}" · 即 record 应有预聚合列 (e.g. query_count_last_30d)
    parser 是确定性 · 不让 LLM 现场算窗口 · 数据预聚合在 caller (per §3.1)
"""

from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ======================================================================
# Pydantic 模型
# ======================================================================

class RuleCondition(BaseModel):
    """单个规则条件"""
    field: str = Field(description="字段名，对应CSV列名")
    operator: str = Field(
        description="操作符: >, <, >=, <=, ==, !=, in, not_in"
    )
    value: Any = Field(description="比较值")


class RuleExpression(BaseModel):
    """嵌套 DSL 表达式 · 支持 AND/OR/NOT 嵌套 + condition leaf + time_window 修饰

    Schema (LLM JSON 出树 · parser 消费):
        condition leaf:
          { "type": "condition", "field": str, "operator": str, "value": Any,
            "time_window": "last_30d" | None }
        group (内部节点):
          { "type": "group", "op": "AND" | "OR" | "NOT", "children": [<expr>, ...] }

    约束:
      - NOT group 必须正好 1 child (违反 → 求值返 False)
      - AND/OR group ≥ 1 child (空 children → 求值返 False)
      - condition leaf 必须有 field + operator (缺一返 False)
      - time_window 必须匹配 ^last_\\d+d$ (非法 → 求值返 False · 静默拒)

    优先级表 / 歧义 case 见 module docstring 顶部。
    """
    type: Literal["condition", "group"] = Field(description="condition leaf 或 group 内部节点")
    # condition leaf 字段
    field: Optional[str] = Field(default=None, description="字段名 (condition leaf only)")
    operator: Optional[str] = Field(
        default=None,
        description="操作符 (condition leaf only): > < >= <= == != in not_in",
    )
    value: Any = Field(default=None, description="比较值 (condition leaf only)")
    time_window: Optional[str] = Field(
        default=None,
        description="时间窗口 modifier (condition leaf only) · 合法 pattern: ^last_\\d+d$",
    )
    # group 内部节点字段
    op: Optional[str] = Field(
        default=None, description="逻辑算子 (group only): AND / OR / NOT"
    )
    children: list["RuleExpression"] = Field(
        default_factory=list, description="子表达式 (group only) · NOT 必须 1 个"
    )


# pydantic v2 forward-ref 解析 (必须 · 因 children: list["RuleExpression"] 自递归)
RuleExpression.model_rebuild()


class StrategyRule(BaseModel):
    """一条风控策略规则

    两种条件表达 (互斥优先级):
      1. expression (新 DSL · 优先) — 嵌套树 · 支持 AND/OR/NOT/time_window
      2. conditions (legacy AND-only) — list AND 关系 · 兼容现有 LLM 出 dict

    apply_rule 优先取 expression · 否则 fallback conditions。
    """
    rule_id: str = Field(description="规则编号，如 R001")
    name: str = Field(description="规则名称")
    description: str = Field(default="", description="规则说明")
    conditions: list[RuleCondition] = Field(
        default_factory=list, description="条件列表(AND关系) · legacy 兼容路径"
    )
    expression: Optional[RuleExpression] = Field(
        default=None,
        description="嵌套表达式树 (新 DSL · 优先于 conditions · 支持 OR/NOT/嵌套/time_window)",
    )
    action: str = Field(
        default="manual_review",
        description="触发动作: approve / reject / manual_review",
    )
    priority: int = Field(default=10, description="优先级(1最高)")


class RuleSet(BaseModel):
    """策略规则集合"""
    rules: list[StrategyRule] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    description: str = Field(default="")


# ======================================================================
# 操作符实现（安全映射，不使用 eval）
# ======================================================================

def _to_num(val: Any) -> float:
    """安全转数字"""
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("，", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _parse_list_value(val: Any) -> list[str]:
    """解析 in / not_in 的值列表"""
    if isinstance(val, list):
        return [str(v).strip() for v in val]
    s = str(val).strip().strip("[]()（）【】")
    return [v.strip().strip("'\"") for v in s.split(",") if v.strip()]


_OPERATORS: dict[str, Any] = {
    ">":      lambda a, b: _to_num(a) > _to_num(b),
    "<":      lambda a, b: _to_num(a) < _to_num(b),
    ">=":     lambda a, b: _to_num(a) >= _to_num(b),
    "<=":     lambda a, b: _to_num(a) <= _to_num(b),
    "==":     lambda a, b: str(a).strip() == str(b).strip(),
    "!=":     lambda a, b: str(a).strip() != str(b).strip(),
    "in":     lambda a, b: str(a).strip() in _parse_list_value(b),
    "not_in": lambda a, b: str(a).strip() not in _parse_list_value(b),
}


# Time window 合法 pattern: last_30d / last_90d / last_365d 等 · ^last_\d+d$
_TIME_WINDOW_RE = re.compile(r"^last_\d+d$")


# ======================================================================
# Expression 解析：LLM dict 嵌套树 → RuleExpression
# ======================================================================

def parse_expression_dict(data: Any) -> RuleExpression | None:
    """LLM dict / 任意输入 → RuleExpression · None on parse failure (silent reject)。

    Schema:
        condition leaf:
          {"type": "condition", "field": str, "operator": str, "value": Any,
           "time_window": "last_30d" | None}
        group:
          {"type": "group", "op": "AND" | "OR" | "NOT", "children": [<expr>, ...]}

    解析容错: child 解析失败的 group 会丢弃该 child · 不阻断整树构建。
    顶层非 dict / 缺 type / type 非 condition|group → 返 None。
    """
    if not isinstance(data, dict):
        return None
    try:
        node_type = data.get("type")
        if node_type == "condition":
            field = data.get("field")
            operator = data.get("operator")
            return RuleExpression(
                type="condition",
                field=str(field) if field is not None else None,
                operator=str(operator) if operator is not None else None,
                value=data.get("value"),
                time_window=data.get("time_window"),
            )
        if node_type == "group":
            children_raw = data.get("children", [])
            if not isinstance(children_raw, list):
                return None
            children: list[RuleExpression] = []
            for c in children_raw:
                child = parse_expression_dict(c)
                if child is not None:
                    children.append(child)
            op_raw = data.get("op", "")
            return RuleExpression(
                type="group",
                op=str(op_raw).upper() if op_raw else None,
                children=children,
            )
    except (ValueError, TypeError, KeyError, AttributeError):
        return None
    return None


# ======================================================================
# Expression 求值：递归
# ======================================================================

def _apply_leaf_condition(expr: RuleExpression, record: dict) -> bool:
    """condition leaf 求值 · 含 time_window 字段重写 + 字段模糊匹配。"""
    field = (expr.field or "").strip()
    operator = expr.operator or ""
    if not field or not operator:
        return False

    # time_window 校验 + field 重写 (per §3.1 确定性)
    time_window = expr.time_window
    if time_window is not None:
        tw = str(time_window).strip()
        if not _TIME_WINDOW_RE.match(tw):
            return False  # 非法 window pattern · 静默拒
        effective_field = f"{field}_{tw}"
    else:
        effective_field = field

    # 字段查找 (模糊匹配 · 去空格 · 与 legacy apply_rule 一致)
    field_value = None
    for k, v in record.items():
        if str(k).strip() == effective_field:
            field_value = v
            break
    if field_value is None:
        return False

    op_func = _OPERATORS.get(operator)
    if op_func is None:
        return False

    try:
        return bool(op_func(field_value, expr.value))
    except (ValueError, TypeError):
        return False


def apply_expression(expr: RuleExpression, record: dict) -> bool:
    """递归求值 RuleExpression · 支持 AND/OR/NOT 嵌套 + time_window leaf。

    Args:
        expr: 表达式树根
        record: 一行数据字典

    Returns:
        True 命中 · False 未命中或表达式非法

    短路求值:
      - AND: 第一个 False 即返 False
      - OR:  第一个 True 即返 True
      - NOT: 必须正好 1 child · 否则返 False
    """
    if expr.type == "condition":
        return _apply_leaf_condition(expr, record)

    if expr.type == "group":
        op = (expr.op or "").upper()
        children = expr.children
        if op == "NOT":
            if len(children) != 1:
                return False
            return not apply_expression(children[0], record)
        if op == "AND":
            if not children:
                return False
            return all(apply_expression(c, record) for c in children)
        if op == "OR":
            if not children:
                return False
            return any(apply_expression(c, record) for c in children)

    return False


def _describe_expression(expr: RuleExpression) -> str:
    """描述表达式为可读 string · 用于 backtest hit_conditions 命中说明。"""
    if expr.type == "condition":
        f = expr.field or "?"
        if expr.time_window:
            f = f"{f}[{expr.time_window}]"
        return f"{f} {expr.operator or '?'} {expr.value!r}"
    if expr.type == "group":
        op = (expr.op or "").upper()
        if op == "NOT" and len(expr.children) == 1:
            return f"NOT ({_describe_expression(expr.children[0])})"
        joiner = f" {op} "
        return "(" + joiner.join(_describe_expression(c) for c in expr.children) + ")"
    return "?"


# ======================================================================
# 解析：LLM输出 -> RuleSet
# ======================================================================

def parse_natural_language_rules(llm_output: dict) -> RuleSet:
    """从LLM结构化输出（dict）解析为 RuleSet。

    Backward compat: 现有 LLM 出 conditions list (AND-only) 路径不动。
    新 DSL: rule item 可含 'expression' (嵌套 dict · 支持 OR/NOT/嵌套/time_window)。
    expression 与 conditions 都给时 · expression 优先 (求值时 dispatch)。

    Args:
        llm_output: LLM返回的JSON dict，期望包含 'rules' 键

    Returns:
        RuleSet 对象
    """
    if not isinstance(llm_output, dict):
        return RuleSet(description="解析失败：输入不是dict")

    rules_data = llm_output.get("rules", [])
    if not isinstance(rules_data, list):
        return RuleSet(description="解析失败：rules不是列表")

    parsed_rules: list[StrategyRule] = []
    for idx, item in enumerate(rules_data):
        if not isinstance(item, dict):
            continue
        try:
            # 解析 conditions (legacy AND-only)
            raw_conditions = item.get("conditions", [])
            conditions = []
            for c in raw_conditions:
                if isinstance(c, dict):
                    conditions.append(RuleCondition(
                        field=str(c.get("field", "")),
                        operator=str(c.get("operator", "==")),
                        value=c.get("value", ""),
                    ))

            # 解析 expression (新 DSL · OR/NOT/嵌套/time_window)
            expression_raw = item.get("expression")
            expression = (
                parse_expression_dict(expression_raw)
                if expression_raw is not None
                else None
            )

            rule = StrategyRule(
                rule_id=item.get("rule_id", f"R{idx + 1:03d}"),
                name=item.get("name", f"规则{idx + 1}"),
                description=item.get("description", ""),
                conditions=conditions,
                expression=expression,
                action=item.get("action", "manual_review"),
                priority=int(item.get("priority", 10)),
            )
            parsed_rules.append(rule)
        except (ValueError, TypeError, KeyError, AttributeError):
            continue

    # 按 priority 升序排列（1最高）
    parsed_rules.sort(key=lambda r: r.priority)

    return RuleSet(
        rules=parsed_rules,
        description=llm_output.get("description", ""),
    )


# ======================================================================
# 执行：规则应用
# ======================================================================

def apply_rule(rule: StrategyRule, record: dict) -> bool:
    """对单条记录应用规则。

    Dispatch 顺序:
      1. rule.expression 非空 → apply_expression (新 DSL · OR/NOT/嵌套/time_window)
      2. fallback rule.conditions (legacy AND-only)

    Args:
        rule: 策略规则
        record: 一行数据的字典

    Returns:
        True 表示该记录命中此规则
    """
    # 新 DSL 优先 (per Q-054 C1 · 支持 OR/NOT/嵌套/time_window)
    if rule.expression is not None:
        return apply_expression(rule.expression, record)

    # legacy AND-only conditions
    if not rule.conditions:
        return False

    for cond in rule.conditions:
        # 模糊匹配字段名（去空格）
        field_value = None
        for k, v in record.items():
            if str(k).strip() == cond.field.strip():
                field_value = v
                break

        if field_value is None:
            # 字段不存在 -> 条件不满足
            return False

        op_func = _OPERATORS.get(cond.operator)
        if op_func is None:
            return False

        try:
            if not op_func(field_value, cond.value):
                return False
        except (ValueError, TypeError):
            return False

    return True


def apply_ruleset(ruleset: RuleSet, records: list[dict]) -> list[dict]:
    """批量应用规则集，返回每条记录的命中结果。

    规则按 priority 从高到低（数字小优先）匹配，命中即停。

    Args:
        ruleset: 规则集合
        records: 数据记录列表

    Returns:
        每条记录的命中结果列表:
        [
            {
                "record_index": int,
                "hit_rule_id": str | None,
                "hit_rule_name": str | None,
                "action": str,           # approve/reject/manual_review/none
                "hit_conditions": list,   # 命中的条件描述
            },
            ...
        ]
    """
    # 确保按 priority 排序
    sorted_rules = sorted(ruleset.rules, key=lambda r: r.priority)
    results = []

    for idx, record in enumerate(records):
        hit_result = {
            "record_index": idx,
            "hit_rule_id": None,
            "hit_rule_name": None,
            "action": "none",
            "hit_conditions": [],
        }

        for rule in sorted_rules:
            if apply_rule(rule, record):
                hit_result["hit_rule_id"] = rule.rule_id
                hit_result["hit_rule_name"] = rule.name
                hit_result["action"] = rule.action
                # hit_conditions 描述: expression 优先 · 否则 conditions AND list
                if rule.expression is not None:
                    hit_result["hit_conditions"] = [_describe_expression(rule.expression)]
                else:
                    hit_result["hit_conditions"] = [
                        f"{c.field} {c.operator} {c.value}" for c in rule.conditions
                    ]
                break  # 命中即停

        results.append(hit_result)

    return results
