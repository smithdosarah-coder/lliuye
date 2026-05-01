# -*- coding: utf-8 -*-
"""shared.decision_ledger.schema — LedgerEntry dataclass + defaults.

Per docs/contracts/decision-ledger.md v1.0.

Two active rules sit here for back-write to CLAUDE.md §3.7.5:

- ``DEFAULT_RETENTION_BY_AGENT``: per-agent retention class defaults
  tied to 银保监 archive requirements.
- ``ALLOWED_JURISDICTIONS``: enumeration of the 5 jurisdiction values.

Module-level constants (not env-driven) so the values are visible in
git history and any change is a code-review-able diff.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

LEDGER_SCHEMA_VERSION = "1.0.0"

# Allowed jurisdiction values · enum-ish (kept as plain strings to avoid
# needing an extra Enum dep across worker boundaries).
ALLOWED_JURISDICTIONS: frozenset[str] = frozenset({
    "银",      # 银行业
    "保",      # 保险业
    "证",      # 证券业
    "HQ",      # 总行 / 集团总部
    "BRANCH",  # 分行 / 分公司
})

DEFAULT_JURISDICTION = "HQ"

# Retention classes · str-ish enum.
RETENTION_SHORT = "short"      # 90 days · routine alerts / candidates
RETENTION_STANDARD = "standard"  # 5 years · 银保监 archive baseline
RETENTION_LONG = "long"        # 10 years · audit-board底稿

ALLOWED_RETENTION_CLASSES: frozenset[str] = frozenset({
    RETENTION_SHORT, RETENTION_STANDARD, RETENTION_LONG,
})

# Per-agent retention default (per docs/contracts/decision-ledger.md §1.3).
DEFAULT_RETENTION_BY_AGENT: dict[str, str] = {
    "credit": RETENTION_STANDARD,
    "report": RETENTION_LONG,
    "alert": RETENTION_SHORT,
    "compliance": RETENTION_STANDARD,
    "channel": RETENTION_SHORT,
    "riskctrl": RETENTION_STANDARD,
}


@dataclass
class LedgerEntry:
    """Single decision audit record (per docs/contracts/decision-ledger.md §1.2)."""

    decision_id: str
    agent_id: str
    endpoint: str
    ts: str
    input_hash: str
    output_hash: str
    evidence_chain: dict = field(default_factory=dict)
    jurisdiction: str = DEFAULT_JURISDICTION
    retention_class: str = RETENTION_STANDARD
    subject_name: str | None = None
    subject_id: str | None = None
    reviewer_id: str | None = None
    reviewer_action: str | None = None
    reviewer_ts: str | None = None
    created_at: str | None = None  # set by sqlite default

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")


def resolve_retention_class(
    agent_id: str, override: str | None = None,
) -> str:
    """Pick retention class: explicit override > per-agent default > standard."""
    if override:
        if override not in ALLOWED_RETENTION_CLASSES:
            raise ValueError(
                f"retention_class must be one of "
                f"{sorted(ALLOWED_RETENTION_CLASSES)}, got {override!r}"
            )
        return override
    return DEFAULT_RETENTION_BY_AGENT.get(agent_id, RETENTION_STANDARD)


def resolve_jurisdiction(override: str | None = None) -> str:
    """Pick jurisdiction: explicit override > env > HQ.

    Env: ``LIUYE_LEDGER_JURISDICTION``.
    """
    import os
    candidate = override or os.environ.get(
        "LIUYE_LEDGER_JURISDICTION", "",
    ).strip() or DEFAULT_JURISDICTION
    if candidate not in ALLOWED_JURISDICTIONS:
        raise ValueError(
            f"jurisdiction must be one of {sorted(ALLOWED_JURISDICTIONS)}, "
            f"got {candidate!r}"
        )
    return candidate
