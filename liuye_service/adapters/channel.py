# -*- coding: utf-8 -*-
"""liuye_service.adapters.channel — Agent1 (Channel · 获客) Cowork adapter.

Per W1-backend brief §3 file 10 + ``liuye_service/CLAUDE.md`` §3 + §4 +
``docs/contracts/liuye-sse-event-matrix.md`` §2.1 + root §3.1.1.

Cowork SSE adapter for the old ``agent_channel`` backend
(``POST /api/channel/run``). HTTP-only contract — never imports
``agent_channel.*`` internal modules (CLAUDE.md §2.3 hardline).

Live flow:

    BFF ──── POST /api/channel/run ───────> agent_channel
                                                │
    BFF <───── SSE v1 stream <──────────────────┘
       │
       ├── SseV1ToLiuyeAdapter.translate(v1 event)
       │
       ▼
    emit(liuye event)  ────> orchestrator SSE bridge ────> frontend

DEMO_MODE flow (when ``LIUYE_DEMO_MODE=true``):

    BFF ──── load_fixture("channel_5candidates") ──> synthesise v1 frames
       │
       ├── feed through SseV1ToLiuyeAdapter
       │
       ▼
    same emit() pipeline as live

SLA: Cowork < 5s p95 (root §3.1.1). Timeout → ``turn.error
code=ADAPTER_TIMEOUT fallback_available=true``. The backend HTTP call
is wrapped in ``httpx.AsyncClient`` with a 5s connect / 30s read
timeout (read > sla because v16 report can run 30s SSE per matrix §2.3).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Mapping, Optional

import httpx

from liuye_service.adapters.base import (
    AgentAdapter,
    envelope,
    load_fixture,
    FixtureLoadError,
    _make_seq,
)
from liuye_service.adapters.sse_v1_to_liuye import SseV1ToLiuyeAdapter
from liuye_service.audit import record_liuye_decision
from liuye_service.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants · centralized so a config tweak doesn't ripple to other adapters
# ---------------------------------------------------------------------------

CHANNEL_AGENT_ID = "channel"
CHANNEL_ENDPOINT = "/api/channel/run"
CHANNEL_BACKEND_URL_DEFAULT = "http://localhost:8001"  # mock-test worker port

# Cowork SLA per root §3.1.1: p95 < 5s. We give a 5s connect deadline and
# 30s read deadline (long-poll headroom for stage-by-stage SSE).
HTTP_TIMEOUT = httpx.Timeout(5.0, read=30.0)

# DEMO_MODE fixture stem (W1-mock-test SSOT).
DEMO_FIXTURE_STEM = "channel_5candidates"


class ChannelAdapter:
    """Cowork SSE adapter for the channel (Agent1) backend.

    Conforms to ``AgentAdapter`` Protocol. Wraps:

    - ``httpx.AsyncClient`` for the live POST + SSE stream
    - ``SseV1ToLiuyeAdapter`` to translate v1 frames into liuye events
    - ``shared.decision_ledger`` (via ``audit.record_liuye_decision``)
      to drop a ``ledger_decision`` row when the turn completes
    """

    agent_id = CHANNEL_AGENT_ID
    boundary = "cowork"

    def __init__(
        self,
        *,
        backend_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.backend_url = backend_url or CHANNEL_BACKEND_URL_DEFAULT
        # Tests can inject a transport-mocked client · production
        # instantiates lazily inside the request to keep startup fast.
        self._http_client = http_client
        # Per-turn translator instances · we discard on turn end.
        self._translators: dict[str, SseV1ToLiuyeAdapter] = {}

    # ------------------------------------------------------------------
    # AgentAdapter Protocol surface
    # ------------------------------------------------------------------

    async def start_turn(
        self,
        turn_id: str,
        persona: str,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Initiate the channel turn · emit ``turn.started`` then stream."""
        trace_id = payload.get("trace_id") or "trace_unknown"
        self._translators[turn_id] = SseV1ToLiuyeAdapter(
            agent_id=self.agent_id, trace_id=trace_id,
        )
        # We do NOT emit ``turn.started`` here · the SSE bridge in
        # ``api.py`` already mints one. The first v1 ``profile_loaded``
        # would also produce one but we dedup downstream.
        async for evt in self._run(turn_id=turn_id, payload=payload, trace_id=trace_id):
            yield evt

    async def dispatch_message(
        self,
        turn_id: str,
        message: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Push a user follow-up message into an already-started channel turn."""
        translator = self._translators.get(turn_id)
        if translator is None:
            # The orchestrator should have called start_turn first · bail.
            yield self._adapter_error(
                turn_id,
                trace_id=message.get("trace_id") or "trace_unknown",
                code="TURN_NOT_STARTED",
                message=f"channel adapter has no translator for turn_id={turn_id}",
            )
            return
        async for evt in self._run(
            turn_id=turn_id,
            payload=message,
            trace_id=translator.trace_id,
        ):
            yield evt

    async def abort_turn(self, turn_id: str, reason: str) -> None:
        """Best-effort teardown · close httpx + drop translator state."""
        translator = self._translators.pop(turn_id, None)
        if translator is None:
            return
        logger.info(
            "[channel_adapter] abort_turn turn_id=%s reason=%s", turn_id, reason,
        )

    # ------------------------------------------------------------------
    # Core dispatch · live or demo mode
    # ------------------------------------------------------------------

    async def _run(
        self,
        *,
        turn_id: str,
        payload: Mapping[str, Any],
        trace_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the channel turn · DEMO_MODE replay or live HTTP."""
        translator = self._translators.get(turn_id) or SseV1ToLiuyeAdapter(
            agent_id=self.agent_id, trace_id=trace_id,
        )
        self._translators[turn_id] = translator

        if get_settings().demo_mode:
            async for evt in self._run_demo(
                turn_id=turn_id, translator=translator, payload=payload,
            ):
                yield evt
            return

        try:
            async for evt in self._run_live(
                turn_id=turn_id, translator=translator, payload=payload,
            ):
                yield evt
        except asyncio.TimeoutError:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_TIMEOUT",
                message=f"channel backend exceeded SLA · backend_url={self.backend_url}",
            )
        except httpx.HTTPError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_HTTP_ERROR",
                message=f"channel HTTP error: {exc}",
            )

    async def _run_demo(
        self,
        *,
        turn_id: str,
        translator: SseV1ToLiuyeAdapter,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay the W1-mock-test fixture as v1 frames · translate to liuye.

        The fixture file is an *Artifact* snapshot (see
        ``tests/fixtures/channel_5candidates.json``). We synthesise the
        smallest v1 sequence that maps to a complete turn:

            profile_loaded → tool_call → stage(x4) → tool_result → done

        and feed each frame through ``SseV1ToLiuyeAdapter.translate``.
        """
        try:
            fixture = load_fixture(DEMO_FIXTURE_STEM)
        except FixtureLoadError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=translator.trace_id,
                code="DEMO_FIXTURE_MISSING",
                message=str(exc),
            )
            return

        snapshot = fixture.get("snapshot", fixture)
        artifact_id = fixture.get("id", "art_channel_demo")
        v1_frames = _synthesise_channel_v1_frames(
            snapshot=snapshot,
            artifact_id=artifact_id,
            persona_id=str(payload.get("persona_id", "rm-wangzhe-east")),
        )
        for frame in v1_frames:
            async for liuye_evt in translator.translate(frame, turn_id):
                yield liuye_evt

    async def _run_live(
        self,
        *,
        turn_id: str,
        translator: SseV1ToLiuyeAdapter,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Live HTTP SSE bridge · POST + iterate v1 frames."""
        client = self._http_client or httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        owns_client = self._http_client is None
        try:
            url = f"{self.backend_url.rstrip('/')}{CHANNEL_ENDPOINT}"
            body = {
                "turn_id": turn_id,
                "trace_id": translator.trace_id,
                **dict(payload),
            }
            async with client.stream("POST", url, json=body) as response:
                async for v1_event in _iter_sse_v1(response):
                    async for liuye_evt in translator.translate(v1_event, turn_id):
                        yield liuye_evt
        finally:
            if owns_client:
                await client.aclose()

    # ------------------------------------------------------------------
    # Audit chain helper · called from orchestrator post-turn (out of scope)
    # ------------------------------------------------------------------

    def record_turn_decision(
        self,
        *,
        turn_id: str,
        trace_id: str,
        input_payload: Mapping[str, Any],
        output_payload: Mapping[str, Any],
        evidence_chain: Mapping[str, Any],
        subject_id: Optional[str] = None,
        parent_turn_id: Optional[str] = None,
    ) -> str:
        """Drop a ``ledger_decision`` row when a channel turn produces a candidate.

        Channel is ``short`` retention (90d · root §3.7.5) since
        candidates are NOT a decision · we still record so the
        evidence chain stays continuous across Cowork→Credit handoff.
        """
        return record_liuye_decision(
            agent_id=self.agent_id,
            endpoint=CHANNEL_ENDPOINT,
            input_payload=dict(input_payload),
            output_payload=dict(output_payload),
            evidence_chain=dict(evidence_chain),
            decision_id=None,
            jurisdiction=get_settings().ledger_jurisdiction,
            retention_class="short",
            subject_id=subject_id,
            parent_turn_id=parent_turn_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _adapter_error(
        self,
        turn_id: str,
        *,
        trace_id: str,
        code: str,
        message: str,
    ) -> dict[str, Any]:
        seq = _make_seq(turn_id)
        return envelope(
            event="turn.error",
            turn_id=turn_id,
            trace_id=trace_id,
            payload={
                "code": code,
                "message": message,
                "retryable": True,
                "human_hint": "获客 Agent 暂时不可用 · 已切换至降级模式",
                "trace_id": trace_id,
                "turn_id": turn_id,
                "seq": seq,
                "fallback_available": True,
            },
            seq=seq,
        )


# ---------------------------------------------------------------------------
# SSE v1 line parser · 共形 with ``docs/contracts/sse-envelope.md`` v1.5
# ---------------------------------------------------------------------------


async def _iter_sse_v1(response: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """Yield decoded v1 event dicts from an httpx streaming response.

    Wire form (per ``sse-envelope.md`` §1.5):

        event: <name>
        data: <single-line JSON>
        \\n

    We deliberately keep this minimal · the legacy 6 agents already emit
    well-formed UTF-8 NDJSON lines · we don't need a full SSE parser.
    """
    import json as _json

    buffer: dict[str, Any] = {}
    async for raw_line in response.aiter_lines():
        line = raw_line.rstrip("\r")
        if not line:
            if buffer:
                yield buffer
                buffer = {}
            continue
        if line.startswith("event:"):
            buffer["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_text = line[len("data:"):].strip()
            try:
                parsed = _json.loads(data_text) if data_text else {}
                if isinstance(parsed, dict):
                    buffer.update(parsed)
                    # ``event`` field inside payload overrides the
                    # SSE wire ``event:`` line when both are present
                    # (some agents put it both places).
                    if "event" not in buffer and "event" in parsed:
                        buffer["event"] = parsed["event"]
            except _json.JSONDecodeError:
                buffer["_raw_data"] = data_text
        # SSE comment lines (``:`` prefix) or ``id:`` lines are ignored.
    if buffer:
        yield buffer


# ---------------------------------------------------------------------------
# Demo-mode v1 frame synthesiser (matrix §2.1 Scenario A)
# ---------------------------------------------------------------------------


def _synthesise_channel_v1_frames(
    *,
    snapshot: Mapping[str, Any],
    artifact_id: str,
    persona_id: str,
) -> list[dict[str, Any]]:
    """Build a minimal v1 frame sequence mirroring matrix §2.1 Scenario A.

    The sequence is:

        profile_loaded → tool_call(signal_search)
        → stage(enterprise_search 20%)
        → stage(signal_aggregation 60%)
        → stage(rerank 90%)
        → tool_result(candidates)
        → done(ChannelPayload)
    """
    candidates = snapshot.get("candidates", [])
    summary = snapshot.get("summary", {})
    seed = snapshot.get("seed", {})

    return [
        {
            "event": "profile_loaded",
            "persona_id": persona_id,
            "profile": seed,
        },
        {
            "event": "tool_call",
            "tool_call_id": "tc_channel_demo",
            "agent": "channel",
            "tool_id": "signal_search",
            "boundary": "cowork",
            "invoker_id": persona_id,
            "input": {
                "query": seed.get("search_intent", ""),
                "profile_seed": seed,
            },
        },
        {
            "event": "stage",
            "stage": "enterprise_search",
            "message": "企业候选检索中",
            "progress": 0.2,
            "stage_index": 1,
            "stage_total": 4,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "signal_aggregation",
            "message": "信号聚合",
            "progress": 0.6,
            "stage_index": 2,
            "stage_total": 4,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "rerank",
            "message": "LLM rerank 候选",
            "progress": 0.9,
            "stage_index": 3,
            "stage_total": 4,
            "status": "running",
        },
        {
            "event": "tool_result",
            "tool_call_id": "tc_channel_demo",
            "artifact_id": artifact_id,
            "result": {
                "candidates": candidates,
                "summary": summary,
            },
        },
        {
            "event": "done",
            "agent": "channel",
            "ok": True,
            "payload": {
                "candidates": candidates,
                "summary": summary,
                "data_source": "demo",
            },
        },
    ]


__all__ = [
    "CHANNEL_AGENT_ID",
    "CHANNEL_ENDPOINT",
    "ChannelAdapter",
]
