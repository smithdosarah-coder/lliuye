# -*- coding: utf-8 -*-
"""Agent4 Phase 1 Task C — trigger_reasons 枚举结构推断锁盘测试。

被测对象：`agent_alert.cross_matcher._infer_trigger_reasons`

锁的是 4 种 route 集合 → 3 值枚举的代数映射，证明：
  - 推断 100% 来自 RuleHit.route（结构信号），不依赖任何关键词/正则黑名单
  - 枚举封闭集 = {external_signal, internal_rule, cross_hit}，空列表表示 green

语义规约见 docs/design/alert-trigger-reasons-taxonomy.md。
"""

from __future__ import annotations

import pytest

from agent_alert.cross_matcher import (
    TRIGGER_REASON_CROSS,
    TRIGGER_REASON_EXTERNAL,
    TRIGGER_REASON_INTERNAL,
    RuleHit,
    _infer_trigger_reasons,
)
from shared.kb_scan.models import RiskLevel


def _hit(route: str, rule_id: str = "RULE-X") -> RuleHit:
    return RuleHit(
        rule_id=rule_id,
        rule_title="t",
        route=route,
        severity=RiskLevel.YELLOW,
        reason="r",
    )


def test_external_only_returns_external_signal():
    hits = [_hit("external", "LAW-001"), _hit("external", "BIZ-002")]
    assert _infer_trigger_reasons(hits) == [TRIGGER_REASON_EXTERNAL]


def test_internal_only_returns_internal_rule():
    hits = [_hit("internal", "POL-001")]
    assert _infer_trigger_reasons(hits) == [TRIGGER_REASON_INTERNAL]


def test_both_routes_collapse_to_cross_hit():
    hits = [_hit("external", "LAW-001"), _hit("internal", "POL-001")]
    assert _infer_trigger_reasons(hits) == [TRIGGER_REASON_CROSS]


def test_empty_hits_returns_empty_list():
    assert _infer_trigger_reasons([]) == []


def test_enum_values_are_frozen_strings():
    # 锁死 3 值字面量 —— 改动即破坏下游 evaluation adapter 与前端 color hook
    assert TRIGGER_REASON_EXTERNAL == "external_signal"
    assert TRIGGER_REASON_INTERNAL == "internal_rule"
    assert TRIGGER_REASON_CROSS == "cross_hit"
