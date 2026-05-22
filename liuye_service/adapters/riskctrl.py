# -*- coding: utf-8 -*-
"""liuye_service.adapters.riskctrl — Agent2 (Riskctrl · 风控) BFF adapter.

W1 Phase D (codex R3 R3.2 #3 user ack · 2026-05-21):
Stub 501 → live · 业务方向改为"客户风险评级" · 与旧 DSL 业务并行 (backward compat).

Per W1-backend brief §3 file 9-13 + ``liuye_service/CLAUDE.md`` §4 + root §3.1.1.

设计 (per codex R3 R3.2 #3 ack):

- **新业务**: ``POST /api/riskctrl/risk_assess`` (本 adapter 主入口) ·
  canonical (client_metadata + decision_context + credit_terms + material_facts) →
  7 维 (信用/财务/交易/行业/担保/集中度/舆情司法) + 评级 (低/中/高) + Top risks +
  缓释 + 后审周期 + LLM reasoning
- **旧 DSL 业务保留** (backward compat): ``/api/riskctrl/dsl_gen`` + ``/api/riskctrl/backtest``
  endpoint 全保留 · agent_riskctrl.api 不动 · 前端老路径仍跑
- canonical input mapper: ``_canonical_to_risk_assess_input`` 归一成
  ``RiskAssessRequest`` shape · backward compat: 旧 raw payload 透传

实现 (HTTP-only contract · 与 alert/compliance/credit 共形):

- backend HTTP endpoint: ``POST /api/riskctrl/risk_assess``
- SSE relay · 复用 ``channel.py:_iter_sse_v1`` parser
- 200 → relay · != 200 → ``ADAPTER_HTTP_ERROR`` + ``fallback_available=True``
- read_timeout=60s (risk_assess 包含 LLM 调用 · 比 alert/compliance 短 · 比 credit 长)

decision_ledger: agent_riskctrl/api.py 暂未自动上链 risk_assess · BFF 不重复 ·
Phase 2 (Q4 2026) 升 job_runtime 时统一接入.
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


RISKCTRL_AGENT_ID = "riskctrl"
# W1 Phase D · 新业务方向 · risk_assess (vs 旧 backtest)
RISKCTRL_ENDPOINT = "/api/riskctrl/risk_assess"
# 旧 DSL endpoint 保留 (backward compat · 不删 · 但本 adapter 不主走)
RISKCTRL_LEGACY_BACKTEST_ENDPOINT = "/api/riskctrl/backtest"
RISKCTRL_BACKEND_URL_DEFAULT = "http://localhost:8002"

_ENDPOINT_MAP: dict[str, str] = {
    "riskctrl": "/api/riskctrl/risk_assess",
}

# risk_assess SLA: deterministic 7-dim 评分 < 1s + LLM reasoning ~5-15s · 总 60s 充足
HTTP_TIMEOUT = httpx.Timeout(5.0, read=60.0)


class RiskctrlAdapter:
    """BFF adapter for Agent2 Riskctrl · HTTP SSE bridge to ``agent_riskctrl.api``.

    W1 Phase D (2026-05-21) · 从 Phase 1 stub (raise NotImplementedError)
    升级为 live HTTP SSE relay · 主走新业务 ``risk_assess`` (客户风险评级) ·
    旧 DSL ``/dsl_gen`` + ``/backtest`` endpoint 全保留 (per codex R3 R3.2 #3 ack).

    Sibling shape of ``CreditAdapter`` / ``AlertAdapter`` · 同 ``_run_live`` 模板.

    boundary='managed_readonly' 保留 (vs Cowork) · risk_assess 业务 SLA ~15s
    比 Cowork 5s p95 长 · 比 alert/compliance 短 · Phase 2 job_runtime 不强制升级.
    """

    agent_id = RISKCTRL_AGENT_ID
    boundary = "managed_readonly"

    def __init__(
        self,
        *,
        backend_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.backend_url = backend_url or RISKCTRL_BACKEND_URL_DEFAULT
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
                message=f"riskctrl adapter has no translator for turn_id={turn_id}",
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
            "[riskctrl_adapter] abort_turn turn_id=%s reason=%s",
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
                message=f"riskctrl backend exceeded SLA · backend_url={self.backend_url}",
            )
        except httpx.HTTPError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_HTTP_ERROR",
                message=f"riskctrl HTTP error: {exc}",
            )

    def _resolve_backend_url(self, agent_id: str) -> str:
        if (
            self.backend_url
            and self.backend_url != RISKCTRL_BACKEND_URL_DEFAULT
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

        W1 Phase D live mode (codex R3 R3.2 #3):

        - ``base = self._resolve_backend_url("riskctrl")``
        - ``url = base + /api/riskctrl/risk_assess``
        - body = ``_canonical_to_risk_assess_input(payload)`` (canonical → RiskAssessRequest)
        - SSE relay · 复用 channel.py ``_iter_sse_v1`` parser
        - 200 → relay · != 200 → ``ADAPTER_HTTP_ERROR``
        """
        client = self._http_client or httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        owns_client = self._http_client is None
        try:
            base = self._resolve_backend_url(self.agent_id).rstrip("/")
            url = f"{base}{_ENDPOINT_MAP[self.agent_id]}"

            mapped_body = _canonical_to_risk_assess_input(dict(payload))
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
                            f"riskctrl backend returned {response.status_code} "
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
                "human_hint": "风控 Agent 暂时不可用 · 已切换至降级模式",
                "trace_id": trace_id,
                "turn_id": turn_id,
                "seq": seq,
                "fallback_available": True,
            },
            seq=seq,
        )


