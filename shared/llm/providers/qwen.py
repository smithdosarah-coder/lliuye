# -*- coding: utf-8 -*-
"""shared.llm.providers.qwen — Qwen alias for DashScope (onboarding 字面命名).

DashScope 提供 qwen-max model · 命名 "qwen" 是 model 维度 · "dashscope" 是 platform 维度.
两者指向同一 backend · alias 用于兼容 onboarding W-E3-A2 字面要求.
"""
from __future__ import annotations

from shared.llm.providers._common import _LLMClientWrapper


class QwenProvider(_LLMClientWrapper):
    """Qwen via DashScope (境内 · PIPL 合规)."""

    name = "qwen"
    region = "cn"
    llm_provider_key = "qwen_cloud"


__all__ = ["QwenProvider"]
