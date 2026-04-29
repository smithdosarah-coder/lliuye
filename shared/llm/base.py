# -*- coding: utf-8 -*-
"""shared.llm.base — re-export shim · 实际定义见 shared.llm_caller.provider.

Phase A worker-A2 · 2026-04-29 · Stage E.3 → llm_caller 收编.
保留 shim 防止破坏 channel_signal.py:311 等 1+ production import.
新代码请直接 from shared.llm_caller import ...
"""
from __future__ import annotations

from shared.llm_caller.provider import (
    LLMProvider,
    ProviderResult,
    ProviderUnavailableError,
)

__all__ = [
    "LLMProvider",
    "ProviderResult",
    "ProviderUnavailableError",
]
