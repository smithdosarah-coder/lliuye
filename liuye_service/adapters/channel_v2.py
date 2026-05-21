# -*- coding: utf-8 -*-
"""liuye_service.adapters.channel_v2 — ChannelAdapter Step 2 影子改写.

Per ROI #2 Step 2 影子改写 (shadow rewrite · 不直切 prod):

- Subclass of ``CoworkHttpAdapter`` (declared in
  ``liuye_service/adapters/cowork_base.py``) reducing channel.py's
  530-line implementation to ~120 lines (~78 % reduction).
- **Lives alongside** the legacy ``ChannelAdapter`` (still in
  ``channel.py``). Production routing is NOT changed by this file;
  switching V1→V2 is a one-line change deferred to user review (see
  TODO at the bottom of this docstring).

Why shadow rather than direct-replace (Codex R2 R2.1 第1条):

> "ROI#2:现在不直切 prod;可派生影子改写。base 门禁只证明基类,非
>  channel 门禁;prod risk 中高。"

Step 1 (base) PASS-gated only the base contract — it did NOT prove that
the rewritten channel preserves byte-for-byte behaviour against the
original. Byte-equivalence is proven in
``tests/unit/adapters/test_channel_v2_equivalence.py`` BEFORE any
production switchover.

Switchover plan (deferred to user):

1. Run ``pytest tests/unit/adapters/test_channel_v2_equivalence.py``;
   confirm 0 frame diffs across all scenarios (demo + live mock).
2. Pick ONE of:
   - **Alias** (low risk): add ``ChannelAdapter = ChannelAdapterV2`` at
     the bottom of ``channel.py``, keep V1 def around for rollback.
   - **Import rewrite** (cleaner): change ``api.py`` adapter
     registration to import from ``channel_v2`` directly.
3. Re-run the full adapter test suite + e2e SSE matrix.
4. After 1 prod day with V2, delete ``channel.py`` body and keep only
   a thin re-export stub.

Constraints honoured:

- **No edit to** ``channel.py`` (V1 untouched · rollback is reverting
  the V2 alias / import switch).
- **No edit to** ``cowork_base.py`` (base contract frozen post Step 1).
- Demo synthesiser reuses ``channel._synthesise_channel_v1_frames`` so
  there is exactly one source of truth for the demo frame sequence.
"""
from __future__ import annotations

from typing import Any, ClassVar, Literal, Mapping

import httpx

from liuye_service.adapters.channel import _synthesise_channel_v1_frames
from liuye_service.adapters.cowork_base import CoworkHttpAdapter


class ChannelAdapterV2(CoworkHttpAdapter):
    """Cowork SSE adapter for the channel (Agent1) backend · V2 影子实现.

    Behavioural contract matches ``liuye_service.adapters.channel.ChannelAdapter``
    1:1; byte-equivalence is proven by
    ``tests/unit/adapters/test_channel_v2_equivalence.py``.

    All inherited Protocol surface (``start_turn`` / ``dispatch_message``
    / ``abort_turn``), live HTTP body construction, demo dispatch, error
    envelope, and audit chain helper come from ``CoworkHttpAdapter``.
    This subclass adds only:

    1. The 8 ClassVar values that identify the channel agent.
    2. The ``_synthesise_demo_v1_frames`` hook implementation, which
       delegates to the canonical ``_synthesise_channel_v1_frames``
       function (still in ``channel.py``) so the demo frame sequence
       has exactly one source of truth.
    """

    # ------- 8 ClassVar contract (mirrors channel.py constants) ---------

    AGENT_ID: ClassVar[str] = "channel"
    # Legacy mock-test :8001 default · constructor injection of a
    # different URL switches the resolver into "explicit override" mode
    # (see ``CoworkHttpAdapter._resolve_backend_url``).
    BACKEND_URL_DEFAULT: ClassVar[str] = "http://localhost:8001"
    ENDPOINT_PATH: ClassVar[str] = "/api/channel/run"
    # Cowork SLA per root §3.1.1 · p95 < 5s · 30s read headroom for SSE.
    HTTP_TIMEOUT: ClassVar[httpx.Timeout] = httpx.Timeout(5.0, read=30.0)
    DEMO_FIXTURE_STEM: ClassVar[str] = "channel_5candidates"
    # Candidates are not a decision · 90d retention (root §3.7.5).
    RETENTION_CLASS: ClassVar[Literal["short", "standard", "long"]] = "short"
    HUMAN_HINT_AGENT_LABEL: ClassVar[str] = "获客"
    # Channel does NOT forward parent_tool_call_id explicitly (it has
    # no parent · channel is the first hop). Credit + report both
    # forward (they're downstream of channel).
    FORWARDS_PARENT_TOOL_CALL_ID: ClassVar[bool] = False

    # ------- Abstract hook implementation -------------------------------

    async def _synthesise_demo_v1_frames(  # type: ignore[override]
        self,
        *,
        snapshot: Mapping[str, Any],
        artifact_id: str,
        persona_id: str,
        payload: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Build the channel demo v1 frame sequence.

        Delegates to the canonical ``_synthesise_channel_v1_frames``
        helper still defined in ``channel.py`` — same function the
        legacy ``ChannelAdapter`` calls. This guarantees V2 emits an
        identical frame list for the same snapshot input (proven by
        ``test_demo_frame_sequence_byte_equivalent``).

        ``payload`` is accepted to satisfy the base hook signature but
        is unused beyond ``persona_id`` extraction (channel ignores
        parent_tool_call_id et al. · see ClassVar above).
        """
        # Default persona_id matches channel.py:244 fallback.
        effective_persona = persona_id or "rm-wangzhe-east"
        return _synthesise_channel_v1_frames(
            snapshot=snapshot,
            artifact_id=artifact_id,
            persona_id=effective_persona,
        )


__all__ = ["ChannelAdapterV2"]
