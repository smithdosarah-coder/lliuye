# -*- coding: utf-8 -*-
"""企业画像增强 (Agent3) — feature_extractor 的增强补丁层。

定位：FeatureExtractor 拿到 company_name 后调用本模块，自动补：
  1. 工商基础（注册资本/法人/成立日期/行业/经营范围/注册地址） via enterprise_info
  2. 上市公司财务指标（ROE/毛利率/资产负债率等） via akshare（仅上市公司命中）

设计要点（CLAUDE.md 约束）：
  - 失败必须优雅降级 → 返回空 dict / 空 list，不抛异常打断 FeatureExtractor 主流程
  - 所有结果必须带 source_url + fetched_at（Evidence-First 证据支撑）
  - akshare 返回的财务数字直接透传，禁止让 LLM 二次解读（数据层优先）
  - 仅填空字段，不覆盖已有人工/材料数据（用户输入优先）
"""
from __future__ import annotations

from typing import Any

from shared.sources.base import QueryRequest
from shared.sources.router import Router

# enterprise_info 源返回的 6 字段（与 shared/sources/impls/enterprise_info.py REQUIRED_FIELDS 对齐）
_PROFILE_FIELDS = (
    "registered_capital",
    "legal_representative",
    "establishment_date",
    "industry",
    "business_scope",
    "registered_address",
)


def _get_attr_or_key(obj: Any, key: str) -> Any:
    """profile 既可能是 dataclass / pydantic 对象，也可能是普通 dict——统一访问。"""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def enhance_enterprise_profile(profile: Any, *, llm_fn=None) -> tuple[dict, list[dict]]:
    """对企业画像做外部源补全。

    Args:
        profile: 任意带 company_name 的对象（dict / dataclass / pydantic 都可以）。
        llm_fn: 预留参数，当前 source 自己持有 LLM，不需要外注入。

    Returns:
        enriched: 应被合并进 profile 的字段 dict（仅含「原本为空、现在补到」的字段）。
        evidence_list: list of {field, source_url, fetched_at, source_name}，给 QC 审计。
    """
    enriched: dict[str, Any] = {}
    evidence_list: list[dict] = []

    company_name = _get_attr_or_key(profile, "company_name")
    if not company_name:
        return enriched, evidence_list

    router = Router()

    # ---- 1. 工商基础（enterprise_info → tavily 降级） ----
    try:
        r = router.query(
            "agent_credit.profile",
            QueryRequest(
                query=str(company_name),
                query_type="company_info",
                limit=1,
            ),
        )
        if r.ok and r.items:
            item = r.items[0] or {}
            for k in _PROFILE_FIELDS:
                v = item.get(k)
                # 仅填空字段：不覆盖已有人工/材料数据
                if v and not _get_attr_or_key(profile, k):
                    enriched[k] = v
            for ev in r.evidence:
                evidence_list.append({
                    "field": "enterprise_info",
                    "source_name": ev.source_name or r.source_name,
                    "source_url": ev.source_url,
                    "fetched_at": ev.fetched_at,
                })
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError, LookupError):
        # 优雅降级：增强失败不影响主流程
        pass

    # ---- 2. 上市公司财务指标（akshare） ----
    # akshare 要 stock_code（如 600519），不是公司名。优先用 profile.stock_code，
    # 再退到 enriched.stock_code（enterprise_info 上市路径会填），都没有就跳过。
    stock_code = (
        _get_attr_or_key(profile, "stock_code")
        or enriched.get("stock_code")
    )
    try:
        if not stock_code:
            raise LookupError("no stock_code → skip akshare financial")
        r2 = router.query(
            "agent_credit.industry_benchmark",
            QueryRequest(
                query=str(stock_code),
                query_type="financial",
                limit=1,
            ),
        )
        if r2.ok and r2.items:
            # 财务结构化数字直接透传，不让 LLM 重算
            enriched["financial_summary"] = r2.items[0]
            for ev in r2.evidence:
                evidence_list.append({
                    "field": "financial_summary",
                    "source_name": ev.source_name or r2.source_name,
                    "source_url": ev.source_url,
                    "fetched_at": ev.fetched_at,
                })
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError, LookupError):
        pass

    return enriched, evidence_list
