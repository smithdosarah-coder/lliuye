# -*- coding: utf-8 -*-
"""liuye_service.adapters.cowork_base — ``CoworkHttpAdapter`` base class.

Per ROI #2 brief (``D:/second-brain/wiki/concepts/CoworkHttpAdapter基类抽取-2026-05-21.md``).
Hoists the ~80 % duplicated skeleton across ``channel.py`` / ``credit.py``
/ ``report.py`` into one base. The remaining 20 % (real business
differences: per-agent ``_synthesise_*_v1_frames``) stays in subclasses
as an abstract hook.

Design (brief §B + §C):

- ClassVar-driven contract — subclass declares 8 attributes; base
  ``__init_subclass__`` validates them at import time so a missing
  attr crashes loudly instead of waiting for the first turn to blow
  up.
- Single abstract hook: ``_synthesise_demo_v1_frames`` covers the
  3 distinct demo flows (channel 5-stage candidates / credit
  decision / report 5-stage long pipeline).
- Explicit ``CoworkHttpAdapter(AgentAdapter)`` so the Protocol from
  ``base.py:63`` is **enforced** rather than duck-typed (closes the
  Protocol gap noted in brief §F.2).
- SSE parsing lives in ``_sse_v1_parser.iter_sse_v1`` — base uses it
  here so subclasses inherit a clean import path (closes the lateral
  import anti-pattern in brief §F.1).

Deviations from brief:

1. ``_resolve_backend_url`` keeps the legacy ``agent_id`` parameter
   (defaulting to ``self.agent_id``) instead of brief's no-arg
   signature. Reason: existing call sites in channel/credit/report
   pass ``self.agent_id`` explicitly; preserving the parameter keeps
   Step 2 byte-equivalence guarantees easy to prove. The brief's
   intent — using ``self.BACKEND_URL_DEFAULT`` as the sentinel for
   "constructor injection vs env" — is honoured.

2. Demo-mode dispatch (in ``_run``) is wrapped in the same
   ``asyncio.TimeoutError`` / ``httpx.HTTPError`` try/except as live
   mode in the source files. The originals only wrapped live; demo
   has no httpx call so neither exception can fire from inside it.
   To stay byte-equivalent we keep the try/except **only around
   live**, demo returns early from the top-of-``_run`` ``if
   get_settings().demo_mode`` branch (same shape as channel.py:184-189).

3. The shared ``_ENDPOINT_MAP`` constant is **dropped** from the
   base — brief §D mandates ``ENDPOINT_PATH`` ClassVar instead. Each
   subclass declares its own path directly; the brittle "look up by
   agent_id" indirection in current channel.py:73-77 / credit.py:63-67
   / report.py:58-62 disappears. Step 2 will remove these dict
   literals from subclasses.

Step 1 (this file) does **not** modify any existing adapter — it only
provides the base for Step 2 to subclass against.
"""
from __future__ import annotations

import asyncio
import logging
from typing import (
    Any,
    AsyncIterator,
    ClassVar,
    Literal,
    Mapping,
    Optional,
)

import httpx

from liuye_service.adapters._sse_v1_parser import iter_sse_v1
from liuye_service.adapters.base import (
    AgentAdapter,
    FixtureLoadError,
    _make_seq,
    envelope,
    load_fixture,
)
from liuye_service.adapters.sse_v1_to_liuye import SseV1ToLiuyeAdapter
from liuye_service.audit import record_liuye_decision
from liuye_service.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default HTTP timeout (channel + credit use this; report overrides to 60s)
# ---------------------------------------------------------------------------

_DEFAULT_HTTP_TIMEOUT = httpx.Timeout(5.0, read=30.0)


# ---------------------------------------------------------------------------
# CoworkHttpAdapter — shared base for channel / credit / report
# ---------------------------------------------------------------------------


