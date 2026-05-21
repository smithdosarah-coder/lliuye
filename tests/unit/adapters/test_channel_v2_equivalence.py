# -*- coding: utf-8 -*-
"""Byte-equivalence tests · ``ChannelAdapterV2`` vs legacy ``ChannelAdapter``.

Per ROI #2 Step 2 影子改写 acceptance (Codex R2 R2.1 第1条):

> "ROI#2:现在不直切 prod;可派生影子改写。base 门禁只证明基类,非
>  channel 门禁;prod risk 中高。"

V1 (``channel.py``) and V2 (``channel_v2.py``) MUST produce **identical**
SSE liuye event streams for the same input. Any frame-level diff blocks
the V1→V2 switchover.

Scope:

1. Demo-mode frame synthesis  · ``_synthesise_channel_v1_frames`` is
   called by both (V2 delegates) · proves the demo path is
   bit-identical.
2. Demo-mode end-to-end       · stream through ``start_turn`` for both;
   compare every translated liuye event.
3. Live-mode end-to-end       · same mock transport feeds both V1 + V2;
   compare every translated liuye event + the captured wire body.
4. Error envelopes            · ``_adapter_error`` shape parity (human
   hint label = "获客" for both).

Out of scope (covered by ``test_cowork_base.py``):

- Base-class ``__init_subclass__`` validation
- ``FORWARDS_PARENT_TOOL_CALL_ID`` branch for the True case (channel is
  False; credit/report cover True)
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterable, Mapping

import httpx
import pytest

from liuye_service.adapters.channel import ChannelAdapter
from liuye_service.adapters.channel_v2 import ChannelAdapterV2


# ---------------------------------------------------------------------------
# Helpers · fixture-free utilities used by all tests below
# ---------------------------------------------------------------------------


def _strip_volatile(evt: Mapping[str, Any]) -> dict[str, Any]:
    """Remove non-deterministic fields before comparison.

    Liuye envelopes include a ``ts`` (timestamp) field minted at
    emission time. Two adapters running back-to-back will produce
    different timestamps even when behaviour is identical. We compare
    the rest of the envelope shape.

    ``seq`` is also stripped: ``_make_seq`` is a module-level counter
    keyed by ``turn_id`` — running V1 first and V2 second in the same
    process consumes the counter, so V2's seq numbers are higher even
    though both adapters mint them via the same helper. The seq
    contract (monotonic per turn) is covered by other tests.
    """
    out = dict(evt)
    out.pop("ts", None)
    if "payload" in out and isinstance(out["payload"], Mapping):
        payload = dict(out["payload"])
        payload.pop("seq", None)
        # Some error envelopes also echo ts inside payload — strip if present.
        payload.pop("ts", None)
        out["payload"] = payload
    out.pop("seq", None)
    return out


async def _collect(stream: AsyncIterator[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drain an async iterator into a list."""
    return [evt async for evt in stream]


def _assert_streams_equivalent(
    v1_events: Iterable[Mapping[str, Any]],
    v2_events: Iterable[Mapping[str, Any]],
    *,
    context: str,
) -> None:
    """Frame-by-frame equality (modulo volatile ts/seq)."""
    v1_list = [_strip_volatile(e) for e in v1_events]
    v2_list = [_strip_volatile(e) for e in v2_events]
    assert len(v1_list) == len(v2_list), (
        f"[{context}] event count diverged · V1={len(v1_list)} V2={len(v2_list)}\n"
        f"V1 events: {[e.get('event') for e in v1_list]}\n"
        f"V2 events: {[e.get('event') for e in v2_list]}"
    )
    for idx, (a, b) in enumerate(zip(v1_list, v2_list)):
        assert a == b, (
            f"[{context}] frame #{idx} diverged\n"
            f"V1: {json.dumps(a, ensure_ascii=False, sort_keys=True)}\n"
            f"V2: {json.dumps(b, ensure_ascii=False, sort_keys=True)}"
        )


