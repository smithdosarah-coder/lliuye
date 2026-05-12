# -*- coding: utf-8 -*-
"""liuye_service.adapters.riskctrl — Agent2 (Riskctrl · 风控) **Managed stub**.

Per W1-backend brief §3 file 9-13 + ``liuye_service/CLAUDE.md`` §4 + root
§3.1.1 + matrix §2.6 + ``CLAUDE.md`` §3.7.1 (Q-040 MAX_ROWS=50000).

**Phase 1 = stub**. The riskctrl agent runs Managed
(``boundary='managed_readonly'``) batch tasks — DSL backtest on ≥ 50 000
sample rows takes ≥ 1 min, well past the Cowork 5s p95 SLA. Phase 1
ships the BFF endpoint surface without the long-poll mechanics; Phase 2
(Q4 2026) plumbs ``shared/job_runtime/`` so the adapter:

1. Submits a ``riskctrl_backtest`` job → returns ``job_id`` + ETA
2. Polls / receives webhook on completion
3. Reads the artifact (docx / xlsx / pdf via
   ``agent_riskctrl/exports.py`` triplet)
4. Emits the final ``turn.completed`` + ``artifact.patch`` envelope

Until Phase 2 the orchestrator never registers a concrete adapter for
riskctrl · any incoming turn for ``agent_id='riskctrl'`` hits this stub
which raises ``NotImplementedError`` with a clear pointer to the Phase
2 milestone. The route registration in ``api.py`` still mounts the
endpoint so the frontend sees a HTTP 501 rather than 404 (mode-symmetry
per matrix §2.6 doc).

Cowork → Managed handoff lineage: when Agent3 Cowork DSL generation
(matrix §2.6 Scenario A Turn 1) needs to spawn this Managed backtest,
it should pass ``parent_tool_call_id`` so the audit chain stays
unbroken. The stub accepts the kwarg in its signature but ignores it
until Phase 2.

References:
- root §3.1.1 Cowork vs Managed boundary
- root §3.7.1 ``MAX_ROWS=50000`` hardline (Q-040 Demo blocker)
- matrix §2.6 Scenario A/B/C (DSL gen → backtest → artifact triplet)
- v3 spec §1 Phase 1 scope · Managed in Phase 2
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Mapping, NoReturn

logger = logging.getLogger(__name__)


RISKCTRL_AGENT_ID = "riskctrl"
RISKCTRL_ENDPOINT = "/api/riskctrl/backtest"  # Managed · returns job_id (Phase 2)


def _phase2_message() -> str:
    """Standard error message · used in every method so the trace stays uniform."""
    return (
        "agent=riskctrl is Managed (job_id + poll · ≥ 1 min backtest) · "
        "Phase 1 BFF does not implement live dispatch · see root §3.1.1 + "
        "matrix §2.6 + W1-backend §11 · ships Phase 2 (Q4 2026 · shared/job_runtime)"
    )


class RiskctrlAdapter:
    """Managed-mode placeholder · raises ``NotImplementedError`` on every dispatch.

    The class exists so ``register_adapter`` in the orchestrator can
    bind a stub at startup; the orchestrator MAY also skip registration
    when ``Settings.managed_phase < 2`` (no env flag yet · Phase 2
    introduces it). Frontend sees HTTP 501 from ``api.py`` when the
    turn is dispatched.
    """

    agent_id = RISKCTRL_AGENT_ID
    boundary = "managed_readonly"

    def __init__(self, **_kwargs: Any) -> None:
        # Accept any constructor kwargs (e.g. backend_url) so the
        # registration plumbing stays uniform with the Cowork adapters
        # · the values are unused in Phase 1.
        pass

    async def start_turn(
        self,
        turn_id: str,
        persona: str,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:  # pragma: no cover · stub
        self._raise(turn_id)
        if False:  # pragma: no cover · for typing the async generator
            yield {}

    async def dispatch_message(
        self,
        turn_id: str,
        message: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:  # pragma: no cover · stub
        self._raise(turn_id)
        if False:  # pragma: no cover · typing fixup
            yield {}

    async def abort_turn(
        self, turn_id: str, reason: str,
    ) -> None:  # pragma: no cover · stub
        logger.info(
            "[riskctrl_adapter:stub] abort_turn ignored · turn_id=%s reason=%s",
            turn_id, reason,
        )

    def _raise(self, turn_id: str) -> NoReturn:
        raise NotImplementedError(
            f"{_phase2_message()} · turn_id={turn_id}",
        )


__all__ = [
    "RISKCTRL_AGENT_ID",
    "RISKCTRL_ENDPOINT",
    "RiskctrlAdapter",
]
