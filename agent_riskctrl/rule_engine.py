# -*- coding: utf-8 -*-
"""风控策略规则引擎 — 规则DSL定义、解析、执行

核心模型:
    RuleCondition  — 单个条件 (field operator value)
    StrategyRule   — 一条策略规则 (多个conditions + action)
    RuleSet        — 规则集合

安全原则: 操作符用固定映射，不使用 eval()
"""

from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Any
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


class StrategyRule(BaseModel):
    """一条风控策略规则"""
    rule_id: str = Field(description="规则编号，如 R001")
    name: str = Field(description="规则名称")
    description: str = Field(default="", description="规则说明")
    conditions: list[RuleCondition] = Field(
        default_factory=list, description="条件列表(AND关系)"
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


# ======================================================================
# 解析：LLM输出 -> RuleSet
# ======================================================================

def parse_natural_language_rules(llm_output: dict) -> RuleSet:
    """从LLM结构化输出（dict）解析为 RuleSet。

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
            # 解析 conditions
            raw_conditions = item.get("conditions", [])
            conditions = []
            for c in raw_conditions:
                if isinstance(c, dict):
                    conditions.append(RuleCondition(
                        field=str(c.get("field", "")),
                        operator=str(c.get("operator", "==")),
                        value=c.get("value", ""),
                    ))

            rule = StrategyRule(
                rule_id=item.get("rule_id", f"R{idx + 1:03d}"),
                name=item.get("name", f"规则{idx + 1}"),
                description=item.get("description", ""),
                conditions=conditions,
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
    """对单条记录应用规则，conditions之间为AND关系。

    Args:
        rule: 策略规则
        record: 一行数据的字典

    Returns:
        True 表示该记录命中此规则
    """
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
                hit_result["hit_conditions"] = [
                    f"{c.field} {c.operator} {c.value}" for c in rule.conditions
                ]
                break  # 命中即停

        results.append(hit_result)

    return results
