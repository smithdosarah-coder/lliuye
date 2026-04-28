# -*- coding: utf-8 -*-
"""shared.llm.providers.deepseek — DeepSeek 官方 API · 境内合规主用."""
from __future__ import annotations

from shared.llm.providers._common import _LLMClientWrapper


class DeepSeekProvider(_LLMClientWrapper):
    """DeepSeek 官方 API (境内 · PIPL 合规默认主用 provider)."""

    name = "deepseek"
    region = "cn"
    llm_provider_key = "deepseek"


__all__ = ["DeepSeekProvider"]
