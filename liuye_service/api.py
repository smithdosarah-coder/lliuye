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
from liuye_service.ledger_review import (
    list_review_events,
    record_review_event,
)
from liuye_service.orchestrator import (
    HEARTBEAT_INTERVAL_SECONDS,
    CoworkOrchestrator,
    default_orchestrator,
    register_default_adapters,
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
    # Bind the 6 adapter implementations (3 Cowork + 3 Managed stubs)
    # so adapter.dispatch_message can fire when sessions/{turn_id}/messages
    # is called. Idempotent · re-registration overwrites. Caller (test
    # fixture) MAY pre-register custom stubs and pass an orchestrator
    # with adapters already bound; we skip the default registration
    # only if the orchestrator already knows the canonical agent_ids.
    if not all(orch.get_adapter(a) for a in ("channel", "credit", "report")):
        register_default_adapters(orch)

    # ReviewWriter that backs grant/deny → append-only ledger_review_events.
    # Defined inside register_liuye_routes so each FastAPI app gets its own
    # closure (test isolation · the global state lives in ``ledger_review``).
    async def _default_review_writer(event: LedgerReviewEvent) -> bool:
        try:
            record_review_event(
                decision_id=event.decision_id,
                reviewer_id=event.reviewer_id,
                action=event.action,
                comment=event.comment,
                idempotency_key=event.idempotency_key,
                signature=event.signature,
                event_id=event.event_id,
                appended_at=event.appended_at,
            )
            return True
        except (ValueError, RuntimeError) as exc:
            logger.warning(
                "[liuye_service] review writer failed for decision=%s: %s",
                event.decision_id, exc,
            )
            return False

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
            review_writer=_default_review_writer,
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
            review_writer=_default_review_writer,
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
        # Append-only LedgerReviewEvent · sqlite-backed · idempotent on
        # (decision_id, idempotency_key) per ``ledger_review.py``.
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
        try:
            persisted = record_review_event(
                decision_id=body.decision_id,
                reviewer_id=body.reviewer_id,
                action=body.action,
                comment=body.comment,
                idempotency_key=body.idempotency_key,
                signature=body.signature,
                event_id=body.event_id,
                appended_at=body.appended_at,
            )
        except ValueError as exc:
            raise HTTPException(
                400,
                detail={
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": str(exc),
                    },
                },
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                500,
                detail={
                    "error": {
                        "code": "LEDGER_WRITE_FAILED",
                        "message": str(exc),
                    },
                },
            ) from exc
        return {
            "event": persisted.model_dump(mode="json"),
            "persisted": True,
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
        # Review chain · append-only events on
        # ``ledger_review_events`` table · ordered by appended_at ASC.
        chain = [
            evt.model_dump(mode="json")
            for evt in list_review_events(decision_id=decision_id)
        ]
        return {"decision": record, "review_chain": chain}

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
    """Fire the adapter dispatch + bridge each event onto the per-turn SSE queue.

    The orchestrator hands every emit() call to this closure, which
    enqueues onto the bounded ``asyncio.Queue`` owned by ``turn_id``.
    The SSE endpoint (``_stream_skeleton``) consumes the queue. On
    adapter completion we push a ``None`` sentinel so the stream can
    close cleanly without waiting on heartbeat timeout.
    """
    queue = orchestrator.get_or_create_sse_queue(turn_id)

    async def _emit(
        *,
        event: str,
        payload: dict[str, Any],
        turn_id: str = turn_id,
        trace_id: str = "trace_unknown",
        tool_call_id: Optional[str] = None,
        **_extras: Any,
    ) -> None:
        # Compose the liuye SSE event envelope so the consumer can write
        # the wire format directly. seq is minted by the queue consumer
        # via ``orchestrator.next_seq`` to keep monotonic order across
        # both adapter-sourced events and heartbeats.
        evt: dict[str, Any] = {
            "event": event,
            "payload": payload,
            "trace_id": trace_id,
        }
        if tool_call_id is not None:
            evt["tool_call_id"] = tool_call_id
        await queue.put(evt)

    try:
        await orchestrator.dispatch_message(
            turn_id=turn_id, message=message, emit=_emit,
        )
    finally:
        # Push end-of-stream sentinel · SSE consumer exits its loop.
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:  # pragma: no cover · consumer keep up
            pass


async def _stream_skeleton(
    orchestrator: CoworkOrchestrator,
    turn_id: str,
):
    """SSE stream · pulls adapter events off the per-turn queue + heartbeats.

    Lifecycle (post-checkpoint-4 wire-up):

    1. Emit ``turn.started`` envelope once (orchestrator state was already
       built when ``POST /api/liuye/sessions`` ran).
    2. Race the adapter queue (``queue.get()``) against a heartbeat
       timeout: whichever wins emits an event. Heartbeat tick is the
       smaller of ``HEARTBEAT_INTERVAL_SECONDS`` so the client never
       declares the connection dead mid-permission-hold.
    3. A ``None`` sentinel on the queue (set by ``_dispatch_via_adapter``
       on adapter completion or ``orchestrator.close_sse_queue``) ends
       the stream cleanly.
    """
    state = orchestrator.get_turn(turn_id)
    trace_id = state.trace_id if state else "trace_unknown"
    queue = orchestrator.get_or_create_sse_queue(turn_id)

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

    try:
        while True:
            current = orchestrator.get_turn(turn_id)
            if current is None or current.closed:
                break
            try:
                # Race the queue against a heartbeat-cadence sleep · adapter
                # events arrive in real time, heartbeats fill the gap.
                evt = await asyncio.wait_for(
                    queue.get(), timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                yield _envelope("heartbeat", {"alive": True})
                continue
            # End-of-stream sentinel · close cleanly.
            if evt is None:
                break
            yield _envelope(
                evt.get("event", "unknown"),
                evt.get("payload", {}),
            )
    except asyncio.CancelledError:  # pragma: no cover · client disconnect
        logger.info("[liuye_service] SSE stream cancelled · turn_id=%s", turn_id)
        raise
    finally:
        # Best-effort cleanup · drops the queue so the next stream on
        # the same turn_id (reconnect) starts fresh.
        orchestrator.close_sse_queue(turn_id)


__all__ = ["register_liuye_routes"]
