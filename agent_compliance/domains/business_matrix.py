# -*- coding: utf-8 -*-
"""业务矩阵域 —— 存量业务制度 + 事件流水 → 可扫描规则矩阵。"""

from __future__ import annotations

from ..event_extractor import EventExtractor
from ..knowledge_base import ComplianceKnowledgeBase
from ..rule_set_builder import RuleSetBuilder


def business_matrix_build_rules(kb: ComplianceKnowledgeBase, *,
                                 use_llm_fallback: bool = False,
                                 llm_client=None, **kwargs):
    """从业务制度 KB 构建 RuleSet（业务矩阵域：规则库构建）。

    薄包装 `RuleSetBuilder(use_llm_fallback, llm_client).build(kb, ...)`。
    """
    builder = RuleSetBuilder(use_llm_fallback=use_llm_fallback, llm_client=llm_client)
    return builder.build(kb, **kwargs)


def business_matrix_extract_events(kb: ComplianceKnowledgeBase) -> list[dict]:
    """从 KB 抽取合规扫描所需事件流水（业务矩阵域：事件抽取）。"""
    return EventExtractor().extract(kb)
