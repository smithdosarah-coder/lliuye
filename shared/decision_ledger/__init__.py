# -*- coding: utf-8 -*-
"""shared.decision_ledger — cross-agent decision audit log (BE7).

Per docs/contracts/decision-ledger.md v1.0.

Distinct from `audit_service.LLMCall` (which logs LLM calls):
  - audit_service = "which LLM calls happened, prompt/response/cost"
  - decision_ledger = "which DECISIONS were made, by whom, with what
    evidence chain, jurisdiction-bound (银/保/证/HQ/BRANCH)"

Two layers complement, never merge.

Public surface:
  - ``LedgerEntry`` dataclass (schema row)
  - ``DecisionLedger`` sqlite-backed store (test-injectable)
  - ``record_decision(...)`` writer · silent-fail · returns decision_id
  - ``get_decision(id)`` / ``query_agent(...)`` / ``query_jurisdiction(...)``
  - ``export_jurisdiction(...)`` zip dump for audit handoff
  - ``record_review(...)`` PATCH reviewer signature
  - ``canonical_hash(payload)`` tamper-detect helper (also used internally)
  - ``hash_subject_id(plain_id)`` PII-safe subject id (16 hex chars)

Author: worker-B4-credit · 2026-05-01 · BE7 game-changer
"""

from __future__ import annotations

from .hashing import canonical_hash, canonical_json_bytes, hash_subject_id
from .schema import (
    ALLOWED_JURISDICTIONS,
    ALLOWED_RETENTION_CLASSES,
    DEFAULT_JURISDICTION,
    DEFAULT_RETENTION_BY_AGENT,
    LEDGER_SCHEMA_VERSION,
    LedgerEntry,
    RETENTION_LONG,
    RETENTION_SHORT,
    RETENTION_STANDARD,
    resolve_jurisdiction,
    resolve_retention_class,
)
from .store import (
    DEFAULT_DB_PATH,
    DecisionLedger,
    LedgerWriteResult,
    default_ledger,
    export_jurisdiction,
    get_decision,
    query_agent,
    query_jurisdiction,
    record_decision,
    record_review,
    set_default_ledger,
)

__all__ = [
    "ALLOWED_JURISDICTIONS",
    "ALLOWED_RETENTION_CLASSES",
    "DEFAULT_DB_PATH",
    "DEFAULT_JURISDICTION",
    "DEFAULT_RETENTION_BY_AGENT",
    "DecisionLedger",
    "LEDGER_SCHEMA_VERSION",
    "LedgerEntry",
    "LedgerWriteResult",
    "RETENTION_LONG",
    "RETENTION_SHORT",
    "RETENTION_STANDARD",
    "canonical_hash",
    "canonical_json_bytes",
    "default_ledger",
    "export_jurisdiction",
    "get_decision",
    "hash_subject_id",
    "query_agent",
    "query_jurisdiction",
    "record_decision",
    "record_review",
    "resolve_jurisdiction",
    "resolve_retention_class",
    "set_default_ledger",
]
