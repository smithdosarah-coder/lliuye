# -*- coding: utf-8 -*-
"""liuye_service.tests.test_sse_adapter — 7 v1 → 11 liuye event mapping.

Per W1-backend brief §5 DoD + ``liuye_service/CLAUDE.md`` §11 (file 17) +
``docs/contracts/liuye-sse-event-matrix.md`` §4 + v3 spec 附录 A.1.

Five test surfaces:

1. **mapping**: 7 SSE v1 events translate to 7 liuye events (+ heartbeat
   passthrough) with the canonical mapping (matrix §4 row 1-8).
2. **dedup**: re-translating the same v1 event yields 0 emitted events.
3. **percent**: v1 progress (0-1 float) → liuye percent (0-100 int) with
   correct boundary handling (0.0 / 0.42 / 1.0).
4. **degraded**: missing required fields → SSE_ADAPTER_FAILED
   ``fallback_available=true`` envelope.
5. **parent_tool_call_id**: passthrough from v1 ``tool_call`` event so
   Cowork→Cowork handoff (Report→Credit per 必修 #51) keeps audit lineage.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from liuye_service.adapters.base import reset_seq
from liuye_service.adapters.sse_v1_to_liuye import (
    SseV1ToLiuyeAdapter,
    _canonical_json,
    _dedup_key,
)


# ---------------------------------------------------------------------------
# Helpers · drain async generator into list (tests are synchronous-ish)
# ---------------------------------------------------------------------------


async def _drain(agen: AsyncIterator[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for evt in agen:
        out.append(evt)
    return out


@pytest.fixture(autouse=True)
def _reset_seq_per_test() -> None:
    """Clear the module-level seq counter so each test starts at seq=1."""
    reset_seq()


@pytest.fixture
def adapter() -> SseV1ToLiuyeAdapter:
    return SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_test_001")


# ---------------------------------------------------------------------------
# 1. Mapping · 7 v1 events → 7 canonical liuye events (+ heartbeat)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mapping_profile_loaded_to_turn_started(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {"event": "profile_loaded", "persona_id": "rm-test", "profile": {"q": "x"}}
    events = await _drain(adapter.translate(v1, "turn_001"))
    assert len(events) == 1
    assert events[0]["event"] == "turn.started"
    assert events[0]["payload"]["persona_id"] == "rm-test"
    assert events[0]["seq"] == 1


@pytest.mark.asyncio
async def test_mapping_stage_to_tool_progress(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {
        "event": "stage",
        "stage": "scoring",
        "message": "评分中",
        "progress": 0.4,
        "status": "running",
    }
    events = await _drain(adapter.translate(v1, "turn_001"))
    assert len(events) == 1
    assert events[0]["event"] == "tool.progress"
    assert events[0]["payload"]["stage_key"] == "scoring"
    assert events[0]["payload"]["percent"] == 40


@pytest.mark.asyncio
async def test_mapping_stream_to_message_created_first_frame_only(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """First v1 stream frame → message.created · subsequent frames suppressed."""
    v1_first = {"event": "stream", "content": "你好", "role": "assistant"}
    v1_more = {"event": "stream", "content": "·客户经理"}
    events_first = await _drain(adapter.translate(v1_first, "turn_001"))
    assert len(events_first) == 1
    assert events_first[0]["event"] == "message.created"
    assert events_first[0]["payload"]["content"] == "你好"
    # Second stream frame · NOT emitted as event (handled as comment).
    events_more = await _drain(adapter.translate(v1_more, "turn_001"))
    assert events_more == [], (
        "Subsequent stream frames must NOT mint new message.created events"
    )


@pytest.mark.asyncio
async def test_mapping_tool_call_to_tool_started(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {
        "event": "tool_call",
        "tool_call_id": "tc_test_001",
        "agent": "credit",
        "tool_id": "credit_decision",
        "boundary": "cowork",
        "invoker_id": "rm-test",
        "input": {"applied_product": "CORP_CREDIT"},
    }
    events = await _drain(adapter.translate(v1, "turn_001"))
    assert len(events) == 1
    assert events[0]["event"] == "tool.started"
    assert events[0]["tool_call_id"] == "tc_test_001"
    assert events[0]["payload"]["tool_id"] == "credit_decision"
    assert events[0]["payload"]["boundary"] == "cowork"


@pytest.mark.asyncio
async def test_mapping_tool_result_to_tool_completed(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {
        "event": "tool_result",
        "tool_call_id": "tc_test_001",
        "artifact_id": "art_001",
        "result": {"verdict": "PASS"},
    }
    events = await _drain(adapter.translate(v1, "turn_001"))
    assert len(events) == 1
    assert events[0]["event"] == "tool.completed"
    assert events[0]["tool_call_id"] == "tc_test_001"
    assert events[0]["artifact_id"] == "art_001"


@pytest.mark.asyncio
async def test_mapping_done_to_turn_completed(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {
        "event": "done",
        "agent": "channel",
        "ok": True,
        "payload": {"candidates": []},
    }
    events = await _drain(adapter.translate(v1, "turn_001"))
    assert len(events) == 1
    assert events[0]["event"] == "turn.completed"
    assert events[0]["payload"]["final_snapshot"]["ok"] is True


@pytest.mark.asyncio
async def test_mapping_error_to_turn_error_9_fields(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """v1 error → liuye turn.error with the strict 9-field payload."""
    v1 = {
        "event": "error",
        "code": "AGENT_TIMEOUT",
        "message": "channel backend exceeded SLA",
        "retryable": True,
    }
    events = await _drain(adapter.translate(v1, "turn_001"))
    assert len(events) == 1
    assert events[0]["event"] == "turn.error"
    payload = events[0]["payload"]
    # Required 9 fields (per TurnErrorPayload v3 §2.1).
    assert payload["code"] == "AGENT_TIMEOUT"
    assert payload["message"] == "channel backend exceeded SLA"
    assert payload["retryable"] is True
    assert payload["trace_id"] == "trace_test_001"
    assert payload["turn_id"] == "turn_001"
    assert "seq" in payload
    assert payload["human_hint"] == "channel backend exceeded SLA"


@pytest.mark.asyncio
async def test_mapping_heartbeat_passthrough(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {"event": "heartbeat"}
    events = await _drain(adapter.translate(v1, "turn_001"))
    assert len(events) == 1
    assert events[0]["event"] == "heartbeat"
    assert events[0]["payload"]["alive"] is True


# ---------------------------------------------------------------------------
# 2. Dedup · re-translate the same v1 event → 0 emit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dedup_same_event_zero_remit(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Re-translating the same v1 envelope MUST NOT emit a second liuye event."""
    v1 = {
        "event": "stage",
        "stage": "fetch",
        "progress": 0.5,
        "status": "running",
    }
    first = await _drain(adapter.translate(v1, "turn_001"))
    second = await _drain(adapter.translate(v1, "turn_001"))
    assert len(first) == 1
    assert second == [], "Dedup violated · duplicate event emitted"


