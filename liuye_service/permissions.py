# -*- coding: utf-8 -*-
"""liuye_service.permissions — 3-tier risk PermissionRequest registry + emit_permission_request.

Per W1-backend brief §3 file 5 + ``liuye_service/CLAUDE.md`` §8 + v3 §2.5
+ ``docs/contracts/liuye-sse-event-matrix.md`` §3 Q2 (PM 2026-05-11 ratify).

Three behaviours collapsed into one module:

1. **3-tier risk registry**: catalogues which UI form-factor (inline /
   modal / drawer) applies to each backend action. Cataloguing here
   centralizes the persona/risk policy so the orchestrator and the
   adapters never disagree.

2. **emit_permission_request**: emits the 11th SSE event
   ``permission.request`` **directly** (NOT via ``sse_v1_to_liuye.py``
   adapter · PM 2026-05-11 Q2 ratify). The adapter is the SSE v1 wire
   compatibility layer — ``permission.request`` has no v1 antecedent.
   It is a control-plane signal the BFF orchestrator mints on its own.

3. **grant / deny handlers**: drive ``orchestrator.resume_turn`` (grant)
   or ``orchestrator.abort_turn`` (deny). Both verify the
   ``idempotency_key`` + ``required_persona`` match and write a
   ``LedgerReviewEvent`` so the audit chain captures the human decision.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol

from liuye_service.schemas import LedgerReviewEvent, PermissionRequest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 3-tier risk registry (per ``liuye_service/CLAUDE.md`` §8 + v3 §2.5)
# ---------------------------------------------------------------------------
# Entries here are the **canonical** mapping. Frontend MUST query this via
# the ``ArtifactAction`` registry endpoint · NEVER hardcode action ids.
#
# Examples per CLAUDE.md §8:
#   low    → inline notice  → F-001 logout / pin / LE-04a 下载已生成 manifest
#   medium → blocking modal → A3-NEW Decision submit / F-053 上链 / F-052-export
#   high   → drawer w/reason→ LE-05 sign-off / LE-04b ZIP / 越权 persona
#
# This dict is the BFF-side index. The richer ``ArtifactAction`` view (label /
# description / required_persona) is built by ``orchestrator`` when serving
# the frontend's ``/api/liuye/actions`` query (Phase 1 endpoint TBD · use
# the registry directly in code now).

ACTION_RISK_TIER: dict[str, str] = {
    # low → inline
    "session_logout": "low",
    "thread_pin": "low",
    "kb_manifest_download": "low",  # LE-04a
    "im_send": "low",
    # medium → modal
    "credit_decision_submit": "medium",  # A3-NEW
    "ledger_write": "medium",            # F-053 上链
    "report_export_docx": "medium",      # F-052-export
    "report_handoff_pass": "medium",
    "kb_upload": "medium",
    # high → drawer with reason
    "ledger_sign_off": "high",      # LE-05
    "report_handoff_partial": "high",
    "managed_zip_export": "high",   # LE-04b
    "pipl_overseas_call": "high",
    "out_of_scope_persona_op": "high",
}

# Actions whose ``idempotency_key`` is **mandatory** (irreversible side-effects).
# Per v3 必修 #21 hardline · all high-risk actions + the medium-risk write paths.
IDEMPOTENCY_REQUIRED_ACTIONS: frozenset[str] = frozenset({
    # all high tier
    "ledger_sign_off",
    "report_handoff_partial",
    "managed_zip_export",
    "pipl_overseas_call",
    "out_of_scope_persona_op",
    # medium tier write paths (any backend mutation)
    "credit_decision_submit",
    "ledger_write",
    "report_handoff_pass",
})


def risk_tier_for(action: str) -> str:
    """Look up the risk tier for a backend action · default 'medium' on miss.

    Defaulting to 'medium' means an unregistered action prompts the user
    via modal (safer than skipping confirmation) without crashing the
    pipeline. ops should add the action to ``ACTION_RISK_TIER`` once the
    policy is decided.
    """
    return ACTION_RISK_TIER.get(action, "medium")


def requires_idempotency_key(action: str) -> bool:
    """Return True when the action MUST carry an idempotency_key.

    All ``high`` tier actions implicitly require one. Some ``medium``
    actions (those that mutate state) also do. ``low`` never does.
    """
    return action in IDEMPOTENCY_REQUIRED_ACTIONS


# ---------------------------------------------------------------------------
# emit_permission_request — direct 11th-event SSE writer (PM 2026-05-11 Q2)
# ---------------------------------------------------------------------------


class SSEWriter(Protocol):
    """Minimal protocol the orchestrator's SSE stream emitter must satisfy.

    Kept structural so tests / mocks can supply a simple callable without
    the orchestrator concrete class.
    """

    async def emit(
        self,
        *,
        event: str,
        payload: dict[str, Any],
        turn_id: str,
        trace_id: str,
        tool_call_id: Optional[str] = None,
    ) -> None:  # pragma: no cover · Protocol contract
        ...


async def emit_permission_request(
    request: PermissionRequest,
    sse_writer: SSEWriter,
    *,
    trace_id: str,
) -> None:
    """Emit the 11th SSE event ``permission.request`` directly · NOT via adapter.

    PM 2026-05-11 ratify (Q2 of perfect-check-6 · ``liuye-sse-event-matrix.md``
    §3 Q2): ``permission.request`` is a **control-plane** signal the BFF
    orchestrator mints on its own. It has no SSE v1 antecedent, so it MUST
    NOT pass through ``adapters/sse_v1_to_liuye.py`` (which is the v1→liuye
    wire-compat layer for the 10 business events).

    Side-effect: orchestrator holds business event emission (``message.delta``
    / ``tool.progress`` / ``artifact.patch`` / ``evidence.attached``) and
    falls back to 15s heartbeat-only until ``grant()`` or ``deny()`` clears
    the parked state. This module emits the event; orchestrator handles the
    hold (see ``orchestrator.py::_permission_holds``).
    """
    if not request.turn_id:
        # Defence in depth · should not happen in practice (orchestrator sets it).
        logger.warning(
            "[permissions] emit_permission_request missing turn_id (request_id=%s)",
            request.id,
        )
        return

    # Match the PermissionRequestEventPayload shape (v3 §2.1 line 69-82).
    # Use model_dump so we don't drift from the generated schema, but flip
    # ``id`` → ``request_id`` to match the wire field name.
    payload = request.model_dump(mode="json", exclude_none=True)
    payload["request_id"] = payload.pop("id")
    # Internal-only fields (turn_id / tool_call_id) are carried in the SSE
    # envelope itself · not in the payload.
    payload.pop("turn_id", None)
    payload.pop("tool_call_id", None)

    await sse_writer.emit(
        event="permission.request",
        payload=payload,
        turn_id=request.turn_id,
        trace_id=trace_id,
        tool_call_id=request.tool_call_id,
    )


# ---------------------------------------------------------------------------
# grant / deny handlers · drive orchestrator resume / abort
# ---------------------------------------------------------------------------


class OrchestratorHandle(Protocol):
    """Subset of orchestrator API we depend on · kept as Protocol for testing."""

    async def resume_turn(
        self, turn_id: str, *, after_permission: PermissionRequest,
    ) -> bool:  # pragma: no cover · Protocol contract
        ...

    async def abort_turn(
        self,
        turn_id: str,
        *,
        reason: str,
        code: str = "PERMISSION_DENIED",
    ) -> bool:  # pragma: no cover · Protocol contract
        ...

    def get_permission_hold(
        self, request_id: str,
    ) -> Optional[PermissionRequest]:  # pragma: no cover · Protocol contract
        ...

    def clear_permission_hold(self, request_id: str) -> None:  # pragma: no cover
        ...


# Pluggable ledger-review writer (kept Protocol so we can stub it in tests
# without dragging in sqlite).
ReviewWriter = Callable[[LedgerReviewEvent], Awaitable[bool]]


async def grant(
    *,
    request_id: str,
    persona_id: str,
    idempotency_key: str,
    reviewer_role: str,
    orchestrator: OrchestratorHandle,
    review_writer: Optional[ReviewWriter] = None,
    comment: Optional[str] = None,
) -> bool:
    """Approve a parked PermissionRequest · resume the turn.

    Returns True when:

    1. the request is still parked (not already resolved · idempotent)
    2. the inbound ``idempotency_key`` matches the parked one
    3. ``reviewer_role`` is in ``required_persona`` (when set)
    4. ``orchestrator.resume_turn`` succeeds

    On failure we DO NOT abort the turn — the orchestrator continues to
    hold the parked state so the user can retry with the correct role /
    key. Caller (REST handler) maps False → HTTP 4xx.
    """
    request = orchestrator.get_permission_hold(request_id)
    if request is None:
        logger.info("[permissions] grant called for unknown request_id=%s", request_id)
        return False

    if request.idempotency_key != idempotency_key:
        logger.warning(
            "[permissions] idempotency mismatch on grant (request=%s)", request_id,
        )
        return False

    if request.required_persona and reviewer_role not in request.required_persona:
        logger.warning(
            "[permissions] persona %s not in required_persona %s",
            reviewer_role, request.required_persona,
        )
        return False

    if request.turn_id is None:
        logger.warning("[permissions] grant request missing turn_id (request=%s)", request_id)
        return False

    ok = await orchestrator.resume_turn(
        request.turn_id, after_permission=request,
    )
    if ok:
        orchestrator.clear_permission_hold(request_id)
        if review_writer is not None:
            await review_writer(_build_review_event(
                request=request,
                reviewer_id=persona_id,
                action="approve",
                comment=comment,
            ))
    return ok


async def deny(
    *,
    request_id: str,
    persona_id: str,
    reason: str,
    orchestrator: OrchestratorHandle,
    review_writer: Optional[ReviewWriter] = None,
) -> bool:
    """Reject a parked PermissionRequest · abort the turn.

    Always writes a LedgerReviewEvent (``action="reject"``) when a writer
    is supplied · the rejection itself is part of the audit chain even
    if the orchestrator state has already cleared.
    """
    request = orchestrator.get_permission_hold(request_id)
    if request is None:
        logger.info("[permissions] deny called for unknown request_id=%s", request_id)
        return False
    if request.turn_id is None:
        logger.warning("[permissions] deny request missing turn_id (request=%s)", request_id)
        return False

    ok = await orchestrator.abort_turn(
        request.turn_id, reason=reason, code="PERMISSION_DENIED",
    )
    orchestrator.clear_permission_hold(request_id)
    if review_writer is not None:
        await review_writer(_build_review_event(
            request=request,
            reviewer_id=persona_id,
            action="reject",
            comment=reason,
        ))
    return ok


def _build_review_event(
    *,
    request: PermissionRequest,
    reviewer_id: str,
    action: str,
    comment: Optional[str],
) -> LedgerReviewEvent:
    """Compose a LedgerReviewEvent envelope for the audit chain.

    The ``decision_id`` slot is filled with the PermissionRequest id when
    no concrete decision_ledger entry exists yet (e.g. a pre-decision
    veto). Downstream ledger_review handler resolves this distinction.
    """
    return LedgerReviewEvent(
        event_id=f"prv_{uuid.uuid4().hex[:16]}",
        decision_id=request.id,
        reviewer_id=reviewer_id,
        # ``LedgerReviewEvent.action`` accepts approve / reject / request_changes / sign_off.
        # Map permission verbs onto the closest ledger verb.
        action=action if action in {"approve", "reject", "request_changes", "sign_off"} else "request_changes",  # noqa: E501
        comment=comment,
        idempotency_key=request.idempotency_key,
        appended_at=datetime.now().astimezone(),
    )


__all__ = [
    "ACTION_RISK_TIER",
    "IDEMPOTENCY_REQUIRED_ACTIONS",
    "OrchestratorHandle",
    "ReviewWriter",
    "SSEWriter",
    "deny",
    "emit_permission_request",
    "grant",
    "requires_idempotency_key",
    "risk_tier_for",
]
