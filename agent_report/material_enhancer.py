# -*- coding: utf-8 -*-
"""信贷报告材料解析增强 (Agent6) — fill_pipeline 的补丁层。

定位：识别到企业名后，自动补「工商 6 字段」+ 提供「法规引用核验」工具。
原 form_filler / fill_pipeline 不动；本模块在 fill 之前/之后被 api.py 调用。

设计要点（CLAUDE.md 约束）：
  - 失败优雅降级 → 返回空 dict / 空 list，不打断既有 fill_pipeline
  - 所有结果带 source_url + fetched_at（Evidence-First 证据支撑）
  - 仅填空字段，不覆盖材料/人工已有内容
  - 法规核验只信 flk.npc.gov.cn 官方源（agent_report.law_citation 偏好链）
"""
from __future__ import annotations

from typing import Any

from shared.sources.base import QueryRequest
from shared.sources.router import Router

# 与 enterprise_info 源 REQUIRED_FIELDS 对齐；与 EnterpriseProfile 字段映射如下：
# - registered_capital → EnterpriseProfile.registered_capital
# - legal_representative → EnterpriseProfile.controller_name (近似)
# - establishment_date → EnterpriseProfile.establishment_date
# - industry → EnterpriseProfile.industry
# - business_scope → EnterpriseProfile.main_business
# - registered_address → EnterpriseProfile.region (近似 — 仅当为空时填)
_PROFILE_FIELDS = (
    "registered_capital",
    "legal_representative",
    "establishment_date",
    "industry",
    "business_scope",
    "registered_address",
)


def enhance_material_with_enterprise_info(company_name: str) -> dict:
    """补企业 6 个工商字段 + 同时返回 evidence 锚点。

    Args:
        company_name: 企业名称；空字符串直接返回 {}。

    Returns:
        dict 含：
          - 0~6 个工商字段（值非空才出现）
          - "_evidence_url": 顶级证据 url（取 evidence[0]）
          - "_fetched_at": 抓取时间
          - "_source_name": 实际命中源（enterprise_info / tavily 等）
        失败 → 空 dict，绝不抛异常。
    """
    if not company_name:
        return {}
    try:
        r = Router().query(
            "agent_report.company_lookup",
            QueryRequest(
                query=str(company_name),
                query_type="company_info",
                limit=1,
            ),
        )
        if not (r.ok and r.items):
            return {}
        item = dict(r.items[0] or {})
        # 仅保留官方约定的 6 字段 + 元信息（避免泄漏 source 内部字段）
        out: dict[str, Any] = {f: item.get(f, "") for f in _PROFILE_FIELDS if item.get(f)}
        if r.evidence:
            out["_evidence_url"] = r.evidence[0].source_url
            out["_fetched_at"] = r.evidence[0].fetched_at
            out["_source_name"] = r.evidence[0].source_name or r.source_name
        else:
            out["_evidence_url"] = ""
            out["_fetched_at"] = r.fetched_at
            out["_source_name"] = r.source_name
        return out
    except Exception:
        # 优雅降级：失败不打断 fill_pipeline
        return {}


def lookup_law_citation(query: str) -> list[dict]:
    """法规引用核验 (Agent6 报告正文引用法律法规时调用)。

    Args:
        query: 法律名称、关键词或条款号。空字符串直接返空。

    Returns:
        list of raw_item（含 title / publish / url 等字段，依 flk_npc 源约定）。
        失败 / 无结果 → 空 list。
    """
    if not query:
        return []
    try:
        r = Router().query(
            "agent_report.law_citation",
            QueryRequest(
                query=str(query),
                query_type="law",
                limit=5,
            ),
        )
        if r.ok:
            return list(r.items)
    except Exception:
        pass
    return []
