# -*- coding: utf-8 -*-
"""shared.evidence_drawer · 6 agent 统一证据展示 component.

per docs/working/allin-final-exec-2026-05-08.md §3.2 共性架构 #2.

抽象 6 agent 把 LLM 输出的每一条 claim 关联到证据链的公共 component:

  attach(claim, source, anchor, version, hash) → evidence_id
  list_evidence(claim_id) → [Evidence]
  get_evidence(evidence_id) → Evidence
  to_drawer_payload(claim_id) → dict (前端 drawer 消费)

设计:
- 复用已有 shared.evidence.EvidenceItem (Evidence-First protocol · 单条证据)
- 复用 shared.evidence_freshness 校验 evidence_date + claim_type SLA
- 复用 shared.data_tiers 给 source_url 打 Tier 1-4 标
- evidence_id = uuid · 全局 unique · 跨 agent 引用稳定
- claim_id 由 caller 提供 (e.g. agent 内部段落 hash · 或 sse event id)

Boundary:
- 本模块**不做** LLM 生成 (那是 shared/evidence/protocol.EvidenceFirstPipeline)
- 仅提供 "已生成的 claim ↔ evidence 多对多" 关联 + 前端消费 payload

下游 (Phase B 各 agent):
- channel: 字段级溯源 (commit ef5ba13 · 已实战)
- credit/report/alert/compliance/riskctrl: Phase B 接入
"""
from .drawer import (
    Evidence,
    EvidenceDrawer,
    default_drawer,
)

__all__ = [
    "Evidence",
    "EvidenceDrawer",
    "default_drawer",
]
