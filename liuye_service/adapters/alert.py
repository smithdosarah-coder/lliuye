# -*- coding: utf-8 -*-
"""liuye_service.adapters.alert — Agent4 (Alert · 预警) **Managed stub**.

Per W1-backend brief §3 file 9-13 + ``liuye_service/CLAUDE.md`` §4 + root
§3.1.1 + matrix §2.4.

**Phase 1 = stub**. Alert is a Managed agent — its primary trigger is
batched customer-behaviour change scans (cron · 夜间扫批 N 客户) and
single-customer drill submissions (job_id + poll · matrix §2.4
Scenario A). Both modes exceed the Cowork 5s p95 SLA so the BFF cannot
stream business results inline; Phase 2 (Q4 2026) wires
``shared/job_runtime/`` so the adapter:

1. Submits an ``alert_drill_submit`` / ``alert_batch_scan`` job →
   returns ``job_id`` + ``estimated_seconds``
2. Receives webhook on completion → new turn (with
   ``parent_turn_id`` linking back to the originating Cowork turn)
3. Reads the artifact (hitlist + scan_summary) from
   ``data/liuye/jobs/<job_id>/``
4. Persists the decision via ``shared.decision_ledger`` (retention
   ``short`` 90d per root §3.7.5 · red severity bumps to ``standard``)

Until Phase 2 the adapter raises ``NotImplementedError`` with a clear
pointer to the milestone. ``api.py`` still mounts the endpoint so the
frontend sees a HTTP 501 rather than 404 (mode-symmetry per matrix §2.4
doc).

Retention class hardline: ``short`` 90d default, ``standard`` for red
severity hits (root §3.7.5 footnote on routine vs critical alerts).
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Mapping, NoReturn

logger = logging.getLogger(__name__)


ALERT_AGENT_ID = "alert"
ALERT_ENDPOINT = "/api/alert/drill"  # Managed · job_id + poll (Phase 2)


def _phase2_message() -> str:
    return (
        "agent=alert is Managed (cron / event-driven · 分钟 ~ 数小时 SLA) · "
        "Phase 1 BFF does not implement live dispatch · see root §3.1.1 + "
        "matrix §2.4 + W1-backend §11 · ships Phase 2 (Q4 2026 · shared/job_runtime)"
    )


class AlertAdapter:
    """Managed-mode placeholder · raises ``NotImplementedError`` on every dispatch."""

    agent_id = ALERT_AGENT_ID
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
            "[alert_adapter:stub] abort_turn ignored · turn_id=%s reason=%s",
            turn_id, reason,
        )

    def _raise(self, turn_id: str) -> NoReturn:
        raise NotImplementedError(
            f"{_phase2_message()} · turn_id={turn_id}",
        )


__all__ = [
    "ALERT_AGENT_ID",
    "ALERT_ENDPOINT",
    "AlertAdapter",
]