# ---------------------------------------------------------------------------
# 1. Demo-mode frame synthesis (pure function · no I/O)
# ---------------------------------------------------------------------------


async def test_demo_frame_sequence_byte_equivalent() -> None:
    """V1's ``_synthesise_channel_v1_frames`` and V2's hook return identical lists.

    V2's hook delegates to the same function, so this is structurally a
    tautology; we still pin it so any future divergence (someone
    forking the synthesiser into V2) fails loudly.
    """
    from liuye_service.adapters.channel import _synthesise_channel_v1_frames

    snapshot = {
        "seed": {
            "search_intent": "对公拓客 · 新能源汽车零部件",
            "seed_industry_code": "C36",
        },
        "candidates": [
            {"rank": 1, "candidate_id": "c1", "difficulty_tier": "简单"},
            {"rank": 2, "candidate_id": "c2", "difficulty_tier": "中等"},
        ],
        "summary": {"total": 2},
    }
    persona_id = "rm-wangzhe-east"
    artifact_id = "art_channel_demo"

    v1_frames = _synthesise_channel_v1_frames(
        snapshot=snapshot, artifact_id=artifact_id, persona_id=persona_id,
    )

    v2_adapter = ChannelAdapterV2()
    v2_frames = await v2_adapter._synthesise_demo_v1_frames(
        snapshot=snapshot,
        artifact_id=artifact_id,
        persona_id=persona_id,
        payload={"persona_id": persona_id},
    )

    assert v1_frames == v2_frames, (
        "V2 hook diverged from V1's _synthesise_channel_v1_frames\n"
        f"V1: {v1_frames}\nV2: {v2_frames}"
    )


# ---------------------------------------------------------------------------
# 2. Demo-mode end-to-end through start_turn
# ---------------------------------------------------------------------------


