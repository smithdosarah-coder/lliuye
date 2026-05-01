# -*- coding: utf-8 -*-
"""shared.decision_ledger.hashing — canonical JSON SHA-256 helpers.

Used by `record_decision` to compute `input_hash` / `output_hash` over the
full decision payload. Determinism guarantees:

- Same dict contents → identical hex digest, regardless of key insertion
  order (sorted keys).
- Unicode preserved (ensure_ascii=False) so 中文 fields don't change the
  digest under different encodings.
- Compact separators (no whitespace) so trivial reformatting doesn't
  change the digest.
- Non-JSON-native types (datetime, dataclass, Decimal) are coerced via
  `str(...)` — the resulting hash is deterministic but caller should
  prefer pre-serializing to dict form for contractual stability.

Tamper-detection use case: an auditor recomputes the hash from the
stored evidence_chain and compares to ledger.input_hash / output_hash.
A mismatch means the source-of-truth was edited after the decision was
recorded.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize ``payload`` to canonical UTF-8 bytes for hashing.

    Sort keys, drop whitespace, preserve Unicode. Falls back to ``str``
    for unknown types.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def canonical_hash(payload: Any) -> str:
    """Return SHA-256 hex digest of the canonical serialization."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def hash_subject_id(plain_id: str | None, *, salt: str = "liuye-ledger-v1") -> str | None:
    """Hash a PII subject id (统一社会信用代码 / 身份证号) to 16-hex prefix.

    Salted SHA-256 truncated to 16 chars — enough to dedupe per-subject
    queries without re-identifying the subject from the ledger row.
    Returns None when input is empty.

    NOTE: not a security-grade anonymizer (16 hex chars = 64 bits, low
    entropy for a known-plaintext attack). For Phase B PoC it's fine;
    Phase C should swap to per-tenant HMAC or a tokenization service.
    """
    if not plain_id:
        return None
    payload = f"{salt}::{plain_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
