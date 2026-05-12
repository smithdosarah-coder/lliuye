# -*- coding: utf-8 -*-
"""liuye_service.adapters.sse_v1_to_liuye — 7 SSE v1 events → 11 liuye events.

Per W1-backend brief §3 file 13 + ``liuye_service/CLAUDE.md`` §3 +
``docs/contracts/liuye-sse-event-matrix.md`` §4 + v3 spec 附录 A.1.

This translator is the **only** wire-compat layer between the legacy
6-agent SSE v1.0 protocol (``docs/contracts/sse-envelope.md`` v1.0) and
the new liuye 11-event SSE (v3 §2.1). One v1 event MAY emit 0..N liuye
events (see mapping table below).

Mapping (verbatim from matrix §4 table · cross-checked v3 附录 A.1):

    v1.0 event          liuye event              method
    ------------------  -----------------------  ---------------------
    profile_loaded   →  turn.started             _on_profile_loaded
    stage            →  tool.progress            _on_stage
    stream           →  message.created          _on_stream
    tool_call        →  tool.started             _on_tool_call
    tool_result      →  tool.completed           _on_tool_result
    done             →  turn.completed           _on_done
    error            →  turn.error               _on_error
    heartbeat (v1)   →  heartbeat                _on_heartbeat

The 3 **new** liuye events are NOT produced by this translator:

    artifact.patch       — BFF emits when an Artifact mutates (P1-10
                           chunked · matrix §3 Q2 + v3 §2.2)
    evidence.attached    — BFF emits when an EvidenceRef is attached
    permission.request   — BFF emits directly via
                           ``permissions.emit_permission_request`` (PM
                           2026-05-11 Q2 ratify · matrix §3 Q3 · NOT
                           via this adapter)

Hard rules (v3 附录 A.2 verbatim · matrix §4.2):

1. **idempotency**: re-translation of the same v1 event MUST NOT
   re-emit downstream events. We use
   ``dedup_key = (event, sha256(canonical_json(payload)))``.
2. **seq injection**: v1 has no seq · we mint via
   ``base._make_seq(turn_id)``. ``(turn_id, seq)`` is unique per turn.
3. **percent conversion**: v1 ``stage.progress`` is 0-1 float (per
   ``sse-envelope.md`` §1.5) · liuye ``tool.progress.percent`` is
   0-100 integer (per v3 §2.3). We multiply by 100 + ``round()``.
4. **degraded fallback**: any translation failure → single
   ``turn.error code=SSE_ADAPTER_FAILED fallback_available=true``.
5. ``permission.request`` 11th event is OUT OF SCOPE here — emitted
   directly by ``permissions.emit_permission_request`` (matrix §3 Q3).
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, AsyncIterator, Mapping, Optional

from liuye_service.adapters.base import (
    _make_seq,
    envelope,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 5-state ProgressMessage status enum (v3 §2.3 line 207 · matrix §1)
# ---------------------------------------------------------------------------

_VALID_PROGRESS_STATUS = frozenset(
    {"pending", "running", "done", "warning", "error"}
)


# ---------------------------------------------------------------------------
# Dedup helpers
# ---------------------------------------------------------------------------


def _canonical_json(payload: Mapping[str, Any]) -> str:
    """Stable JSON for hashing · sorted keys · no whitespace."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _dedup_key(event: str, payload: Mapping[str, Any]) -> str:
    """``(event, sha256(payload))`` keyspace for v1 re-deliveries."""
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{event}::{digest}"


# ---------------------------------------------------------------------------
# Translator class · stateful per turn (dedup set + tool_call_id context)
# ---------------------------------------------------------------------------


