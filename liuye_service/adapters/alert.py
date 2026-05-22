# -*- coding: utf-8 -*-
"""liuye_service.adapters.alert — Agent4 (Alert · 预警) BFF adapter.

W1 Phase C (codex R3 R3.2 default design · 2026-05-21):
Stub 501 → live · HTTP SSE 桥接到 ``agent_alert.api:POST /api/alert/scan``.

Per W1-backend brief §3 file 9-13 + ``liuye_service/CLAUDE.md`` §4 + root §3.1.1.

设计 (与 ``credit.py`` / ``channel.py`` 共形 · HTTP-only contract):

- backend HTTP endpoint: ``POST /api/alert/scan`` (agent_alert/api.py:682)
  · 入参 ``AlertScanRequest`` (scenario_key / uploaded_files / provider / api_key / force_mock)
  · SSE stream · 末尾 done envelope with ``hit_list`` + ``dispositions`` + ``data_source``
- Tavily 缺 key → ``scan_engine.build_alert_provider`` 自动 mode label
  (``tavily_key_missing`` / ``web_fallback_<Err>`` / ``web_live``)·
  done envelope ``data_source`` 显式 ``mock_fallback`` · 不静默假 live
- canonical input: ``CanonicalInput.client_metadata.company_name + uscc`` 派生 ·
  通过 ``_canonical_to_alert_input`` mapper 归一成 ``AlertScanRequest`` shape ·
  backward compat: 旧 raw payload (含 ``scenario_key`` 或 ``uploaded_files``) 透传不变
- Managed boundary semantics 保留 (boundary='managed_readonly'):
  · 此 adapter 仍是 best-effort relay · 不持有 job state
  · Phase 2 (Q4 2026 · ``shared/job_runtime/``) 升级到真 job_id + poll · webhook 触发 follow-up turn
  · Phase C 本次仅落地 inline SSE relay · 解决"前端 click → 后端 401 OK" prod ping
- decision_ledger retention: ``short`` 90d default (root §3.7.5 footnote) ·
  severity=red 升 ``standard`` 5y (agent_alert/api.py 内部已上链 · BFF 不重复)

Cowork SLA 注意: alert 业务 SLA ≥ 1 min (cron 扫批 / drill detail LLM 处置建议) ·
本 adapter ``boundary='managed_readonly'`` 仍保留 · 但 Phase C 走真 HTTP SSE relay ·
read timeout 拉到 180s (vs Cowork 30s) · 上游 SSE 撑住即可.
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


ALERT_AGENT_ID = "alert"
ALERT_ENDPOINT = "/api/alert/scan"  # W1 Phase C · stub 501 → live
ALERT_BACKEND_URL_DEFAULT = "http://localhost:8002"  # mock-test worker port · 兼测试

_ENDPOINT_MAP: dict[str, str] = {
    "alert": "/api/alert/scan",
}

# Managed SLA > 1 min · read timeout 180s (vs Cowork 30s) · connect 5s
HTTP_TIMEOUT = httpx.Timeout(5.0, read=180.0)


class AlertAdapter:
    """BFF adapter for Agent4 Alert · HTTP SSE bridge to ``agent_alert.api``.

    W1 Phase C (2026-05-21) · 从 Phase 1 stub (raise NotImplementedError)
    升级为 live HTTP SSE relay · 直连 ``agent_alert/api.py:POST /api/alert/scan``.

    Sibling shape of ``CreditAdapter`` (~credit.py) · 同 ``_run_live`` 模板 ·
    主要差异:

    - ``boundary='managed_readonly'`` (vs credit 'cowork') · 但实际跑 SSE relay
      · Phase 2 升级为 job_runtime · 现 Phase C 透明 inline relay
    - read_timeout=180s (vs credit 30s) · alert 业务 SLA > 1 min
    - canonical mapper: 取 ``client_metadata.company_name`` 作 scenario_key ·
      或 passthrough scenario_key/uploaded_files 显式覆盖
    - 不本地上链 ledger (agent_alert/api.py 内部 ``_record_alert_decisions_to_ledger``
      已上 · BFF 重复无意义)
    """

    agent_id = ALERT_AGENT_ID
    boundary = "managed_readonly"

    def __init__(
        self,
        *,
        backend_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.backend_url = backend_url or ALERT_BACKEND_URL_DEFAULT
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
                message=f"alert adapter has no translator for turn_id={turn_id}",
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
            "[alert_adapter] abort_turn turn_id=%s reason=%s", turn_id, reason,
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
                message=f"alert backend exceeded SLA · backend_url={self.backend_url}",
            )
        except httpx.HTTPError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_HTTP_ERROR",
                message=f"alert HTTP error: {exc}",
            )

    def _resolve_backend_url(self, agent_id: str) -> str:
        """Per-adapter URL 覆写 (与 credit.py / channel.py 共形)."""
        if (
            self.backend_url
            and self.backend_url != ALERT_BACKEND_URL_DEFAULT
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

        W1 Phase C live mode:

        - ``base = self._resolve_backend_url("alert")``
        - ``url = base + /api/alert/scan``
        - body = ``_canonical_to_alert_input(payload)`` (canonical → AlertScanRequest)
        - SSE relay · agent_alert.api 已发 ``encode_event`` (data: <json>) ·
          复用 channel.py ``_iter_sse_v1`` parser · 转 liuye envelope
        - 200 → relay · != 200 → ``ADAPTER_HTTP_ERROR`` + ``fallback_available=True``
        """
        client = self._http_client or httpx.AsyncClient(timeout=HTTP_TIMEOUT)
        owns_client = self._http_client is None
        try:
            base = self._resolve_backend_url(self.agent_id).rstrip("/")
            url = f"{base}{_ENDPOINT_MAP[self.agent_id]}"

            mapped_body = _canonical_to_alert_input(dict(payload))
            body: dict[str, Any] = {
                "turn_id": turn_id,
                "trace_id": translator.trace_id,
                **mapped_body,
            }
            parent_tcid = payload.get("parent_tool_call_id")
            if parent_tcid:
                body["parent_tool_call_id"] = parent_tcid

            # Reuse channel adapter's SSE v1 line parser
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
                            f"alert backend returned {response.status_code} "
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
                "human_hint": "预警 Agent 暂时不可用 · 已切换至降级模式",
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


