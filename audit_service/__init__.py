# -*- coding: utf-8 -*-
"""audit_service — LLM call audit trail (Stage E.1 hardening).

银保监合规底线: 所有自动决策可追溯 · 留痕 = 满足合规底线 (PIPL + 银保监监管要求).

Public surface:
  - ``LLMCall`` dataclass · 单次 LLM 调用记录
  - ``AuditRecorder`` · sqlite store (default ``data/audit/llm_calls.db``)
  - ``audit_llm_call(...)`` decorator · 包装 FastAPI endpoint · pre/post hook
  - ``estimate_cost_cny / truncate_text`` 工具函数
  - ``query_calls(...)`` query helper for /api/audit/llm_calls endpoint

Author: Worker A1 (Stage E 第 1 批) · 2026-04-28
"""
from __future__ import annotations

from .decorators import audit_llm_call
from .recorder import (
    AuditRecorder,
    LLMCall,
    default_recorder,
    estimate_cost_cny,
    query_calls,
    truncate_text,
)

__all__ = [
    "AuditRecorder",
    "LLMCall",
    "audit_llm_call",
    "default_recorder",
    "estimate_cost_cny",
    "query_calls",
    "truncate_text",
]