class SseV1ToLiuyeAdapter:
    """Translate one agent's v1 SSE stream into the liuye 11-event SSE.

    One instance per turn (or per long-lived agent connection · v1
    semantics are stateful around ``tool_call`` / ``tool_result``
    pairing). Concrete agent adapters (channel / credit / report)
    own one instance and call ``translate(v1_event, turn_id)`` per
    incoming raw v1 frame.
    """

    def __init__(self, *, agent_id: str, trace_id: str) -> None:
        self.agent_id = agent_id
        self.trace_id = trace_id
        # Dedup keys seen so far for this stream · bounded by the
        # number of v1 events the agent emits (single-digit MB worst
        # case · trim on long-lived streams if needed).
        self._dedup: set[str] = set()
        # ``stream`` (token-by-token) collapses to one ``message.created``
        # for the FIRST token · subsequent tokens go into the delta
        # comment line (per matrix §4 row 3) which is NOT a counted
        # event. We remember whether we've emitted the first frame.
        self._message_id_by_seq: dict[int, str] = {}
        self._message_started: bool = False
        # Active ToolCall context · v1 emits ``stage`` events with no
        # owning tool_call_id · we inherit from the most recent
        # ``tool_call`` v1 event so liuye ``tool.progress`` always has
        # a parent (per matrix §1 + v3 §2.3 hardline).
        self._current_tool_call_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def translate(
        self,
        v1_event: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Translate one v1 event → 0..N liuye envelopes.

        Yields one or more pre-enveloped liuye event dicts (already
        carrying ``schema_version`` / ``seq`` / ``ts`` / etc.).

        Failure mode: ANY raised exception inside a handler becomes a
        single ``turn.error code=SSE_ADAPTER_FAILED`` with
        ``fallback_available=true`` per matrix §4.2 hard rule 5.
        """
        evt = v1_event.get("event") if isinstance(v1_event, Mapping) else None
        if not isinstance(evt, str) or not evt:
            yield self._error_envelope(
                turn_id,
                code="SSE_ADAPTER_FAILED",
                message=f"v1 event missing 'event' field: {v1_event!r}",
            )
            return

        dedup = _dedup_key(evt, v1_event)
        if dedup in self._dedup:
            logger.debug(
                "[sse_v1_to_liuye] dropping duplicate v1 event · key=%s", dedup,
            )
            return
        self._dedup.add(dedup)

        handler_name = _V1_HANDLERS.get(evt)
        if handler_name is None:
            # Unknown v1 event · skip silently (forward-compat per
            # sse-envelope.md §1.5 "consumer 容忍未识别 event").
            logger.info(
                "[sse_v1_to_liuye] unknown v1 event %r · skipping (forward-compat)",
                evt,
            )
            return

        try:
            async for liuye_evt in getattr(self, handler_name)(v1_event, turn_id):
                yield liuye_evt
        except Exception as exc:  # noqa: BLE001 · adapter degraded fallback
            logger.warning(
                "[sse_v1_to_liuye] handler %s failed on v1 event %r: %s",
                handler_name, evt, exc,
                exc_info=True,
            )
            yield self._error_envelope(
                turn_id,
                code="SSE_ADAPTER_FAILED",
                message=f"{handler_name} failed: {exc}",
            )

    # ------------------------------------------------------------------
    # 7 handlers (one per v1 event type · matrix §4 mapping)
    # ------------------------------------------------------------------

    async def _on_profile_loaded(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``profile_loaded`` → liuye ``turn.started``.

        v1 carries ``profile`` (Agent-specific seed) · we pass it
        through as ``payload.profile`` + add ``persona_id`` (echoed
        from the upstream agent context where available).
        """
        payload: dict[str, Any] = {}
        if "persona_id" in v1:
            payload["persona_id"] = v1["persona_id"]
        # ``profile`` is the Agent6/Agent1 seed payload (per matrix §2.1).
        if "profile" in v1:
            payload["profile"] = v1["profile"]
        yield envelope(
            event="turn.started",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload=payload,
        )

    async def _on_stage(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``stage`` → liuye ``tool.progress``.

        Field mapping (matrix §4 row 2 + §3 Q1):
        - v1 ``stage`` (string · e.g. ``"parse"``) → liuye ``stage_key``
        - v1 ``message`` (中文 · e.g. ``"解析用户意图..."``) → ``stage_label``
        - v1 ``progress`` (0-1 float) → ``percent`` (0-100 int · ``round(v * 100)``)
        - v1 ``status`` (running/done/warning/error) → liuye 5-enum status
        - v1 ``stage_index`` / ``stage_total`` (optional) → pass-through
        - v1 ``detail`` (optional · free text) → pass-through
        """
        stage_key = v1.get("stage") or v1.get("stage_key") or "unknown"
        stage_label = v1.get("message") or v1.get("stage_label") or stage_key
        # v1 progress is 0-1 float · liuye is 0-100 int (Q1)
        raw_progress = v1.get("progress")
        percent: Optional[int] = None
        if isinstance(raw_progress, (int, float)):
            try:
                percent = max(0, min(100, int(round(float(raw_progress) * 100))))
            except (TypeError, ValueError):
                percent = None
        elif isinstance(v1.get("percent"), (int, float)):
            # already 0-100 (some agents already emit liuye-shaped percent)
            percent = max(0, min(100, int(round(float(v1["percent"])))))

        # Normalise status to the 5-enum (default running).
        status = v1.get("status") or "running"
        if status not in _VALID_PROGRESS_STATUS:
            # ``done`` / ``ok`` / ``success`` legacy variants → ``done``
            status = "done" if status in {"ok", "success", "completed"} else "running"

        payload: dict[str, Any] = {
            "stage_key": stage_key,
            "stage_label": stage_label,
            "status": status,
        }
        if percent is not None:
            payload["percent"] = percent
        if "stage_index" in v1:
            payload["stage_index"] = v1["stage_index"]
        if "stage_total" in v1:
            payload["stage_total"] = v1["stage_total"]
        if "eta_seconds" in v1:
            payload["eta_seconds"] = v1["eta_seconds"]
        if "detail" in v1:
            payload["detail"] = v1["detail"]

        yield envelope(
            event="tool.progress",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload=payload,
            tool_call_id=self._current_tool_call_id,
        )

    async def _on_stream(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``stream`` (token-by-token) → liuye ``message.created`` (first frame).

        Per matrix §4 row 3: subsequent token deltas should go on the
        wire as SSE ``comment:`` lines (NOT counted as events). The
        adapter ONLY emits ``message.created`` once per turn · the rest
        are handled by the SSE bridge in ``api.py`` (it concatenates
        deltas onto the existing message_id without minting a new
        event).
        """
        content = v1.get("content") or v1.get("text") or ""
        if not self._message_started:
            self._message_started = True
            message_id = f"msg_{uuid.uuid4().hex[:16]}"
            yield envelope(
                event="message.created",
                turn_id=turn_id,
                trace_id=self.trace_id,
                payload={
                    "content": content,
                    "role": v1.get("role", "assistant"),
                },
                message_id=message_id,
            )
        # else: subsequent tokens are deltas · NOT emitted as events.

    async def _on_tool_call(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``tool_call`` → liuye ``tool.started``.

        v1 payload typically has ``tool_name`` / ``args``. liuye needs
        ``tool_id`` + ``input`` + ``boundary`` (Cowork or
        Managed_readonly) + ``invoker_id`` (P0-8 R9 audit chain). The
        adapter sets ``tool_call_id`` (new uuid) and remembers it for
        subsequent ``stage`` / ``tool_result`` events.

        ``parent_tool_call_id`` (Cowork→Managed handoff · 必修 #51) is
        passed through when present so e.g. Report → Credit lineage
        survives.
        """
        tool_call_id = (
            v1.get("tool_call_id")
            or v1.get("id")
            or f"tc_{uuid.uuid4().hex[:16]}"
        )
        self._current_tool_call_id = tool_call_id

        payload: dict[str, Any] = {
            "agent": v1.get("agent", self.agent_id),
            "tool_id": v1.get("tool_id") or v1.get("tool_name") or "unknown",
            "input": v1.get("input") or v1.get("args") or {},
            "boundary": v1.get("boundary", "cowork"),
        }
        if "invoker_id" in v1:
            payload["invoker_id"] = v1["invoker_id"]
        if "parent_tool_call_id" in v1:
            payload["parent_tool_call_id"] = v1["parent_tool_call_id"]

        yield envelope(
            event="tool.started",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload=payload,
            tool_call_id=tool_call_id,
        )

    async def _on_tool_result(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``tool_result`` → liuye ``tool.completed``.

        Carries the tool's terminal output + (optional) ``artifact_id``
        when the result materialises an Artifact (channel candidates /
        credit decision / report draft).
        """
        tool_call_id = (
            v1.get("tool_call_id") or self._current_tool_call_id or "tc_unknown"
        )
        payload: dict[str, Any] = {
            "result": v1.get("result") or {},
        }
        artifact_id = v1.get("artifact_id")
        if artifact_id:
            payload["artifact_id"] = artifact_id

        yield envelope(
            event="tool.completed",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload=payload,
            tool_call_id=tool_call_id,
            artifact_id=artifact_id,
        )

    async def _on_done(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``done`` → liuye ``turn.completed``.

        v1 ``done`` is the DoneEnvelope (per ``sse-envelope.md`` §2)
        with ``payload`` carrying the full agent-specific snapshot
        (ChannelPayload / CreditPayload / ReportPayload tails).
        We pass the whole v1 body as ``final_snapshot`` so the client
        gets a single authoritative state object.
        """
        final_snapshot: dict[str, Any] = {}
        # Pass everything but the wire metadata · keeps the snapshot
        # legible without leaking SSE plumbing.
        for k, v in v1.items():
            if k in {"event"}:
                continue
            final_snapshot[k] = v

        # ``ok`` is normalised so downstream consumers (FE banner /
        # ledger pipeline) read a single key regardless of v1 quirks.
        if "ok" not in final_snapshot:
            final_snapshot["ok"] = True

        yield envelope(
            event="turn.completed",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload={"final_snapshot": final_snapshot},
        )

    async def _on_error(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``error`` → liuye ``turn.error`` (TurnErrorPayload 9 fields).

        v1 ``error`` is loosely-typed (``code`` / ``message`` / ``stage``
        / ``traceback``). We compose the strict liuye 9-field shape and
        inject defaults for fields v1 doesn't carry (``retryable`` /
        ``human_hint``).
        """
        seq = _make_seq(turn_id)
        code = v1.get("code") or v1.get("error_code") or "AGENT_ERROR"
        msg = v1.get("message") or v1.get("detail") or "agent error"
        retryable = bool(v1.get("retryable", False))
        # Chinese human hint is required by TurnErrorPayload · default to
        # the upstream message when the agent didn't supply one.
        human_hint = v1.get("human_hint") or msg

        payload = {
            "code": code,
            "message": msg,
            "retryable": retryable,
            "human_hint": human_hint,
            "trace_id": self.trace_id,
            "turn_id": turn_id,
            "seq": seq,
            "tool_call_id": v1.get("tool_call_id") or self._current_tool_call_id,
            "retry_after_ms": v1.get("retry_after_ms"),
            "fallback_available": v1.get("fallback_available"),
        }
        # Strip Nones · liuye payload uses ``extra='forbid'`` so empty
        # optionals are cleaner left out.
        payload = {k: v for k, v in payload.items() if v is not None}

        yield envelope(
            event="turn.error",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload=payload,
            tool_call_id=v1.get("tool_call_id") or self._current_tool_call_id,
            seq=seq,
        )

    async def _on_heartbeat(
        self,
        v1: Mapping[str, Any],
        turn_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """v1 ``heartbeat`` → liuye ``heartbeat`` (15s tick).

        Old agents may or may not emit heartbeats. When they do, we
        pass through. When they don't, the BFF's
        ``orchestrator._stream_skeleton`` injects its own 15s tick.
        """
        yield envelope(
            event="heartbeat",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload={"alive": True},
        )

    # ------------------------------------------------------------------
    # Degraded fallback envelope
    # ------------------------------------------------------------------

    def _error_envelope(
        self,
        turn_id: str,
        *,
        code: str,
        message: str,
    ) -> dict[str, Any]:
        """Compose the standard ``SSE_ADAPTER_FAILED`` envelope.

        Per matrix §4.2 rule 5: any translator failure MUST emit a
        single ``turn.error`` carrying ``fallback_available=true`` so
        the frontend can pull a full snapshot rather than chase the
        broken stream.
        """
        seq = _make_seq(turn_id)
        return envelope(
            event="turn.error",
            turn_id=turn_id,
            trace_id=self.trace_id,
            payload={
                "code": code,
                "message": message,
                "retryable": True,
                "human_hint": "事件流转换失败 · 已切换至完整快照模式",
                "trace_id": self.trace_id,
                "turn_id": turn_id,
                "seq": seq,
                "fallback_available": True,
            },
            seq=seq,
        )


# ---------------------------------------------------------------------------
# v1 event → handler method name dispatch table
# ---------------------------------------------------------------------------

_V1_HANDLERS: dict[str, str] = {
    "profile_loaded": "_on_profile_loaded",
    "stage": "_on_stage",
    "stream": "_on_stream",
    "tool_call": "_on_tool_call",
    "tool_result": "_on_tool_result",
    "done": "_on_done",
    "error": "_on_error",
    "heartbeat": "_on_heartbeat",
}


__all__ = [
    "SseV1ToLiuyeAdapter",
]
