# -*- coding: utf-8 -*-
"""auth_service.rbac — RBAC ACCESS matrix with row-level/action gate.

Spec: auth-protocol.md §3.4 + Q-052 #8 (RM 权限契约目标 收窄)
镜像: web/src/lib/store/auth-store.ts ACCESS_V2 + Action enum

Phase B Sprint 3 contract sub-PR 1 · 2026-05-05:
- 加 Action enum (invoke/read/export/handoff/approve) · row-level/action gate
- ACCESS_V2 row-level (role → agent → action set) · 替代 binary ACCESS 为 single source
- 收窄 ACCESS["rm"] per Q-052 #8: 主调 channel+report · 看 credit+alert read-only · 不可调 riskctrl+compliance
- 保留 ACCESS / can_access / can_handoff / access_for 作为 ACCESS_V2 derived (binary backward compat · sub-PR 2 implementation 改 caller)
"""
from __future__ import annotations

from typing import Literal

# Action enum · row-level/action gate
Action = Literal["invoke", "read", "export", "handoff", "approve"]

VALID_ACTIONS: tuple[Action, ...] = ("invoke", "read", "export", "handoff", "approve")
VALID_ROLES = ("rm", "credit_officer", "compliance_officer", "risk_manager", "admin")
VALID_AGENTS = ("channel", "report", "credit", "alert", "compliance", "riskctrl")


# 镜像 web/src/lib/store/auth-store.ts:ACCESS_V2 (row-level/action gate)
# Q-052 #8 RM 权限契约目标 收窄:
#   - 主调 channel + report (operational 4 actions: invoke/read/export/handoff)
#     - 不含 approve · RM 不是审批方 (审贷员/合规官/风险经理才 approve)
#   - 看 credit + alert (read-only · 仅 read)
#   - 不可调 riskctrl + compliance (NOT in dict · 任何 action 都 False)
ACCESS_V2: dict[str, dict[str, frozenset[Action]]] = {
    "rm": {
        "channel": frozenset({"invoke", "read", "export", "handoff"}),
        "report":  frozenset({"invoke", "read", "export", "handoff"}),
        "credit":  frozenset({"read"}),
        "alert":   frozenset({"read"}),
        # riskctrl: 不可调 (per Q-052 #8)
        # compliance: 不可调 (per Q-052 #8)
    },
    "credit_officer": {
        "credit":   frozenset({"invoke", "read", "approve", "handoff"}),
        "report":   frozenset({"read", "export"}),
        "alert":    frozenset({"read"}),
    },
    "compliance_officer": {
        "compliance": frozenset({"invoke", "read", "approve", "handoff"}),
        "report":     frozenset({"read", "export"}),
        "alert":      frozenset({"read"}),
    },
    "risk_manager": {
        "riskctrl": frozenset({"invoke", "read", "approve"}),
        "alert":    frozenset({"invoke", "read", "approve", "handoff"}),
        "credit":   frozenset({"read"}),
    },
    "admin": {
        agent: frozenset({"invoke", "read", "export", "handoff", "approve"})
        for agent in VALID_AGENTS
    },
}


# 镜像 web/src/lib/store/auth-store.ts:HANDOFFS
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


# Backward compat · derived from ACCESS_V2
# binary ACCESS (role → list[agent_id]) = 任 1 action 允许的 agent
ACCESS: dict[str, list[str]] = {
    role: [agent for agent, actions in agent_map.items() if actions]
    for role, agent_map in ACCESS_V2.items()
}


def can_access(role: str, agent_id: str) -> bool:
    """Binary check · backward compat · 任 1 action 允许即 True."""
    return bool(ACCESS_V2.get(role, {}).get(agent_id))


def can_action(role: str, agent_id: str, action: str) -> bool:
    """Row-level/action gate · per Q-052 #8 contract.

    Args:
        role: 用户角色 (e.g. "rm" / "credit_officer")
        agent_id: agent 标识 (e.g. "channel" / "compliance")
        action: 动作 (one of VALID_ACTIONS)

    Returns:
        True if role 对 agent 有该 action 权限.
    """
    role_map = ACCESS_V2.get(role, {})
    actions = role_map.get(agent_id, frozenset())
    return action in actions


def actions_for(role: str, agent_id: str) -> frozenset[Action]:
    """取 role 对 agent 的允许 action 集 · 不存在则 empty frozenset."""
    return ACCESS_V2.get(role, {}).get(agent_id, frozenset())


def can_handoff(role: str, from_agent: str, to_agent: str) -> bool:
    pairs = HANDOFFS.get(role, [])
    return any(p["from"] == from_agent and p["to"] == to_agent for p in pairs)


def access_for(role: str) -> list[str]:
    """Backward compat · 任 1 action 允许的 agent list."""
    return ACCESS.get(role, [])
