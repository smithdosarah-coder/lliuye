# -*- coding: utf-8 -*-
"""shared.llm.router — re-export shim · 实际定义见 shared.llm_caller.{retry, provider}.

Phase A worker-A2 · 2026-04-29 · Stage E.3 → llm_caller 收编.
保留 shim 防止破坏 channel_signal.py:311 等 1+ production import.

新代码请直接:
    from shared.llm_caller import chat_with_fallback, get_provider, ...
"""
from __future__ import annotations

from shared.llm_caller.provider import (
    _REGISTRY,
    get_provider,
    list_providers,
)
from shared.llm_caller.retry import (
    DEFAULT_FALLBACK_CHAIN,
    _resolve_chain,
    _try_each,
    chat_json_with_fallback,
    chat_with_fallback,
)

__all__ = [
    "DEFAULT_FALLBACK_CHAIN",
    "_REGISTRY",
    "_resolve_chain",
    "_try_each",
    "chat_json_with_fallback",
    "chat_with_fallback",
    "get_provider",
    "list_providers",
]
