# -*- coding: utf-8 -*-
"""shared.decision_ledger.store — sqlite-backed DecisionLedger.

Mirrors the threading + silent-fail pattern of `audit_service.recorder`
so multi-thread FastAPI workers can share one process-wide ledger
without contention surprises.

Failure isolation (per BE7 hard line + Agent3 BE2 wrapper pattern):
- Every write returns the decision_id even when the underlying INSERT
  fails. Caller can echo to client and retry separately.
- Every read returns [] / None on sqlite error. Callers (REST endpoints)
  raise HTTPException themselves.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sqlite3
import threading
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hashing import canonical_hash, hash_subject_id
from .schema import (
    LEDGER_SCHEMA_VERSION,
    LedgerEntry,
    resolve_jurisdiction,
    resolve_retention_class,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "ledger" / "decisions.sqlite"

EVIDENCE_MAX_BYTES = 64 * 1024  # truncate evidence_chain to 64KB to keep
                                 # the sqlite row size bounded.

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
  decision_id      TEXT PRIMARY KEY,
  agent_id         TEXT NOT NULL,
  endpoint         TEXT NOT NULL,
  ts               TEXT NOT NULL,
  input_hash       TEXT NOT NULL,
  output_hash      TEXT NOT NULL,
  evidence_chain   TEXT NOT NULL,
  reviewer_id      TEXT,
  reviewer_action  TEXT,
  reviewer_ts      TEXT,
  jurisdiction     TEXT NOT NULL,
  retention_class  TEXT NOT NULL,
  subject_name     TEXT,
  subject_id       TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  is_feedback      INTEGER NOT NULL DEFAULT 0,
  feedback_meta    TEXT
);
CREATE INDEX IF NOT EXISTS idx_agent_ts        ON decisions(agent_id, ts);
CREATE INDEX IF NOT EXISTS idx_jurisdiction_ts ON decisions(jurisdiction, ts);
CREATE INDEX IF NOT EXISTS idx_subject         ON decisions(subject_id);
CREATE INDEX IF NOT EXISTS idx_is_feedback     ON decisions(is_feedback, ts);
"""

# Phase A.5 (2026-05-09) · feedback_meta + is_feedback 加到现有 schema · 旧 db 文件用
# ALTER 升级 (silent-skip if column 已存在 · sqlite raise OperationalError when dup).
_SCHEMA_MIGRATIONS = (
    "ALTER TABLE decisions ADD COLUMN is_feedback INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE decisions ADD COLUMN feedback_meta TEXT",
)


def _truncate_json(payload: Any, max_bytes: int) -> str:
    """Serialize then truncate to keep sqlite rows bounded.

    Truncated rows still dehydrate via json.loads (the original payload
    already canonical-hashed, so the audit trail keeps integrity). When
    truncation triggers we wrap in a sentinel to make the loss visible
    to the auditor.
    """
    blob = json.dumps(payload, ensure_ascii=False, default=str)
    encoded = blob.encode("utf-8")
    if len(encoded) <= max_bytes:
        return blob
    # encode -> truncate -> decode (lossy), then wrap in sentinel
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return json.dumps(
        {"_truncated": True, "_original_size": len(encoded), "blob": truncated},
        ensure_ascii=False,
    )


@dataclass
class LedgerWriteResult:
    decision_id: str
    persisted: bool
    error: str | None = None


