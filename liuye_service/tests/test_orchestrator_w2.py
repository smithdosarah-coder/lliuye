# -*- coding: utf-8 -*-
"""liuye_service.tests.test_orchestrator_w2 — per-turn asyncio.Queue + permission hold tests.

Per W2-backend brief §4.7 + ``liuye_service/CLAUDE.md`` §3 + v3 §2.1.

Test surfaces (W1 orchestrator was a skeleton · this is the W2 wire-up
verification + backpressure + permission-hold integration):

1. **start_turn → TurnState minted** with seq=0 / parent_turn_id forward.
2. **next_seq monotonic** per turn_id.
3. **get_or_create_sse_queue** is idempotent · maxsize=256 enforced.
4. **close_sse_queue** pushes None sentinel · pop drops state.
5. **register_permission_hold** parks the turn · holds_by_request reverse lookup.
6. **dispatch_message suppressed during hold** (per matrix §3 Q2).
7. **resume_turn clears the hold** + leaves turn open.
8. **abort_turn closes the turn + queue sentinel + holds cleared**.
9. **adapter dispatch raises** → orchestrator aborts gracefully.
10. **Cross-mode parent_turn_id** preserved through start_turn.
11. **backpressure**: full queue blocks producer until consumer drains.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Mapping, Optional

import pytest

from liuye_service.orchestrator import (
    CoworkOrchestrator,
    HEARTBEAT_INTERVAL_SECONDS,
    TurnState,
    set_default_orchestrator,
)
from liuye_service.schemas import PermissionRequest


@pytest.fixture
def orch() -> CoworkOrchestrator:
    """Provide a fresh CoworkOrchestrator · cleared default after test."""
    instance = CoworkOrchestrator()
    yield instance
    set_default_orchestrator(None)


# ---------------------------------------------------------------------------
# 1. start_turn · TurnState minted · seq=0 · parent_turn_id forward
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_turn_mints_turn_id_and_state(orch: CoworkOrchestrator) -> None:
    turn_id = await orch.start_turn(
        persona="rm",
        agent_id="credit",
        trace_id="trace_t1",
        payload={"q": "x"},
    )
    assert turn_id.startswith("turn_")
    state = orch.get_turn(turn_id)
    assert state is not None
    assert state.persona == "rm"
    assert state.agent_id == "credit"
    assert state.trace_id == "trace_t1"
    assert state.seq == 0
    assert state.closed is False
    assert state.parent_turn_id is None


@pytest.mark.asyncio
async def test_start_turn_carries_parent_turn_id(orch: CoworkOrchestrator) -> None:
    """parent_turn_id (cross-mode link · v1.1 schema) survives start_turn."""
    turn_id = await orch.start_turn(
        persona="rm",
        agent_id="credit",
        trace_id="trace_t2",
        payload={},
        parent_turn_id="turn_parent_001",
    )
    state = orch.get_turn(turn_id)
    assert state is not None
    assert state.parent_turn_id == "turn_parent_001"


# ---------------------------------------------------------------------------
# 2. next_seq monotonic per turn_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_next_seq_monotonic_per_turn(orch: CoworkOrchestrator) -> None:
    t1 = await orch.start_turn(
        persona="rm", agent_id="credit", trace_id="trace_a", payload={},
    )
    t2 = await orch.start_turn(
        persona="rm", agent_id="report", trace_id="trace_b", payload={},
    )
    seqs_t1 = [orch.next_seq(t1) for _ in range(3)]
    seqs_t2 = [orch.next_seq(t2) for _ in range(2)]
    assert seqs_t1 == [1, 2, 3]
    assert seqs_t2 == [1, 2]


def test_next_seq_unknown_turn_returns_zero(orch: CoworkOrchestrator) -> None:
    """next_seq on unknown turn_id returns 0 · safe noop."""
    assert orch.next_seq("turn_does_not_exist") == 0


# ---------------------------------------------------------------------------
# 3. get_or_create_sse_queue · idempotent · maxsize=256 enforced
# ---------------------------------------------------------------------------


def test_get_or_create_sse_queue_idempotent(orch: CoworkOrchestrator) -> None:
    q1 = orch.get_or_create_sse_queue("turn_q1")
    q2 = orch.get_or_create_sse_queue("turn_q1")
    assert q1 is q2, "second call must return the same queue instance"


def test_get_or_create_sse_queue_maxsize_default_256(orch: CoworkOrchestrator) -> None:
    """Default queue maxsize matches the W2 brief (256 frames)."""
    q = orch.get_or_create_sse_queue("turn_q2")
    assert q.maxsize == 256


def test_get_or_create_sse_queue_custom_maxsize(orch: CoworkOrchestrator) -> None:
    q = orch.get_or_create_sse_queue("turn_q3", maxsize=8)
    assert q.maxsize == 8


# ---------------------------------------------------------------------------
# 4. close_sse_queue · None sentinel pushed · state dropped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_sse_queue_pushes_none_sentinel(
    orch: CoworkOrchestrator,
) -> None:
    """close_sse_queue pushes ``None`` so the consumer exits cleanly."""
    q = orch.get_or_create_sse_queue("turn_close_001")
    orch.close_sse_queue("turn_close_001")
    item = await asyncio.wait_for(q.get(), timeout=1.0)
    assert item is None, "expected None sentinel from close_sse_queue"


def test_close_sse_queue_drops_internal_state(orch: CoworkOrchestrator) -> None:
    orch.get_or_create_sse_queue("turn_close_002")
    orch.close_sse_queue("turn_close_002")
    # Next get_or_create on same id returns a fresh queue.
    new_q = orch.get_or_create_sse_queue("turn_close_002")
    assert new_q.empty()


def test_close_sse_queue_unknown_turn_safe(orch: CoworkOrchestrator) -> None:
    """close_sse_queue on unknown turn_id is a no-op · no exception."""
    orch.close_sse_queue("turn_never_created")  # Should not raise


# ---------------------------------------------------------------------------
# 5. register_permission_hold + reverse-lookup index
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_permission_hold_parks_turn(
    orch: CoworkOrchestrator,
) -> None:
    turn_id = await orch.start_turn(
        persona="rm", agent_id="credit", trace_id="trace_h1", payload={},
    )
    req = PermissionRequest(
        id="req_hold_001",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_hold_001",
        turn_id=turn_id,
    )
    await orch.register_permission_hold(req)
    state = orch.get_turn(turn_id)
    assert state is not None
    assert state.held_by_permission == "req_hold_001"
    # Reverse lookup works.
    found = orch.get_permission_hold("req_hold_001")
    assert found is not None
    assert found.id == "req_hold_001"


@pytest.mark.asyncio
async def test_register_permission_hold_missing_turn_id_safe(
    orch: CoworkOrchestrator,
) -> None:
    """Defence in depth · request without turn_id is logged + skipped."""
    req = PermissionRequest(
        id="req_no_turn",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_x",
        turn_id=None,
    )
    await orch.register_permission_hold(req)  # No raise
    assert orch.get_permission_hold("req_no_turn") is None


@pytest.mark.asyncio
async def test_register_permission_hold_unknown_turn_id_safe(
    orch: CoworkOrchestrator,
) -> None:
    """Hold on an unknown turn_id is logged + skipped (no crash)."""
    req = PermissionRequest(
        id="req_unknown_turn",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_y",
        turn_id="turn_does_not_exist",
    )
    await orch.register_permission_hold(req)
    assert orch.get_permission_hold("req_unknown_turn") is None


# ---------------------------------------------------------------------------
# 6. dispatch_message suppressed during hold · per matrix §3 Q2
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_message_suppressed_when_held(
    orch: CoworkOrchestrator,
) -> None:
    """Business events MUST be suppressed while a permission hold is active."""
    turn_id = await orch.start_turn(
        persona="rm", agent_id="credit", trace_id="trace_s1", payload={},
    )

    class _Adapter:
        agent_id = "credit"
        dispatched: list[Any] = []

        async def dispatch_message(
            self, turn_id: str, message: Mapping[str, Any],
        ) -> AsyncIterator[dict[str, Any]]:
            self.dispatched.append((turn_id, dict(message)))
            yield {"event": "message.created", "payload": {"content": "hi"}}

    adapter = _Adapter()
    orch.register_adapter(adapter)

    # Park the turn behind a permission request.
    req = PermissionRequest(
        id="req_s1",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_s1",
        turn_id=turn_id,
    )
    await orch.register_permission_hold(req)

    emitted: list[dict[str, Any]] = []

    async def fake_emit(**kwargs: Any) -> None:
        emitted.append(kwargs)

    await orch.dispatch_message(
        turn_id=turn_id, message={"hello": "world"}, emit=fake_emit,
    )
    assert _Adapter.dispatched == [], (
        "adapter MUST NOT receive dispatch_message while turn is held"
    )
    assert emitted == []


# ---------------------------------------------------------------------------
# 7. resume_turn clears the hold · turn still open
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_turn_clears_hold(orch: CoworkOrchestrator) -> None:
    turn_id = await orch.start_turn(
        persona="rm", agent_id="credit", trace_id="trace_r1", payload={},
    )
    req = PermissionRequest(
        id="req_resume_001",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_r1",
        turn_id=turn_id,
    )
    await orch.register_permission_hold(req)
    state = orch.get_turn(turn_id)
    assert state is not None
    assert state.held_by_permission == "req_resume_001"

    ok = await orch.resume_turn(turn_id, after_permission=req)
    assert ok is True
    # Hold cleared but turn still open.
    assert state.held_by_permission is None
    assert state.closed is False


@pytest.mark.asyncio
async def test_resume_turn_unknown_turn_returns_false(
    orch: CoworkOrchestrator,
) -> None:
    req = PermissionRequest(
        id="r_x",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_x",
        turn_id="turn_unknown",
    )
    ok = await orch.resume_turn("turn_unknown", after_permission=req)
    assert ok is False


# ---------------------------------------------------------------------------
# 8. abort_turn closes turn + queue sentinel + hold cleared
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abort_turn_closes_and_pushes_sentinel(
    orch: CoworkOrchestrator,
) -> None:
    turn_id = await orch.start_turn(
        persona="rm", agent_id="credit", trace_id="trace_a1", payload={},
    )
    q = orch.get_or_create_sse_queue(turn_id)

    # Park behind a permission so abort_turn clears hold too.
    req = PermissionRequest(
        id="req_abort_001",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_abort_001",
        turn_id=turn_id,
    )
    await orch.register_permission_hold(req)

    ok = await orch.abort_turn(turn_id, reason="user cancel", code="PERMISSION_DENIED")
    assert ok is True
    state = orch.get_turn(turn_id)
    assert state is not None
    assert state.closed is True
    assert state.held_by_permission is None

    # Queue closed · None sentinel observable.
    item = await asyncio.wait_for(q.get(), timeout=1.0)
    assert item is None


@pytest.mark.asyncio
async def test_abort_turn_unknown_turn_returns_false(
    orch: CoworkOrchestrator,
) -> None:
    ok = await orch.abort_turn("turn_never", reason="x")
    assert ok is False


# ---------------------------------------------------------------------------
# 9. Adapter dispatch raises → graceful abort + ADAPTER_DISPATCH_FAILED code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_dispatch_message_raises_triggers_abort(
    orch: CoworkOrchestrator,
) -> None:
    """Adapter exception during AsyncIterator dispatch → orchestrator aborts."""

    class _BadAdapter:
        agent_id = "credit"

        async def dispatch_message(
            self, turn_id: str, message: Mapping[str, Any],
        ) -> AsyncIterator[dict[str, Any]]:
            raise RuntimeError("synthetic adapter failure")
            yield  # pragma: no cover · async-gen contract

    orch.register_adapter(_BadAdapter())
    turn_id = await orch.start_turn(
        persona="rm", agent_id="credit", trace_id="trace_bad", payload={},
    )

    emitted: list[dict[str, Any]] = []

    async def fake_emit(**kwargs: Any) -> None:
        emitted.append(kwargs)

    await orch.dispatch_message(
        turn_id=turn_id, message={"x": 1}, emit=fake_emit,
    )
    state = orch.get_turn(turn_id)
    assert state is not None
    assert state.closed is True, "turn must be closed after adapter exception"


# ---------------------------------------------------------------------------
# 10. Backpressure · bounded queue blocks producer until consumer drains
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backpressure_bounded_queue_blocks_producer() -> None:
    """When queue is full, ``put`` awaits · ``get`` unblocks immediately.

    This is the canonical backpressure shape · producer (adapter) cannot
    overrun consumer (SSE endpoint) without bound.
    """
    orch = CoworkOrchestrator()
    q = orch.get_or_create_sse_queue("turn_bp", maxsize=2)
    await q.put({"event": "e1"})
    await q.put({"event": "e2"})
    assert q.full()

    # Schedule a put · it blocks until consumer drains.
    put_done = asyncio.Event()

    async def producer() -> None:
        await q.put({"event": "e3"})
        put_done.set()

    task = asyncio.create_task(producer())
    # Brief wait · should still be blocked.
    await asyncio.sleep(0.01)
    assert not put_done.is_set()
    # Consumer drains one frame · producer unblocks.
    await q.get()
    await asyncio.wait_for(put_done.wait(), timeout=1.0)
    await task


# ---------------------------------------------------------------------------
# 11. HEARTBEAT_INTERVAL_SECONDS pin · 15s (matrix §3 Q3)
# ---------------------------------------------------------------------------


def test_heartbeat_interval_pinned_to_15s() -> None:
    """Client declares dead after 30s · we tick at 15s · matrix §3 Q3 ratify."""
    assert HEARTBEAT_INTERVAL_SECONDS == 15.0
