# -*- coding: utf-8 -*-
"""liuye_service.ledger_review — append-only LedgerReviewEvent handler.

Per W1-backend brief §4.5 + ``liuye_service/CLAUDE.md`` §5 + v3 §2.5 +
``docs/contracts/decision-ledger.md`` v1.0 + 必修 #30 + #69.

Two responsibilities (single source of truth for both):

1. **append-only ledger review event store**: a *new* sqlite table
   ``ledger_review_events`` co-located with the existing
   ``decisions`` table in ``data/ledger/decisions.sqlite``. The store
   NEVER mutates the original decision row · every reviewer action is
   recorded as a new event row keyed by ``event_id``. This keeps the
   audit chain tamper-evident.

2. **idempotency_key dedup**: the same ``idempotency_key`` for the same
   ``decision_id`` is allowed at most once. Re-submission with the same
   key returns the original event row (HTTP 200 idempotent semantic at
   the REST layer · see ``api.py``).

The old ``shared.decision_ledger.record_review`` PATCH path on
``decisions.reviewer_id / reviewer_action / reviewer_ts`` is **kept**
for backward compatibility — the legacy ``ledger_service/api.py``
endpoint ``/api/ledger/{decision_id}/review`` is now marked
``@deprecated v1`` and the new UI calls this v2 endpoint at
``POST /api/liuye/ledger/decisions/{decision_id}/review_events``.

Cross-mode parent_turn_id linkage: ``LedgerReviewEvent`` carries no
``parent_turn_id`` field (per v3 §2.5 schema). The linkage lives on
the parent ``decisions`` row (v1.1 ``parent_turn_id`` column). Queries
that need "all review events on a Cowork→Managed chain" join via the
parent_turn_id-indexed parent rows.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from liuye_service.schemas import LedgerReviewEvent
from shared.decision_ledger.store import DEFAULT_DB_PATH, default_ledger

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema · append-only event log · co-located with the decisions table.
# ---------------------------------------------------------------------------

_REVIEW_EVENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ledger_review_events (
  event_id         TEXT PRIMARY KEY,
  decision_id      TEXT NOT NULL,
  reviewer_id      TEXT NOT NULL,
  action           TEXT NOT NULL,
  comment          TEXT,
  idempotency_key  TEXT NOT NULL,
  signature        TEXT,
  appended_at      TEXT NOT NULL,
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_review_decision    ON ledger_review_events(decision_id);
CREATE INDEX IF NOT EXISTS idx_review_idempotency ON ledger_review_events(decision_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_review_reviewer    ON ledger_review_events(reviewer_id, appended_at);
"""


# Lock for schema init only · the sqlite layer handles row-level locking.
_SCHEMA_LOCK = threading.Lock()
_SCHEMA_INIT_PATHS: set[Path] = set()


def _ensure_schema(db_path: Path) -> None:
    """Idempotent schema init · runs once per DB path per process.

    The ``decisions`` table is already created by ``DecisionLedger``
    when ``default_ledger()`` runs. We just add the review events
    table on the same DB file.
    """
    with _SCHEMA_LOCK:
        if db_path in _SCHEMA_INIT_PATHS:
            return
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(db_path) as conn:
                conn.executescript(_REVIEW_EVENT_SCHEMA_SQL)
                conn.commit()
            _SCHEMA_INIT_PATHS.add(db_path)
        except sqlite3.Error as exc:  # pragma: no cover · disk failure
            logger.warning(
                "[ledger_review] schema init failed for %s: %s", db_path, exc,
            )


# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------


