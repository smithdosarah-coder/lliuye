# -*- coding: utf-8 -*-
"""shared.evidence · Evidence-First Protocol 基座（CLAUDE.md §3.3）

所有 LLM 生成内容走三阶段：
  Phase 1 — Collect（证据汇集）
  Phase 2 — Generate Grounded（锚定撰写）
  Phase 3 — Self-Audit（自审门控）

每条 claim 必须携带证据链；缺证据的字段显式标 `未能自动填写`，拒绝编造。
"""

from .protocol import (
    AuditFinding,
    AuditedResult,
    EvidenceBundle,
    EvidenceFirstPipeline,
    EvidenceItem,
    GroundedDraft,
    UNFILLED_MARKER,
)

__all__ = [
    "AuditFinding",
    "AuditedResult",
    "EvidenceBundle",
    "EvidenceFirstPipeline",
    "EvidenceItem",
    "GroundedDraft",
    "UNFILLED_MARKER",
]
