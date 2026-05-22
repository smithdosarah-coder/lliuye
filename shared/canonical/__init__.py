# -*- coding: utf-8 -*-
"""shared.canonical — 4 agent canonical input schema (W1 第 1 步).

Per codex R3 R3.4 W1 第 1 步 + user ack codex R3 5 决策:

- credit 7 维 ✅ · compliance 10 rule ✅ · riskctrl 改"客户风险评级" ✅ ·
  alert 加企业信息公示网+浪潮信息 ✅ · ledger LLM 生成 OK ✅

CanonicalInput 是所有 4 agent (credit / compliance / riskctrl / alert) BFF
adapter 的统一入口形态 · 由 4 个 schema 层组成:

1. client_metadata    — templates/client-metadata-schema.json     (33 fields · agent14 已拆)
2. credit_terms       — templates/credit-terms-schema.json        (12 fields · agent14 已拆)
3. material_facts     — templates/material-facts-schema.json      (23 fields · agent14 已拆)
4. decision_context   — templates/decision-context-schema.json    (7 fields · 本次 W1 新增 · credit Agent 决策结果)

下游 adapter 的入参契约:

- credit:     需要 client_metadata + credit_terms + material_facts (decision_context 缺 · 是输出)
- compliance: 需要 client_metadata + material_facts (decision_context optional)
- riskctrl:   需要 client_metadata + decision_context (credit_terms optional · material_facts optional)
- alert:      需要 client_metadata (含 company_name/uscc · 单客 drill 入口) · decision_context optional
"""
from __future__ import annotations

from .contracts import (
    CanonicalInput,
    ClientMetadata,
    CreditTerms,
    DecisionContext,
    MaterialFacts,
    canonical_from_dict,
    credit_done_to_decision_context,
)

__all__ = [
    "CanonicalInput",
    "ClientMetadata",
    "CreditTerms",
    "DecisionContext",
    "MaterialFacts",
    "canonical_from_dict",
    "credit_done_to_decision_context",
]