def test_dedup_key_canonical_json_is_stable() -> None:
    """``dedup_key`` is order-insensitive · same payload reordered hashes equal."""
    a = {"event": "stage", "stage": "x", "progress": 0.5}
    b = {"progress": 0.5, "event": "stage", "stage": "x"}
    assert _canonical_json(a) == _canonical_json(b)
    assert _dedup_key("stage", a) == _dedup_key("stage", b)


def test_dedup_key_includes_event_name_in_prefix() -> None:
    """``dedup_key`` is ``"<event>::<sha256>"`` per spec."""
    key = _dedup_key("stage", {"stage": "x", "progress": 0.5})
    assert key.startswith("stage::")
    assert len(key) == len("stage::") + 64  # sha256 hex = 64 chars


# ---------------------------------------------------------------------------
# 3. Percent conversion · 0-1 float → 0-100 int (matrix §3 Q1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_percent_boundary_zero() -> None:
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    v1 = {"event": "stage", "stage": "x", "progress": 0.0, "status": "pending"}
    events = await _drain(adapter.translate(v1, "turn_x"))
    assert events[0]["payload"]["percent"] == 0


@pytest.mark.asyncio
async def test_percent_boundary_one() -> None:
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    v1 = {"event": "stage", "stage": "x", "progress": 1.0, "status": "done"}
    events = await _drain(adapter.translate(v1, "turn_x"))
    assert events[0]["payload"]["percent"] == 100


@pytest.mark.asyncio
async def test_percent_mid_value_42() -> None:
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    v1 = {"event": "stage", "stage": "x", "progress": 0.42, "status": "running"}
    events = await _drain(adapter.translate(v1, "turn_x"))
    assert events[0]["payload"]["percent"] == 42


