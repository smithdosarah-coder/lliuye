# -*- coding: utf-8 -*-
"""共享文本相似度 utility · stdlib SequenceMatcher.

Phase B Sprint 2 决策 2 引入 · few-shot 自动 pipeline 用于 dedup (相似度 > 0.85
同 agent 同 task type 视为重复).

设计:
  - 不引外部 dep (sklearn / fasttext) · stdlib 够用
  - 字符级 ratio · 中英文都 OK · 无需分词
  - dict 序列化为稳定字符串后比 (sort keys + 紧凑 json)

API:
  text_ratio(a, b) -> float  ∈ [0, 1]
  dict_ratio(a, b) -> float  ∈ [0, 1]
  is_duplicate(a, b, threshold=0.85) -> bool
"""
from __future__ import annotations

import json
from difflib import SequenceMatcher
from typing import Any


def _stable_serialize(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def text_ratio(a: str, b: str) -> float:
    """字符级相似度 ∈ [0, 1] · 双侧空串返 0.0."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def dict_ratio(a: dict, b: dict) -> float:
    """dict → 稳定字符串后比 · 字段顺序不影响."""
    return text_ratio(_stable_serialize(a), _stable_serialize(b))


def is_duplicate(a: str | dict, b: str | dict, threshold: float = 0.85) -> bool:
    """高于 threshold 视作重复 · 默认 0.85 (per Sprint 2 决策 2)."""
    sa = _stable_serialize(a)
    sb = _stable_serialize(b)
    return text_ratio(sa, sb) >= threshold


def jaccard_set(a: set | list | tuple, b: set | list | tuple) -> float:
    """集合 Jaccard 相似度 ∈ [0, 1] · 双侧空集返 0.0.

    Phase B Sprint 2 BE9.2 (2026-05-04) 引入 · alert_clusterer 用 ≥ 0.7 阈值
    跨客户聚类同类信号 (per docs/contracts/agent-handoff-schemas.md §6.4).

    Args:
        a, b: iterable of hashable (rule_id / signal_kind / etc)

    Returns:
        |a ∩ b| / |a ∪ b| · 双空 = 0.0 (定义为非匹配)

    Examples:
        >>> jaccard_set({"LAW-001", "FIN-002"}, {"LAW-001", "FIN-002", "POL-001"})
        0.6666666666666666
        >>> jaccard_set({"a"}, {"a"})
        1.0
        >>> jaccard_set([], [])
        0.0
    """
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


__all__ = ["dict_ratio", "is_duplicate", "jaccard_set", "text_ratio"]
