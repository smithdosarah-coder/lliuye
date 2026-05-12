# -*- coding: utf-8 -*-
"""liuye_service.adapters.credit — Agent3 (Credit · 授信) Cowork adapter.

Per W1-backend brief §3 file 11 + ``liuye_service/CLAUDE.md`` §3 + §4 +
``docs/contracts/liuye-sse-event-matrix.md`` §2.2 + root §3.1.1 + §3.7.5.

Cowork SSE adapter for the old ``agent_credit`` backend
(``POST /api/credit/run``). HTTP-only contract — never imports
``agent_credit.*`` internal modules.

Cowork SLA: < 5s p95 (4-dim scoring + red-line check + decision-graph
peer_gap lookup). The actual ``credit_decision_submit`` (上链 ·
``ledger_write`` medium-risk PermissionRequest) is a SEPARATE turn
triggered by the frontend confirm modal — this adapter ONLY produces
the score-radar artifact + verdict, then the orchestrator parks a
PermissionRequest before the ledger write turn (matrix §2.2 Scenario A
ratification).

Decision-ledger linkage: credit retention is ``standard`` (5y · per
root §3.7.5) since授信 decisions are bank-audit subjects. We call
``record_liuye_decision(..., retention_class='standard')`` once the
turn lands a PASS / FAIL verdict.

Report → Credit handoff: when the caller passes
``parent_tool_call_id`` (e.g. ``tc_report_v16_pipeline``), we forward
it to ``agent_credit`` so the SSE v1 ``tool_call`` event carries the
lineage. The translator picks it up and emits ``tool.started`` with
both ``tool_call_id`` (new uuid) + ``parent_tool_call_id`` (handoff
link · v3 §2.1 + 必修 #51).
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


CREDIT_AGENT_ID = "credit"
CREDIT_ENDPOINT = "/api/credit/run"
CREDIT_BACKEND_URL_DEFAULT = "http://localhost:8002"  # mock-test worker port

HTTP_TIMEOUT = httpx.Timeout(5.0, read=30.0)
DEMO_FIXTURE_STEM = "credit_decision_PASS"


class CreditAdapter:
    """Cowork SSE adapter for the credit (Agent3) backend.

    Sibling of ``ChannelAdapter`` · same skeleton, different backend
    URL + retention class + fixture. The duplication is intentional:
    keeping per-agent adapters explicit means swapping one (e.g.
    Phase 2 hardening) does not impact the others.
    """

    agent_id = CREDIT_AGENT_ID
    boundary = "cowork"

    def __init__(
        self,
        *,
        backend_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.backend_url = backend_url or CREDIT_BACKEND_URL_DEFAULT
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
                message=f"credit adapter has no translator for turn_id={turn_id}",
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
            "[credit_adapter] abort_turn turn_id=%s reason=%s", turn_id, reason,
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
                message=f"credit backend exceeded SLA · backend_url={self.backend_url}",
            )
        except httpx.HTTPError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_HTTP_ERROR",
                message=f"credit HTTP error: {exc}",
            )

    async def _run_demo(
        self,
        *,
        turn_id: str,
        translator: SseV1ToLiuyeAdapter,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay ``credit_decision_PASS`` fixture · synthesise matrix §2.2 Scenario A frames."""
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
        artifact_id = fixture.get("id", "art_credit_demo")
        v1_frames = _synthesise_credit_v1_frames(
            snapshot=snapshot,
            artifact_id=artifact_id,
            persona_id=str(payload.get("persona_id", "ra-审贷会")),
            parent_tool_call_id=str(payload.get("parent_tool_call_id") or "") or None,
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
            url = f"{self.backend_url.rstrip('/')}{CREDIT_ENDPOINT}"
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
        """Drop a ``ledger_decision`` row · credit retention=standard 5y per §3.7.5."""
        return record_liuye_decision(
            agent_id=self.agent_id,
            endpoint=CREDIT_ENDPOINT,
            input_payload=dict(input_payload),
            output_payload=dict(output_payload),
            evidence_chain=dict(evidence_chain),
            decision_id=None,
            jurisdiction=get_settings().ledger_jurisdiction,
            retention_class="standard",
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
                "human_hint": "授信 Agent 暂时不可用 · 已切换至降级模式",
                "trace_id": trace_id,
                "turn_id": turn_id,
                "seq": seq,
                "fallback_available": True,
            },
            seq=seq,
        )


# ---------------------------------------------------------------------------
# Demo-mode v1 frame synthesiser (matrix §2.2 Scenario A)
# ---------------------------------------------------------------------------


def _synthesise_credit_v1_frames(
    *,
    snapshot: Mapping[str, Any],
    artifact_id: str,
    persona_id: str,
    parent_tool_call_id: Optional[str],
) -> list[dict[str, Any]]:
    """Build a v1 sequence mirroring matrix §2.2 Scenario A (4-dim PASS).

    Sequence:

        profile_loaded → tool_call(credit_decision)
        → stage(reuse_report_json 10%)
        → stage(4dim_scoring 40%)
        → stage(red_line_check 70%)
        → stage(peer_gap_evidence 85%)
        → tool_result(score_radar)
        → done(CreditPayload)
    """
    header = snapshot.get("header", {})
    scoring = snapshot.get("scoring", {})
    decision = snapshot.get("decision", {})

    tool_call_payload: dict[str, Any] = {
        "tool_call_id": "tc_credit_demo",
        "agent": "credit",
        "tool_id": "credit_decision",
        "boundary": "cowork",
        "invoker_id": persona_id,
        "input": {
            "applied_product": header.get("applied_product"),
            "applied_amount_wan": header.get("applied_amount_wan"),
            "applied_term_months": header.get("applied_term_months"),
            "subject_name": header.get("subject_name"),
        },
    }
    if parent_tool_call_id:
        tool_call_payload["parent_tool_call_id"] = parent_tool_call_id

    return [
        {
            "event": "profile_loaded",
            "persona_id": persona_id,
            "profile": header,
        },
        {"event": "tool_call", **tool_call_payload},
        {
            "event": "stage",
            "stage": "reuse_report_json",
            "message": "复用 Agent6 ReportJSON",
            "progress": 0.1,
            "stage_index": 1,
            "stage_total": 4,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "4dim_scoring",
            "message": "4 维评分计算中",
            "progress": 0.4,
            "stage_index": 2,
            "stage_total": 4,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "red_line_check",
            "message": "红线检查",
            "progress": 0.7,
            "stage_index": 3,
            "stage_total": 4,
            "status": "running",
        },
        {
            "event": "stage",
            "stage": "peer_gap_evidence",
            "message": "peer_gap evidence linkage (BE2 graph)",
            "progress": 0.85,
            "stage_index": 4,
            "stage_total": 4,
            "status": "running",
        },
        {
            "event": "tool_result",
            "tool_call_id": "tc_credit_demo",
            "artifact_id": artifact_id,
            "result": {
                "scoring": scoring,
                "decision": decision,
            },
        },
        {
            "event": "done",
            "agent": "credit",
            "ok": True,
            "payload": {
                "score_radar": scoring,
                "decision_verdict": decision.get("verdict", "PASS"),
                "red_lines": decision.get("red_lines", []),
                "data_source": "demo",
            },
        },
    ]


__all__ = [
    "CREDIT_AGENT_ID",
    "CREDIT_ENDPOINT",
    "CreditAdapter",
]
