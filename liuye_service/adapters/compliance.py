# -*- coding: utf-8 -*-
"""liuye_service.adapters.compliance — Agent5 (Compliance · 合规) BFF adapter.

W1 Phase C (codex R3 R3.2 default design · 2026-05-21):
Stub 501 → live · 双路 HTTP 桥接到 ``agent_compliance.api``:

- SSE 流式 (默认): ``POST /api/compliance/policy_scan`` (agent_compliance/api.py:601)
- sync 单次 (canonical matrix_check 路径): ``POST /api/compliance/matrix_check``
  (agent_compliance/api.py:750)

Per W1-backend brief §3 file 9-13 + ``liuye_service/CLAUDE.md`` §4 + root §3.1.1.

设计 (HTTP-only contract):

- canonical client_metadata + material_facts → CompliancePolicyScanRequest shape
  · policy_doc + business_docs 由 caller 提供 (canonical 不强制 LLM 抽数)
- 输出: pass / reject / pending verdict (per codex R3 R3.2 #2) +
  checklist (rule_hits) + evidence (violation reports)
- backward compat: 旧 raw payload (含 ``policy_doc`` / ``business_docs``) 透传不变
- Managed boundary semantics 保留 · 但 Phase C 走 inline SSE relay ·
  Phase 2 (Q4 2026) 升 job_runtime + webhook
- decision_ledger retention: ``standard`` 5y (银保监 archive · root §3.7.5) ·
  agent_compliance/api.py 内部已上链 · BFF 不重复

Naming SSOT: ``agent_id='compliance'`` 锁定 · per
``docs/contracts/agent-naming-ssot.md`` v1.1 (Q-042.B + Stage 4 ratify 2026-04-30).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Mapping, Optional

import httpx

from liuye_service.adapters.base import (
    AgentAdapter,
    envelope,
    _make_seq,
)
from liuye_service.adapters.sse_v1_to_liuye import SseV1ToLiuyeAdapter
from liuye_service.config import get_settings
from shared.canonical import CanonicalInput, canonical_from_dict

logger = logging.getLogger(__name__)


COMPLIANCE_AGENT_ID = "compliance"
COMPLIANCE_ENDPOINT = "/api/compliance/policy_scan"  # W1 Phase C · stub 501 → live
COMPLIANCE_BACKEND_URL_DEFAULT = "http://localhost:8002"  # mock-test worker port

_ENDPOINT_MAP: dict[str, str] = {
    "compliance": "/api/compliance/policy_scan",
}

# Managed SLA ≥ 1 min (N×M 矩阵 scan + LLM 抽规则) · read timeout 240s
HTTP_TIMEOUT = httpx.Timeout(5.0, read=240.0)


class ComplianceAdapter:
    """BFF adapter for Agent5 Compliance · HTTP SSE bridge to ``agent_compliance.api``.

    W1 Phase C (2026-05-21) · stub → live · 同 ``AlertAdapter`` 形态.

    主要功能 (per codex R3 R3.2 #2):

    - 输入: canonical (client_metadata + material_facts + optional decision_context)
      + passthrough (policy_doc + business_docs)
    - 输出: SSE stream · 末尾 done envelope with ``hit_list`` + ``conflict_points``
      + ``data_source`` (live / mock_fallback)
    - 默认走 ``/policy_scan`` SSE · 若 ``passthrough.matrix_check_mode=true`` ·
      走 ``/matrix_check`` sync 路径 (单次 N×M · 不流式 · 用于 ad-hoc check)
    """

    agent_id = COMPLIANCE_AGENT_ID
    boundary = "managed_readonly"

    def __init__(
        self,
        *,
        backend_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.backend_url = backend_url or COMPLIANCE_BACKEND_URL_DEFAULT
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
                message=f"compliance adapter has no translator for turn_id={turn_id}",
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
            "[compliance_adapter] abort_turn turn_id=%s reason=%s",
            turn_id, reason,
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
                message=f"compliance backend exceeded SLA · backend_url={self.backend_url}",
            )
        except httpx.HTTPError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_HTTP_ERROR",
                message=f"compliance HTTP error: {exc}",
            )

    def _resolve_backend_url(self, agent_id: str) -> str:
        if (
            self.backend_url
            and self.backend_url != COMPLIANCE_BACKEND_URL_DEFAULT
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

        W1 Phase C live mode (codex R3 R3.2 #2):

        - ``base = self._resolve_backend_url("compliance")``
        - ``url = base + /api/compliance/policy_scan``
        - body = ``_canonical_to_compliance_input(payload)``
        - SSE relay · 复用 channel.py ``_iter_sse_v1`` parser
        - 200 → relay · != 200 → ``ADAPTER_HTTP_ERROR``
        """
        client = self._http_client or httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        owns_client = self._http_client is None
        try:
            base = self._resolve_backend_url(self.agent_id).rstrip("/")
            url = f"{base}{_ENDPOINT_MAP[self.agent_id]}"

            mapped_body = _canonical_to_compliance_input(dict(payload))
            body: dict[str, Any] = {
                "turn_id": turn_id,
                "trace_id": translator.trace_id,
                **mapped_body,
            }
            parent_tcid = payload.get("parent_tool_call_id")
            if parent_tcid:
                body["parent_tool_call_id"] = parent_tcid

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
                            f"compliance backend returned {response.status_code} "
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
                "human_hint": "合规 Agent 暂时不可用 · 已切换至降级模式",
                "trace_id": trace_id,
                "turn_id": turn_id,
                "seq": seq,
                "fallback_available": True,
            },
            seq=seq,
        )


