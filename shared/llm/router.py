# -*- coding: utf-8 -*-
"""shared.llm.router — provider factory + fallback chain.

API:
    get_provider(name=None)                    · factory · 默认 LLM_PROVIDER env
    chat_with_fallback(system, user, ...)      · 主 fail → 自动切备份 · 全失败抛
    chat_json_with_fallback(system, user, ...) · 同上 · JSON mode

Fallback chain (PIPL 合规 · 境内优先):
    DEFAULT_FALLBACK_CHAIN = ["deepseek", "dashscope"]
    可通过 env LLM_FALLBACK_CHAIN 覆盖 · e.g. "deepseek,qwen,dashscope"
"""
from __future__ import annotations

import logging
import os

from shared.llm.base import LLMProvider, ProviderResult, ProviderUnavailableError
from shared.llm.providers.dashscope import DashScopeProvider
from shared.llm.providers.deepseek import DeepSeekProvider
from shared.llm.providers.moonshot import MoonshotProvider
from shared.llm.providers.qwen import QwenProvider

logger = logging.getLogger(__name__)

# 全部 4 provider 注册表 · name → instance (singleton · stateless · 安全多次复用)
_REGISTRY: dict[str, LLMProvider] = {
    "deepseek": DeepSeekProvider(),
    "dashscope": DashScopeProvider(),
    "qwen": QwenProvider(),
    "moonshot": MoonshotProvider(),
}

# Default fallback chain (PIPL 合规 · 境内优先)
DEFAULT_FALLBACK_CHAIN: tuple[str, ...] = ("deepseek", "dashscope")


def _resolve_chain(custom: list[str] | None = None) -> list[str]:
    """优先级: custom > env LLM_FALLBACK_CHAIN > DEFAULT_FALLBACK_CHAIN."""
    if custom:
        return list(custom)
    env = os.environ.get("LLM_FALLBACK_CHAIN", "").strip()
    if env:
        return [s.strip() for s in env.split(",") if s.strip() in _REGISTRY]
    return list(DEFAULT_FALLBACK_CHAIN)


def get_provider(name: str | None = None) -> LLMProvider:
    """Factory · 取 name (or env LLM_PROVIDER · or fallback chain[0]).

    Raises:
        ProviderUnavailableError if name 不在 registry.
    """
    target = name or os.environ.get("LLM_PROVIDER", "").strip() or DEFAULT_FALLBACK_CHAIN[0]
    if target not in _REGISTRY:
        raise ProviderUnavailableError(
            f"Unknown provider: {target} · valid: {sorted(_REGISTRY)}",
        )
    return _REGISTRY[target]


def list_providers() -> list[dict]:
    """admin / health endpoint · 返各 provider name + region + available 状态."""
    return [
        {
            "name": p.name,
            "region": p.region,
            "available": p.is_available(),
        }
        for p in _REGISTRY.values()
    ]


def _try_each(
    chain: list[str],
    op_name: str,
    fn,
) -> ProviderResult:
    """共用 fallback loop · op_name 仅 logging · fn(provider) → ProviderResult."""
    last_error: Exception | None = None
    tried: list[str] = []
    for name in chain:
        provider = _REGISTRY.get(name)
        if provider is None:
            continue
        if not provider.is_available():
            tried.append(f"{name}:no-key")
            continue
        try:
            result = fn(provider)
            # 标记 fallback 链 · audit / debug 用
            result.metadata["fallback_chain"] = chain
            result.metadata["fallback_tried"] = tried
            return result
        except ProviderUnavailableError as e:
            last_error = e
            tried.append(f"{name}:err")
            logger.warning("[shared.llm] %s %s failed: %s", op_name, name, e)
            continue
    raise ProviderUnavailableError(
        f"{op_name} all providers fail · chain={chain} · tried={tried} · last={last_error}",
    )


def chat_with_fallback(
    system: str,
    user: str,
    *,
    temperature: float | None = None,
    api_key: str = "",
    chain: list[str] | None = None,
) -> ProviderResult:
    """主 fail → 自动切下一个 · audit 通过 metadata.fallback_tried 可见."""
    resolved = _resolve_chain(chain)
    return _try_each(
        resolved,
        "chat",
        lambda p: p.chat(
            system, user, temperature=temperature, api_key=api_key,
        ),
    )


def chat_json_with_fallback(
    system: str,
    user: str,
    *,
    schema_hint: str = "",
    temperature: float | None = None,
    api_key: str = "",
    chain: list[str] | None = None,
) -> ProviderResult:
    """JSON mode + fallback chain."""
    resolved = _resolve_chain(chain)
    return _try_each(
        resolved,
        "chat_json",
        lambda p: p.chat_json(
            system, user,
            schema_hint=schema_hint,
            temperature=temperature,
            api_key=api_key,
        ),
    )


__all__ = [
    "DEFAULT_FALLBACK_CHAIN",
    "chat_json_with_fallback",
    "chat_with_fallback",
    "get_provider",
    "list_providers",
]