# ---------------------------------------------------------------------------
# W1 Phase D · Canonical input mapper (codex R3 R3.2 #3)
# ---------------------------------------------------------------------------


def _canonical_to_risk_assess_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Map ``CanonicalInput`` → ``agent_riskctrl.api.RiskAssessRequest``.

    RiskAssessRequest 现形态 (agent_riskctrl/api.py · Phase D 新增):
        {
          "client_metadata": dict (33 字段),
          "decision_context": dict | None (7 字段 · credit Agent 决策结果),
          "credit_terms": dict | None (12 字段),
          "material_facts": dict | None (23 字段),
          "use_llm": bool,
        }

    Mapper 行为:

    1. 若 payload **不含** canonical signature (无 ``client_metadata`` key) ·
       直接 passthrough (backward compat · 老 DSL 路径不破)
    2. 若 payload 含 canonical signature · 走 ``canonical_from_dict`` 归一 ·
       4 layer 全透传 · 加 ``use_llm`` passthrough (默认 True)
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
            "[riskctrl_adapter] canonical_from_dict failed · fallback raw · err=%s",
            exc,
        )
        return dict(payload)

    body: dict[str, Any] = {
        "client_metadata": dict(ci.client_metadata.fields),
        "decision_context": (
            {
                "verdict": ci.decision_context.verdict,
                "score": ci.decision_context.score,
                "score_breakdown": dict(ci.decision_context.score_breakdown),
                "redlines_triggered": list(ci.decision_context.redlines_triggered),
                "cases_referenced": list(ci.decision_context.cases_referenced),
                "reasoning": ci.decision_context.reasoning,
                "confidence": ci.decision_context.confidence,
            }
            if ci.decision_context else None
        ),
        "credit_terms": dict(ci.credit_terms.fields) if ci.credit_terms else None,
        "material_facts": dict(ci.material_facts.fields) if ci.material_facts else None,
        "use_llm": bool(ci.passthrough.get("use_llm", True)),
    }
    # Drop None for cleaner Pydantic schema (use_llm bool · 不 drop)
    body = {k: v for k, v in body.items() if not (v is None and k != "use_llm")}
    return body


__all__ = [
    "RISKCTRL_AGENT_ID",
    "RISKCTRL_ENDPOINT",
    "RISKCTRL_LEGACY_BACKTEST_ENDPOINT",
    "RiskctrlAdapter",
    "_canonical_to_risk_assess_input",
]
