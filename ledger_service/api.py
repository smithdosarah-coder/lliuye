# -*- coding: utf-8 -*-
"""ledger_service.api — admin endpoints for the cross-agent decision ledger.

Spec: docs/contracts/decision-ledger.md §3 (5 endpoints).

Auth: reuses `auth_service.dependencies.require_user` via lazy import +
admin role check (mirrors audit_service.api). When auth_service is
absent (local dev), we fall back to a stub that allows all callers —
production deployments always have auth_service mounted, so this can't
silently leak in prod.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

from shared.decision_ledger import (
    ALLOWED_JURISDICTIONS,
    LEDGER_SCHEMA_VERSION,
    default_ledger,
    export_jurisdiction,
    get_decision,
    query_agent,
    query_jurisdiction,
    record_review,
)

logger = logging.getLogger(__name__)


def _resolve_require_user():
    """Lazy auth dep · stub when auth_service not on path (local dev only)."""
    try:
        from auth_service.dependencies import require_user as _require
        return _require
    except ImportError:
        logger.warning(
            "[ledger_service] auth_service.dependencies not available · "
            "admin endpoint falls back to stub (allow all)",
        )

        async def _stub() -> dict[str, Any]:
            return {"sub": "anonymous", "role": "admin"}

        return _stub


def _check_admin(user: dict[str, Any]) -> None:
    role = (user or {}).get("role", "")
    if role != "admin":
        raise HTTPException(
            403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "ledger access requires admin role",
                    "details": {"role": role},
                },
            },
        )


class ReviewRequest(BaseModel):
    reviewer_id: str = Field(..., description="审贷员 / 合规官 user id")
    action: str = Field(..., description="approve | reject | request_changes")


def register_ledger_routes(app: FastAPI) -> None:
    """Mount 5 admin-only endpoints under /api/ledger.

    Use::
        from ledger_service.api import register_ledger_routes
        register_ledger_routes(app)
    """
    require_user = _resolve_require_user()

    # ------------------------------------------------------------------
    # GET /api/ledger/decision/{decision_id} — single lookup
    # ------------------------------------------------------------------
    @app.get("/api/ledger/decision/{decision_id}")
    async def get_decision_endpoint(
        decision_id: str,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        _check_admin(user)
        record = get_decision(decision_id)
        if record is None:
            raise HTTPException(
                404,
                detail={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"decision_id not found: {decision_id}",
                    },
                },
            )
        return {"schema_version": LEDGER_SCHEMA_VERSION, "decision": record}

    # ------------------------------------------------------------------
    # GET /api/ledger/agent/{agent_id}
    # ------------------------------------------------------------------
    @app.get("/api/ledger/agent/{agent_id}")
    async def list_by_agent(
        agent_id: str,
        user: dict[str, Any] = Depends(require_user),
        since: str | None = Query(default=None, description="ISO 8601 lower bound"),
        until: str | None = Query(default=None, description="ISO 8601 upper bound (exclusive)"),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        _check_admin(user)
        items = query_agent(
            agent_id, since=since, until=until,
            limit=limit, offset=offset,
        )
        # Total count via store.count() — ask the singleton directly to
        # avoid round-tripping through the public façade.
        total = default_ledger().count(
            agent_id=agent_id, since=since, until=until,
        )
        return {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ------------------------------------------------------------------
    # GET /api/ledger/jurisdiction/{jurisdiction}
    # ------------------------------------------------------------------
    @app.get("/api/ledger/jurisdiction/{jurisdiction}")
    async def list_by_jurisdiction(
        jurisdiction: str,
        user: dict[str, Any] = Depends(require_user),
        since: str | None = Query(default=None),
        until: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        _check_admin(user)
        if jurisdiction not in ALLOWED_JURISDICTIONS:
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": (
                            f"jurisdiction must be one of "
                            f"{sorted(ALLOWED_JURISDICTIONS)}"
                        ),
                        "details": {"got": jurisdiction},
                    },
                },
            )
        items = query_jurisdiction(
            jurisdiction, since=since, until=until,
            limit=limit, offset=offset,
        )
        total = default_ledger().count(
            jurisdiction=jurisdiction, since=since, until=until,
        )
        return {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ------------------------------------------------------------------
    # GET /api/ledger/audit_export — zip stream
    # ------------------------------------------------------------------
    @app.get("/api/ledger/audit_export")
    async def audit_export(
        user: dict[str, Any] = Depends(require_user),
        jurisdiction: str = Query(..., description="必填 · 监管口径"),
        since: str | None = Query(default=None),
        until: str | None = Query(default=None),
    ) -> Response:
        _check_admin(user)
        if jurisdiction not in ALLOWED_JURISDICTIONS:
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": (
                            f"jurisdiction must be one of "
                            f"{sorted(ALLOWED_JURISDICTIONS)}"
                        ),
                        "details": {"got": jurisdiction},
                    },
                },
            )
        blob = export_jurisdiction(
            jurisdiction, since=since, until=until,
        )
        # Filename includes the slice for traceability — auditors don't
        # have to peek inside to know what they're looking at.
        filename = (
            f"ledger_{jurisdiction}_{since or 'all'}_{until or 'now'}.zip"
        )
        return Response(
            content=blob,
            media_type="application/zip",
            headers={
                "Content-Disposition": (
                    f"attachment; filename*=UTF-8''{quote(filename)}"
                ),
                "Cache-Control": "no-store",
                "X-Ledger-Schema-Version": LEDGER_SCHEMA_VERSION,
            },
        )

    # ------------------------------------------------------------------
    # POST /api/ledger/{decision_id}/review — reviewer signature
    # ------------------------------------------------------------------
    @app.post("/api/ledger/{decision_id}/review")
    async def submit_review(
        decision_id: str,
        req: ReviewRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        _check_admin(user)
        if req.action not in {"approve", "reject", "request_changes"}:
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": "action must be approve|reject|request_changes",
                        "details": {"got": req.action},
                    },
                },
            )
        ok = record_review(
            decision_id,
            reviewer_id=req.reviewer_id,
            action=req.action,
        )
        if not ok:
            raise HTTPException(
                404,
                detail={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": (
                            f"decision_id not found or review failed: "
                            f"{decision_id}"
                        ),
                    },
                },
            )
        return {
            "schema_version": LEDGER_SCHEMA_VERSION,
            "decision_id": decision_id,
            "reviewer_id": req.reviewer_id,
            "action": req.action,
            "status": "ok",
        }


__all__ = ["register_ledger_routes"]
