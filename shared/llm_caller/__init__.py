# -*- coding: utf-8 -*-
"""shared.llm_caller — Phase A worker-A2 唯一化 LLM caller layer.

5 modules:
  · provider.py  · LLMProvider Protocol + ProviderResult + 4 providers + _REGISTRY
  · retry.py     · DEFAULT_FALLBACK_CHAIN + chat_with_fallback + chat_json_with_fallback
  · audit.py     · with_audit ctx · 包 audit_service.decorators (silent fail)
  · prompts.py   · build_chat_messages + with_json_schema_hint utilities
  · client.py    · LLMCaller facade · provider+retry+audit 串

收编 (Stage E.3 → Phase A):
  · root llm.LLMClient                · backing 不动 (caller 1 keep)
  · shared/llm/{base, router, providers/*}  · 改 re-export shim · 1 production import 不破

设计原则 (PIPL 合规):
  · 境内优先 fallback chain · DEFAULT_FALLBACK_CHAIN = ("deepseek", "dashscope")
  · region 标记 cn/overseas · audit 可识别跨境
  · LLMProvider Protocol · 上层只见接口 · 底层 SDK 隔离

Boundary:
  · agent_*/api.py 旧 callers 不动 (A4 territory · 5 子 worker 后续迁)
  · root prompts.py · section_generator inline prompts 不动 (A4 territory)
  · shared/prompts/contract.py 是 A1 worker spec 的 impl · skeleton 待 A1 spec done

Phase A 验收硬线 #2 (charter §1):
  shared/llm_caller/ core 完 · shared/sse_envelope.py 完 · shared/prompts/contract.py 完 · pytest PASS
"""
from __future__ import annotations

# Phase A worker-A2 · M1 · provider layer
from shared.llm_caller.provider import (
    DashScopeProvider,
    DeepSeekProvider,
    LLMProvider,
    MoonshotProvider,
    ProviderResult,
    ProviderUnavailableError,
    QwenProvider,
    get_provider,
    list_providers,
)

# Phase A worker-A2 · M2 · retry / fallback chain layer
from shared.llm_caller.retry import (
    DEFAULT_FALLBACK_CHAIN,
    chat_json_with_fallback,
    chat_with_fallback,
)

# Phase A worker-A2 · M3 · audit layer
from shared.llm_caller.audit import (
    AuditHandle,
    extract_audit_extras,
    record_llm_call,
    with_audit,
)

# Phase A worker-A2 · M4 · prompt composition primitives (无业务 prompt 文本)
from shared.llm_caller.prompts import (
    build_chat_messages,
    truncate_for_context,
    with_few_shot,
    with_json_schema_hint,
)

__all__ = [
    "AuditHandle",
    "DEFAULT_FALLBACK_CHAIN",
    "DashScopeProvider",
    "DeepSeekProvider",
    "LLMProvider",
    "MoonshotProvider",
    "ProviderResult",
    "ProviderUnavailableError",
    "QwenProvider",
    "build_chat_messages",
    "chat_json_with_fallback",
    "chat_with_fallback",
    "extract_audit_extras",
    "get_provider",
    "list_providers",
    "record_llm_call",
    "truncate_for_context",
    "with_audit",
    "with_few_shot",
    "with_json_schema_hint",
]
