# -*- coding: utf-8 -*-
"""shared.policy_registry.hashing — deterministic id helpers.

Used by `register_policy_version` to compute stable
`policy_id` / `version_id` / `clause_id` so the same policy text always
produces the same ids across re-imports. Mirrors
`shared.decision_ledger.hashing` design (canonical JSON + SHA-256).

Two layers:
- ``policy_id`` — keyed by issuer + title (case-folded); stable across
  versions of the same policy.
- ``version_id`` — keyed by policy_id + effective_date + body sha; new
  effective_date or any text edit produces a new version.
- ``clause_id`` — keyed by version_id + article_no + paragraph_index.
  Stable per version so diff/coverage metrics line up across runs.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _sha256_hex(payload: str | bytes) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


def canonical_hash(payload: Any) -> str:
    return _sha256_hex(canonical_json(payload))


def policy_id(issuer: str, title: str) -> str:
    """Stable id for the *family* of versions of a policy.

    Case-folded so "银保监" / "银保监 " produce the same id; whitespace
    collapsed to single space.
    """
    canon = " ".join((issuer or "").split()).strip().lower()
    canon += "||"
    canon += " ".join((title or "").split()).strip().lower()
    return "POL-" + _sha256_hex(canon)[:16]


def version_id(policy_id_: str, effective_date: str, body_sha: str) -> str:
    """Stable id for a single immutable revision of a policy."""
    canon = f"{policy_id_}::{effective_date or ''}::{body_sha}"
    return "VER-" + _sha256_hex(canon)[:16]


def body_sha(text: str) -> str:
    """SHA-256 of the canonicalised policy body — used for version_id."""
    canon = "\n".join(line.rstrip() for line in (text or "").splitlines()).strip()
    return _sha256_hex(canon)


def clause_id(version_id_: str, article_no: str, paragraph_index: int) -> str:
    """Stable id for one segmented clause inside a policy version.

    Index is a content-position pointer; combined with version_id it
    survives re-segmentation of unchanged text.
    """
    canon = f"{version_id_}::{article_no or ''}::{int(paragraph_index)}"
    return "CL-" + _sha256_hex(canon)[:16]


__all__ = [
    "body_sha",
    "canonical_hash",
    "canonical_json",
    "clause_id",
    "policy_id",
    "version_id",
]
