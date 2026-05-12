# -*- coding: utf-8 -*-
"""liuye_service.adapters.compliance — Agent5 (Compliance · 合规) **Managed stub**.

Per W1-backend brief §3 file 9-13 + ``liuye_service/CLAUDE.md`` §4 + root
§3.1.1 + matrix §2.5.

**Phase 1 = stub**. Compliance is a Managed agent triggered by policy
publication events (银保监 / 央行 / 内规变更 · 批量 N 业务线扫). Matrix
§2.5 documents two scenarios:

- Scenario A — single policy event → conflict-point clipboard (≥ 1 min
  matrix scan)
- Scenario B — multi-business matrix scan (6 business lines · chunked
  artifact patches)

Both exceed Cowork 5s p95 SLA. Phase 2 (Q4 2026) wires
``shared/job_runtime/`` so the adapter:

1. Submits a ``compliance_policy_scan`` / ``compliance_matrix_scan``
   job → returns ``job_id`` + ``estimated_seconds``
2. Receives webhook on completion → new turn
3. Reads the artifact (conflict_points + matrix_scan + draft_revision)
   from ``data/liuye/jobs/<job_id>/``
4. Persists the decision via ``shared.decision_ledger`` (retention
   ``standard`` 5y per root §3.7.5 · 银保监 archive requirement)

Until Phase 2 the adapter raises ``NotImplementedError`` with a clear
pointer to the milestone. ``api.py`` still mounts the endpoint so the
frontend sees a HTTP 501 rather than 404 (mode-symmetry per matrix §2.5
doc).

Naming SSOT: ``agent_id='compliance'`` is the locked full-stack name
per ``docs/contracts/agent-naming-ssot.md`` v1.1 (Q-042.B + Stage 4
cleanup ratify 2026-04-30). The legacy ``compli`` shortform survives
ONLY in the CSS color token ``--t-compli`` (root CLAUDE.md §7).
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Mapping, NoReturn

logger = logging.getLogger(__name__)


COMPLIANCE_AGENT_ID = "compliance"
COMPLIANCE_ENDPOINT = "/api/compliance/scan"  # Managed · job_id + poll (Phase 2)


def _phase2_message() -> str:
    return (
        "agent=compliance is Managed (policy-event driven · matrix scan ≥ 1 min) · "
        "Phase 1 BFF does not implement live dispatch · see root §3.1.1 + "
        "matrix §2.5 + W1-backend §11 · ships Phase 2 (Q4 2026 · shared/job_runtime)"
    )


class ComplianceAdapter:
    """Managed-mode placeholder · raises ``NotImplementedError`` on every dispatch."""

    agent_id = COMPLIANCE_AGENT_ID
    boundary = "managed_readonly"

    def __init__(self, **_kwargs: Any) -> None:
        pass

    async def start_turn(
        self,
        turn_id: str,
        persona: str,
        payload: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:  # pragma: no cover · stub
        self._raise(turn_id)
        if False:  # pragma: no cover · typing
            yield {}

    async def dispatch_message(
        self,
        turn_id: str,
        message: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:  # pragma: no cover · stub
        self._raise(turn_id)
        if False:  # pragma: no cover · typing
            yield {}

    async def abort_turn(
        self, turn_id: str, reason: str,
    ) -> None:  # pragma: no cover · stub
        logger.info(
            "[compliance_adapter:stub] abort_turn ignored · turn_id=%s reason=%s",
            turn_id, reason,
        )

    def _raise(self, turn_id: str) -> NoReturn:
        raise NotImplementedError(
            f"{_phase2_message()} · turn_id={turn_id}",
        )


__all__ = [
    "COMPLIANCE_AGENT_ID",
    "COMPLIANCE_ENDPOINT",
    "ComplianceAdapter",
]
