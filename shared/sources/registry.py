# -*- coding: utf-8 -*-
"""Source registry — 运行时按 name 查找已注册的 BaseSource 实例。

使用方式:
    from shared.sources.registry import register, get
    register(TavilySource())
    s = get("tavily")
    s.query(QueryRequest(query="招商银行", query_type="generic"))
"""
from __future__ import annotations

from .base import BaseSource

_registry: dict[str, BaseSource] = {}


def register(source: BaseSource) -> None:
    """注册一个 source。同名重复注册会覆盖（便于测试/热重载）。"""
    if not getattr(source, "name", None):
        raise ValueError("source.name is required")
    _registry[source.name] = source


def get(name: str) -> BaseSource:
    """按 name 取 source。未注册抛 KeyError（上层决定兜底策略）。"""
    if name not in _registry:
        raise KeyError(f"source not registered: {name}")
    return _registry[name]


def has(name: str) -> bool:
    return name in _registry


def all_sources() -> list[BaseSource]:
    """返回所有已注册 source（列表拷贝，外部修改不影响内部状态）。"""
    return list(_registry.values())


def clear() -> None:
    """清空 registry（单元测试用）。生产代码不要调。"""
    _registry.clear()
