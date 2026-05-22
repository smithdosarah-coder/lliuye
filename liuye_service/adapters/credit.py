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
from shared.canonical import CanonicalInput, canonical_from_dict

logger = logging.getLogger(__name__)


CREDIT_AGENT_ID = "credit"
# W2 backend brief §4.2 perfect-check fix #1: real endpoint is /api/credit/decision
# (not /api/credit/run). Kept as module-level constant for legacy callers ·
# the live path uses ``_ENDPOINT_MAP['credit']`` via the shared lookup.
CREDIT_ENDPOINT = "/api/credit/decision"
CREDIT_BACKEND_URL_DEFAULT = "http://localhost:8002"  # mock-test worker port

# W2 perfect-check fix #1 · shared endpoint map (mirrors channel.py).
# Defined here too so credit can stay a pure HTTP adapter without
# importing channel internals (HTTP-only contract per liuye CLAUDE.md §2.3).
_ENDPOINT_MAP: dict[str, str] = {
    "channel": "/api/channel/run",
    "credit": "/api/credit/decision",
    "report": "/api/report/v16/fill",
}

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

    def _resolve_backend_url(self, agent_id: str) -> str:
        """Per-adapter URL 覆写 (W2 brief §4.1 + perfect-check fix #2).

        Mirrors ``ChannelAdapter._resolve_backend_url`` · constructor
        injection (default ``CREDIT_BACKEND_URL_DEFAULT`` = mock :8002)
        wins for legacy tests, else ``Settings.resolve_backend_url``
        resolves env (``LIUYE_BACKEND_CREDIT_URL > LIUYE_BACKEND_BASE_URL``).
        """
        if (
            self.backend_url
            and self.backend_url != CREDIT_BACKEND_URL_DEFAULT
        ):
            return self.backend_url
        return get_settings().resolve_backend_url(agent_id)

    async def _run_live(
        self,
        *,
        turn_id: str,
        translator: SseV1ToLiuyeAdapter,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Live HTTP SSE bridge · POST + iterate v1 frames.

        W2 backend brief §4.2 live mode + parent_tool_call_id passthrough:

        - ``base = self._resolve_backend_url("credit")``
        - ``url = base + _ENDPOINT_MAP['credit']`` = ``/api/credit/decision``
        - body forwards ``parent_tool_call_id`` (Report → Credit handoff ·
          W1 第 3 棒 gotcha #4) so the v1 ``tool_call`` event carries the
          lineage; the SSE translator emits ``tool.started`` with both
          ``tool_call_id`` (new uuid) + ``parent_tool_call_id`` (handoff link).
        - Cowork SLA: connect=5s / read=30s

        W1 Phase B (codex R3 R3.4 W2 · 2026-05-21): canonical input adapter.
        若 payload 含 ``client_metadata`` key (新 canonical 路径) · 走
        ``_canonical_to_credit_input`` mapper 归一成 agent_credit
        ``DecisionRequestV4`` 形态 (stage_tab / report_json / materials /
        appetite_config / preset_name)· 旧 raw payload 路径 (已含 stage_tab
        + report_json) 不变 · backward compat.
        """
        client = self._http_client or httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        owns_client = self._http_client is None
        try:
            base = self._resolve_backend_url(self.agent_id).rstrip("/")
            url = f"{base}{_ENDPOINT_MAP[self.agent_id]}"

            # W1 Phase B canonical input branch: 若 payload 是 canonical shape
            # (含 client_metadata layer) · 跑 mapper 归一 · 否则 backward compat
            # 直接透传 (channel/old e2e test 走此路径).
            mapped_body = _canonical_to_credit_input(dict(payload))
            body: dict[str, Any] = {
                "turn_id": turn_id,
                "trace_id": translator.trace_id,
                **mapped_body,
            }
            # Defensive: even if payload already carried it (orchestrator
            # forwards from the SSE bridge), make sure the wire body has
            # the handoff key spelled exactly · old agent_credit consumers
            # expect ``parent_tool_call_id`` verbatim per v3 §2.1 + 必修 #51.
            parent_tcid = payload.get("parent_tool_call_id")
            if parent_tcid:
                body["parent_tool_call_id"] = parent_tcid
            # Local import keeps the cross-adapter coupling explicit while
            # honouring the HTTP-only contract (no agent_* internals).
            from liuye_service.adapters.channel import _iter_sse_v1
            async with client.stream(
                "POST", url, json=body, timeout=HTTP_TIMEOUT,
            ) as response:
                if response.status_code != 200:
                    yield self._adapter_error(
                        turn_id,
                        trace_id=translator.trace_id,
                        code="ADAPTER_HTTP_ERROR",
                        message=(
                            f"credit backend returned {response.status_code} "
                            f"· url={url}"
                        ),
                    )
                    return
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


# ---------------------------------------------------------------------------
# W1 Phase B · Canonical input mapper (codex R3 R3.4 W2)
# ---------------------------------------------------------------------------


def _canonical_to_credit_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Map ``CanonicalInput`` (4-layer canonical) → agent_credit ``DecisionRequestV4``.

    agent_credit ``POST /api/credit/decision`` 现有形态 (api.py:568):
        {
          "stage_tab": "corporate" | "small_business" | "retail",
          "report_json": dict | None,
          "materials": list[dict] | None,
          "preset_name": str | None,
          "appetite_config": dict | None,
          "provider": str | None, "api_key": str | None,
          "mock": bool,
        }

    Mapper 行为:

    1. 若 payload **不含** canonical signature (无 ``client_metadata`` key) ·
       直接 passthrough (backward compat · 不破坏现有 raw shape).

    2. 若 payload 含 canonical signature ·
       - client_metadata + credit_terms + material_facts → report_json (新建 dict)
       - canonical ``stage_tab`` passthrough · 缺则按 client_metadata 推断
         (CLIENT_ID_NUMBER 存在 → retail · CLIENT_USCC 存在 → corporate · 默认 small_business)
       - canonical ``materials`` passthrough (若有)· 否则 None
       - canonical ``appetite_config`` passthrough · 缺则 None (走 agent_credit default)
       - canonical ``preset_name`` passthrough · 缺则 None

    3. passthrough 字段 (mock / provider / api_key / parent_tool_call_id) 原样保留.

    Note: 这是 mapper 不是 validator · pydantic validation 走 ``canonical_from_dict``
    (单独 wrap 在调用点 · 当前 ``_run_live`` 不强制 validate · 留 backward
    compat 透传路径)。
    """
    if not isinstance(payload, dict):
        return {}

    # Detect canonical signature: client_metadata as dict layer
    has_canonical = isinstance(payload.get("client_metadata"), dict)
    if not has_canonical:
        # Backward compat: 已是 raw shape · 直接 passthrough
        return dict(payload)

    # Canonical path: 走 pydantic 归一 + 重 wrap 成 DecisionRequestV4 shape
    try:
        ci = canonical_from_dict(payload)
    except Exception as exc:  # noqa: BLE001 · validation 失败 fallback raw
        logger.warning(
            "[credit_adapter] canonical_from_dict failed · fallback raw payload · err=%s",
            exc,
        )
        return dict(payload)

    cm_fields = ci.client_metadata.fields
    ct_fields = ci.credit_terms.fields if ci.credit_terms else {}
    mf_fields = ci.material_facts.fields if ci.material_facts else {}

    # Infer stage_tab from client_metadata if not provided in passthrough
    stage_tab = ci.passthrough.get("stage_tab")
    if not stage_tab:
        if cm_fields.get("CLIENT_ID_NUMBER"):
            stage_tab = "retail"
        elif cm_fields.get("CLIENT_USCC"):
            stage_tab = "corporate"
        else:
            stage_tab = "small_business"

    # Build report_json (canonical-merged · agent_credit 复用 Agent6 ReportJSON shape)
    # 形态对齐 agent_credit/api.py _decision_event_stream_v4 期待:
    #   header (subject_name/applied_product/applied_amount_wan) +
    #   business_line (stage_tab) + financial_anchors (financial.*)
    report_json: dict[str, Any] = {
        "header": {
            "subject_name": cm_fields.get("CLIENT_FULL_NAME", ""),
            "uscc": cm_fields.get("CLIENT_USCC", ""),
            "applied_product": ct_fields.get("CREDIT_PURPOSE", "综合授信"),
            "applied_amount_wan": _parse_amount_wan(ct_fields.get("CREDIT_AMOUNT", "")),
            "applied_term_months": _parse_term_months(ct_fields.get("CREDIT_PERIOD", "")),
            "industry": cm_fields.get("CLIENT_INDUSTRY_FULL", ""),
            "industry_code": cm_fields.get("CLIENT_INDUSTRY_CODE", ""),
            "location": cm_fields.get("CLIENT_LOCATION_CITY", ""),
            "establishment_date": cm_fields.get("CLIENT_ESTABLISHMENT_DATE", ""),
            "registered_capital": cm_fields.get("CLIENT_REGISTERED_CAPITAL", ""),
            "employee_count": cm_fields.get("CLIENT_EMPLOYEE_COUNT", ""),
            "operating_years": cm_fields.get("CLIENT_OPERATING_YEARS", ""),
        },
        "business_line": stage_tab,
        "client_metadata": dict(cm_fields),
        "credit_terms": dict(ct_fields),
        "material_facts": dict(mf_fields),
        # financial_anchors: 由 material_facts 现金流叙述派生 · agent_credit 自己 extract
        # (canonical 不强制 LLM 抽数 · 留给 feature_extractor)
        "financial_anchors": _extract_financial_anchors(mf_fields),
    }

    # 若 caller 透传了 report_json (e.g. Agent6 handoff)· canonical 让位
    upstream_report_json = ci.passthrough.get("report_json")
    if isinstance(upstream_report_json, dict) and upstream_report_json:
        # Merge: upstream 优先 · canonical 仅补缺
        merged = dict(report_json)
        merged.update(upstream_report_json)
        report_json = merged

    body: dict[str, Any] = {
        "stage_tab": stage_tab,
        "report_json": report_json,
        "materials": ci.passthrough.get("materials"),
        "preset_name": ci.passthrough.get("preset_name"),
        "appetite_config": ci.passthrough.get("appetite_config"),
        "provider": ci.passthrough.get("provider"),
        "api_key": ci.passthrough.get("api_key"),
        "mock": bool(ci.passthrough.get("mock", False)),
    }

    # Drop None to avoid Pydantic schema noise · keep mock=False explicit
    body = {k: v for k, v in body.items() if not (v is None and k != "mock")}
    return body


def _parse_amount_wan(s: Any) -> Optional[float]:
    """'5000 万元' → 5000.0 · '5000万' → 5000.0 · 解析失败 None."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    # Strip 中文单位 / 空格
    cleaned = s.replace("万元", "").replace("万", "").replace("元", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_term_months(s: Any) -> Optional[int]:
    """'一年' → 12 · '12 个月' → 12 · '36 月' → 36 · '3 年' → 36 · 解析失败 None."""
    if s is None:
        return None
    if isinstance(s, int):
        return s
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    # 中文数字 → 阿拉伯 (简化版 · 仅一/二/三...十)
    cn_digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                 "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    import re as _re
    # 提取数字
    m = _re.search(r"(\d+)", s)
    if m:
        n = int(m.group(1))
    else:
        n = None
        for cn, v in cn_digits.items():
            if cn in s:
                n = v
                break
    if n is None:
        return None
    if "年" in s:
        return n * 12
    # 默认月
    return n


def _extract_financial_anchors(mf_fields: dict[str, Any]) -> dict[str, Any]:
    """从 material_facts 派生 financial_anchors (agent_credit feature_extractor 兜底).

    canonical 不强制 LLM 抽数 · 仅做 deterministic 1-to-1 mapping:
      - CREDIT_OUTSTANDING_BALANCE → debt_balance
      - CREDIT_OVERDUE_RECORD      → overdue_status (retail)
      - CLIENT_MONTHLY_INCOME      → monthly_income (retail)
      - CLIENT_DSR                 → dsr (retail)
    缺字段 → 不出现在 financial_anchors · agent_credit 走 LLM 抽数路径.
    """
    anchors: dict[str, Any] = {}
    if mf_fields.get("CREDIT_OUTSTANDING_BALANCE"):
        anchors["debt_balance"] = mf_fields["CREDIT_OUTSTANDING_BALANCE"]
    if mf_fields.get("CREDIT_OVERDUE_RECORD"):
        anchors["overdue_status"] = mf_fields["CREDIT_OVERDUE_RECORD"]
    if mf_fields.get("CLIENT_MONTHLY_INCOME"):
        anchors["monthly_income"] = mf_fields["CLIENT_MONTHLY_INCOME"]
    if mf_fields.get("CLIENT_DSR"):
        anchors["dsr"] = mf_fields["CLIENT_DSR"]
    if mf_fields.get("REPAYMENT_ABILITY_ASSESSMENT"):
        anchors["repayment_assessment"] = mf_fields["REPAYMENT_ABILITY_ASSESSMENT"]
    return anchors


__all__ = [
    "CREDIT_AGENT_ID",
    "CREDIT_ENDPOINT",
    "CreditAdapter",
    "_canonical_to_credit_input",
]
