# -*- coding: utf-8 -*-
"""liuye_service.adapters.report — Agent6 (Report · v16) Cowork adapter.

Per W1-backend brief §3 file 12 + ``liuye_service/CLAUDE.md`` §3 + §4 +
``docs/contracts/liuye-sse-event-matrix.md`` §2.3 + root §3.1.1 + §3.7.5.

Cowork SSE adapter for the old ``agent_report`` backend
(``POST /api/report/v16/fill``). HTTP-only contract — never imports
``agent_report.*`` internal modules.

SLA: < 30s SSE per matrix §2.3 (v16 5-stage pipeline · classifier →
truth_fill → generator → evidence_link → qc_gate is materially slower
than channel/credit · the 30s allowance reflects 材料解析 latency).
Timeout policy is the same as channel/credit · adapter emits
``turn.error code=ADAPTER_TIMEOUT`` and lets the orchestrator decide
whether to abort the turn.

Decision-ledger linkage: report retention is ``long`` (10y · per root
§3.7.5) since v16 outputs are 审贷会 底稿. We call
``record_liuye_decision(..., retention_class='long')`` once the turn
emits a ReportJSON with ``unfilled_marker_count=0`` (or with markers
when QC PARTIAL · matrix §2.3 Scenario B).

The mock-test worker has NOT yet delivered ``report_v16_PARTIAL.json``
(checkpoint 2/11 only has channel + credit fixtures). When DEMO_MODE
is on but the fixture is missing, the adapter falls back to a single
``turn.error code=DEMO_FIXTURE_MISSING`` rather than crashing — the
W1-mock-test worker's later baton will land the fixture, then a
restart picks it up.
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


REPORT_AGENT_ID = "report"
REPORT_ENDPOINT = "/api/report/v16/fill"
REPORT_BACKEND_URL_DEFAULT = "http://localhost:8003"  # mock-test worker port

# Report SLA per matrix §2.3 = 30s · we set read=60s so we have headroom
# before httpx aborts (the BFF then surfaces ADAPTER_TIMEOUT).
HTTP_TIMEOUT = httpx.Timeout(5.0, read=60.0)

DEMO_FIXTURE_STEM = "report_v16_PARTIAL"


class ReportAdapter:
    """Cowork SSE adapter for the report (Agent6 · v16) backend."""

    agent_id = REPORT_AGENT_ID
    boundary = "cowork"

    def __init__(
        self,
        *,
        backend_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.backend_url = backend_url or REPORT_BACKEND_URL_DEFAULT
        self._http_client = http_client
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
        trace_id = payload.get("trace_id") or "trace_unknown"
        self._translators[turn_id] = SseV1ToLiuyeAdapter(
            agent_id=self.agent_id, trace_id=trace_id,
        )
        async for evt in self._run(turn_id=turn_id, payload=payload, trace_id=trace_id):
            yield evt

    async def dispatch_message(
        self,
        turn_id: str,
        message: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        translator = self._translators.get(turn_id)
        if translator is None:
            yield self._adapter_error(
                turn_id,
                trace_id=message.get("trace_id") or "trace_unknown",
                code="TURN_NOT_STARTED",
                message=f"report adapter has no translator for turn_id={turn_id}",
            )
            return
        async for evt in self._run(
            turn_id=turn_id, payload=message, trace_id=translator.trace_id,
        ):
            yield evt

    async def abort_turn(self, turn_id: str, reason: str) -> None:
        translator = self._translators.pop(turn_id, None)
        if translator is None:
            return
        logger.info(
            "[report_adapter] abort_turn turn_id=%s reason=%s", turn_id, reason,
        )

    # ------------------------------------------------------------------
    # Core dispatch
    # ------------------------------------------------------------------

    async def _run(
        self,
        *,
        turn_id: str,
        payload: Mapping[str, Any],
        trace_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
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
                message=f"report backend exceeded SLA · backend_url={self.backend_url}",
            )
        except httpx.HTTPError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_HTTP_ERROR",
                message=f"report HTTP error: {exc}",
            )

    async def _run_demo(
        self,
        *,
        turn_id: str,
        translator: SseV1ToLiuyeAdapter,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay ``report_v16_PARTIAL`` fixture · matrix §2.3 Scenario B."""
        try:
            fixture = load_fixture(DEMO_FIXTURE_STEM)
        except FixtureLoadError as exc:
            # Mock-test worker has not yet delivered this fixture
            # (W1-mock-test progress shows only 2/11). The adapter
            # surfaces the situation honestly · UI shows DEMO mode
            # banner with explicit message · matches Evidence-First
            # ethos (CLAUDE.md §3.3): never編一个出来.
            yield self._adapter_error(
                turn_id,
                trace_id=translator.trace_id,
                code="DEMO_FIXTURE_MISSING",
                message=str(exc),
            )
            return

        snapshot = fixture.get("snapshot", fixture)
        artifact_id = fixture.get("id", "art_report_demo")
        v1_frames = _synthesise_report_v1_frames(
            snapshot=snapshot,
            artifact_id=artifact_id,
            persona_id=str(payload.get("persona_id", "rm-wangzhe")),
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
        client = self._http_client or httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        owns_client = self._http_client is None
        try:
            url = f"{self.backend_url.rstrip('/')}{REPORT_ENDPOINT}"
            body = {
                "turn_id": turn_id,
                "trace_id": translator.trace_id,
                **dict(payload),
            }
            async with client.stream("POST", url, json=body) as response:
                from liuye_service.adapters.channel import _iter_sse_v1
                async for v1_event in _iter_sse_v1(response):
                    async for liuye_evt in translator.translate(v1_event, turn_id):
                        yield liuye_evt
        finally:
            if owns_client:
                await client.aclose()

    # ------------------------------------------------------------------
    # Audit chain
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
        """Drop a ``ledger_decision`` row · report retention=long 10y per §3.7.5."""
        return record_liuye_decision(
            agent_id=self.agent_id,
            endpoint=REPORT_ENDPOINT,
            input_payload=dict(input_payload),
            output_payload=dict(output_payload),
            evidence_chain=dict(evidence_chain),
            decision_id=None,
            jurisdiction=get_settings().ledger_jurisdiction,
            retention_class="long",
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
                "human_hint": "报告 Agent 暂时不可用 · 已切换至降级模式",
                "trace_id": trace_id,
                "turn_id": turn_id,
                "seq": seq,
                "fallback_available": True,
            },
            seq=seq,
        )


