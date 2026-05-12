# -*- coding: utf-8 -*-
"""liuye_service.trace — distributed trace context helper.

Per W1-backend brief §3 file 3 + ``liuye_service/CLAUDE.md`` §1.

``trace_id`` is the *single* correlation key across:

- BFF orchestrator + adapters (this module)
- 6 backend agents (each ``agent_*/api.py`` already emits ``trace_id`` in SSE envelope)
- ``audit_service.recorder.LLMCall`` (per-call audit row)
- ``shared.decision_ledger.LedgerEntry`` (per-decision row · jurisdiction-bound)

The new frontend additionally has a ``liuye_session_id`` (long-lived ·
correlates a user's session across many turns) and a ``turn_id`` (one
SSE stream per turn · per v3 §2.1) and an optional ``tool_call_id``
(one ToolCall envelope per backend tool invocation · per v3 §2.3).

This module is intentionally framework-free (no FastAPI imports) so it
can be reused by both the request lifecycle and the background outbox
worker without circular imports.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Mapping, Optional

# ---------------------------------------------------------------------------
# Header names · used by adapter + frontend SSE EventSource reconnect
# ---------------------------------------------------------------------------

HEADER_LIUYE_SESSION_ID = "X-Liuye-Session-Id"
HEADER_TRACE_ID = "X-Trace-Id"
HEADER_TURN_ID = "X-Liuye-Turn-Id"
HEADER_TOOL_CALL_ID = "X-Liuye-Tool-Call-Id"


def _new_id(prefix: str) -> str:
    """Generate a stable, traceable id prefixed for log greppability."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


@dataclass(frozen=True)
class LiuyeTraceContext:
    """Immutable correlation envelope · passed through request / orchestrator / adapter.

    Frozen so a downstream task cannot accidentally mutate the trace id
    halfway through a turn (which would silently break audit chain). Use
    ``replace(ctx, turn_id="...")`` or one of the helpers to derive a
    new context.
    """

    trace_id: str = field(default_factory=lambda: _new_id("trace"))
    liuye_session_id: str = field(default_factory=lambda: _new_id("sess"))
    turn_id: Optional[str] = None
    tool_call_id: Optional[str] = None

    def with_turn(self, turn_id: str) -> "LiuyeTraceContext":
        """Derive a child context bound to ``turn_id`` · keeps trace_id + session."""
        return LiuyeTraceContext(
            trace_id=self.trace_id,
            liuye_session_id=self.liuye_session_id,
            turn_id=turn_id,
            tool_call_id=None,  # reset · new turn = new tool_call chain
        )

    def with_tool_call(self, tool_call_id: str) -> "LiuyeTraceContext":
        """Derive a child context for a specific ToolCall · keeps trace + session + turn."""
        return LiuyeTraceContext(
            trace_id=self.trace_id,
            liuye_session_id=self.liuye_session_id,
            turn_id=self.turn_id,
            tool_call_id=tool_call_id,
        )

    def to_response_headers(self) -> dict[str, str]:
        """Echo trace fields back to the client (frontend uses for log dedup)."""
        out: dict[str, str] = {
            HEADER_TRACE_ID: self.trace_id,
            HEADER_LIUYE_SESSION_ID: self.liuye_session_id,
        }
        if self.turn_id:
            out[HEADER_TURN_ID] = self.turn_id
        if self.tool_call_id:
            out[HEADER_TOOL_CALL_ID] = self.tool_call_id
        return out


def new_trace_context(
    *,
    liuye_session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> LiuyeTraceContext:
    """Mint a fresh trace context · used at the start of a new turn.

    Args:
        liuye_session_id: optional · reuse an existing session (RM stays logged-in
            across turns). Mint a new one on first request.
        trace_id: optional · let an upstream gateway (Cloudflare / nginx) pin the
            trace; otherwise mint locally.
    """
    return LiuyeTraceContext(
        trace_id=trace_id or _new_id("trace"),
        liuye_session_id=liuye_session_id or _new_id("sess"),
    )


def from_request_headers(headers: Mapping[str, str]) -> LiuyeTraceContext:
    """Reconstruct a trace context from inbound HTTP headers.

    Accepts both canonical (``X-Trace-Id``) and lower-case keys (FastAPI
    normalizes inbound to lower-case). Missing fields trigger a fresh
    mint so downstream code never sees an empty trace_id.
    """
    # Build a lower-case view once so case-insensitive lookups don't allocate
    # repeatedly.
    norm = {k.lower(): v for k, v in headers.items()}

    def _get(name: str) -> str | None:
        return norm.get(name.lower())

    return LiuyeTraceContext(
        trace_id=_get(HEADER_TRACE_ID) or _new_id("trace"),
        liuye_session_id=_get(HEADER_LIUYE_SESSION_ID) or _new_id("sess"),
        turn_id=_get(HEADER_TURN_ID),
        tool_call_id=_get(HEADER_TOOL_CALL_ID),
    )


__all__ = [
    "HEADER_LIUYE_SESSION_ID",
    "HEADER_TOOL_CALL_ID",
    "HEADER_TRACE_ID",
    "HEADER_TURN_ID",
    "LiuyeTraceContext",
    "from_request_headers",
    "new_trace_context",
]
