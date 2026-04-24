# -*- coding: utf-8 -*-
"""DSL 生成域 —— 自然语言策略诉求 → DSL 规则 → 批量应用。"""

from __future__ import annotations

from ..rule_engine import (
    RuleSet,
    StrategyRule,
    apply_rule as _apply_rule,
    apply_ruleset as _apply_ruleset,
    parse_natural_language_rules as _parse_natural_language_rules,
)


def dsl_gen_parse_from_llm(llm_output: dict) -> RuleSet:
    """把 LLM JSON 输出解析成可执行 RuleSet（DSL 生成域入口）。"""
    return _parse_natural_language_rules(llm_output)


def dsl_gen_apply_rule(rule: StrategyRule, record: dict) -> bool:
    """单条记录对单条规则求值（DSL 生成域：规则应用单元）。"""
    return _apply_rule(rule, record)


def dsl_gen_apply_ruleset(ruleset: RuleSet, records: list[dict]) -> list[dict]:
    """把 RuleSet 批量应用到记录集，返回逐条命中结果（DSL 生成域：批量应用）。"""
    return _apply_ruleset(ruleset, records)
