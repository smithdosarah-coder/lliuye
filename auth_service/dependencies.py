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
from auth_service.rbac import can_access

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
