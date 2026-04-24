# -*- coding: utf-8 -*-
"""双路交叉域 —— 外部信号 × 内部指标交叉命中 → 分级 + 触发理由推理。"""

from __future__ import annotations

from ..cross_matcher import CrossMatcher, RuleHit, _infer_trigger_reasons as _infer_trigger_reasons_impl


def cross_match_customer(search_provider, target, rules, **kwargs):
    """对单客户跑外部 × 内部交叉匹配（双路交叉域：主入口）。

    薄包装 `CrossMatcher(search_provider).match_customer(target, rules, ...)`。
    """
    return CrossMatcher(search_provider).match_customer(target, rules, **kwargs)


def cross_match_infer_trigger_reasons(hits: list[RuleHit]) -> list[str]:
    """从命中规则列表推断触发理由（双路交叉域：理由化解释）。"""
    return _infer_trigger_reasons_impl(hits)
