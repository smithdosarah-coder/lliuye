# -*- coding: utf-8 -*-
"""shared.entity_resolver · 企业实体归一基础设施.

PM 2026-05-07 ALL IN step 2.2 · codex R1 第 1 关键洞察:
  16% 匹配率根因之一 = "同一公司多源错配" (海康在 gsxt/Tavily/微信名字不一样 → 系统当 3 家)

解法: USCC (统一社会信用代码) 作主键 · LLM fuzzy match 兜底 · 多源 candidate 合并去重.

公开 API:
  - resolve_entity(name, uscc=None) -> EntityKey · 标准化入口
  - normalize_company_name(name) -> str · 规则化清洗
  - validate_uscc(uscc) -> bool · 18 位校验

Phase 2 (step 2.4-2.5) 接到 channel agent · 多源 candidate 合并时去重.
"""
from .resolver import (
    EntityKey,
    normalize_company_name,
    resolve_entity,
    validate_uscc,
)

__all__ = [
    "EntityKey",
    "normalize_company_name",
    "resolve_entity",
    "validate_uscc",
]
