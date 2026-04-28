# -*- coding: utf-8 -*-
"""shared.llm · LLM Provider Abstraction (Stage E.3 · PIPL Data Compliance · 2026-04-28).

Spec: docs/onboarding/W-E3-A2-pipl-data-compliance.md.

模块:
  base.py         · LLMProvider Protocol (chat / chat_json) + ProviderResult dataclass
  providers/*.py  · 4 thin wrapper around llm.LLMClient
                    · deepseek (官方 API · 境内合规默认)
                    · dashscope (阿里云 DashScope · qwen-max · 境内合规备份)
                    · qwen (与 dashscope 同 · 命名 alias 兼容 onboarding 字面)
                    · moonshot (Kimi · NVIDIA 代理 · 备用)
  router.py       · get_provider(name) factory · 按 .env LLM_PROVIDER 选默认 ·
                    fallback chain (主 fail → 自动切备份)

设计原则 (PIPL 合规):
  - **境内 LLM 默认**: deepseek 主用 · dashscope 备份 · 都在中国大陆 · 无跨境数据流
  - **境外 SDK 隔离**: openai/anthropic 仍可用但需显式 LLM_PROVIDER=openai · production 应禁
  - **fallback chain 保留 audit**: 主 fail → 备份 success · 每次 call 仍记录到 audit_service
  - **Protocol 不绑定 SDK**: 各 provider impl 自包 LLMClient · 上层只见 Protocol 接口

Boundary:
  - 复用现有 llm.LLMClient (config.py MODEL_CONFIG 4 provider 已配)
  - 不重写 LLM API call 逻辑 · 只加 Protocol 包装 + fallback chain
  - 6 Agent 现有 import 不强制改 (additive · spec gap 留 main CLI fix-forward)
"""
from __future__ import annotations

from shared.llm.base import LLMProvider, ProviderResult, ProviderUnavailableError
from shared.llm.router import (
    DEFAULT_FALLBACK_CHAIN,
    chat_with_fallback,
    chat_json_with_fallback,
    get_provider,
)

__all__ = [
    "DEFAULT_FALLBACK_CHAIN",
    "LLMProvider",
    "ProviderResult",
    "ProviderUnavailableError",
    "chat_json_with_fallback",
    "chat_with_fallback",
    "get_provider",
]