class DecisionLedger:
    """sqlite-backed cross-agent decision audit log.

    Thread-safe via per-call connection + per-instance write lock.
    Every method silent-fails on sqlite errors so a ledger outage never
    cascades into a decision-flow outage.
    """

    schema_version: str = LEDGER_SCHEMA_VERSION

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(_SCHEMA_SQL)
                # Phase A.5 ALTER · silent-skip if column 已存在
                for sql in _SCHEMA_MIGRATIONS:
                    try:
                        conn.execute(sql)
                    except sqlite3.OperationalError:
                        pass  # duplicate column name (already migrated)
                conn.commit()
        except sqlite3.Error as e:  # pragma: no cover · disk failure
            logger.warning("[decision_ledger] schema init failed: %s", e)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        agent_id: str,
        endpoint: str,
        input_payload: Any,
        output_payload: Any,
        evidence_chain: Any,
        decision_id: str | None = None,
        jurisdiction: str | None = None,
        retention_class: str | None = None,
        subject_name: str | None = None,
        subject_id: str | None = None,
        ts: str | None = None,
    ) -> LedgerWriteResult:
        """Persist one decision; never raises sqlite errors upward."""
        decision_id = decision_id or str(uuid.uuid4())
        try:
            entry = LedgerEntry(
                decision_id=decision_id,
                agent_id=agent_id,
                endpoint=endpoint,
                ts=ts or LedgerEntry.now_iso(),
                input_hash=canonical_hash(input_payload),
                output_hash=canonical_hash(output_payload),
                evidence_chain=evidence_chain or {},
                jurisdiction=resolve_jurisdiction(jurisdiction),
                retention_class=resolve_retention_class(
                    agent_id, retention_class,
                ),
                subject_name=subject_name,
                # Subjects are PII — always hash before storage.
                subject_id=hash_subject_id(subject_id) if subject_id else None,
            )
        except (TypeError, ValueError) as exc:
            # Validation errors (bad jurisdiction / retention_class) are
            # caller bugs — surface them via the result object so tests
            # can assert on them while production callers still get an
            # id back.
            return LedgerWriteResult(
                decision_id=decision_id, persisted=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        evidence_blob = _truncate_json(entry.evidence_chain, EVIDENCE_MAX_BYTES)
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO decisions (
                      decision_id, agent_id, endpoint, ts,
                      input_hash, output_hash, evidence_chain,
                      reviewer_id, reviewer_action, reviewer_ts,
                      jurisdiction, retention_class,
                      subject_name, subject_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.decision_id, entry.agent_id, entry.endpoint,
                        entry.ts, entry.input_hash, entry.output_hash,
                        evidence_blob,
                        entry.reviewer_id, entry.reviewer_action,
                        entry.reviewer_ts,
                        entry.jurisdiction, entry.retention_class,
                        entry.subject_name, entry.subject_id,
                    ),
                )
                conn.commit()
            return LedgerWriteResult(decision_id=decision_id, persisted=True)
        except (sqlite3.Error, OSError) as exc:
            logger.warning(
                "[decision_ledger] sqlite write failed for %s: %s",
                decision_id, exc,
            )
            return LedgerWriteResult(
                decision_id=decision_id, persisted=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    # ------------------------------------------------------------------
    # Feedback (Phase A.5 · per cross-agent-feedback-protocol)
    # ------------------------------------------------------------------

    def record_feedback(
        self,
        *,
        producer_agent: str,
        consumer_agents: list[str],
        feedback_type: str,
        original_decision_id: str,
        subject_entity_key: str,
        payload: dict[str, Any],
        decision_id: str | None = None,
        ts: str | None = None,
        jurisdiction: str | None = None,
    ) -> LedgerWriteResult:
        """Persist one cross-agent feedback event · per cross-agent-feedback-protocol.

        Retention auto-derived from consumer_agents (per M1 · MAX(consumer retention)).
        """
        from .schema import (
            DEFAULT_RETENTION_BY_AGENT, RETENTION_LONG, RETENTION_STANDARD,
            RETENTION_SHORT,
        )
        if not consumer_agents:
            return LedgerWriteResult(
                decision_id=decision_id or "", persisted=False,
                error="ValueError: consumer_agents required (≥ 1)",
            )

        # M1 · retention 取 MAX(consumer agent retention)
        rank = {RETENTION_SHORT: 0, RETENTION_STANDARD: 1, RETENTION_LONG: 2}
        consumer_classes = [
            DEFAULT_RETENTION_BY_AGENT.get(a, RETENTION_STANDARD)
            for a in consumer_agents
        ]
        feedback_retention = max(consumer_classes, key=lambda c: rank[c])

        feedback_meta = {
            "feedback_type": feedback_type,
            "consumer_agents": list(consumer_agents),
            "original_decision_id": original_decision_id,
            "subject_entity_key": subject_entity_key,
            "payload": dict(payload),
        }

        decision_id = decision_id or str(uuid.uuid4())
        try:
            entry = LedgerEntry(
                decision_id=decision_id,
                agent_id=producer_agent,
                endpoint=f"feedback/{feedback_type}",
                ts=ts or LedgerEntry.now_iso(),
                input_hash=canonical_hash(payload),
                output_hash=canonical_hash({"event_id": decision_id}),
                evidence_chain={"original_decision_id": original_decision_id},
                jurisdiction=resolve_jurisdiction(jurisdiction),
                retention_class=feedback_retention,
                subject_name=None,  # entity_key 已在 feedback_meta
                subject_id=None,
                is_feedback=True,
                feedback_meta=feedback_meta,
            )
        except (TypeError, ValueError) as exc:
            return LedgerWriteResult(
                decision_id=decision_id, persisted=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        evidence_blob = _truncate_json(entry.evidence_chain, EVIDENCE_MAX_BYTES)
        feedback_meta_blob = json.dumps(entry.feedback_meta, ensure_ascii=False)
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO decisions (
                      decision_id, agent_id, endpoint, ts,
                      input_hash, output_hash, evidence_chain,
                      reviewer_id, reviewer_action, reviewer_ts,
                      jurisdiction, retention_class,
                      subject_name, subject_id,
                      is_feedback, feedback_meta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.decision_id, entry.agent_id, entry.endpoint,
                        entry.ts, entry.input_hash, entry.output_hash,
                        evidence_blob,
                        entry.reviewer_id, entry.reviewer_action,
                        entry.reviewer_ts,
                        entry.jurisdiction, entry.retention_class,
                        entry.subject_name, entry.subject_id,
                        1, feedback_meta_blob,
                    ),
                )
                conn.commit()
            return LedgerWriteResult(decision_id=decision_id, persisted=True)
        except (sqlite3.Error, OSError) as exc:
            logger.warning(
                "[decision_ledger] feedback sqlite write failed for %s: %s",
                decision_id, exc,
            )
            return LedgerWriteResult(
                decision_id=decision_id, persisted=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def query_feedback_after(
        self,
        *,
        last_decision_id: str | None,
        consumer_agent: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Watcher 用 · 拉 last_decision_id 之后未消费的 feedback event.

        排序按 ROWID ASC (insertion order · sqlite 自动递增 · 不受 created_at 秒精度影响).
        Filter: is_feedback=1 · consumer_agent in feedback_meta.consumer_agents.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if last_decision_id:
                    rows = conn.execute(
                        """
                        SELECT * FROM decisions
                        WHERE is_feedback = 1
                          AND ROWID > (
                            SELECT ROWID FROM decisions WHERE decision_id = ?
                          )
                        ORDER BY ROWID ASC
                        LIMIT ?
                        """,
                        (last_decision_id, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM decisions
                        WHERE is_feedback = 1
                        ORDER BY ROWID ASC
                        LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()
        except sqlite3.Error as exc:
            logger.warning("[decision_ledger] feedback query failed: %s", exc)
            return []

        out: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            # 反序列化 feedback_meta
            if d.get("feedback_meta"):
                try:
                    d["feedback_meta"] = json.loads(d["feedback_meta"])
                except json.JSONDecodeError:
                    continue  # skip 损坏 entry · 不阻塞 stream
            # filter consumer
            consumers = d["feedback_meta"].get("consumer_agents", []) if isinstance(d.get("feedback_meta"), dict) else []
            if consumer_agent not in consumers:
                continue
            out.append(d)
        return out

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, decision_id: str) -> dict[str, Any] | None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM decisions WHERE decision_id = ?",
                    (decision_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            logger.warning("[decision_ledger] sqlite get failed: %s", exc)
            return None
        if row is None:
            return None
        return self._row_to_dict(row)

    def query(
        self,
        *,
        agent_id: str | None = None,
        jurisdiction: str | None = None,
        subject_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if jurisdiction:
            clauses.append("jurisdiction = ?")
            params.append(jurisdiction)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(hash_subject_id(subject_id))
        if since:
            clauses.append("ts >= ?")
            params.append(since)
        if until:
            clauses.append("ts < ?")
            params.append(until)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            f"SELECT * FROM decisions {where} "
            "ORDER BY ts DESC, decision_id DESC LIMIT ? OFFSET ?"
        )
        params_with_paging = params + [int(limit), int(offset)]
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params_with_paging).fetchall()
        except sqlite3.Error as exc:
            logger.warning("[decision_ledger] sqlite query failed: %s", exc)
            return []
        return [self._row_to_dict(r) for r in rows]

    def count(
        self,
        *,
        agent_id: str | None = None,
        jurisdiction: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> int:
        clauses: list[str] = []
        params: list[Any] = []
        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        if jurisdiction:
            clauses.append("jurisdiction = ?")
            params.append(jurisdiction)
        if since:
            clauses.append("ts >= ?")
            params.append(since)
        if until:
            clauses.append("ts < ?")
            params.append(until)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT COUNT(*) FROM decisions {where}"
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(sql, params).fetchone()
            return int(row[0]) if row else 0
        except sqlite3.Error as exc:
            logger.warning("[decision_ledger] sqlite count failed: %s", exc)
            return 0

    def export_zip(
        self,
        *,
        jurisdiction: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> bytes:
        """Return a zip archive (in-memory) containing one JSON file
        per decision plus a manifest. For audit handoff.

        Returns empty zip on read failure (silent-fail).
        """
        rows = self.query(
            jurisdiction=jurisdiction, since=since, until=until,
            limit=100_000, offset=0,
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "schema_version": self.schema_version,
                "exported_at": LedgerEntry.now_iso(),
                "filter": {
                    "jurisdiction": jurisdiction,
                    "since": since,
                    "until": until,
                },
                "count": len(rows),
                "decision_ids": [r["decision_id"] for r in rows],
            }
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            for row in rows:
                zf.writestr(
                    f"decisions/{row['decision_id']}.json",
                    json.dumps(row, ensure_ascii=False, indent=2),
                )
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Reviewer PATCH (人审签字)
    # ------------------------------------------------------------------

    def record_review(
        self,
        decision_id: str,
        *,
        reviewer_id: str,
        action: str,
        ts: str | None = None,
    ) -> bool:
        """PATCH reviewer_id / reviewer_action / reviewer_ts.

        Returns True on successful update, False otherwise (decision_id
        not found, sqlite error, or invalid action).
        """
        if action not in {"approve", "reject", "request_changes"}:
            return False
        ts = ts or LedgerEntry.now_iso()
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    """
                    UPDATE decisions
                       SET reviewer_id = ?,
                           reviewer_action = ?,
                           reviewer_ts = ?
                     WHERE decision_id = ?
                    """,
                    (reviewer_id, action, ts, decision_id),
                )
                conn.commit()
                return cur.rowcount > 0
        except (sqlite3.Error, OSError) as exc:
            logger.warning("[decision_ledger] sqlite review failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        # rehydrate evidence_chain blob
        ev = d.get("evidence_chain")
        if isinstance(ev, str):
            try:
                d["evidence_chain"] = json.loads(ev)
            except (ValueError, TypeError):
                d["evidence_chain"] = {"_unparseable": True, "raw": ev}
        return d


# ============================================================================
# Default ledger (singleton-ish · per process · mirrors audit_service.recorder)
# ============================================================================

_default_ledger: DecisionLedger | None = None
_default_lock = threading.Lock()


def default_ledger() -> DecisionLedger:
    """Lazy singleton. Env override: ``LIUYE_LEDGER_DB_PATH``."""
    global _default_ledger
    if _default_ledger is not None:
        return _default_ledger
    with _default_lock:
        if _default_ledger is not None:
            return _default_ledger
        env_path = os.environ.get("LIUYE_LEDGER_DB_PATH")
        path = Path(env_path) if env_path else DEFAULT_DB_PATH
        _default_ledger = DecisionLedger(path)
        return _default_ledger


def set_default_ledger(ledger: DecisionLedger | None) -> None:
    """Test helper · inject or reset the process-wide default ledger."""
    global _default_ledger
    with _default_lock:
        _default_ledger = ledger


# ============================================================================
# Façade · Top-level functions used by callers across agents
# ============================================================================


def record_decision(
    *,
    agent_id: str,
    endpoint: str,
    input_payload: Any,
    output_payload: Any,
    evidence_chain: Any,
    decision_id: str | None = None,
    jurisdiction: str | None = None,
    retention_class: str | None = None,
    subject_name: str | None = None,
    subject_id: str | None = None,
    ts: str | None = None,
    ledger: DecisionLedger | None = None,
) -> str:
    """Public façade — see docs/contracts/decision-ledger.md §2.1.

    Returns the decision_id even when the underlying write fails so the
    caller can still echo to clients. Failure isolated.
    """
    target = ledger or default_ledger()
    result = target.record(
        agent_id=agent_id,
        endpoint=endpoint,
        input_payload=input_payload,
        output_payload=output_payload,
        evidence_chain=evidence_chain,
        decision_id=decision_id,
        jurisdiction=jurisdiction,
        retention_class=retention_class,
        subject_name=subject_name,
        subject_id=subject_id,
        ts=ts,
    )
    return result.decision_id


def get_decision(
    decision_id: str, *, ledger: DecisionLedger | None = None,
) -> dict[str, Any] | None:
    return (ledger or default_ledger()).get(decision_id)


def query_agent(
    agent_id: str,
    *,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    ledger: DecisionLedger | None = None,
) -> list[dict[str, Any]]:
    return (ledger or default_ledger()).query(
        agent_id=agent_id, since=since, until=until,
        limit=limit, offset=offset,
    )


def query_jurisdiction(
    jurisdiction: str,
    *,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    ledger: DecisionLedger | None = None,
) -> list[dict[str, Any]]:
    return (ledger or default_ledger()).query(
        jurisdiction=jurisdiction, since=since, until=until,
        limit=limit, offset=offset,
    )


def export_jurisdiction(
    jurisdiction: str,
    *,
    since: str | None = None,
    until: str | None = None,
    ledger: DecisionLedger | None = None,
) -> bytes:
    return (ledger or default_ledger()).export_zip(
        jurisdiction=jurisdiction, since=since, until=until,
    )


def record_review(
    decision_id: str,
    *,
    reviewer_id: str,
    action: str,
    ts: str | None = None,
    ledger: DecisionLedger | None = None,
) -> bool:
    return (ledger or default_ledger()).record_review(
        decision_id, reviewer_id=reviewer_id, action=action, ts=ts,
    )


__all__ = [
    "DEFAULT_DB_PATH",
    "DecisionLedger",
    "LedgerWriteResult",
    "default_ledger",
    "export_jurisdiction",
    "get_decision",
    "query_agent",
    "query_jurisdiction",
    "record_decision",
    "record_review",
    "set_default_ledger",
]
