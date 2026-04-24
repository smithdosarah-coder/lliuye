# -*- coding: utf-8 -*-
"""Policy seed builder — 从 InternalClauseIndex 生成外部新政策搜索 query。

约束 (Batch 2 · onboarding red line):
    - 禁止用 "合规 监管 风险" 这类空 query 兜底
    - 必须基于真抽出的条款主体拼
    - filters.time_range = "6_months" 限定最近 6 月
    - 走规则/模板,不走 LLM
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .internal_policy_indexer import InternalClause


# scope → 监管主体偏置语
_SCOPE_HINT = {
    "credit-sop": "银保监 授信审查 新规",
    "customer-admission": "银保监 客户准入 新规",
    "kyc-aml": "反洗钱 人民银行 新规",
    "review-checklists": "银保监 审查 清单 新规",
    "risk-preference": "银保监 风险偏好 新规",
}

# 过滤:content 太短 / 全是数字标点 → 不做 seed
_MIN_SEMANTIC_LEN = 6


@dataclass
class PolicySeedQuery:
    """一条搜索种子(携带回指的 clause_id)。"""
    query: str
    clause_id: str
    business_scope: str
    filters: dict


def _keyword_query_from_clause(clause: InternalClause) -> str | None:
    """把单条 clause → 合法的搜索 query。

    拼接: <scope 提示> + <section_title> + <top2 keyword>
    """
    hint = _SCOPE_HINT.get(clause.business_scope, "银保监 新规")
    parts: list[str] = [hint]
    if clause.section_title and len(clause.section_title) <= 20:
        parts.append(clause.section_title)
    for kw in clause.keywords[:2]:
        if kw and kw not in parts:
            parts.append(kw)
    # 去空 + 去重 + 删重复空格
    parts = [p for p in parts if p]
    query = " ".join(parts)
    query = re.sub(r"\s+", " ", query).strip()
    # 空壳兜底禁令
    semantic = query.replace("新规", "").replace("银保监", "").replace("人民银行", "").strip()
    if len(semantic) < _MIN_SEMANTIC_LEN:
        return None
    return query


def build_policy_seeds(
    clauses: list[InternalClause],
    max_queries: int = 8,
    time_range_months: int = 6,
) -> list[PolicySeedQuery]:
    """把 internal clauses 抽样成外搜 seed。

    去重策略: 同一个 (business_scope, section_title) 只出 1 条 seed,
    避免对同章节重复搜。
    """
    seen_keys: set[tuple[str, str]] = set()
    out: list[PolicySeedQuery] = []
    for clause in clauses:
        key = (clause.business_scope, clause.section_title)
        if key in seen_keys:
            continue
        q = _keyword_query_from_clause(clause)
        if not q:
            continue
        seen_keys.add(key)
        out.append(PolicySeedQuery(
            query=q,
            clause_id=clause.clause_id,
            business_scope=clause.business_scope,
            filters={
                "time_range": f"{time_range_months}_months",
                "search_depth": "advanced",
            },
        ))
        if len(out) >= max_queries:
            break
    return out
