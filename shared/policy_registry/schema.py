# -*- coding: utf-8 -*-
"""shared.policy_registry.schema — dataclasses for versioned policy storage.

Three layers (per docs/contracts/agent-compliance-policy-registry.md §1):

- ``PolicyDocument``      → identity (policy_id family)
- ``PolicyVersion``       → one immutable revision (version_id, body_sha,
                            effective_date, fetched_at, source_url)
- ``PolicyClause``        → one segmented clause inside a version
                            (clause_id, article, paragraph_index, text)

Module-level constants live here (not env-driven) so any change is
reviewable in git diff. Mirrors `shared.decision_ledger.schema`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

POLICY_REGISTRY_SCHEMA_VERSION = "1.0.0"

# Issuer enum — kept as plain strings (cross-worker compatibility).
ALLOWED_ISSUERS: frozenset[str] = frozenset({
    "银保监",   # CBIRC
    "央行",     # PBoC
    "证监会",   # CSRC
    "国务院",   # State Council
    "人大",     # NPC
    "其他",
})

DEFAULT_ISSUER = "其他"


@dataclass
class PolicyDocument:
    """Identity card for a *family* of policy versions.

    One row per policy_id. Title and issuer are the human-facing keys;
    the policy_id itself is derived deterministically from them via
    `hashing.policy_id`.
    """

    policy_id: str
    title: str
    issuer: str = DEFAULT_ISSUER
    category: str = ""          # e.g. 客户准入 / 反洗钱 / 信息披露
    description: str = ""       # short human note
    created_at: str | None = None  # set by sqlite default

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyVersion:
    """One immutable revision of a policy."""

    version_id: str
    policy_id: str
    effective_date: str         # YYYY-MM-DD; empty if unknown
    fetched_at: str             # ISO timestamp
    body_sha: str               # SHA-256 of canonicalised body text
    source_url: str = ""
    body_text: str = ""         # full normalised text (kept inline; bounded)
    clause_count: int = 0
    superseded_by: str | None = None  # later version_id, if any
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")


@dataclass
class PolicyClause:
    """One segmented clause inside a PolicyVersion.

    article: e.g. "第六条" — maps 1:1 to scan_engine._ARTICLE_RE captures.
    paragraph_index: 0-based ordinal inside that article (handles 第六条
    一/二/三 multi-段 layout).
    """

    clause_id: str
    version_id: str
    article: str
    paragraph_index: int
    text: str
    category: str = "其他"
    keywords: list[str] = field(default_factory=list)
    threshold: dict = field(default_factory=dict)
    severity_hint: str = "major"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "ALLOWED_ISSUERS",
    "DEFAULT_ISSUER",
    "POLICY_REGISTRY_SCHEMA_VERSION",
    "PolicyClause",
    "PolicyDocument",
    "PolicyVersion",
]
