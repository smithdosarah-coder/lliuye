# -*- coding: utf-8 -*-
"""Scanner registry — name → BaseScanner 实例查找.

mirror ``shared/sources/registry.py``。

使用:
    from shared.kb_scan.registry import register, get
    register(AlertCustomerScannerAdapter())
    s = get("alert_customer")
    s.scan(ScanRequest(scope="batch_loan_customers"))
"""
from __future__ import annotations

from .base import BaseScanner

_registry: dict[str, BaseScanner] = {}


def register(scanner: BaseScanner) -> None:
    """注册一个 scanner. 同名重复注册会覆盖 (便于测试 / 热重载)."""
    if not getattr(scanner, "name", None):
        raise ValueError("scanner.name is required")
    _registry[scanner.name] = scanner


def get(name: str) -> BaseScanner:
    """按 name 取 scanner. 未注册抛 KeyError (上层决定兜底)."""
    if name not in _registry:
        raise KeyError(f"scanner not registered: {name}")
    return _registry[name]


def has(name: str) -> bool:
    return name in _registry


def all_scanners() -> list[BaseScanner]:
    """返所有已注册 scanner (列表拷贝)."""
    return list(_registry.values())


def clear() -> None:
    """清空 registry (测试用)."""
    _registry.clear()


__all__ = ["all_scanners", "clear", "get", "has", "register"]
