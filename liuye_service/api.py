# -*- coding: utf-8 -*-
"""liuye_service.api — FastAPI router · 10 REST + 1 SSE endpoint.

Per W1-backend brief §3 file 8 + §3.5 endpoint inventory + ``liuye_service/CLAUDE.md`` §11.

Mounted onto the existing ``api_server.py`` via ``register_liuye_routes(app)``.
This module does NOT touch ``api_server.py`` itself · the caller adds a
3-6 line register call near the other ``register_*_routes`` invocations.

LIUYE_ENABLED gate: when ``Settings.enabled`` is False (default), this
module does not mount its endpoints (per v3 必修 #37). The 6 legacy agent
endpoints stay untouched. Flip the env to True only after W1 is signed
off so the new frontend can talk to the BFF.

Endpoint surface (W1-backend brief §3.5):

    REST (10):
      GET    /api/liuye/health
      POST   /api/liuye/sessions
      POST   /api/liuye/sessions/{turn_id}/messages
      POST   /api/liuye/tools/{tool_id}/invoke
      POST   /api/liuye/permissions/{request_id}/grant
      POST   /api/liuye/permissions/{request_id}/deny
      POST   /api/liuye/ledger/decisions/{id}/review_events
      GET    /api/liuye/ledger/decisions/{id}
      POST   /api/liuye/kb/upload
      GET    /api/liuye/kb/search

    SSE (1):
      GET    /api/liuye/sessions/{turn_id}/stream

Hidden gotchas worth flagging for the next relay:

- FastAPI registers routes in the order they are decorated. ``health``
  comes first so probe traffic never touches auth dependencies.
- ``Depends(require_user)`` is applied per-endpoint (not router-wide)
  so health stays anonymous and permission grant / deny carry the
  caller persona for ``required_persona`` checks.
- The SSE endpoint returns a placeholder that emits ``turn.started`` +
  ``heartbeat`` and then idles. Adapter wiring + the SSE v1 → liuye
  translation lands in the next relay (file 9-13).
- Phase 1 NotImplementedError-style endpoints (``/api/liuye/kb/*``,
  ``/api/liuye/tools/*``) return 501 with a stable error code so
  frontend can render a non-blocking "feature coming Phase 2" notice.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from liuye_service import __version__
from liuye_service.audit import record_liuye_decision
from liuye_service.config import get_settings
from liuye_service.orchestrator import (
    HEARTBEAT_INTERVAL_SECONDS,
    CoworkOrchestrator,
    default_orchestrator,
)
from liuye_service.permissions import (
    deny as deny_permission,
    grant as grant_permission,
    requires_idempotency_key,
)
from liuye_service.schemas import (
    LedgerReviewEvent,
    PermissionRequest,
)
from liuye_service.trace import LiuyeTraceContext, from_request_headers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auth dependency · lazy import so local dev without auth_service still boots
# ---------------------------------------------------------------------------


def _resolve_require_user():
    """Lazy auth dep · mirror ledger_service.api pattern."""
    try:
        from auth_service.dependencies import require_user as _require
        return _require
    except ImportError:  # pragma: no cover · auth_service should always exist
        logger.warning(
            "[liuye_service] auth_service.dependencies missing · falling back to stub",
        )

        async def _stub() -> dict[str, Any]:
            return {"sub": "anonymous", "role": "rm"}

        return _stub


# ---------------------------------------------------------------------------
# Request bodies · Pydantic
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    persona: str = Field(..., description="Caller persona id · e.g. 'rm' / 'credit_officer' / 'compliance_officer'.")
    agent_id: str = Field(..., description="Target Cowork agent id · 'channel' / 'credit' / 'report'.")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific kickoff payload (passed through to the adapter).",
    )
    parent_turn_id: Optional[str] = Field(
        None,
        description="Optional · cross-mode parent (Cowork DSL → Managed backtest) per v3 §2.1 + LedgerEntry v1.1.",
    )


class DispatchMessageRequest(BaseModel):
    message: dict[str, Any] = Field(
        ...,
        description="User message envelope · adapter-specific shape (text / tool params / file refs).",
    )


class InvokeToolRequest(BaseModel):
    turn_id: str = Field(..., description="Bind the invocation to an existing turn.")
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool input · validated by Zod inputSchemas on the frontend side.",
    )


class GrantPermissionRequest(BaseModel):
    persona_id: str = Field(..., description="Persona id of the granter (echoed into LedgerReviewEvent).")
    idempotency_key: str = Field(..., description="Must match the parked PermissionRequest.idempotency_key.")
    comment: Optional[str] = Field(None, description="Optional · auditor comment.")


class DenyPermissionRequest(BaseModel):
    persona_id: str = Field(..., description="Persona id of the denier.")
    reason: str = Field(..., description="Human-readable rejection reason · 写入 LedgerReviewEvent.comment.")


# ---------------------------------------------------------------------------
# Public mount point · 3-6 line append into api_server.py
# ---------------------------------------------------------------------------


def register_liuye_routes(
    app: FastAPI,
    *,
    orchestrator: Optional[CoworkOrchestrator] = None,
) -> bool:
    """Mount the 11 liuye endpoints onto ``app``.

    Gated by ``Settings.enabled`` (env ``LIUYE_ENABLED``). Returns True
    when routes were mounted, False when skipped (legacy 6-agent path
    unchanged). Caller MAY log the boolean to ``state-snapshot.md``.

    Use::
        from liuye_service.api import register_liuye_routes
        register_liuye_routes(app)

    The orchestrator parameter is optional · test code injects a stub.
    """
    settings = get_settings()
    if not settings.enabled:
        logger.info(
            "[liuye_service] LIUYE_ENABLED=false · skipping route mount (legacy 6-agent path preserved)",
        )
        return False

    require_user = _resolve_require_user()
    orch = orchestrator or default_orchestrator()

    # ------------------------------------------------------------------
    # 1. GET /api/liuye/health · anonymous · probe traffic
    # ------------------------------------------------------------------
    @app.get("/api/liuye/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "ledger_jurisdiction": settings.ledger_jurisdiction,
            "demo_mode": settings.demo_mode,
        }

    # ------------------------------------------------------------------
    # 2. POST /api/liuye/sessions · start a new turn
    # ------------------------------------------------------------------
    @app.post("/api/liuye/sessions", status_code=201)
    async def start_session(
        body: StartSessionRequest,
        request: Request,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        ctx = from_request_headers(request.headers)
        turn_id = await orch.start_turn(
            persona=body.persona,
            agent_id=body.agent_id,
            trace_id=ctx.trace_id,
            payload=body.payload,
            parent_turn_id=body.parent_turn_id,
        )
        return {
            "turn_id": turn_id,
            "trace_id": ctx.trace_id,
            "liuye_session_id": ctx.liuye_session_id,
        }

    # ------------------------------------------------------------------
    # 3. POST /api/liuye/sessions/{turn_id}/messages · push user message
    # ------------------------------------------------------------------
    @app.post("/api/liuye/sessions/{turn_id}/messages", status_code=202)
    async def dispatch_message(
        turn_id: str,
        body: DispatchMessageRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        state = orch.get_turn(turn_id)
        if state is None:
            raise HTTPException(
                404,
                detail={"error": {"code": "TURN_NOT_FOUND", "message": turn_id}},
            )
        # Fire-and-forget · the actual SSE emission happens through the
        # streaming endpoint. Adapter dispatch is async so we schedule
        # without blocking the REST handler.
        asyncio.create_task(_dispatch_via_adapter(
            orchestrator=orch, turn_id=turn_id, message=body.message,
        ))
        return {"accepted": True, "turn_id": turn_id}

    # ------------------------------------------------------------------
    # 4. POST /api/liuye/tools/{tool_id}/invoke · explicit tool call (Phase 2)
    # ------------------------------------------------------------------
    @app.post("/api/liuye/tools/{tool_id}/invoke", status_code=501)
    async def invoke_tool(
        tool_id: str,
        body: InvokeToolRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> JSONResponse:
        # Phase 1 stub · adapter wiring + ToolCall protocol implementation
        # land in the next relay (file 9-13).
        return JSONResponse(
            status_code=501,
            content={
                "error": {
                    "code": "TOOL_INVOKE_PHASE2",
                    "message": f"explicit tool invoke for {tool_id!r} ships in Phase 2 · use POST sessions/{{turn_id}}/messages for Phase 1",  # noqa: E501
                    "details": {"tool_id": tool_id, "turn_id": body.turn_id},
                },
            },
        )

    # ------------------------------------------------------------------
    # 5. POST /api/liuye/permissions/{request_id}/grant
    # ------------------------------------------------------------------
    @app.post("/api/liuye/permissions/{request_id}/grant")
    async def grant_endpoint(
        request_id: str,
        body: GrantPermissionRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        ok = await grant_permission(
            request_id=request_id,
            persona_id=body.persona_id,
            idempotency_key=body.idempotency_key,
            reviewer_role=user.get("role", ""),
            orchestrator=orch,
            comment=body.comment,
            # review_writer wired in by ``ledger_review.py`` (next relay)
            review_writer=None,
        )
        if not ok:
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "PERMISSION_GRANT_REJECTED",
                        "message": "request not parked / idempotency mismatch / persona forbidden",
                        "details": {"request_id": request_id},
                    },
                },
            )
        return {"granted": True, "request_id": request_id}

    # ------------------------------------------------------------------
    # 6. POST /api/liuye/permissions/{request_id}/deny
    # ------------------------------------------------------------------
    @app.post("/api/liuye/permissions/{request_id}/deny")
    async def deny_endpoint(
        request_id: str,
        body: DenyPermissionRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        ok = await deny_permission(
            request_id=request_id,
            persona_id=body.persona_id,
            reason=body.reason,
            orchestrator=orch,
            review_writer=None,
        )
        if not ok:
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "PERMISSION_DENY_FAILED",
                        "message": "request not parked or already resolved",
                        "details": {"request_id": request_id},
                    },
                },
            )
        return {"denied": True, "request_id": request_id}

    # ------------------------------------------------------------------
    # 7. POST /api/liuye/ledger/decisions/{id}/review_events · append-only
    # ------------------------------------------------------------------
    @app.post(
        "/api/liuye/ledger/decisions/{decision_id}/review_events",
        status_code=201,
    )
    async def append_review_event(
        decision_id: str,
        body: LedgerReviewEvent,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        # Phase 1 stub · ``ledger_review.py`` (next relay) owns the
        # append-only write + idempotency_key dedup. We do basic shape
        # validation here so callers fail fast.
        if body.decision_id != decision_id:
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": "decision_id mismatch between path and body",
                    },
                },
            )
        # Echo back the event with the server-stamped appended_at — the
        # actual sqlite write lands in ledger_review.py · this skeleton
        # returns 201 so frontend pipelines can be smoke-tested.
        return {
            "event": body.model_dump(mode="json"),
            "persisted": False,  # flipped by ledger_review.py in next relay
            "note": "skeleton · sqlite write wires in ledger_review.py (file 15 / next relay)",
        }

    # ------------------------------------------------------------------
    # 8. GET /api/liuye/ledger/decisions/{id} · decision + review chain
    # ------------------------------------------------------------------
    @app.get("/api/liuye/ledger/decisions/{decision_id}")
    async def get_decision_endpoint(
        decision_id: str,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        # We DO NOT duplicate ledger_service/api.py's admin endpoint.
        # This BFF endpoint just thin-wraps the existing shared module
        # so the new frontend can pull a single record + review chain.
        from shared.decision_ledger import get_decision

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
        # Review chain wiring lands in ledger_review.py · skeleton returns
        # the bare record with an empty chain.
        return {"decision": record, "review_chain": []}

    # ------------------------------------------------------------------
    # 9. POST /api/liuye/kb/upload (Phase 2 stub)
    # ------------------------------------------------------------------
    @app.post("/api/liuye/kb/upload", status_code=501)
    async def kb_upload(
        user: dict[str, Any] = Depends(require_user),
    ) -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={
                "error": {
                    "code": "KB_UPLOAD_PHASE2",
                    "message": "KBDoc upload ships in Phase 2 · use existing /api/feedback for Phase 1",
                },
            },
        )

    # ------------------------------------------------------------------
    # 10. GET /api/liuye/kb/search (Phase 2 stub)
    # ------------------------------------------------------------------
    @app.get("/api/liuye/kb/search", status_code=501)
    async def kb_search(
        q: str = "",
        user: dict[str, Any] = Depends(require_user),
    ) -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={
                "error": {
                    "code": "KB_SEARCH_PHASE2",
                    "message": "KB search ships in Phase 2 · use evidence_refs in artifact snapshots for Phase 1",
                    "details": {"q": q},
                },
            },
        )

    # ------------------------------------------------------------------
    # 11. GET /api/liuye/sessions/{turn_id}/stream · SSE
    # ------------------------------------------------------------------
    @app.get("/api/liuye/sessions/{turn_id}/stream")
    async def stream(
        turn_id: str,
        request: Request,
        last_event_id: Optional[str] = None,
        user: dict[str, Any] = Depends(require_user),
    ) -> StreamingResponse:
        state = orch.get_turn(turn_id)
        if state is None:
            raise HTTPException(
                404,
                detail={"error": {"code": "TURN_NOT_FOUND", "message": turn_id}},
            )
        return StreamingResponse(
            _stream_skeleton(orch, turn_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    logger.info(
        "[liuye_service] mounted 11 endpoints · LIUYE_ENABLED=true · version=%s",
        __version__,
    )
    return True


# ---------------------------------------------------------------------------
# Helpers · adapter dispatch + SSE skeleton
# ---------------------------------------------------------------------------


async def _dispatch_via_adapter(
    *,
    orchestrator: CoworkOrchestrator,
    turn_id: str,
    message: dict[str, Any],
) -> None:
    """Skeleton dispatch hook · next relay wires real adapters + SSE bridge."""

    async def _emit(**_kwargs: Any) -> None:
        # The SSE bridge / queue between dispatch and stream lands in
        # the next relay (file 13: ``adapters/sse_v1_to_liuye.py``).
        return None

    await orchestrator.dispatch_message(
        turn_id=turn_id, message=message, emit=_emit,
    )


async def _stream_skeleton(
    orchestrator: CoworkOrchestrator,
    turn_id: str,
):
    """Minimal SSE stream · emits turn.started + heartbeat 15s.

    Real translation pipeline (10 SSE v1 events → 11 liuye events via
    ``adapters/sse_v1_to_liuye.py``) plus ``permission.request`` direct
    emit (``permissions.emit_permission_request``) lands in the next
    relay. This skeleton keeps the SSE contract loadable so frontend
    integration can begin without blocking on the adapter relay.
    """
    state = orchestrator.get_turn(turn_id)
    trace_id = state.trace_id if state else "trace_unknown"

    # SSE id format: "<turn_id>:<seq>" so EventSource Last-Event-ID
    # carries both ids in one round-trip.
    def _envelope(event: str, payload: dict[str, Any]) -> str:
        seq = orchestrator.next_seq(turn_id)
        body = {
            "schema_version": "1",
            "event": event,
            "turn_id": turn_id,
            "trace_id": trace_id,
            "seq": seq,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        return f"id: {turn_id}:{seq}\nevent: {event}\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"

    # 1. turn.started
    yield _envelope("turn.started", {"persona": state.persona if state else None})

    # 2. periodic heartbeat · adapter relay replaces this loop with the
    #    real event bridge. heartbeat continues even during permission
    #    holds so the client does not declare the connection dead.
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            current = orchestrator.get_turn(turn_id)
            if current is None or current.closed:
                break
            yield _envelope("heartbeat", {"alive": True})
    except asyncio.CancelledError:  # pragma: no cover · client disconnect
        logger.info("[liuye_service] SSE stream cancelled · turn_id=%s", turn_id)
        raise


__all__ = ["register_liuye_routes"]
