# -*- coding: utf-8 -*-
"""auth_service.rbac — ACCESS matrix 镜像 frontend auth-store.ts:61-67.

Spec: auth-protocol.md §3.4 · 与前端硬保持镜像 · 改动一定同步两边 (走 RFC).
"""
from __future__ import annotations

# 镜像 web/src/lib/store/auth-store.ts:61-67
ACCESS: dict[str, list[str]] = {
    "rm":                 ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
    "credit_officer":     ["credit", "report", "alert"],
    "compliance_officer": ["compliance", "report", "alert"],
    "risk_manager":       ["riskctrl", "alert", "credit"],
    "admin":              ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
}


# 镜像 web/src/lib/store/auth-store.ts:72-92 (HANDOFFS)
HANDOFFS: dict[str, list[dict[str, str]]] = {
    "rm": [
        {"from": "channel", "to": "report"},
        {"from": "report",  "to": "credit"},
        {"from": "alert",   "to": "compliance"},
    ],
    "credit_officer":     [{"from": "credit",  "to": "report"}],
    "compliance_officer": [{"from": "compliance",  "to": "report"}],
    "risk_manager": [
        {"from": "alert", "to": "compliance"},
        {"from": "alert", "to": "credit"},
    ],
    "admin": [
        {"from": "channel", "to": "report"},
        {"from": "report",  "to": "credit"},
        {"from": "alert",   "to": "compliance"},
        {"from": "alert",   "to": "credit"},
        {"from": "credit",  "to": "report"},
        {"from": "compliance",  "to": "report"},
    ],
}

VALID_ROLES = tuple(ACCESS.keys())
VALID_AGENTS = ("channel", "report", "credit", "alert", "compliance", "riskctrl")


def can_access(role: str, agent_id: str) -> bool:
    return agent_id in ACCESS.get(role, [])


def can_handoff(role: str, from_agent: str, to_agent: str) -> bool:
    pairs = HANDOFFS.get(role, [])
    return any(p["from"] == from_agent and p["to"] == to_agent for p in pairs)


def access_for(role: str) -> list[str]:
    return ACCESS.get(role, [])