def _canonical_to_alert_input(payload: dict[str, Any]) -> dict[str, Any]:
    """Map ``CanonicalInput`` → ``agent_alert.api.AlertScanRequest``.

    AlertScanRequest 现形态 (agent_alert/api.py:130):
        {
          "scenario_key": str (空 → backend 默认场景),
          "uploaded_files": list[str] | None,
          "provider": str | None,  # "deepseek" / etc
          "api_key": str | None,
          "force_mock": bool,
        }

    Mapper 行为:

    1. 若 payload **不含** canonical signature (无 ``client_metadata`` key) ·
       直接 passthrough (backward compat · 旧 raw shape 不破)
    2. 若 payload 含 canonical signature ·
       - ``scenario_key`` = passthrough.scenario_key (显式优先) ·
         缺则用 ``client_metadata.company_name`` (单客 drill 入口)
       - ``uploaded_files`` = passthrough.uploaded_files (透传)
       - ``provider`` / ``api_key`` = passthrough 透传
       - ``force_mock`` = passthrough.force_mock (bool · 默认 False)
    3. canonical ``company_name`` + ``uscc`` 派生作 ``client_filter`` (Phase C+) ·
       agent_alert.api 暂不消费 · 留作 Phase 2 job_runtime 接入位
    """
    if not isinstance(payload, dict):
        return {}

    has_canonical = isinstance(payload.get("client_metadata"), dict)
    if not has_canonical:
        return dict(payload)

    try:
        ci = canonical_from_dict(payload)
    except Exception as exc:  # noqa: BLE001 · validation fail · fallback raw
        logger.warning(
            "[alert_adapter] canonical_from_dict failed · fallback raw payload · err=%s",
            exc,
        )
        return dict(payload)

    # Derive scenario_key: explicit passthrough > company_name (单客 drill) > ""
    scenario_key = ci.passthrough.get("scenario_key") or ci.company_name or ""

    body: dict[str, Any] = {
        "scenario_key": str(scenario_key),
        "uploaded_files": ci.passthrough.get("uploaded_files"),
        "provider": ci.passthrough.get("provider"),
        "api_key": ci.passthrough.get("api_key"),
        "force_mock": bool(ci.passthrough.get("force_mock", False)),
    }
    # Drop None to avoid Pydantic schema noise · keep force_mock=False explicit
    body = {k: v for k, v in body.items() if not (v is None and k != "force_mock")}
    return body


__all__ = [
    "ALERT_AGENT_ID",
    "ALERT_ENDPOINT",
    "AlertAdapter",
    "_canonical_to_alert_input",
]
