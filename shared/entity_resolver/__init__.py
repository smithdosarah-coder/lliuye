# -*- coding: utf-8 -*-
"""shared.entity_resolver · 企业实体归一基础设施.

PM 2026-05-07 ALL IN step 2.2 · codex R1 第 1 关键洞察:
  16% 匹配率根因之一 = "同一公司多源错配" (海康在 gsxt/Tavily/微信名字不一样 → 系统当 3 家)

解法: USCC (统一社会信用代码) 作主键 · LLM fuzzy match 兜底 · 多源 candidate 合并去重.

公开 API:
  - resolve_entity(name, uscc=None, strict=False) -> EntityKey · 标准化入口
  - normalize_company_name(name) -> str · 规则化清洗
  - validate_uscc(uscc, strict=False) -> bool · 格式 + 可选 GB32100 校验码
  - validate_uscc_format(uscc) -> bool · 仅格式 (长度 + 字符集)
  - validate_uscc_checksum(uscc) -> bool · 真校验码 (GB 32100-2015)
  - make_unique_id(name, uscc, idx) -> str · 候选 unique id 派生 (per candidate-identity-contract)

Phase 2 (step 2.4-2.5) 接到 channel agent · 多源 candidate 合并时去重.
Phase A common (2026-05-09) 加 GB 32100 校验 + make_unique_id helper.
"""
from .candidate_helpers import (
    ensure_candidate_id,
    ensure_list_unique_ids,
    verify_candidate_ids,
)
from .resolver import (
    EntityKey,
    make_unique_id,
    normalize_company_name,
    resolve_entity,
    validate_uscc,
    validate_uscc_checksum,
    validate_uscc_format,
)

__all__ = [
    "EntityKey",
    "ensure_candidate_id",
    "ensure_list_unique_ids",
    "make_unique_id",
    "normalize_company_name",
    "resolve_entity",
    "validate_uscc",
    "validate_uscc_checksum",
    "validate_uscc_format",
    "verify_candidate_ids",
]
