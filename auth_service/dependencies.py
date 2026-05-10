# -*- coding: utf-8 -*-
"""auth_service.dependencies — FastAPI Depends factory.

Spec: auth-protocol.md §7 Backend ACCESS Enforcement (defence in depth).

Usage:
    from auth_service.dependencies import require_user, require_agent

    @app.get("/api/secret/data")
    async def secret(user=Depends(require_user)):
        return {"hello": user["sub"]}

    @app.post("/api/channel/run")
    async def channel_run(req: Req, user=Depends(require_agent("channel"))):
        # require_agent enforces ACCESS matrix
        ...

Cookie name: zhongan_auth (per auth-protocol.md §5).
"""
from __future__ import annotations

from typing import Any

from fastapi import Cookie, HTTPException

from auth_service.jwt_util import JWTError, verify
from auth_service.rbac import DEMO_ELIGIBLE_ROLES, can_access, can_action

COOKIE_NAME = "zhongan_auth"


async def require_user(zhongan_auth: str | None = Cookie(default=None)) -> dict[str, Any]:
    """从 cookie 取 JWT · 解码 + 验签 + 验 exp · 返 payload 或抛 401."""
    if not zhongan_auth:
        raise HTTPException(401, detail={"error": {"code": "AUTH_MISSING", "message": "未登录"}})
    try:
        payload = verify(zhongan_auth)
    except JWTError as e:
        raise HTTPException(
            401,
            detail={"error": {"code": "AUTH_INVALID", "message": str(e)}},
        ) from e
    return payload


def require_agent(agent_id: str):
    """Factory · 返一个 FastAPI dependency · 验 cookie + ACCESS matrix · 不通过 403."""

    async def _check(zhongan_auth: str | None = Cookie(default=None)) -> dict[str, Any]:
        if not zhongan_auth:
            raise HTTPException(
                401,
                detail={"error": {"code": "AUTH_MISSING", "message": "未登录"}},
            )
        try:
            payload = verify(zhongan_auth)
        except JWTError as e:
            raise HTTPException(
                401,
                detail={"error": {"code": "AUTH_INVALID", "message": str(e)}},
            ) from e
        if not can_access(payload.get("role", ""), agent_id):
            raise HTTPException(
                403,
                detail={
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": (
                            f"role {payload.get('role')!r} 无权访问 agent {agent_id!r}"
                        ),
                        "details": {
                            "role": payload.get("role"),
                            "agent": agent_id,
                        },
                    }
                },
            )
        return payload

    return _check


def require_action(agent_id: str, action: str):
    """Factory · 返 FastAPI dependency · 验 cookie + ACCESS_V2 row-level/action enforcement.

    per Q-052 #8 contract sub-PR 1:
    - role-level binary check (require_agent) 不够 · row-level action gate
    - 例: RM 对 credit/alert 仅有 read action · 不能 invoke

    Usage:
        @app.post("/api/compliance/policy_diff")
        async def policy_diff(req, user=Depends(require_action("compliance", "invoke"))):
            ...
    """

    async def _check(zhongan_auth: str | None = Cookie(default=None)) -> dict[str, Any]:
        if not zhongan_auth:
            raise HTTPException(
                401,
                detail={"error": {"code": "AUTH_MISSING", "message": "未登录"}},
            )
        try:
            payload = verify(zhongan_auth)
        except JWTError as e:
            raise HTTPException(
                401,
                detail={"error": {"code": "AUTH_INVALID", "message": str(e)}},
            ) from e
        if not can_action(payload.get("role", ""), agent_id, action):
            # Phase A.6 · demo action 拒绝时返 401 (per PM spec · 不暴露 agent 存在性)
            # · 其他 action 拒绝返 403 (经典 RBAC 语义)
            status_code = 401 if action == "demo" else 403
            err_code = "AUTH_DEMO_FORBIDDEN" if action == "demo" else "ACCESS_DENIED"
            raise HTTPException(
                status_code,
                detail={
                    "error": {
                        "code": err_code,
                        "message": (
                            f"role {payload.get('role')!r} 对 agent {agent_id!r} "
                            f"无 {action!r} 权限"
                        ),
                        "details": {
                            "role": payload.get("role"),
                            "agent": agent_id,
                            "action": action,
                        },
                    }
                },
            )
        return payload

    return _check


def require_demo():
    """Phase A.6 · 便捷封装 · admin / demo_user 才允 invoke "demo" action.

    与 `require_action(<agent>, "demo")` 等价 · 但 agent 维度抽掉 (demo 跨 agent).
    内部用 "_global" 占位 · 实际靠 can_action 的 "demo" 特殊分支判定.

    Usage:
        @app.post("/api/demo/seed")
        async def demo_seed(user=Depends(require_demo())):
            ...
    """
    async def _check(zhongan_auth: str | None = Cookie(default=None)) -> dict[str, Any]:
        if not zhongan_auth:
            raise HTTPException(
                401,
                detail={"error": {"code": "AUTH_MISSING", "message": "未登录"}},
            )
        try:
            payload = verify(zhongan_auth)
        except JWTError as e:
            raise HTTPException(
                401,
                detail={"error": {"code": "AUTH_INVALID", "message": str(e)}},
            ) from e
        role = payload.get("role", "")
        if role not in DEMO_ELIGIBLE_ROLES:
            raise HTTPException(
                401,
                detail={
                    "error": {
                        "code": "AUTH_DEMO_FORBIDDEN",
                        "message": f"role {role!r} 无 demo 权限",
                        "details": {"role": role},
                    }
                },
            )
        return payload

    return _check
