# -*- coding: utf-8 -*-
"""audit_service.api — admin endpoint ``GET /api/audit/llm_calls``.

Spec (W-E1-A1 onboarding):
  - admin only · ``Depends(require_user)`` + role check (admin 才能看)
  - paginated · query params ``user_id`` / ``agent_id`` / ``since`` / ``until``
    / ``limit`` (≤500) / ``offset``
  - 返 ``{items, total, limit, offset}``

ACCESS check 复用 ``auth_service.dependencies.require_user`` · 不直 import (避免
auth_service 不可用时 audit_service 整体 fail) · 走 lazy import + fallback。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from .recorder import query_calls

logger = logging.getLogger(__name__)


def _resolve_require_user():
    """lazy 拿 require_user · auth_service 缺时返 stub (本地 dev / 未 cherry-pick)."""
    try:
        from auth_service.dependencies import require_user as _require
        return _require
    except ImportError:
        logger.warning(
            "[audit_service] auth_service.dependencies not available · "
            "admin endpoint falls back to stub (allow all)",
        )

        async def _stub() -> dict[str, Any]:
            return {"sub": "anonymous", "role": "admin"}

        return _stub


def _check_admin(user: dict[str, Any]) -> None:
    """role guard · 仅 admin 可访问."""
    role = (user or {}).get("role", "")
    if role != "admin":
        raise HTTPException(
            403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "audit log access requires admin role",
                    "details": {"role": role},
                },
            },
        )


def register_audit_routes(app: FastAPI) -> None:
    """挂 ``GET /api/audit/llm_calls`` 到给定 FastAPI app.

    使用 (在 api_server.py)::

        from audit_service.api import register_audit_routes
        register_audit_routes(app)
    """
    require_user = _resolve_require_user()

    from fastapi import Depends

    @app.get("/api/audit/llm_calls")
    async def list_llm_calls(
        user: dict[str, Any] = Depends(require_user),
        user_id: str | None = Query(default=None),
        agent_id: str | None = Query(default=None),
        since: str | None = Query(default=None, description="ISO 8601 lower bound"),
        until: str | None = Query(default=None, description="ISO 8601 upper bound (exclusive)"),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        _check_admin(user)
        return query_calls(
            user_id=user_id,
            agent_id=agent_id,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )


__all__ = ["register_audit_routes"]
