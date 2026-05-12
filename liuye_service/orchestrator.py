# -*- coding: utf-8 -*-
"""liuye_service.orchestrator — Cowork SSE turn orchestrator (skeleton).

Per W1-backend brief §3 file 7 + v3 §2.1 + ``liuye_service/CLAUDE.md`` §3.

Responsibilities (this skeleton stubs the adapter / LLM wiring · later
relays fill them in):

- ``start_turn``       — mint a new turn_id + seq counter · register state
- ``dispatch_message`` — hand off a user message to an adapter (async)
- ``resume_turn``      — after PermissionRequest grant · resume parked stream (seq+1)
- ``abort_turn``       — after PermissionRequest deny / hard error · emit turn.error + turn.completed ok=false
- ``register_permission_hold`` / ``get_permission_hold`` /
  ``clear_permission_hold`` — drives ``permissions.py``

We deliberately keep the adapter call surface abstract here · the W1
backend file checklist puts concrete ``adapters/{channel,credit,report}.py``
in the next relay. The orchestrator only knows "given a turn, route the
message"; it never imports ``agent_*`` directly (HTTP isolation hardline
per ``liuye_service/CLAUDE.md`` §2.3).

Permission hold state · thread-safety hidden gotcha:
    FastAPI runs async handlers on a single event-loop thread (asyncio).
    We use ``asyncio.Lock`` to serialize permission-state mutations
    rather than threading.Lock so an awaited handler does not deadlock
    the loop. For multi-worker deployment (uvicorn --workers > 1) the
    permission state is **per worker** · use Redis when scaling out
    (Phase 1 in-memory is sufficient for the demo cluster).

heartbeat 15s · per ``liuye-sse-event-matrix.md`` §3 Q3 ratify. The
heartbeat loop is started when a turn enters a permission-hold state
so the client does not declare the connection dead during a wait.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional, Protocol

from liuye_service.schemas import PermissionRequest

logger = logging.getLogger(__name__)

# Heartbeat cadence (per v3 §2.1 + SSE matrix §3 Q3). Client declares dead
# after 30s silence · we tick at 15s to give a safety margin.
HEARTBEAT_INTERVAL_SECONDS = 15.0


# ---------------------------------------------------------------------------
# Adapter protocol · what an adapter looks like to the orchestrator
# ---------------------------------------------------------------------------


class CoworkAdapter(Protocol):
    """Adapter contract · ``adapters/{channel,credit,report}.py`` implement this."""

    agent_id: str  # 'channel' / 'credit' / 'report'

    async def dispatch(
        self,
        *,
        turn_id: str,
        trace_id: str,
        message: dict[str, Any],
        emit: "EmitFn",
    ) -> None:  # pragma: no cover · Protocol contract
        ...


# Type alias for the emit callable handed to adapters · signature mirrors
# ``permissions.SSEWriter.emit``. Defined at module scope so circular
# imports stay quiet.
EmitFn = Callable[..., Awaitable[None]]


# ---------------------------------------------------------------------------
# Turn state · one per active SSE stream
# ---------------------------------------------------------------------------


@dataclass
class TurnState:
    """In-memory per-turn record · single FastAPI worker scope.

    For multi-worker scale-out a Redis-backed implementation should
    replace this class. Phase 1 demo cluster runs one worker per host.
    """

    turn_id: str
    trace_id: str
    persona: str
    agent_id: str
    seq: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    held_by_permission: Optional[str] = None  # request_id of the parked PermissionRequest
    parent_turn_id: Optional[str] = None      # cross-mode link (v3 §2.1 + LedgerEntry v1.1)
    closed: bool = False

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


# ---------------------------------------------------------------------------
# Orchestrator core
# ---------------------------------------------------------------------------


class CoworkOrchestrator:
    """In-memory orchestrator · one instance per FastAPI app.

    The W1 skeleton focuses on lifecycle hooks and permission-hold
    state. Concrete adapter dispatch + heartbeat loop wiring land in
    the next relay (file 9-13: ``adapters/*``).
    """

    def __init__(self) -> None:
        self._turns: dict[str, TurnState] = {}
        # turn_id -> PermissionRequest (only one outstanding per turn)
        self._permission_holds: dict[str, PermissionRequest] = {}
        # request_id -> turn_id  (reverse index · used by permissions module)
        self._holds_by_request: dict[str, str] = {}
        self._adapters: dict[str, CoworkAdapter] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Adapter registration · called once at FastAPI startup
    # ------------------------------------------------------------------

    def register_adapter(self, adapter: CoworkAdapter) -> None:
        """Bind an adapter to its ``agent_id`` for later dispatch."""
        self._adapters[adapter.agent_id] = adapter

    def get_adapter(self, agent_id: str) -> Optional[CoworkAdapter]:
        return self._adapters.get(agent_id)

    # ------------------------------------------------------------------
    # Turn lifecycle
    # ------------------------------------------------------------------

    async def start_turn(
        self,
        *,
        persona: str,
        agent_id: str,
        trace_id: str,
        payload: dict[str, Any],
        parent_turn_id: Optional[str] = None,
    ) -> str:
        """Mint a new turn · register state · return turn_id.

        ``parent_turn_id`` carries the cross-mode link (Cowork → Managed)
        per v3 §2.1 + LedgerEntry v1.1. Single-mode turns leave it None.
        """
        turn_id = f"turn_{uuid.uuid4().hex[:16]}"
        async with self._lock:
            self._turns[turn_id] = TurnState(
                turn_id=turn_id,
                trace_id=trace_id,
                persona=persona,
                agent_id=agent_id,
                parent_turn_id=parent_turn_id,
            )
        logger.info(
            "[orchestrator] start_turn turn_id=%s agent=%s persona=%s parent=%s",
            turn_id, agent_id, persona, parent_turn_id,
        )
        # The actual ``turn.started`` SSE emission happens once the client
        # connects to ``/sessions/{turn_id}/stream`` · skeleton does not
        # synchronously emit.
        return turn_id

    async def dispatch_message(
        self,
        *,
        turn_id: str,
        message: dict[str, Any],
        emit: EmitFn,
    ) -> None:
        """Hand off a user message to the adapter bound to this turn.

        The adapter is responsible for translating its SSE v1 stream into
        liuye events via ``adapters/sse_v1_to_liuye.py`` and calling
        ``emit(...)`` for each translated event.

        ``parent_tool_call_id`` (v3 §2.1 + 必修 #51) is preserved here by
        leaving the message envelope intact · adapter forwards it to
        agent backend so e.g. Report → Credit handoff keeps lineage.
        """
        state = self._turns.get(turn_id)
        if state is None or state.closed:
            logger.warning(
                "[orchestrator] dispatch_message on unknown/closed turn_id=%s", turn_id,
            )
            return
        if state.held_by_permission:
            # Spec: business events MUST be suspended while a permission
            # hold is active (matrix §3 Q2). Heartbeat continues so the
            # client does not declare the connection dead.
            logger.info(
                "[orchestrator] dispatch_message suppressed · turn %s held by request %s",
                turn_id, state.held_by_permission,
            )
            return

        adapter = self._adapters.get(state.agent_id)
        if adapter is None:
            logger.error(
                "[orchestrator] no adapter registered for agent_id=%s", state.agent_id,
            )
            await self.abort_turn(
                turn_id,
                reason=f"adapter not configured for agent_id={state.agent_id}",
                code="ADAPTER_MISSING",
            )
            return

        await adapter.dispatch(
            turn_id=turn_id,
            trace_id=state.trace_id,
            message=message,
            emit=emit,
        )

    async def resume_turn(
        self,
        turn_id: str,
        *,
        after_permission: PermissionRequest,
    ) -> bool:
        """Resume a turn after a PermissionRequest grant · seq+1.

        Implementation note: the actual "continue from where we paused"
        replay is the adapter's responsibility · this method simply
        clears the permission hold so subsequent ``dispatch_message``
        calls proceed. The adapter that emitted the parking call also
        emits the resume token-by-token continuation.
        """
        state = self._turns.get(turn_id)
        if state is None or state.closed:
            return False
        async with self._lock:
            if state.held_by_permission == after_permission.id:
                state.held_by_permission = None
        logger.info(
            "[orchestrator] resume_turn turn_id=%s request_id=%s",
            turn_id, after_permission.id,
        )
        return True

    async def abort_turn(
        self,
        turn_id: str,
        *,
        reason: str,
        code: str = "PERMISSION_DENIED",
    ) -> bool:
        """Abort a turn · skeleton marks closed; emit logic lives in api.py / adapter.

        Adapter is expected to emit:
            - ``turn.error code=<code> human_hint=<reason>``  (TurnErrorPayload)
            - ``turn.completed ok=false``
        and then close the SSE stream. The orchestrator only owns state.
        """
        state = self._turns.get(turn_id)
        if state is None:
            return False
        async with self._lock:
            state.closed = True
            state.held_by_permission = None
        logger.info(
            "[orchestrator] abort_turn turn_id=%s code=%s reason=%s",
            turn_id, code, reason,
        )
        return True

    # ------------------------------------------------------------------
    # Permission-hold state (consumed by ``permissions.py``)
    # ------------------------------------------------------------------

    async def register_permission_hold(
        self, request: PermissionRequest,
    ) -> None:
        """Park a turn behind a PermissionRequest · subsequent dispatch is suppressed."""
        if not request.turn_id:
            logger.warning(
                "[orchestrator] register_permission_hold missing turn_id (request=%s)",
                request.id,
            )
            return
        async with self._lock:
            state = self._turns.get(request.turn_id)
            if state is None or state.closed:
                logger.warning(
                    "[orchestrator] permission hold on unknown turn_id=%s", request.turn_id,
                )
                return
            state.held_by_permission = request.id
            self._permission_holds[request.turn_id] = request
            self._holds_by_request[request.id] = request.turn_id

    def get_permission_hold(self, request_id: str) -> Optional[PermissionRequest]:
        turn_id = self._holds_by_request.get(request_id)
        if turn_id is None:
            return None
        return self._permission_holds.get(turn_id)

    def clear_permission_hold(self, request_id: str) -> None:
        turn_id = self._holds_by_request.pop(request_id, None)
        if turn_id is not None:
            self._permission_holds.pop(turn_id, None)

    # ------------------------------------------------------------------
    # Helpers · used by tests + api.py
    # ------------------------------------------------------------------

    def next_seq(self, turn_id: str) -> int:
        """Return the next monotonic seq for ``turn_id`` · 0 if turn not found."""
        state = self._turns.get(turn_id)
        return state.next_seq() if state else 0

    def get_turn(self, turn_id: str) -> Optional[TurnState]:
        return self._turns.get(turn_id)


# ---------------------------------------------------------------------------
# Process-wide singleton (mirrors decision_ledger.default_ledger pattern)
# ---------------------------------------------------------------------------

_default_orchestrator: Optional[CoworkOrchestrator] = None


def default_orchestrator() -> CoworkOrchestrator:
    """Lazy singleton · one orchestrator per FastAPI worker."""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = CoworkOrchestrator()
    return _default_orchestrator


def set_default_orchestrator(
    orchestrator: Optional[CoworkOrchestrator],
) -> None:
    """Test helper · inject or reset the singleton."""
    global _default_orchestrator
    _default_orchestrator = orchestrator


__all__ = [
    "HEARTBEAT_INTERVAL_SECONDS",
    "CoworkAdapter",
    "CoworkOrchestrator",
    "EmitFn",
    "TurnState",
    "default_orchestrator",
    "set_default_orchestrator",
]
