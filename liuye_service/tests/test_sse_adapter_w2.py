# -*- coding: utf-8 -*-
"""liuye_service.tests.test_sse_adapter_w2 — W2-backend hardening test surface.

Per W2-backend brief §4.3 + matrix v1.1 §3 hidden assumption + W2 第 3 棒.

This module SHADOWS the W1 ``test_sse_adapter.py`` 20-test file (NEVER
mutate it · W1 baseline 20/20 PASS is the regression contract). W2 adds:

1. **_validate_v1_event_shape**: non-mapping / missing 'event' / blank
   event name → ValidationResult(ok=False) with verbatim reason
2. **stress dedup**: 1000 events with overlapping payload hashes →
   no false-positive dedup (canonical_json stable)
3. **percent boundary edge cases**: NaN / Infinity / negative / > 1.0
   / non-numeric → graceful fallback (no exception · no percent key
   when invalid)
4. **_current_tool_call_id inheritance**: tool_call followed by 3+ stage
   events without explicit tool_call_id → all stage events inherit
5. **translator_metrics observability**: events_translated / dedup_skipped
   / failed / unknown_event counters bump correctly

These tests focus on the **W2 contract surface** (hardening + metrics +
edge cases) · not the W1 happy-path mapping (covered by test_sse_adapter).
"""
from __future__ import annotations

import math
from typing import Any, AsyncIterator

import pytest

from liuye_service.adapters.base import reset_seq
from liuye_service.adapters.sse_v1_to_liuye import (
    SseV1ToLiuyeAdapter,
    TranslatorMetrics,
    ValidationResult,
    _validate_v1_event_shape,
)