@pytest.mark.asyncio
async def test_percent_already_int_passthrough() -> None:
    """When v1 already emits 0-100 int (legacy variant), preserve it."""
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    v1 = {"event": "stage", "stage": "x", "percent": 73, "status": "running"}
    events = await _drain(adapter.translate(v1, "turn_x"))
    assert events[0]["payload"]["percent"] == 73


# ---------------------------------------------------------------------------
# 4. Degraded fallback · missing fields → SSE_ADAPTER_FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_degraded_missing_event_field() -> None:
    """v1 envelope missing 'event' MUST produce SSE_ADAPTER_FAILED turn.error."""
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    v1 = {"stage": "no_event_field", "progress": 0.5}
    events = await _drain(adapter.translate(v1, "turn_x"))
    assert len(events) == 1
    payload = events[0]["payload"]
    assert events[0]["event"] == "turn.error"
    assert payload["code"] == "SSE_ADAPTER_FAILED"
    assert payload["fallback_available"] is True


@pytest.mark.asyncio
async def test_degraded_unknown_event_silent_skip() -> None:
    """Unknown but well-formed v1 events MUST be skipped (forward-compat)."""
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    v1 = {"event": "future_event_phase_3"}
    events = await _drain(adapter.translate(v1, "turn_x"))
    assert events == [], (
        "Unknown v1 events must be silently skipped (sse-envelope.md §1.5)"
    )


# ---------------------------------------------------------------------------
# 5. parent_tool_call_id passthrough (Report → Credit handoff · 必修 #51)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_tool_call_id_passthrough() -> None:
    """``parent_tool_call_id`` on v1 tool_call survives to liuye tool.started."""
    adapter = SseV1ToLiuyeAdapter(agent_id="credit", trace_id="trace_x")
    v1 = {
        "event": "tool_call",
        "tool_call_id": "tc_credit_001",
        "agent": "credit",
        "tool_id": "credit_decision",
        "boundary": "cowork",
        "invoker_id": "rm-test",
        "input": {"applied_product": "CORP_CREDIT"},
        # Cross-Cowork handoff · Agent6 Report→Credit (per 必修 #51).
        "parent_tool_call_id": "tc_report_v16_pipeline_001",
    }
    events = await _drain(adapter.translate(v1, "turn_x"))
    assert len(events) == 1
    assert events[0]["event"] == "tool.started"
    assert (
        events[0]["payload"]["parent_tool_call_id"] == "tc_report_v16_pipeline_001"
    ), "parent_tool_call_id dropped during translation · lineage break"


# ---------------------------------------------------------------------------
# 6. Tool-call context inheritance · stage inherits parent tool_call_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_inherits_recent_tool_call_id() -> None:
    """v1 stage events after a tool_call inherit the parent tool_call_id."""
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    v1_tool = {
        "event": "tool_call",
        "tool_call_id": "tc_search_001",
        "agent": "channel",
        "tool_id": "signal_search",
        "boundary": "cowork",
        "invoker_id": "rm-test",
        "input": {},
    }
    v1_stage = {
        "event": "stage",
        "stage": "rerank",
        "progress": 0.8,
        "status": "running",
    }
    await _drain(adapter.translate(v1_tool, "turn_x"))
    events = await _drain(adapter.translate(v1_stage, "turn_x"))
    assert events[0]["event"] == "tool.progress"
    assert events[0]["tool_call_id"] == "tc_search_001"


# ---------------------------------------------------------------------------
# 7. Seq monotonic · all envelopes carry monotonically-increasing seq
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seq_monotonic_across_v1_event_sequence() -> None:
    """Concatenate 4 v1 events → liuye seq starts at 1 and only grows."""
    adapter = SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_x")
    sequence = [
        {"event": "profile_loaded", "persona_id": "rm-test"},
        {
            "event": "tool_call",
            "tool_call_id": "tc_001",
            "tool_id": "x",
            "input": {},
        },
        {"event": "stage", "stage": "y", "progress": 0.5, "status": "running"},
        {
            "event": "tool_result",
            "tool_call_id": "tc_001",
            "result": {"ok": True},
        },
    ]
    seqs: list[int] = []
    for v1 in sequence:
        for evt in await _drain(adapter.translate(v1, "turn_seq")):
            seqs.append(evt["seq"])
    assert seqs == sorted(set(seqs)), "seq must be strictly increasing"
    assert seqs[0] == 1
