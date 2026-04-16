# -*- coding: utf-8 -*-
"""RuleEngineV2 — 红线规则引擎（对公 30 条 / 对私 20 条，JSON 可编辑）"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .risk_appetite_config import RiskAppetiteConfig

_MOCK_DIR = Path(__file__).parent / "mock_data"


@dataclass
class RedLineHit:
    rule_id: str
    rule_name: str
    category: str = ""
    threshold: Any = None
    actual_value: Any = None
    severity: str = "low"
    is_hard: bool = False
    can_waive: bool = True
    waiver_conditions: list = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _to_number(x: Any) -> float | None:
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _check_condition(actual: Any, operator: str, threshold: Any) -> bool:
    a = _to_number(actual)
    t = _to_number(threshold)
    if a is None or t is None:
        return False
    if operator == ">":
        return a > t
    if operator == ">=":
        return a >= t
    if operator == "<":
        return a < t
    if operator == "<=":
        return a <= t
    if operator == "==":
        return a == t
    if operator == "!=":
        return a != t
    return False


class RuleEngineV2:
    """红线规则引擎"""

    def __init__(self, appetite: RiskAppetiteConfig | None = None):
        self.appetite = appetite
        self._cache: dict[str, list[dict]] = {}

    def _load_rules(self, segment: str) -> list[dict]:
        if segment in self._cache:
            return self._cache[segment]
        name = f"red_line_rules_{segment}.json"
        path = _MOCK_DIR / name
        rules: list[dict] = []
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh) or {}
                rules = data.get("rules", []) or []
            except Exception:
                rules = []
        self._cache[segment] = rules
        return rules

    def reload(self, segment: str | None = None):
        if segment:
            self._cache.pop(segment, None)
        else:
            self._cache.clear()

    def check(self, features: dict, segment: str) -> list[RedLineHit]:
        rules = self._load_rules(segment)
        hits: list[RedLineHit] = []
        for rule in rules:
            rule_id = rule.get("id", "")
            default_th = rule.get("default_threshold")
            threshold = default_th
            if self.appetite is not None:
                threshold = self.appetite.get_threshold(rule_id, default_th)

            expr = rule.get("feature_expr", "")
            actual = features.get(expr)
            if actual is None:
                continue
            if _check_condition(actual, rule.get("operator", ">"), threshold):
                hits.append(RedLineHit(
                    rule_id=rule_id,
                    rule_name=rule.get("name", ""),
                    category=rule.get("category", ""),
                    threshold=threshold,
                    actual_value=actual,
                    severity=rule.get("severity", "low"),
                    is_hard=bool(rule.get("is_hard", False)),
                    can_waive=bool(rule.get("can_waive", True)),
                    waiver_conditions=list(rule.get("waiver_conditions") or []),
                    description=rule.get("description", ""),
                ))
        return hits

    def list_rules(self, segment: str) -> list[dict]:
        """给 UI 展示所有规则"""
        return list(self._load_rules(segment))
