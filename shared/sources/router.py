# -*- coding: utf-8 -*-
"""Router — 按 domain 查询偏好链，调降级器执行。

domain 命名约定: `<agent_mod>.<capability>`，例如:
- agent_compliance.policy_scan
- agent_credit.profile
- agent_report.law_citation

调用方只需要：
    router = Router()
    result = router.query("agent_credit.profile",
                          QueryRequest(query="招商银行", query_type="research"))
    if result.ok:
        render(result.items, result.evidence)
"""
from __future__ import annotations

from .base import QueryRequest, QueryResult
from .degrader import execute_with_degradation

_preferences: dict[str, list[str]] = {}


def register_preference(domain: str, chain: list[str]) -> None:
    """为一个 domain 注册降级偏好链。

    覆盖式注册——重复调用同一个 domain 会覆盖（方便热重载 / 测试）。
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


class Router:
    """轻量外观类，给 agent 侧一个稳定入口。"""

    def query(self, domain: str, request: QueryRequest) -> QueryResult:
        chain = _preferences.get(domain, [])
        if not chain:
            return QueryResult(
                ok=False,
                source_name="router",
                error=f"no preference registered for domain={domain}",
            )
        return execute_with_degradation(chain, request)
