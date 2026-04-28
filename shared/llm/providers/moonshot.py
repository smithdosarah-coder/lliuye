# -*- coding: utf-8 -*-
"""shared.llm.providers.moonshot — Moonshot Kimi · NVIDIA 代理 · 备用 provider.

注: NVIDIA 代理路径 · 物理 hop 可能跨境 · PIPL 合规审视后再启用.
默认 fallback chain 不含 · 显式 LLM_PROVIDER=moonshot 才走.
"""
from __future__ import annotations

from shared.llm.providers._common import _LLMClientWrapper


class MoonshotProvider(_LLMClientWrapper):
    """Moonshot Kimi via NVIDIA proxy (region 标 'overseas' · PIPL 慎用)."""

    name = "moonshot"
    region = "overseas"  # NVIDIA proxy · 物理跨境 · PIPL 合规需评估
    llm_provider_key = "kimi-k2.5"


__all__ = ["MoonshotProvider"]
