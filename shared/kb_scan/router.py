# -*- coding: utf-8 -*-
"""ScannerRouter — 按 domain 注册 scanner 偏好链 · 调 degrader 执行.

mirror ``shared/sources/router.py``。

domain 命名约定: ``<agent_mod>.<capability>`` · 例如:
  - agent_alert.batch_loan_scan
  - agent_compliance.policy_scan
  - agent_channel.signal_scan
  - agent_report.template_scan

调用:
    from shared.kb_scan.router import ScannerRouter
    from shared.kb_scan.base import ScanRequest

    router = ScannerRouter()
    result = router.scan(
        "agent_alert.batch_loan_scan",
        ScanRequest(scope="batch_loan_customers", kb_id="kb_xxx"),
    )
    if result.ok:
        render(result.hit_list)
"""
from __future__ import annotations

from .base import ScanRequest, ScanRunResult
from .degrader import execute_with_degradation

_preferences: dict[str, list[str]] = {}


def register_preference(domain: str, chain: list[str]) -> None:
    """为一个 domain 注册降级偏好链.

    覆盖式注册 — 同 domain 重复调用会覆盖 (便于热重载 / 测试)。
    """
    if not domain:
        raise ValueError("domain is required")
    if not chain:
        raise ValueError("chain must be non-empty")
    _preferences[domain] = list(chain)


def get_preference(domain: str) -> list[str]:
    return list(_preferences.get(domain, []))


def all_preferences() -> dict[str, list[str]]:
    return {k: list(v) for k, v in _preferences.items()}


def clear_preferences() -> None:
    _preferences.clear()


class ScannerRouter:
    """轻量外观类 · 给 agent 侧稳定入口."""

    def scan(self, domain: str, request: ScanRequest) -> ScanRunResult:
        chain = _preferences.get(domain, [])
        if not chain:
            return ScanRunResult(
                ok=False,
                scanner_name="kb_scan.router",
                error=f"no preference registered for domain={domain}",
            )
        return execute_with_degradation(chain, request)


__all__ = [
    "ScannerRouter",
    "all_preferences",
    "clear_preferences",
    "get_preference",
    "register_preference",
]
