# -*- coding: utf-8 -*-
"""shared.llm.providers._common — re-export shim · 实际定义见 shared.llm_caller.provider.

Phase A worker-A2 · 2026-04-29 · Stage E.3 → llm_caller 收编.
新代码请直接 from shared.llm_caller import _LLMClientWrapper.
"""
from __future__ import annotations

from shared.llm_caller.provider import (
    LLMProvider,
    ProviderResult,
    ProviderUnavailableError,
    _LLMClientWrapper,
)

__all__ = [
    "LLMProvider",
    "ProviderResult",
    "ProviderUnavailableError",
    "_LLMClientWrapper",
]