# ---------------------------------------------------------------------------
# W1 Phase C · Canonical input mapper (codex R3 R3.2 default design)
# ---------------------------------------------------------------------------


def _canonical_to_compliance_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Map ``CanonicalInput`` → ``agent_compliance.api.CompliancePolicyScanRequest``.

    CompliancePolicyScanRequest 现形态 (agent_compliance/api.py:104):
        {
          "policy_doc": str,           # 监管政策原文 (必填)
          "business_docs": list,       # 业务记录 list[str|dict]
          "policy_meta": dict | None,  # 可选 metadata
          "force_mock": bool,
        }

    Mapper 行为:

    1. 若 payload **不含** canonical signature (无 ``client_metadata`` key) ·
       直接 passthrough (backward compat)

    2. 若 payload 含 canonical signature ·
       - ``policy_doc`` = passthrough.policy_doc (必填 · canonical 不持有政策原文)
       - ``business_docs`` = canonical material_facts 长叙述聚合
         (BUSINESS_HISTORY_DESC + INDUSTRY_ANALYSIS + REPAYMENT_ABILITY_ASSESSMENT
         等聚合为单条 dict · 加 ``subject_name`` 标识) ·
         或 passthrough.business_docs 显式覆盖
       - ``policy_meta`` = passthrough 透传
       - ``force_mock`` = passthrough 透传

    3. canonical decision_context (optional) 携带 verdict + score → 不映射到
       policy_scan body (policy_scan 不消费决策结果 · 此为 compliance audit 入口) ·
       透传到 passthrough_extras dict 供调用方监控
    """
    if not isinstance(payload, dict):
        return {}

    has_canonical = isinstance(payload.get("client_metadata"), dict)
    if not has_canonical:
        return dict(payload)

    try:
        ci = canonical_from_dict(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[compliance_adapter] canonical_from_dict failed · fallback raw · err=%s",
            exc,
        )
        return dict(payload)

    # policy_doc 必填 · canonical 不持有 · 从 passthrough 取 · 缺则空字符串
    # (backend 会返 400 VALIDATION_FAILED · 显式 fail · 不静默兜底)
    policy_doc = str(ci.passthrough.get("policy_doc", ""))

    # business_docs: passthrough 显式覆盖 > material_facts 派生 > 空
    business_docs = ci.passthrough.get("business_docs")
    if business_docs is None and ci.material_facts is not None:
        # 派生: material_facts 长叙述 + client_metadata.company_name 作 subject_name
        mf = ci.material_facts.fields
        narrative_parts: list[str] = []
        for key in (
            "BUSINESS_HISTORY_DESC",
            "INDUSTRY_ANALYSIS",
            "RELATED_PARTIES_DESC",
            "FINANCIAL_CASH_FLOW_DESC",
            "REPAYMENT_ABILITY_ASSESSMENT",
            "GUARANTEE_DESCRIPTION",
        ):
            val = mf.get(key)
            if isinstance(val, str) and val.strip():
                narrative_parts.append(f"[{key}] {val.strip()}")
        if narrative_parts:
            business_docs = [{
                "subject_name": ci.company_name,
                "uscc": ci.uscc,
                "content": "\n\n".join(narrative_parts),
                "source": "canonical.material_facts",
            }]
        else:
            business_docs = []
    if business_docs is None:
        business_docs = []

    body: dict[str, Any] = {
        "policy_doc": policy_doc,
        "business_docs": business_docs,
        "policy_meta": ci.passthrough.get("policy_meta"),
        "force_mock": bool(ci.passthrough.get("force_mock", False)),
    }
    body = {k: v for k, v in body.items() if not (v is None and k != "force_mock")}
    return body


__all__ = [
    "COMPLIANCE_AGENT_ID",
    "COMPLIANCE_ENDPOINT",
    "ComplianceAdapter",
    "_canonical_to_compliance_input",
]