async def _drain(agen: AsyncIterator[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for evt in agen:
        out.append(evt)
    return out


@pytest.fixture(autouse=True)
def _reset_seq_per_test() -> None:
    reset_seq()


@pytest.fixture
def adapter() -> SseV1ToLiuyeAdapter:
    return SseV1ToLiuyeAdapter(agent_id="channel", trace_id="trace_w2_001")


# ---------------------------------------------------------------------------
# 1. _validate_v1_event_shape · shape contract
# ---------------------------------------------------------------------------


def test_validate_v1_event_shape_happy_path() -> None:
    """Well-formed v1 event passes validation."""
    result = _validate_v1_event_shape({"event": "stage", "stage": "x"})
    assert isinstance(result, ValidationResult)
    assert result.ok is True
    assert result.reason is None


def test_validate_v1_event_shape_non_mapping() -> None:
    """Non-dict input (list / string / None) fails fast."""
    for bad in (None, "stage", ["event", "stage"], 42):
        result = _validate_v1_event_shape(bad)
        assert result.ok is False
        assert result.reason is not None
        assert "not a mapping" in result.reason


def test_validate_v1_event_shape_missing_event() -> None:
    result = _validate_v1_event_shape({"stage": "scoring"})
    assert result.ok is False
    assert result.reason is not None
    assert "missing required 'event' field" in result.reason


def test_validate_v1_event_shape_blank_event_name() -> None:
    """Empty string / whitespace-only event name → invalid."""
    for blank in ("", "   ", "\t"):
        result = _validate_v1_event_shape({"event": blank})
        assert result.ok is False
        assert result.reason is not None
        assert "non-empty string" in result.reason


def test_validate_v1_event_shape_non_string_event() -> None:
    result = _validate_v1_event_shape({"event": 42})
    assert result.ok is False
    assert result.reason is not None
    assert "non-empty string" in result.reason


@pytest.mark.asyncio
async def test_translate_uses_validation_reason_in_envelope(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Validation failure surfaces the reason verbatim in turn.error payload."""
    events = await _drain(adapter.translate({"stage": "x"}, "turn_w2"))
    assert len(events) == 1
    assert events[0]["event"] == "turn.error"
    payload = events[0]["payload"]
    assert payload["code"] == "SSE_ADAPTER_FAILED"
    assert payload["fallback_available"] is True
    # The reason from _validate_v1_event_shape is carried through.
    assert "missing required 'event' field" in payload["message"]


# ---------------------------------------------------------------------------
# 2. Stress dedup · 1000 events, no false positives
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dedup_stress_1000_unique_events(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """1000 unique v1 events MUST all emit · no false-positive dedup.

    Edge case: each event differs only in a numeric field. dedup_key is
    sha256(canonical_json(payload)) so any field change → different key.
    """
    emit_count = 0
    for i in range(1000):
        v1 = {
            "event": "stage",
            "stage": "fetch",
            "progress": i / 1000.0,
            "status": "running",
        }
        events = await _drain(adapter.translate(v1, "turn_stress"))
        emit_count += len(events)
    assert emit_count == 1000, (
        f"dedup false positive · expected 1000 unique events, got {emit_count}"
    )
    # All 1000 events translated · metrics counter agrees.
    assert adapter.translator_metrics.events_translated == 1000
    assert adapter.translator_metrics.dedup_skipped == 0


@pytest.mark.asyncio
async def test_dedup_stress_500_unique_500_duplicates(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """500 unique events + 500 duplicates → exactly 500 emit + 500 skip."""
    for i in range(500):
        v1 = {
            "event": "stage",
            "stage": "rerank",
            "progress": i / 500.0,
            "status": "running",
        }
        # Send each event twice · second one should be deduped.
        await _drain(adapter.translate(v1, "turn_stress"))
        await _drain(adapter.translate(v1, "turn_stress"))
    assert adapter.translator_metrics.events_translated == 500
    assert adapter.translator_metrics.dedup_skipped == 500


# ---------------------------------------------------------------------------
# 3. Percent boundary · NaN / Infinity / negative / > 1.0 / non-numeric
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_percent_negative_clamps_to_zero(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {"event": "stage", "stage": "x", "progress": -0.5, "status": "running"}
    events = await _drain(adapter.translate(v1, "turn_w2"))
    assert len(events) == 1
    # max(0, ...) clamp · negative → 0
    assert events[0]["payload"]["percent"] == 0


@pytest.mark.asyncio
async def test_percent_above_one_clamps_to_hundred(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    v1 = {"event": "stage", "stage": "x", "progress": 1.5, "status": "running"}
    events = await _drain(adapter.translate(v1, "turn_w2"))
    # min(100, ...) clamp · > 1.0 → 100
    assert events[0]["payload"]["percent"] == 100


@pytest.mark.asyncio
async def test_percent_nan_gracefully_dropped(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """NaN progress should not emit a percent key (graceful fallback)."""
    v1 = {"event": "stage", "stage": "x", "progress": math.nan, "status": "running"}
    events = await _drain(adapter.translate(v1, "turn_w2"))
    assert len(events) == 1
    # NaN → int(round()) raises ValueError; caught and stripped.
    assert "percent" not in events[0]["payload"]


@pytest.mark.asyncio
async def test_percent_infinity_gracefully_dropped(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Infinity progress should not emit a percent key (graceful fallback)."""
    v1 = {"event": "stage", "stage": "x", "progress": math.inf, "status": "running"}
    events = await _drain(adapter.translate(v1, "turn_w2"))
    assert len(events) == 1
    # Infinity → int(round()) raises OverflowError; caught and stripped.
    assert "percent" not in events[0]["payload"]


@pytest.mark.asyncio
async def test_percent_non_numeric_dropped(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Non-numeric progress (str/None/list) → no percent key."""
    for bad in ("0.42", None, [0.42], {"value": 0.42}):
        a = SseV1ToLiuyeAdapter(agent_id="channel", trace_id=f"trace_{type(bad).__name__}")
        v1 = {"event": "stage", "stage": "x", "progress": bad, "status": "running"}
        events = await _drain(a.translate(v1, "turn_w2"))
        assert len(events) == 1
        assert "percent" not in events[0]["payload"], (
            f"progress={bad!r} should not produce a percent key"
        )


# ---------------------------------------------------------------------------
# 4. _current_tool_call_id inheritance · 3+ stages after tool_call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_three_stages_inherit_recent_tool_call_id(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Multi-stage inheritance · 3 sequential stage events after tool_call all carry it."""
    v1_tool = {
        "event": "tool_call",
        "tool_call_id": "tc_multistage_001",
        "agent": "channel",
        "tool_id": "signal_search",
        "boundary": "cowork",
        "invoker_id": "rm-test",
        "input": {},
    }
    await _drain(adapter.translate(v1_tool, "turn_inherit"))

    for stage_name, progress in (
        ("fetch", 0.2), ("rerank", 0.5), ("score", 0.8),
    ):
        v1_stage = {
            "event": "stage",
            "stage": stage_name,
            "progress": progress,
            "status": "running",
        }
        events = await _drain(adapter.translate(v1_stage, "turn_inherit"))
        assert len(events) == 1
        assert events[0]["event"] == "tool.progress"
        assert events[0]["tool_call_id"] == "tc_multistage_001", (
            f"stage {stage_name} dropped tool_call_id inheritance"
        )


@pytest.mark.asyncio
async def test_new_tool_call_replaces_inheritance(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Second tool_call MUST replace the inherited id for subsequent stages."""
    await _drain(adapter.translate(
        {"event": "tool_call", "tool_call_id": "tc_first", "tool_id": "x", "input": {}},
        "turn_replace",
    ))
    await _drain(adapter.translate(
        {"event": "tool_call", "tool_call_id": "tc_second", "tool_id": "y", "input": {}},
        "turn_replace",
    ))
    events = await _drain(adapter.translate(
        {"event": "stage", "stage": "after_second", "progress": 0.5, "status": "running"},
        "turn_replace",
    ))
    assert events[0]["tool_call_id"] == "tc_second"


# ---------------------------------------------------------------------------
# 5. translator_metrics observability · counters
# ---------------------------------------------------------------------------


def test_translator_metrics_init_zero(adapter: SseV1ToLiuyeAdapter) -> None:
    """Fresh adapter starts all counters at 0."""
    m = adapter.translator_metrics
    assert isinstance(m, TranslatorMetrics)
    assert m.as_dict() == {
        "events_translated": 0,
        "dedup_skipped": 0,
        "failed": 0,
        "unknown_event": 0,
    }


@pytest.mark.asyncio
async def test_translator_metrics_counts_unknown_event(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Unknown but well-formed v1 event bumps unknown_event counter."""
    await _drain(adapter.translate({"event": "future_event_phase_3"}, "turn_w2"))
    assert adapter.translator_metrics.unknown_event == 1
    assert adapter.translator_metrics.events_translated == 0


@pytest.mark.asyncio
async def test_translator_metrics_counts_validation_failure(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Validation failure bumps failed counter."""
    await _drain(adapter.translate({"stage": "missing_event"}, "turn_w2"))
    assert adapter.translator_metrics.failed == 1
    assert adapter.translator_metrics.events_translated == 0


@pytest.mark.asyncio
async def test_translator_metrics_combined(
    adapter: SseV1ToLiuyeAdapter,
) -> None:
    """Mix of well-formed / duplicate / unknown / invalid · all counters bump."""
    # 1 well-formed
    await _drain(adapter.translate(
        {"event": "stage", "stage": "x", "progress": 0.5, "status": "running"},
        "turn_mix",
    ))
    # 1 duplicate of the above
    await _drain(adapter.translate(
        {"event": "stage", "stage": "x", "progress": 0.5, "status": "running"},
        "turn_mix",
    ))
    # 1 unknown event
    await _drain(adapter.translate({"event": "future_event"}, "turn_mix"))
    # 1 invalid shape
    await _drain(adapter.translate({"stage": "no_event_field"}, "turn_mix"))

    m = adapter.translator_metrics
    assert m.events_translated == 1
    assert m.dedup_skipped == 1
    assert m.unknown_event == 1
    assert m.failed == 1


@pytest.mark.asyncio
async def test_translator_metrics_handler_exception_counts_failed(
    adapter: SseV1ToLiuyeAdapter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Handler raises → failed counter bumps + SSE_ADAPTER_FAILED envelope."""
    async def _bad_handler(v1, turn_id):  # type: ignore[no-untyped-def]
        raise RuntimeError("synthetic handler failure")
        yield  # pragma: no cover · async-gen contract

    monkeypatch.setattr(adapter, "_on_stage", _bad_handler)
    events = await _drain(adapter.translate(
        {"event": "stage", "stage": "x", "progress": 0.5, "status": "running"},
        "turn_handler_fail",
    ))
    assert len(events) == 1
    assert events[0]["event"] == "turn.error"
    assert events[0]["payload"]["code"] == "SSE_ADAPTER_FAILED"
    assert adapter.translator_metrics.failed == 1