@pytest.fixture
def force_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Toggle ``LIUYE_DEMO_MODE`` via the settings cache used by both adapters."""
    # Both V1 (channel.py) and V2 (via cowork_base) call get_settings().
    # We patch the module-level lookup in BOTH places so V1 and V2 see
    # the same flag.
    class _Settings:
        demo_mode = True
        ledger_jurisdiction = "CN"
        fixtures_path = "tests/fixtures"

        def resolve_backend_url(self, agent_id: str) -> str:
            return "http://unused-in-demo"

    settings = _Settings()
    monkeypatch.setattr(
        "liuye_service.adapters.channel.get_settings", lambda: settings,
    )
    monkeypatch.setattr(
        "liuye_service.adapters.cowork_base.get_settings", lambda: settings,
    )


async def test_demo_mode_end_to_end_byte_equivalent(
    force_demo_mode: None,
) -> None:
    """Drive V1 + V2 through ``start_turn`` in demo mode · compare streams.

    Uses the real ``channel_5candidates.json`` fixture so we exercise
    the full demo path (load_fixture → synthesise → translator). The
    SseV1ToLiuyeAdapter is the real class — V1 and V2 share it.
    """
    payload = {
        "trace_id": "trace_eq_demo",
        "persona_id": "rm-wangzhe-east",
    }

    v1 = ChannelAdapter()
    v1_events = await _collect(
        v1.start_turn(turn_id="turn_eq_demo_v1", persona="审贷员", payload=payload),
    )

    v2 = ChannelAdapterV2()
    v2_events = await _collect(
        v2.start_turn(turn_id="turn_eq_demo_v2", persona="审贷员", payload=payload),
    )

    # turn_id is stamped onto every envelope · normalise so structural
    # equality survives the different turn ids we used above.
    def _normalize_turn_id(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for e in events:
            ne = dict(e)
            ne["turn_id"] = "NORMALIZED"
            if "payload" in ne and isinstance(ne["payload"], Mapping):
                p = dict(ne["payload"])
                if "turn_id" in p:
                    p["turn_id"] = "NORMALIZED"
                ne["payload"] = p
            out.append(ne)
        return out

    _assert_streams_equivalent(
        _normalize_turn_id(v1_events),
        _normalize_turn_id(v2_events),
        context="demo_mode_end_to_end",
    )


# ---------------------------------------------------------------------------
# 3. Live-mode end-to-end · same MockTransport feeds V1 + V2
# ---------------------------------------------------------------------------


_SSE_BODY_LINES = (
    "event: profile_loaded",
    'data: {"event": "profile_loaded", "persona_id": "rm-wangzhe-east", "profile": {"seed_industry_code": "C36"}}',
    "",
    "event: tool_call",
    'data: {"event": "tool_call", "tool_call_id": "tc_live", "agent": "channel", "tool_id": "signal_search", "boundary": "cowork", "invoker_id": "rm-wangzhe-east", "input": {}}',
    "",
    "event: stage",
    'data: {"event": "stage", "stage": "enterprise_search", "message": "lookup", "progress": 0.5, "stage_index": 1, "stage_total": 2, "status": "running"}',
    "",
    "event: tool_result",
    'data: {"event": "tool_result", "tool_call_id": "tc_live", "artifact_id": "art_live", "result": {"candidates": []}}',
    "",
    "event: done",
    'data: {"event": "done", "agent": "channel", "ok": true, "payload": {"candidates": [], "data_source": "live"}}',
    "",
)


def _build_mock_client(captured: dict[str, Any]) -> httpx.AsyncClient:
    """Mock transport that captures the wire body and returns canned SSE."""

    def _handler(request: httpx.Request) -> httpx.Response:
        captured.setdefault("requests", []).append({
            "method": request.method,
            "url": str(request.url),
            "body": json.loads(request.content.decode("utf-8")),
        })
        body = "\n".join(_SSE_BODY_LINES) + "\n"
        return httpx.Response(
            200,
            content=body.encode("utf-8"),
            headers={"content-type": "text/event-stream"},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(_handler))


@pytest.fixture
def force_live_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """``demo_mode = False`` for both channel and cowork_base lookups."""

    class _Settings:
        demo_mode = False
        ledger_jurisdiction = "CN"
        fixtures_path = "tests/fixtures"

        def resolve_backend_url(self, agent_id: str) -> str:
            # Returned URL is irrelevant — both adapters short-circuit
            # to ``self.backend_url`` when constructor injection occurs
            # (we inject a different URL below).
            return "http://env-resolved:9999"

    settings = _Settings()
    monkeypatch.setattr(
        "liuye_service.adapters.channel.get_settings", lambda: settings,
    )
    monkeypatch.setattr(
        "liuye_service.adapters.cowork_base.get_settings", lambda: settings,
    )


async def test_live_mode_end_to_end_byte_equivalent(
    force_live_mode: None,
) -> None:
    """Drive V1 + V2 against the same MockTransport · compare streams + bodies."""
    payload = {
        "trace_id": "trace_eq_live",
        "persona_id": "rm-wangzhe-east",
        "snapshot": {"seed_industry_code": "C36"},
    }

    # V1 run
    v1_captured: dict[str, Any] = {}
    v1_client = _build_mock_client(v1_captured)
    # backend_url MUST differ from the legacy default so the override
    # branch in _resolve_backend_url is taken — same behaviour for V2.
    v1 = ChannelAdapter(backend_url="http://mock-v1:8001", http_client=v1_client)
    v1_events = await _collect(
        v1.start_turn(turn_id="turn_eq_live_v1", persona="审贷员", payload=payload),
    )
    await v1_client.aclose()

    # V2 run
    v2_captured: dict[str, Any] = {}
    v2_client = _build_mock_client(v2_captured)
    v2 = ChannelAdapterV2(backend_url="http://mock-v2:8001", http_client=v2_client)
    v2_events = await _collect(
        v2.start_turn(turn_id="turn_eq_live_v2", persona="审贷员", payload=payload),
    )
    await v2_client.aclose()

    # Wire body equivalence (modulo trace_id / turn_id substitution)
    assert v1_captured["requests"][0]["method"] == v2_captured["requests"][0]["method"]
    # URLs differ only in the host we injected
    assert v1_captured["requests"][0]["url"].endswith("/api/channel/run")
    assert v2_captured["requests"][0]["url"].endswith("/api/channel/run")

    v1_body = dict(v1_captured["requests"][0]["body"])
    v2_body = dict(v2_captured["requests"][0]["body"])
    # turn_id differs between the two runs · normalise
    v1_body["turn_id"] = "NORMALIZED"
    v2_body["turn_id"] = "NORMALIZED"
    assert v1_body == v2_body, (
        f"wire body diverged\nV1: {v1_body}\nV2: {v2_body}"
    )

    # SSE stream equivalence
    def _normalize_turn_id(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for e in events:
            ne = dict(e)
            ne["turn_id"] = "NORMALIZED"
            if "payload" in ne and isinstance(ne["payload"], Mapping):
                p = dict(ne["payload"])
                if "turn_id" in p:
                    p["turn_id"] = "NORMALIZED"
                ne["payload"] = p
            out.append(ne)
        return out

    _assert_streams_equivalent(
        _normalize_turn_id(v1_events),
        _normalize_turn_id(v2_events),
        context="live_mode_end_to_end",
    )


# ---------------------------------------------------------------------------
# 4. Adapter error envelope parity (human hint label = "获客")
# ---------------------------------------------------------------------------


def test_adapter_error_envelope_parity() -> None:
    """V1 and V2 produce identical ``turn.error`` envelopes (modulo seq)."""
    v1 = ChannelAdapter()
    v2 = ChannelAdapterV2()

    err_v1 = v1._adapter_error(
        turn_id="turn_err",
        trace_id="trace_err",
        code="ADAPTER_TIMEOUT",
        message="channel backend exceeded SLA · backend_url=http://localhost:8001",
    )
    err_v2 = v2._adapter_error(
        turn_id="turn_err",
        trace_id="trace_err",
        code="ADAPTER_TIMEOUT",
        message="channel backend exceeded SLA · backend_url=http://localhost:8001",
    )

    assert _strip_volatile(err_v1) == _strip_volatile(err_v2), (
        f"error envelope diverged\nV1: {err_v1}\nV2: {err_v2}"
    )
    # Spot-check the human hint label is "获客" for both
    assert "获客" in err_v1["payload"]["human_hint"]
    assert "获客" in err_v2["payload"]["human_hint"]


def test_classvars_match_v1_constants() -> None:
    """V2 ClassVar values must equal V1's module-level constants.

    Pins the 8 values so a future channel.py constant change doesn't
    silently drift from V2 (would break byte-equivalence in prod
    without surfacing here).
    """
    from liuye_service.adapters import channel as v1mod

    assert ChannelAdapterV2.AGENT_ID == v1mod.CHANNEL_AGENT_ID == "channel"
    assert ChannelAdapterV2.BACKEND_URL_DEFAULT == v1mod.CHANNEL_BACKEND_URL_DEFAULT
    assert ChannelAdapterV2.ENDPOINT_PATH == v1mod.CHANNEL_ENDPOINT == "/api/channel/run"
    assert ChannelAdapterV2.HTTP_TIMEOUT.read == v1mod.HTTP_TIMEOUT.read == 30.0
    assert ChannelAdapterV2.HTTP_TIMEOUT.connect == v1mod.HTTP_TIMEOUT.connect == 5.0
    assert ChannelAdapterV2.DEMO_FIXTURE_STEM == v1mod.DEMO_FIXTURE_STEM == "channel_5candidates"
    assert ChannelAdapterV2.RETENTION_CLASS == "short"
    assert ChannelAdapterV2.HUMAN_HINT_AGENT_LABEL == "获客"
    assert ChannelAdapterV2.FORWARDS_PARENT_TOOL_CALL_ID is False
