# -*- coding: utf-8 -*-
"""shared.llm.providers.dashscope — 阿里云 DashScope (qwen-max) · 境内合规备份."""
from __future__ import annotations

from shared.llm.providers._common import _LLMClientWrapper


class DashScopeProvider(_LLMClientWrapper):
    """阿里云 DashScope OpenAI 兼容 (境内 · PIPL 合规备份 provider).

    主 DeepSeek fail 时 router fallback 到这里 · 仍境内 · 不出境.
    Model: qwen-max (config.MODEL_CONFIG["qwen_cloud"]).
    """

    name = "dashscope"
    region = "cn"
    llm_provider_key = "qwen_cloud"


__all__ = ["DashScopeProvider"]
