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

LEDGER_SCHEMA_VERSION = "1.1.0"  # v1.1 (PM 2026-05-11 ratify perfect-check-6 · 加 optional parent_turn_id · non-breaking minor bump from 1.0.0)

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
    """Single decision audit record (per docs/contracts/decision-ledger.md §1.2).

    Phase A.5 (2026-05-09 · per RFC cross-agent-feedback-channel ratify):
    - is_feedback: True 时此 entry 是 cross-agent feedback event (per cross-agent-feedback-protocol)
    - feedback_meta: feedback event 业务数据 (FeedbackType / consumer_agents / payload)
    - 现有 entry (is_feedback=False) ABI 不破
    - watcher 用 `WHERE is_feedback = 1` 过滤

    v1.1 (2026-05-11 · PM 刘野 ratify perfect-check-6):
    - parent_turn_id: 跨 mode 父子 turn link · 仅 Cowork → Managed 场景必填 · 单 mode entry 留 None
    - 现有 v1.0 entry 全部 parent_turn_id=None (NULL · sqlite ALTER TABLE 加列默认 NULL · 兼容)
    - 具体 case: Agent2 DSL 生成 turn (Cowork) → backtest 新 turn (Managed) · backtest LedgerEntry 必填 parent_turn_id 指向 DSL turn 的 turn_id
    """

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
    is_feedback: bool = False  # Phase A.5 · True iff cross-agent feedback event
    feedback_meta: dict | None = None  # Phase A.5 · per cross-agent-feedback-protocol §2
    # v1.1 (2026-05-11 PM ratify perfect-check-6) · 跨 mode 父子 turn link
    # 仅 Cowork → Managed 场景填 · 单 mode entry 留 None (NULL · 兼容现有 v1.0 entry)
    # sqlite migration: ALTER TABLE decisions ADD COLUMN parent_turn_id TEXT (默认 NULL · 不需 backfill)
    parent_turn_id: str | None = None

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
