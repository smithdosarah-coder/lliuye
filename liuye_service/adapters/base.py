# -*- coding: utf-8 -*-
"""liuye_service.adapters.base — ``AgentAdapter`` Protocol + shared utilities.

Per W1-backend brief §3 file 9 + ``liuye_service/CLAUDE.md`` §3 + §4 +
``docs/contracts/liuye-sse-event-matrix.md`` §4.

This module is the **abstract contract** the orchestrator uses to talk to
every concrete agent adapter (Cowork + Managed alike). The Phase 1 file
checklist puts 3 Cowork adapters (channel/credit/report) and 3 Managed
stubs (riskctrl/alert/compliance) all behind this Protocol so the
``register_adapter()`` call in ``api.py`` is uniform.

Three responsibilities collapsed here:

1. **AgentAdapter Protocol**: ``start_turn`` / ``dispatch_message`` /
   ``abort_turn`` signatures · the orchestrator never imports a concrete
   adapter class directly. ``api.py`` does the binding.

2. **Per-turn seq counter**: SSE v1 has no ``seq`` (per
   ``docs/contracts/sse-envelope.md`` §1.5) · liuye does (per v3 §2.1
   reconnect rules). The adapter MUST mint a monotonically-increasing
   ``seq`` per ``turn_id``. ``_make_seq(turn_id)`` is the shared
   helper used by both the per-agent HTTP adapters and the SSE v1
   translator.

3. **LIUYE_FIXTURES_PATH loader**: when ``LIUYE_DEMO_MODE=true``
   adapters read JSON fixtures from the configured path (W1-mock-test
   §8 + W1-backend §4.10 PM ratify) instead of hitting the live agent
   HTTP. The default path is ``tests/fixtures/`` · the
   ``LIUYE_FIXTURES_PATH`` env var overrides for staging / blue-green.

We do NOT implement concrete LLM calls in this module · every adapter
that needs an LLM defers to ``shared.llm_caller.LLMCaller`` (per root
§3.6 + ``liuye_service/CLAUDE.md`` §6) · single fallback chain ·
audit-on-every-call.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Mapping,
    Optional,
    Protocol,
)

from liuye_service.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AgentAdapter Protocol (the orchestrator contract)
# ---------------------------------------------------------------------------


class AgentAdapter(Protocol):
    """Common contract for every concrete adapter (Cowork + Managed).

    The orchestrator never imports concrete classes; it programs against
    this Protocol. Cowork adapters stream live SSE events translated
    from agent v1 SSE. Managed adapters raise ``NotImplementedError`` in
    Phase 1 · Phase 2 (Q4 2026) wires them to ``shared/job_runtime/``.

    Each method returns an async iterator of ``LiuyeChatEvent`` dicts
    (already enveloped per v3 §2.1: ``schema_version`` / ``event`` /
    ``turn_id`` / ``trace_id`` / ``seq`` / ``ts`` / ``payload``). The
    SSE bridge in ``api.py`` serialises each event onto the wire.
    """

    agent_id: str  # e.g. 'channel' / 'credit' / 'report' / 'riskctrl' / ...
    boundary: str  # 'cowork' or 'managed_readonly'

    async def start_turn(
        self,
        turn_id: str,
        persona: str,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:  # pragma: no cover · Protocol contract
        """Open a new turn against the underlying agent.

        Cowork adapters typically yield a ``turn.started`` event then
        forward translated v1 events. Managed adapters return after
        submitting a job_id + emit a single ``tool.completed`` carrying
        the job_id (Phase 2).
        """
        ...

    async def dispatch_message(
        self,
        turn_id: str,
        message: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:  # pragma: no cover · Protocol contract
        """Push a user message into an already-started turn.

        Idempotent · re-sending the same message MUST NOT duplicate
        downstream effects (the adapter uses ``dedup_key = (event,
        sha256(payload))`` in the SSE translator).
        """
        ...

    async def abort_turn(
        self,
        turn_id: str,
        reason: str,
    ) -> None:  # pragma: no cover · Protocol contract
        """Tear down adapter-side state and (best-effort) cancel any
        in-flight HTTP request to the underlying agent.

        Called when the orchestrator aborts the turn (permission deny
        / hard error). Silent-fail: any HTTP cancellation error is
        logged but never raised back to the caller.
        """
        ...


# ---------------------------------------------------------------------------
# Per-turn monotonic seq counter (process-local · thread-safe)
# ---------------------------------------------------------------------------


# We keep this as a module-level dict so the SSE v1 translator and the
# HTTP per-agent adapters can share the counter without passing the
# orchestrator handle around. The shape is intentionally dict-like so a
# Redis-backed implementation can drop in for multi-worker scale-out
# (Phase 1 = single FastAPI worker per host).
_SEQ_BY_TURN: dict[str, int] = {}
_SEQ_LOCK = threading.Lock()


def _make_seq(turn_id: str) -> int:
    """Return the next monotonic seq for ``turn_id`` (1-based).

    Thread-safe: FastAPI runs the event loop on one OS thread but
    long-running adapters that drop into a thread pool (httpx blocking
    fallback, fixture file I/O) must not race. We use a plain
    ``threading.Lock`` because the critical section is a dict bump.

    Multi-worker scale-out (uvicorn ``--workers > 1``) needs a Redis
    backend keyed by ``liuye:seq:{turn_id}``. Phase 1 in-memory is
    sufficient for the demo cluster.
    """
    with _SEQ_LOCK:
        nxt = _SEQ_BY_TURN.get(turn_id, 0) + 1
        _SEQ_BY_TURN[turn_id] = nxt
        return nxt


def reset_seq(turn_id: Optional[str] = None) -> None:
    """Clear the seq counter for one turn or all turns.

    Test helper · production code never calls this. The orchestrator
    abort flow leaves the counter dangling so any in-flight delayed
    SSE frame still has its seq when it lands.
    """
    with _SEQ_LOCK:
        if turn_id is None:
            _SEQ_BY_TURN.clear()
        else:
            _SEQ_BY_TURN.pop(turn_id, None)


# ---------------------------------------------------------------------------
# LIUYE_FIXTURES_PATH loader (DEMO_MODE fixture replay)
# ---------------------------------------------------------------------------


class FixtureLoadError(RuntimeError):
    """Raised when a fixture JSON is missing or malformed.

    Adapters convert this into a ``turn.error
    code=DEMO_FIXTURE_MISSING`` rather than crashing the BFF · keeps
    the user-facing UI honest about demo-vs-live mode.
    """


def fixtures_root() -> Path:
    """Resolve the on-disk fixtures directory · ``LIUYE_FIXTURES_PATH`` wins.

    Default = ``credit_report_agent_work/tests/fixtures/`` (W1-mock-test
    SSOT per W1-backend brief §4.10 PM ratify). Backend adapters MUST
    NOT keep a second copy under ``liuye_service/fixtures/demo/`` (drift
    risk).
    """
    return Path(get_settings().fixtures_path).expanduser().resolve()


def load_fixture(name: str) -> dict[str, Any]:
    """Read a fixture JSON file by stem name · e.g. ``load_fixture("channel_5candidates")``.

    Args:
        name: stem (no ``.json`` suffix). Path components are rejected
              to keep the loader from walking outside the configured
              fixtures root.

    Raises:
        FixtureLoadError: file missing, unreadable, or not valid JSON.
    """
    if "/" in name or "\\" in name or name.startswith(".."):
        raise FixtureLoadError(
            f"fixture name {name!r} contains a path component · refusing to load",
        )
    target = fixtures_root() / f"{name}.json"
    if not target.exists():
        raise FixtureLoadError(
            f"fixture {name!r} not found at {target}",
        )
    try:
        with target.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureLoadError(
            f"failed to read fixture {name!r}: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Envelope helper · used by every adapter when it emits a liuye event
# ---------------------------------------------------------------------------


# Hookable timestamp factory so tests can freeze time without monkey
# patching ``datetime`` globally.
from datetime import datetime, timezone

TimestampFactory = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def envelope(
    *,
    event: str,
    turn_id: str,
    trace_id: str,
    payload: Mapping[str, Any],
    tool_call_id: Optional[str] = None,
    artifact_id: Optional[str] = None,
    message_id: Optional[str] = None,
    seq: Optional[int] = None,
    ts_factory: TimestampFactory = _utc_now,
) -> dict[str, Any]:
    """Build a liuye-shaped SSE envelope · adds ``seq`` via ``_make_seq``.

    Per ``protocols/generated.py:LiuyeChatEvent3`` + matrix §1 layout:

    - ``schema_version`` fixed ``"1"``
    - ``seq`` monotonic per turn_id (1-based · auto if not supplied)
    - ``ts`` ISO 8601 UTC · ``datetime.isoformat()``
    - optional ``tool_call_id`` / ``artifact_id`` / ``message_id`` per
      event type (see matrix §1 table)
    """
    body: dict[str, Any] = {
        "schema_version": "1",
        "event": event,
        "turn_id": turn_id,
        "trace_id": trace_id,
        "seq": seq if seq is not None else _make_seq(turn_id),
        "ts": ts_factory().isoformat(),
        "payload": dict(payload),
    }
    if tool_call_id is not None:
        body["tool_call_id"] = tool_call_id
    if artifact_id is not None:
        body["artifact_id"] = artifact_id
    if message_id is not None:
        body["message_id"] = message_id
    return body


# ---------------------------------------------------------------------------
# Type alias for the adapter dispatch callable (used by orchestrator)
# ---------------------------------------------------------------------------


EmitFn = Callable[..., Awaitable[None]]


__all__ = [
    "AgentAdapter",
    "EmitFn",
    "FixtureLoadError",
    "TimestampFactory",
    "envelope",
    "fixtures_root",
    "load_fixture",
    "_make_seq",
    "reset_seq",
]