class CoworkHttpAdapter(AgentAdapter):
    """Shared base for Cowork HTTP adapters (channel / credit / report).

    Subclass contract (all 8 ClassVars required; validated at import time):

    - ``AGENT_ID``            — short id, e.g. ``"channel"``
    - ``BACKEND_URL_DEFAULT`` — legacy mock-test default URL (kept as
      the sentinel for "constructor injection vs env lookup")
    - ``ENDPOINT_PATH``       — concrete backend HTTP path
    - ``HTTP_TIMEOUT``        — ``httpx.Timeout`` (channel/credit
      default = ``Timeout(5.0, read=30.0)``, report = ``read=60.0``)
    - ``DEMO_FIXTURE_STEM``   — fixture file stem (no ``.json``)
    - ``RETENTION_CLASS``     — ledger retention bucket
    - ``HUMAN_HINT_AGENT_LABEL`` — Chinese short label for error envelope
      (``"获客"`` / ``"授信"`` / ``"报告"``)
    - ``FORWARDS_PARENT_TOOL_CALL_ID`` — whether to copy
      ``parent_tool_call_id`` into the wire body in live mode
      (``False`` for channel, ``True`` for credit + report)

    Subclass MUST implement:

    - ``_synthesise_demo_v1_frames(snapshot, artifact_id, persona_id,
      payload) -> list[dict]`` — builds the per-agent v1 frame sequence.

    Public API matches the ``AgentAdapter`` Protocol (``start_turn`` /
    ``dispatch_message`` / ``abort_turn``).
    """

    # ------- ClassVar contract (subclass MUST set these) ----------------

    AGENT_ID: ClassVar[str]
    BACKEND_URL_DEFAULT: ClassVar[str]
    ENDPOINT_PATH: ClassVar[str]
    HTTP_TIMEOUT: ClassVar[httpx.Timeout] = _DEFAULT_HTTP_TIMEOUT
    DEMO_FIXTURE_STEM: ClassVar[str]
    RETENTION_CLASS: ClassVar[Literal["short", "standard", "long"]]
    HUMAN_HINT_AGENT_LABEL: ClassVar[str]
    FORWARDS_PARENT_TOOL_CALL_ID: ClassVar[bool]

    # ------- AgentAdapter Protocol instance attrs (mirror legacy adapters) -

    boundary: ClassVar[str] = "cowork"

    # The Protocol declares ``agent_id`` as an instance attr; we expose
    # it as a property that returns ``self.AGENT_ID`` so the value
    # tracks the ClassVar and there is exactly one source of truth.

    @property
    def agent_id(self) -> str:  # type: ignore[override]
        return self.AGENT_ID

    # ------- subclass-validation hook -----------------------------------

    _REQUIRED_CLASSVARS: ClassVar[tuple[str, ...]] = (
        "AGENT_ID",
        "BACKEND_URL_DEFAULT",
        "ENDPOINT_PATH",
        "HTTP_TIMEOUT",
        "DEMO_FIXTURE_STEM",
        "RETENTION_CLASS",
        "HUMAN_HINT_AGENT_LABEL",
        "FORWARDS_PARENT_TOOL_CALL_ID",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Fail loudly at import time if subclass forgot a ClassVar.

        Brief §C mandate: ``Python ClassVar[...] 标注 + base class
        __init_subclass__ 钩子做 schema 校验(subclass 漏填某个 attr →
        import 时报错而非运行时崩)``.

        We treat ``FORWARDS_PARENT_TOOL_CALL_ID`` carefully — a value
        of ``False`` is legitimate (channel sets it that way) so we
        check membership in the class's own MRO chain rather than
        truthiness.
        """
        super().__init_subclass__(**kwargs)
        # Allow further subclasses below an intermediate base (Phase 2
        # may layer ``CoworkHttpAdapterWithRetry`` etc.) — only validate
        # when the subclass is concrete (no further subclassing of
        # CoworkHttpAdapter itself).
        missing: list[str] = []
        for attr in cls._REQUIRED_CLASSVARS:
            # Walk MRO and look for an explicit assignment (not just
            # the annotation). The brief example uses ``hasattr`` but
            # that would treat the unset ClassVar annotation on the
            # base as "present"; we instead require the attribute be
            # defined somewhere in the MRO chain above ``object`` and
            # below ``CoworkHttpAdapter`` (exclusive).
            value = cls.__dict__.get(attr)
            if value is not None:
                continue
            # Inherited from an intermediate subclass? Walk MRO.
            for ancestor in cls.__mro__[1:]:
                if ancestor is CoworkHttpAdapter:
                    break
                if attr in ancestor.__dict__:
                    value = ancestor.__dict__[attr]
                    break
            # HTTP_TIMEOUT has a base-class default — that's fine.
            if value is None and attr == "HTTP_TIMEOUT":
                value = _DEFAULT_HTTP_TIMEOUT
            if value is None:
                missing.append(attr)
        if missing:
            raise TypeError(
                f"{cls.__name__} 漏填 CoworkHttpAdapter ClassVar: {missing!r} · "
                "参见 liuye_service/adapters/cowork_base.py docstring",
            )

    # ------- constructor ------------------------------------------------

    def __init__(
        self,
        *,
        backend_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.backend_url = backend_url or self.BACKEND_URL_DEFAULT
        # Tests can inject a transport-mocked client; production
        # instantiates lazily inside the request to keep startup fast.
        self._http_client = http_client
        # Per-turn translator instances; we discard on turn end.
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
        """Initiate the turn; stream translated liuye events."""
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
        """Push a follow-up message into an already-started turn."""
        translator = self._translators.get(turn_id)
        if translator is None:
            yield self._adapter_error(
                turn_id,
                trace_id=message.get("trace_id") or "trace_unknown",
                code="TURN_NOT_STARTED",
                message=f"{self.agent_id} adapter has no translator for turn_id={turn_id}",
            )
            return
        async for evt in self._run(
            turn_id=turn_id,
            payload=message,
            trace_id=translator.trace_id,
        ):
            yield evt

    async def abort_turn(self, turn_id: str, reason: str) -> None:
        """Best-effort teardown; drop translator state."""
        translator = self._translators.pop(turn_id, None)
        if translator is None:
            return
        logger.info(
            "[%s_adapter] abort_turn turn_id=%s reason=%s",
            self.agent_id, turn_id, reason,
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
        """Run the turn · DEMO_MODE replay or live HTTP.

        Mirrors ``channel.py:_run`` byte-for-byte (modulo agent label
        in error messages). DEMO branch returns early; live branch
        wraps ``_run_live`` in the standard ``asyncio.TimeoutError`` +
        ``httpx.HTTPError`` exception envelope.
        """
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
                message=f"{self.agent_id} backend exceeded SLA · backend_url={self.backend_url}",
            )
        except httpx.HTTPError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=trace_id,
                code="ADAPTER_HTTP_ERROR",
                message=f"{self.agent_id} HTTP error: {exc}",
            )

    async def _run_demo(
        self,
        *,
        turn_id: str,
        translator: SseV1ToLiuyeAdapter,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay the W1-mock-test fixture as v1 frames; translate to liuye.

        Delegates the per-agent frame synthesis to the subclass hook
        ``_synthesise_demo_v1_frames`` — the only real business diff.
        """
        try:
            fixture = load_fixture(self.DEMO_FIXTURE_STEM)
        except FixtureLoadError as exc:
            yield self._adapter_error(
                turn_id,
                trace_id=translator.trace_id,
                code="DEMO_FIXTURE_MISSING",
                message=str(exc),
            )
            return

        snapshot = fixture.get("snapshot", fixture)
        artifact_id = fixture.get("id", f"art_{self.agent_id}_demo")
        v1_frames = await self._synthesise_demo_v1_frames(
            snapshot=snapshot,
            artifact_id=artifact_id,
            persona_id=str(payload.get("persona_id", "")),
            payload=payload,
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
        """Live HTTP SSE bridge · POST + iterate v1 frames.

        Body construction:

        - mandatory: ``turn_id`` + ``trace_id`` + payload pass-through
        - conditional: ``parent_tool_call_id`` only when
          ``FORWARDS_PARENT_TOOL_CALL_ID`` is ``True`` (channel skips,
          credit + report forward)
        """
        client = self._http_client or httpx.AsyncClient(timeout=self.HTTP_TIMEOUT)
        owns_client = self._http_client is None
        try:
            base = self._resolve_backend_url(self.agent_id).rstrip("/")
            url = f"{base}{self.ENDPOINT_PATH}"
            body: dict[str, Any] = {
                "turn_id": turn_id,
                "trace_id": translator.trace_id,
                **dict(payload),
            }
            if self.FORWARDS_PARENT_TOOL_CALL_ID:
                parent_tcid = payload.get("parent_tool_call_id")
                if parent_tcid:
                    body["parent_tool_call_id"] = parent_tcid
            async with client.stream(
                "POST", url, json=body, timeout=self.HTTP_TIMEOUT,
            ) as response:
                if response.status_code != 200:
                    yield self._adapter_error(
                        turn_id,
                        trace_id=translator.trace_id,
                        code="ADAPTER_HTTP_ERROR",
                        message=(
                            f"{self.agent_id} backend returned {response.status_code} "
                            f"· url={url}"
                        ),
                    )
                    return
                async for v1_event in iter_sse_v1(response):
                    async for liuye_evt in translator.translate(v1_event, turn_id):
                        yield liuye_evt
        finally:
            if owns_client:
                await client.aclose()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_backend_url(self, agent_id: Optional[str] = None) -> str:
        """Per-adapter URL 覆写 (W2 brief §4.1 + perfect-check fix #2).

        Resolution order:

        1. Constructor-supplied ``backend_url`` (test injection · highest
           priority since tests need deterministic URLs). Detected by
           comparing against ``self.BACKEND_URL_DEFAULT`` — if they
           differ, the caller injected a custom URL.
        2. ``Settings.resolve_backend_url(agent_id)`` (env-driven · D10
           hybrid 彩排 ``LIUYE_BACKEND_{AGENT}_URL > LIUYE_BACKEND_BASE_URL``).

        The ``agent_id`` parameter defaults to ``self.agent_id`` for
        convenience but is kept on the signature so existing call sites
        (``self._resolve_backend_url(self.agent_id)`` in channel/credit/
        report) work unchanged during the Step 2 migration.
        """
        if (
            self.backend_url
            and self.backend_url != self.BACKEND_URL_DEFAULT
        ):
            return self.backend_url
        target = agent_id or self.agent_id
        return get_settings().resolve_backend_url(target)

    def _adapter_error(
        self,
        turn_id: str,
        *,
        trace_id: str,
        code: str,
        message: str,
    ) -> dict[str, Any]:
        """Build the ``turn.error`` envelope.

        The ``human_hint`` is composed from ``HUMAN_HINT_AGENT_LABEL``
        — that's the only string that varies across the 3 Cowork
        adapters (``"获客"`` vs ``"授信"`` vs ``"报告"``).
        """
        seq = _make_seq(turn_id)
        return envelope(
            event="turn.error",
            turn_id=turn_id,
            trace_id=trace_id,
            payload={
                "code": code,
                "message": message,
                "retryable": True,
                "human_hint": f"{self.HUMAN_HINT_AGENT_LABEL} Agent 暂时不可用 · 已切换至降级模式",
                "trace_id": trace_id,
                "turn_id": turn_id,
                "seq": seq,
                "fallback_available": True,
            },
            seq=seq,
        )

    # ------------------------------------------------------------------
    # Audit chain helper · called from orchestrator post-turn
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
        """Drop a ``ledger_decision`` row · retention bucket from class attr.

        Retention class is per-agent (channel=short / credit=standard /
        report=long · root §3.7.5); endpoint string is per-agent
        (``ENDPOINT_PATH``).
        """
        return record_liuye_decision(
            agent_id=self.agent_id,
            endpoint=self.ENDPOINT_PATH,
            input_payload=dict(input_payload),
            output_payload=dict(output_payload),
            evidence_chain=dict(evidence_chain),
            decision_id=None,
            jurisdiction=get_settings().ledger_jurisdiction,
            retention_class=self.RETENTION_CLASS,
            subject_id=subject_id,
            parent_turn_id=parent_turn_id,
        )

    # ------------------------------------------------------------------
    # Abstract hook · subclass must implement
    # ------------------------------------------------------------------

    async def _synthesise_demo_v1_frames(
        self,
        *,
        snapshot: Mapping[str, Any],
        artifact_id: str,
        persona_id: str,
        payload: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Build the per-agent v1 frame sequence for DEMO_MODE.

        Subclass MUST override. The frame list is iterated in
        ``_run_demo`` and each frame is fed through
        ``SseV1ToLiuyeAdapter.translate``.

        ``payload`` is the full original turn payload so the subclass
        can pick out fields it needs (e.g. ``parent_tool_call_id`` for
        credit handoff). Channel ignores ``payload`` beyond
        ``persona_id``; credit reads ``parent_tool_call_id``; report
        will eventually read its own fields.

        We mark the hook ``async`` so subclasses that need to call an
        ``await``able (rare in DEMO_MODE but possible — e.g. lazy
        fixture decryption in production) don't have to change the
        signature later.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _synthesise_demo_v1_frames",
        )


__all__ = ["CoworkHttpAdapter"]
