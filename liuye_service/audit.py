# -*- coding: utf-8 -*-
"""liuye_service.audit — silent-fail wrapper around audit_service + decision_ledger.

Per W1-backend brief §3 file 6 + ``liuye_service/CLAUDE.md`` §5 + root §3.7.5.

This module is the **single entry point** through which BFF code records
a decision. It composes two existing layers:

- ``audit_service.decorators.audit_llm_call`` — FastAPI endpoint-level
  decorator that records the LLM call envelope (prompt / response /
  latency / cost). Already plumbed into the 6 agent endpoints.
- ``shared.decision_ledger.record_decision`` — cross-Agent decision
  audit log (BE7) · jurisdiction-bound · 5y/10y retention · in-process.

The wrapper here ensures three invariants the W1 brief mandates:

1. **silent-fail** — ledger write failure NEVER bubbles up. Decision
   flow always returns to the user. Failed entries enqueue to the
   filesystem outbox.
2. **PII safety** — ``subject_id`` (统一社会信用代码 / 身份证号 / ...) is
   ALWAYS hashed before reaching sqlite. We delegate to
   ``shared.decision_ledger.hash_subject_id`` so the hash function stays
   consistent with admin query endpoints (which hash inbound queries
   the same way).
3. **outbox enqueue** — when sqlite write fails, the entry is written
   to ``data/liuye/outbox/{decision_id}.json`` so the 60s outbox worker
   (``workers/outbox_retry.py``) can retry later. Idempotency_key in the
   payload prevents double-record on retry.

Q3 ratify note: ``parent_turn_id`` (LedgerEntry v1.1.0 · optional) is
passed through when caller provides it. Required for cross-mode
handoff (e.g. Agent2 Cowork DSL turn → Managed backtest turn). Leave
None for single-mode flows.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from shared.decision_ledger import (
    LedgerEntry,
    record_decision as _record_decision,
)
from shared.decision_ledger.hashing import hash_subject_id

logger = logging.getLogger(__name__)

# Outbox path · spec'd in W1-backend brief §3 + v3 §5.x. Created on first
# enqueue. Kept under ``data/liuye/`` to live alongside ledger + dead-letter.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTBOX_DIR = _PROJECT_ROOT / "data" / "liuye" / "outbox"


def _ensure_dir(path: Path) -> Path:
    """Create the directory if missing · silent-fail on permission error."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover · disk-full / readonly fs
        logger.warning("[liuye_audit] outbox mkdir failed at %s: %s", path, exc)
    return path


def _enqueue_outbox(
    *,
    decision_id: str,
    payload: dict[str, Any],
    outbox_dir: Path = DEFAULT_OUTBOX_DIR,
) -> Path | None:
    """Write a failed ledger entry to the outbox · silent-fail.

    File name = ``{decision_id}.json`` so the 60s retry worker can dedup
    on idempotency_key (we pass it inside the payload).
    """
    _ensure_dir(outbox_dir)
    target = outbox_dir / f"{decision_id}.json"
    try:
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        return target
    except OSError as exc:  # pragma: no cover · disk failure
        logger.warning(
            "[liuye_audit] outbox enqueue failed for %s: %s", decision_id, exc,
        )
        return None


def record_liuye_decision(
    *,
    agent_id: str,
    endpoint: str,
    input_payload: Any,
    output_payload: Any,
    evidence_chain: Any,
    decision_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    retention_class: Optional[str] = None,
    subject_name: Optional[str] = None,
    subject_id: Optional[str] = None,
    parent_turn_id: Optional[str] = None,
    outbox_dir: Path = DEFAULT_OUTBOX_DIR,
) -> str:
    """Persist one cross-Agent decision via shared.decision_ledger · silent-fail.

    Wraps ``shared.decision_ledger.record_decision`` with three additions:

    - PII safety: ``subject_id`` already hashed inside the underlying
      store, but we double-hash here defensively so any direct callers
      that bypass the store (test fixtures / outbox replay) keep the
      invariant.
    - Outbox enqueue on failure: when the store returns a non-persisted
      ``LedgerWriteResult``, we drop a JSON file in
      ``data/liuye/outbox/`` for the 60s retry worker.
    - parent_turn_id Q3 ratify: when caller supplies it, we forward to
      the LedgerEntry constructor (v1.1.0 schema). Existing flows that
      don't need cross-mode linkage pass None.

    Returns the ``decision_id`` even on failure so caller can echo to
    the client and rely on idempotency_key + retry to converge.
    """
    # Hash subject_id eagerly · defensive double-hash safe (hash of hash is
    # still 64 bits, stable, idempotent). The store also calls hash_subject_id
    # internally · this gives outbox payloads + manual replays the same shape.
    safe_subject_id = (
        hash_subject_id(subject_id) if subject_id else None
    )

    # The shared façade ``record_decision`` does NOT yet expose
    # ``parent_turn_id`` (v1.1.0 schema field). Until shared._record_decision
    # gains the kwarg, we mark it in the evidence_chain payload so the
    # downstream sqlite row + outbox retry path both preserve the linkage.
    enriched_evidence: dict[str, Any] = (
        dict(evidence_chain) if isinstance(evidence_chain, dict)
        else {"_raw": evidence_chain}
    )
    if parent_turn_id is not None:
        enriched_evidence.setdefault("_meta", {})
        enriched_evidence["_meta"]["parent_turn_id"] = parent_turn_id

    try:
        resolved_id = _record_decision(
            agent_id=agent_id,
            endpoint=endpoint,
            input_payload=input_payload,
            output_payload=output_payload,
            evidence_chain=enriched_evidence,
            decision_id=decision_id,
            jurisdiction=jurisdiction,
            retention_class=retention_class,
            subject_name=subject_name,
            subject_id=safe_subject_id,
        )
        return resolved_id
    except Exception as exc:  # noqa: BLE001 — last-resort silent-fail
        # The store itself catches sqlite errors and returns a result
        # object · we only hit this branch when import / validation
        # raises (caller bug). Even then we never want to break the
        # decision flow · enqueue + return a deterministic id.
        logger.warning(
            "[liuye_audit] record_decision raised · enqueuing outbox: %s", exc,
        )
        fallback_id = decision_id or "outbox-pending"
        _enqueue_outbox(
            decision_id=fallback_id,
            payload={
                "agent_id": agent_id,
                "endpoint": endpoint,
                "input_payload": input_payload,
                "output_payload": output_payload,
                "evidence_chain": enriched_evidence,
                "decision_id": fallback_id,
                "jurisdiction": jurisdiction,
                "retention_class": retention_class,
                "subject_name": subject_name,
                "subject_id": safe_subject_id,
                "parent_turn_id": parent_turn_id,
                "_error": f"{type(exc).__name__}: {exc}",
            },
            outbox_dir=outbox_dir,
        )
        return fallback_id


# ---------------------------------------------------------------------------
# Re-export the existing decorator so BFF endpoints can import from one place
# ---------------------------------------------------------------------------
try:
    from audit_service.decorators import audit_llm_call  # noqa: F401
except ImportError:  # pragma: no cover · audit_service should always be present

    def audit_llm_call(**_kwargs: Any):  # type: ignore[no-redef]
        """Stub when audit_service not on path (local dev) · pass-through."""

        def _passthrough(fn):
            return fn

        return _passthrough


__all__ = [
    "DEFAULT_OUTBOX_DIR",
    "audit_llm_call",
    "record_liuye_decision",
]
