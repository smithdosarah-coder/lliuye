# -*- coding: utf-8 -*-
"""shared.llm — re-export shim · 实际定义见 shared.llm_caller.

Phase A worker-A2 · 2026-04-29 · Stage E.3 (`shared/llm/`) 收编到 `shared/llm_caller/`.

保留 shim 防止破坏 channel_signal.py:311 等 1+ production import.
新代码请直接:
    from shared.llm_caller import (
        LLMCaller, chat, chat_json,
        chat_with_fallback, chat_json_with_fallback,
        get_provider, list_providers, DEFAULT_FALLBACK_CHAIN,
        ProviderResult, ProviderUnavailableError,
    )

PIPL 合规设计 (CLAUDE.md §3.6):
  · 境内优先 fallback chain · DEFAULT_FALLBACK_CHAIN = ("deepseek", "dashscope")
  · region 标记 cn/overseas · audit 可识别跨境
  · 通过 env LLM_FALLBACK_CHAIN 覆盖默认 (e.g. "deepseek,qwen,dashscope")
"""
from __future__ import annotations

from shared.llm_caller import (
    DEFAULT_FALLBACK_CHAIN,
    LLMProvider,
    ProviderResult,
    ProviderUnavailableError,
    chat_json_with_fallback,
    chat_with_fallback,
    get_provider,
    list_providers,
)

__all__ = [
    "DEFAULT_FALLBACK_CHAIN",
    "LLMProvider",
    "ProviderResult",
    "ProviderUnavailableError",
    "chat_json_with_fallback",
    "chat_with_fallback",
    "get_provider",
    "list_providers",
]
