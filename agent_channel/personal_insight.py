# -*- coding: utf-8 -*-
"""Agent1 候选客户/候选企业个人画像 — Phase B Sprint 3 BE12 (2026-05-05).

per BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE12 schema:
    payload {candidate_id, person_features, product_fit, compliance_check,
             talking_points, pii_redacted, latency_ms}

per Q-052 #2 永不 multi-tenant + B7 BE13 4 维度评价 (个人画像 35% / 产品适配 25% /
合规+话术 20% / PII+latency 20%):
- 后端 only · 不改 frontend layout (per onboarding · B5 owns layout)
- 复用 shared/personal_profile.py (PII redact 走 shared)
- LLM 走 shared/llm_caller (BASELINE=30 · 不增 legacy)

实施 status:
- BE12 schema + 函数 stub (本 sub-PR · ship to API endpoint)
- BE12 真业务逻辑 (LLM grounded 生成 talking_points · PII redact · compliance check)
  → sub-PR 2 implementation (per Q-052 atomic 跨前后端 atomic)
"""
from __future__ import annotations

import time
from typing import Any, TypedDict


class PersonFeatures(TypedDict, total=False):
    """候选客户的个人画像核心特征 · BE12 person_features schema."""

    role:           str   # 决策角色 (e.g. "实际控制人" / "财务总监" / "采购负责人")
    industry_yr:   int   # 行业年限
    education:     str   # 学历 (PII redacted 走 hash · 不存原文)
    age_range:     str   # 年龄区间 (PII redacted · "30-39" 不存具体)
    risk_appetite: str   # 风险偏好 ("保守" / "稳健" / "激进")
    decision_path: str   # 决策路径偏好 ("单点决策" / "委员会")


class ProductFit(TypedDict):
    """候选客户与推荐产品的 fit 度评估."""

    recommended_products: list[str]   # 产品 SKU list (按 fit 降序)
    fit_score:            int         # 0-100 · 产品适配度
    fit_reasons:          list[str]   # 推荐理由 list (各 ≤ 50 char)
    miss_reasons:         list[str]   # 不适配产品的理由 list


class ComplianceCheck(TypedDict):
    """合规检查结果 · 反洗钱 / sanction list / pep 等."""

    pep:           bool                  # 政治公众人物 (PEP)
    sanction:      bool                  # 制裁名单
    aml_risk:      str                   # 反洗钱风险等级 ("低" / "中" / "高")
    flags:         list[str]             # 命中合规标签 list
    last_checked:  str                   # ISO 时间戳 · 最近一次合规扫描
    sources:       list[str]             # 来源 list (e.g. ["pbc_gov", "ofac"])


class TalkingPoints(TypedDict):
    """LLM grounded 生成的话术 · per CLAUDE.md §3.1 概率性计算 · 走 shared/llm_caller."""

    opener:       str        # 开场白 (≤ 100 char)
    key_messages: list[str]  # 关键信息点 list (≤ 5 条)
    objection_responses: list[dict]  # 异议应对 list[{objection, response}]
    closing:      str        # 收尾话术


class PersonalInsightPayload(TypedDict):
    """完整 BE12 personal_insight payload schema · GET /api/channel/personal_insight/{candidate_id}."""

    candidate_id:     str
    person_features:  PersonFeatures
    product_fit:      ProductFit
    compliance_check: ComplianceCheck
    talking_points:   TalkingPoints
    pii_redacted:     bool                # True if 任何 PII 字段已 hash/redact
    latency_ms:       int                 # 端到端 latency · 性能维度 (per B7 BE13 PII+latency 20%)


def build_personal_insight_stub(candidate_id: str) -> PersonalInsightPayload:
    """BE12 personal_insight payload stub · sub-PR 2 implementation 接 LLM 业务逻辑.

    本 sub-PR 1 (contract first) · 仅 schema + stub return.
    sub-PR 2 implementation:
    - person_features: 从 internal_kb (data/channel_kb/) + 外部企查查抽取
    - product_fit: 走 shared/llm_caller (LLM grounded · 证据链)
    - compliance_check: 走 shared/sources (pbc_gov + ofac)
    - talking_points: 走 shared/llm_caller (LLM grounded · 8 段 system prompt)
    - pii_redacted: shared/personal_profile.redact() 走完全部 PII 字段
    - latency_ms: 端到端测量
    """
    t0 = time.time()
    out: PersonalInsightPayload = {
        "candidate_id": candidate_id,
        "person_features": {
            "role": "未能自动填写",
            "industry_yr": 0,
            "education": "未能自动填写",
            "age_range": "未能自动填写",
            "risk_appetite": "未能自动填写",
            "decision_path": "未能自动填写",
        },
        "product_fit": {
            "recommended_products": [],
            "fit_score": 0,
            "fit_reasons": [],
            "miss_reasons": ["sub-PR 1 stub · sub-PR 2 implementation 接 LLM grounded"],
        },
        "compliance_check": {
            "pep": False,
            "sanction": False,
            "aml_risk": "未知",
            "flags": [],
            "last_checked": "",
            "sources": [],
        },
        "talking_points": {
            "opener": "未能自动填写",
            "key_messages": [],
            "objection_responses": [],
            "closing": "未能自动填写",
        },
        "pii_redacted": True,  # stub · 没真 PII 数据 · 视作已 redact
        "latency_ms": int((time.time() - t0) * 1000),
    }
    return out