def record_review_event(
    *,
    decision_id: str,
    reviewer_id: str,
    action: str,
    idempotency_key: str,
    comment: Optional[str] = None,
    signature: Optional[str] = None,
    event_id: Optional[str] = None,
    appended_at: Optional[datetime] = None,
    db_path: Optional[Path] = None,
) -> LedgerReviewEvent:
    """Append a new ``LedgerReviewEvent`` row · idempotent via ``idempotency_key``.

    Returns the persisted ``LedgerReviewEvent`` Pydantic model. When an
    existing event row with the same ``(decision_id, idempotency_key)``
    is found, returns that row's data (idempotent semantics · re-tries
    of the same submission converge).

    Raises:
        ValueError: ``action`` not in the LedgerReviewEvent literal set
                    or required fields missing.
        RuntimeError: sqlite write failed (caller surfaces as HTTP 500).

    The ``decision_id`` is NOT required to exist in the ``decisions``
    table — a pre-decision veto can record a review event before the
    original decision lands (per ``permissions._build_review_event``
    fallback to ``request.id``).
    """
    # Validate via Pydantic before touching sqlite · raises ValueError
    # with field-level details we can surface to the REST layer.
    appended_dt = appended_at or datetime.now(timezone.utc)
    event = LedgerReviewEvent(
        event_id=event_id or f"rev_{uuid.uuid4().hex[:16]}",
        decision_id=decision_id,
        reviewer_id=reviewer_id,
        action=action,
        comment=comment,
        idempotency_key=idempotency_key,
        signature=signature,
        appended_at=appended_dt,
    )

    path = db_path or _resolve_db_path()
    _ensure_schema(path)

    # idempotency_key gate · same (decision_id, idempotency_key) returns
    # the original row · we DO NOT insert a duplicate.
    existing = _find_by_idempotency(path, decision_id, idempotency_key)
    if existing is not None:
        logger.info(
            "[ledger_review] idempotent return · decision=%s key=%s event=%s",
            decision_id, idempotency_key, existing.event_id,
        )
        return existing

    try:
        with sqlite3.connect(path) as conn:
            conn.execute(
                """
                INSERT INTO ledger_review_events (
                  event_id, decision_id, reviewer_id, action,
                  comment, idempotency_key, signature, appended_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id, event.decision_id, event.reviewer_id,
                    event.action, event.comment, event.idempotency_key,
                    event.signature, event.appended_at.isoformat(),
                ),
            )
            conn.commit()
    except sqlite3.IntegrityError as exc:
        # Race · another writer landed the same event_id (uuid collision
        # is astronomically unlikely · this is the (decision_id,
        # idempotency_key) double-submit race). Fall back to the
        # already-persisted row · idempotent behaviour preserved.
        logger.info(
            "[ledger_review] insert race · decision=%s key=%s · returning existing: %s",
            decision_id, idempotency_key, exc,
        )
        existing = _find_by_idempotency(path, decision_id, idempotency_key)
        if existing is not None:
            return existing
        raise RuntimeError(
            f"ledger_review insert failed and no existing row found: {exc}",
        ) from exc
    except sqlite3.Error as exc:
        logger.warning(
            "[ledger_review] sqlite write failed for decision=%s: %s",
            decision_id, exc,
        )
        raise RuntimeError(f"ledger_review write failed: {exc}") from exc

    return event


def list_review_events(
    *,
    decision_id: str,
    db_path: Optional[Path] = None,
) -> list[LedgerReviewEvent]:
    """List all review events for a decision · ordered by ``appended_at`` ASC.

    Returns an empty list when no events exist (NOT an error · a fresh
    decision has no review chain).
    """
    path = db_path or _resolve_db_path()
    _ensure_schema(path)
    try:
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM ledger_review_events
                 WHERE decision_id = ?
                 ORDER BY appended_at ASC, ROWID ASC
                """,
                (decision_id,),
            ).fetchall()
    except sqlite3.Error as exc:
        logger.warning(
            "[ledger_review] list query failed for decision=%s: %s",
            decision_id, exc,
        )
        return []
    return [_row_to_event(r) for r in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_db_path() -> Path:
    """Resolve the active ledger db path · mirror default_ledger().

    Re-uses the shared ``decision_ledger`` default path so review events
    co-locate with their parent decisions. Avoids a second sqlite file
    that ops would need to back up separately.
    """
    return Path(default_ledger().db_path)


def _find_by_idempotency(
    path: Path,
    decision_id: str,
    idempotency_key: str,
) -> Optional[LedgerReviewEvent]:
    """Return the existing event row for ``(decision_id, idempotency_key)`` or None."""
    try:
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM ledger_review_events
                 WHERE decision_id = ? AND idempotency_key = ?
                 LIMIT 1
                """,
                (decision_id, idempotency_key),
            ).fetchone()
    except sqlite3.Error as exc:
        logger.warning(
            "[ledger_review] idempotency lookup failed: %s", exc,
        )
        return None
    if row is None:
        return None
    return _row_to_event(row)


def _row_to_event(row: sqlite3.Row) -> LedgerReviewEvent:
    """Convert a sqlite3.Row into a LedgerReviewEvent · re-validates via Pydantic."""
    d = dict(row)
    return LedgerReviewEvent(
        event_id=d["event_id"],
        decision_id=d["decision_id"],
        reviewer_id=d["reviewer_id"],
        action=d["action"],
        comment=d.get("comment"),
        idempotency_key=d["idempotency_key"],
        signature=d.get("signature"),
        appended_at=datetime.fromisoformat(d["appended_at"]),
    )


__all__ = [
    "list_review_events",
    "record_review_event",
]
