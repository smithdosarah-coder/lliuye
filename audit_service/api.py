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

from .recorder import query_by_run_id, query_calls

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
        e2e_run_id: str | None = Query(
            default=None,
            description="ROI #5 · GitHub Actions run_id 过滤 (X-Liuye-E2E-Run-Id header)",
        ),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        _check_admin(user)
        return query_calls(
            user_id=user_id,
            agent_id=agent_id,
            since=since,
            until=until,
            e2e_run_id=e2e_run_id,
            limit=limit,
            offset=offset,
        )

    # ------------------------------------------------------------------------
    # ROI #5 · E2E 证据链 export endpoint (daily-visual workflow 调)
    #
    # 设计:
    #   - admin role 才允 (复用 _check_admin · 不需要扩 RBAC matrix 加 "audit" agent)
    #   - 单次 cron run 通常 ≤ 500 record · 默认 limit=1000 / max=5000
    #   - 返 envelope 含 agents_hit / endpoints_hit / errors / total_cost_cny
    #     方便 Issue 评论模板渲染提要 (不必下载 artifact 也能看摘要)
    #
    # 调用:
    #   curl -s -H "Cookie: zhongan_auth=<admin JWT>" \
    #     "https://liuye.me/api/audit/by_run_id/${RUN_ID}?limit=5000" \
    #     -o audit-trail.json
    # ------------------------------------------------------------------------
    @app.get("/api/audit/by_run_id/{run_id}")
    async def get_audit_by_run_id(
        run_id: str,
        user: dict[str, Any] = Depends(require_user),
        limit: int = Query(default=1000, ge=1, le=5000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        """ROI #5 · 按 GitHub Actions run_id 拉证据链.

        - admin role 才允 (银保监合规留痕 · 不暴露给 RM/credit_officer 等)
        - 返 ``{run_id, count, total, agents_hit, endpoints_hit, errors,
              total_cost_cny, items, limit, offset, has_more}``
        - empty result 返 200 + count=0 (不返 404 · 让 workflow 即使 audit 缺
          也能继续 issue 流程 · 别 502 卡死)
        """
        _check_admin(user)
        # 防 path injection: run_id 仅允 alphanum + - _ . · GH run_id 实际为纯数字
        sanitized = "".join(ch for ch in run_id if ch.isalnum() or ch in "-_.")[:64]
        if not sanitized:
            raise HTTPException(
                400,
                detail={"error": {"code": "INVALID_RUN_ID", "message": "run_id 非法 (仅允字母数字 - _ .)"}},
            )
        return query_by_run_id(sanitized, limit=limit, offset=offset)


__all__ = ["register_audit_routes"]