# ---------------------------------------------------------------------------
# Demo-mode v1 frame synthesiser (matrix §2.3 Scenario A · 5-stage pipeline)
# ---------------------------------------------------------------------------


def _synthesise_report_v1_frames(
    *,
    snapshot: Mapping[str, Any],
    artifact_id: str,
    persona_id: str,
) -> list[dict[str, Any]]:
    """Build a v1 sequence mirroring matrix §2.3 Scenario A (5 stage v16)."""
    report_json = snapshot.get("report_json", {})
    qc_result = snapshot.get("qc_result", {"passed": 9, "total": 9})
    unfilled_count = snapshot.get("unfilled_marker_count", 0)

    return [
        {
            "event": "profile_loaded",
            "persona_id": persona_id,
            "profile": snapshot.get("seed", {}),
        },
        {
            "event": "tool_call",
            "tool_call_id": "tc_report_v16_demo",
            "agent": "report",
            "tool_id": "report_v16_pipeline",
            "boundary": "cowork",
            "invoker_id": persona_id,
            "input": {"template_id": snapshot.get("template_id"), "materials": snapshot.get("materials", [])},
        },
        {
            "event": "stage",
            "stage": "classifier",
            "message": "材料分类",
            "progress": 0.1,
            "stage_index": 1,
            "stage_total": 5,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "truth_fill",
            "message": "结构化预填",
            "progress": 0.3,
            "stage_index": 2,
            "stage_total": 5,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "generator",
            "message": "段落生成 (三阶段 Evidence-First)",
            "progress": 0.5,
            "stage_index": 3,
            "stage_total": 5,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "evidence_link",
            "message": "证据链校验",
            "progress": 0.75,
            "stage_index": 4,
            "stage_total": 5,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "qc_gate",
            "message": "QC 终审 (9 维度)",
            "progress": 0.95,
            "stage_index": 5,
            "stage_total": 5,
            "status": "running",
        },
        {
            "event": "tool_result",
            "tool_call_id": "tc_report_v16_demo",
            "artifact_id": artifact_id,
            "result": {
                "report_json": report_json,
                "qc_result": qc_result,
                "unfilled_marker_count": unfilled_count,
            },
        },
        {
            "event": "done",
            "agent": "report",
            "ok": True,
            "payload": {
                "report_json": report_json,
                "qc_result": qc_result,
                "unfilled_marker_count": unfilled_count,
                "data_source": "demo",
            },
        },
    ]


__all__ = [
    "REPORT_AGENT_ID",
    "REPORT_ENDPOINT",
    "ReportAdapter",
]
