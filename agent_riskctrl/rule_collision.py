# -*- coding: utf-8 -*-
"""agent_riskctrl.rule_collision — 互斥/遮蔽 (BE6.3).

检测同一字段被多 rule 同时命中时的 priority + override 语义 ·
不破现有 rule_engine.apply_ruleset (priority order · 命中即停) ·
仅在外层加 collision 分析层.

业务真痛 (per docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE6):
  风险经理写完 N 条 DSL 规则后不知道:
    1. **遮蔽** (shadowing): 高优先级规则覆盖低优先级 · 后者永远不会命中
       → e.g. R001(prio=1) reject debt_ratio>0.5 · R005(prio=10) approve debt_ratio>0.7
       任何 debt_ratio>0.7 必先命中 R001 · R005 永远死代码
    2. **互斥冲突** (contradiction): 同一字段两 rule 给出相反 action
       → e.g. R001 reject if industry='房地产' · R002 approve if industry='房地产'
       priority 决定哪个赢 · 但风险经理可能不察觉
    3. **覆盖死区** (coverage gap): 某字段值范围没规则覆盖
       → e.g. debt_ratio>0.8 reject · 0.5-0.8 没规则 · manual_review 也没规则
       低风险高负债客户全 fall through "none"

设计:
  · 静态分析 (analyze RuleSet · 不需 sample data) · 报告 priority/override/coverage
  · 动态分析 (analyze on records · 配 sample data) · 实测哪些 rule 真死/真冲突
  · 不强制阻断 DSL gen · 仅给报告 · 风险经理 review 后决定改不改

Public surface:
  - ``detect_priority_shadows(ruleset) -> list[ShadowReport]``
    (静态 · 同字段 same operator 子集判定)
  - ``detect_action_contradictions(ruleset) -> list[ContradictionReport]``
    (静态 · 同字段相反 action)
  - ``analyze_collisions(ruleset, records=None) -> CollisionReport``
    (整合 + 可选动态实测)
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from agent_riskctrl.dsl_field_dict import get_field_spec
from agent_riskctrl.rule_engine import RuleSet, StrategyRule, apply_rule


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@dataclass
class ShadowReport:
    """High-priority rule shadowing low-priority rule on same field+operator."""
    shadowed_rule_id: str
    shadowed_rule_name: str
    shadowing_rule_id: str
    shadowing_rule_name: str
    field_name: str
    operator: str
    reason: str  # 人话解释


@dataclass
class ContradictionReport:
    """Two rules on same field give opposite actions."""
    rule_a_id: str
    rule_a_action: str
    rule_b_id: str
    rule_b_action: str
    field_name: str
    winner_rule_id: str  # 按 priority 决出
    reason: str


@dataclass
class DeadRuleReport:
    """Rule never hits any record (dynamic analysis)."""
    rule_id: str
    rule_name: str
    reason: str


@dataclass
class CollisionReport:
    """整合报告 · 静态 + (可选) 动态."""
    shadows: list[ShadowReport] = field(default_factory=list)
    contradictions: list[ContradictionReport] = field(default_factory=list)
    dead_rules: list[DeadRuleReport] = field(default_factory=list)
    total_rules: int = 0
    total_fields_covered: int = 0

    @property
    def has_issues(self) -> bool:
        return bool(self.shadows or self.contradictions or self.dead_rules)

    def to_dict(self) -> dict:
        return {
            "shadows": [
                {
                    "shadowed_rule_id": s.shadowed_rule_id,
                    "shadowed_rule_name": s.shadowed_rule_name,
                    "shadowing_rule_id": s.shadowing_rule_id,
                    "shadowing_rule_name": s.shadowing_rule_name,
                    "field": s.field_name,
                    "operator": s.operator,
                    "reason": s.reason,
                }
                for s in self.shadows
            ],
            "contradictions": [
                {
                    "rule_a_id": c.rule_a_id,
                    "rule_a_action": c.rule_a_action,
                    "rule_b_id": c.rule_b_id,
                    "rule_b_action": c.rule_b_action,
                    "field": c.field_name,
                    "winner_rule_id": c.winner_rule_id,
                    "reason": c.reason,
                }
                for c in self.contradictions
            ],
            "dead_rules": [
                {"rule_id": d.rule_id, "rule_name": d.rule_name, "reason": d.reason}
                for d in self.dead_rules
            ],
            "total_rules": self.total_rules,
            "total_fields_covered": self.total_fields_covered,
            "has_issues": self.has_issues,
        }


# ---------------------------------------------------------------------------
# 静态分析: shadow detection
# ---------------------------------------------------------------------------


def _to_float(v: object) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _shadows_on_same_op(
    high: StrategyRule, low: StrategyRule, field_name: str, operator: str,
) -> ShadowReport | None:
    """高优先级 rule 是否 shadow 低优先级 rule (相同字段 + 相同 op)."""
    high_cond = _find_cond(high, field_name, operator)
    low_cond = _find_cond(low, field_name, operator)
    if high_cond is None or low_cond is None:
        return None

    # == op 走 string 比较 · 数值 op 走 float 比较
    shadows = False
    reason = ""

    if operator == "==":
        if str(high_cond.value).strip() == str(low_cond.value).strip():
            shadows = True
            reason = (
                f"R[{high.rule_id}] {field_name}=={high_cond.value} 与"
                f" R[{low.rule_id}] {field_name}=={low_cond.value} 同值 · "
                f"高优先级永远先命中 · 低优先级死代码"
            )
        return ShadowReport(
            shadowed_rule_id=low.rule_id, shadowed_rule_name=low.name,
            shadowing_rule_id=high.rule_id, shadowing_rule_name=high.name,
            field_name=field_name, operator=operator, reason=reason,
        ) if shadows else None

    hv = _to_float(high_cond.value)
    lv = _to_float(low_cond.value)
    if hv is None or lv is None:
        return None

    # 子集判定 · 高 rule 命中区间是否完全包住低 rule 命中区间
    if operator in (">", ">="):
        # high: x > hv · low: x > lv · low ⊂ high 当 lv >= hv
        if lv >= hv:
            shadows = True
            reason = (
                f"R[{high.rule_id}] {field_name}{operator}{hv} 命中"
                f" {field_name}>={hv} · 完全包住 R[{low.rule_id}]"
                f" {field_name}{operator}{lv} ({lv}>={hv})"
            )
    elif operator in ("<", "<="):
        if lv <= hv:
            shadows = True
            reason = (
                f"R[{high.rule_id}] {field_name}{operator}{hv} 命中"
                f" {field_name}<={hv} · 完全包住 R[{low.rule_id}]"
                f" {field_name}{operator}{lv} ({lv}<={hv})"
            )

    if shadows:
        return ShadowReport(
            shadowed_rule_id=low.rule_id, shadowed_rule_name=low.name,
            shadowing_rule_id=high.rule_id, shadowing_rule_name=high.name,
            field_name=field_name, operator=operator, reason=reason,
        )
    return None


def _find_cond(rule: StrategyRule, field_name: str, operator: str):
    spec = get_field_spec(field_name)
    canonical = spec.name if spec else field_name
    for c in rule.conditions:
        c_spec = get_field_spec(c.field)
        c_canonical = c_spec.name if c_spec else c.field
        if c_canonical == canonical and c.operator == operator:
            return c
    return None


def detect_priority_shadows(ruleset: RuleSet) -> list[ShadowReport]:
    """检测 priority 遮蔽: 高优 rule 完全包住低优 rule.

    Conservative · 仅检测**单条件 same op** (e.g. 都用 `>`) · 不展开复合 AND/OR.
    复合规则 (多 condition) 当前跳过 · 后续可加 SAT-style 子集判定.
    """
    reports: list[ShadowReport] = []
    sorted_rules = sorted(ruleset.rules, key=lambda r: r.priority)
    for i, high in enumerate(sorted_rules):
        if len(high.conditions) != 1:
            continue
        h_cond = high.conditions[0]
        for low in sorted_rules[i + 1:]:
            if len(low.conditions) != 1:
                continue
            l_cond = low.conditions[0]
            # 字段 alias 化
            h_spec = get_field_spec(h_cond.field)
            l_spec = get_field_spec(l_cond.field)
            h_canonical = h_spec.name if h_spec else h_cond.field
            l_canonical = l_spec.name if l_spec else l_cond.field
            if h_canonical != l_canonical:
                continue
            if h_cond.operator != l_cond.operator:
                continue
            r = _shadows_on_same_op(high, low, h_canonical, h_cond.operator)
            if r:
                reports.append(r)
    return reports


# ---------------------------------------------------------------------------
# 静态分析: action contradiction
# ---------------------------------------------------------------------------


def detect_action_contradictions(ruleset: RuleSet) -> list[ContradictionReport]:
    """检测同字段相反 action.

    定义: 两 rule 都涉及同一字段 (任何 condition) 且 action ∈ {reject, approve}
    互不同 · 报告 priority 决出的 winner.
    """
    reports: list[ContradictionReport] = []
    rules = list(ruleset.rules)

    for i, a in enumerate(rules):
        a_fields = _rule_fields(a)
        for b in rules[i + 1:]:
            b_fields = _rule_fields(b)
            common = a_fields & b_fields
            if not common:
                continue
            opposite = (
                (a.action == "reject" and b.action == "approve") or
                (a.action == "approve" and b.action == "reject")
            )
            if not opposite:
                continue
            winner = a.rule_id if a.priority < b.priority else b.rule_id
            field_str = ", ".join(sorted(common))
            reports.append(ContradictionReport(
                rule_a_id=a.rule_id, rule_a_action=a.action,
                rule_b_id=b.rule_id, rule_b_action=b.action,
                field_name=field_str,
                winner_rule_id=winner,
                reason=(
                    f"R[{a.rule_id}] action={a.action} 与 R[{b.rule_id}]"
                    f" action={b.action} 在字段 [{field_str}] 上相反 · "
                    f"按 priority 由 R[{winner}] 胜出 (低 priority 数 = 高优)"
                ),
            ))
    return reports


def _rule_fields(rule: StrategyRule) -> set[str]:
    out: set[str] = set()
    for c in rule.conditions:
        spec = get_field_spec(c.field)
        canonical = spec.name if spec else c.field
        out.add(canonical)
    return out


# ---------------------------------------------------------------------------
# 动态分析: dead rule detection (需 sample records)
# ---------------------------------------------------------------------------


def detect_dead_rules(
    ruleset: RuleSet, records: list[dict],
) -> list[DeadRuleReport]:
    """跑一遍 sample · 哪些 rule 0 命中.

    与 backtesting.run_backtest 内的 rule_hit_counts 一致 ·
    但本 fn 独立 · 不依赖 priority-stop · **逐 rule 独立判**
    (priority-stop 下死的 rule 也可能被独立判时命中其他记录).

    Args:
        ruleset:
        records: list[dict] · CSV row 转 dict

    Returns:
        list[DeadRuleReport] · 真零命中 rule
    """
    if not records:
        return []
    reports: list[DeadRuleReport] = []
    for rule in ruleset.rules:
        hit = False
        for rec in records:
            if apply_rule(rule, rec):
                hit = True
                break
        if not hit:
            reports.append(DeadRuleReport(
                rule_id=rule.rule_id, rule_name=rule.name,
                reason=f"在 {len(records)} 条样本中 0 命中 · 可能字段写错或阈值不合理",
            ))
    return reports


# ---------------------------------------------------------------------------
# 整合 entry point
# ---------------------------------------------------------------------------


def analyze_collisions(
    ruleset: RuleSet, records: list[dict] | None = None,
) -> CollisionReport:
    """跑全套 collision 分析.

    Args:
        ruleset:
        records: 可选 · 给则跑动态 dead-rule 检测 · 不给则仅静态

    Returns:
        CollisionReport (含 shadows + contradictions + (可选) dead_rules)
    """
    fields_covered: set[str] = set()
    for rule in ruleset.rules:
        fields_covered.update(_rule_fields(rule))

    report = CollisionReport(
        shadows=detect_priority_shadows(ruleset),
        contradictions=detect_action_contradictions(ruleset),
        dead_rules=(
            detect_dead_rules(ruleset, records) if records else []
        ),
        total_rules=len(ruleset.rules),
        total_fields_covered=len(fields_covered),
    )
    return report


__all__ = [
    "CollisionReport",
    "ContradictionReport",
    "DeadRuleReport",
    "ShadowReport",
    "analyze_collisions",
    "detect_action_contradictions",
    "detect_dead_rules",
    "detect_priority_shadows",
]
