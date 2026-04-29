# -*- coding: utf-8 -*-
"""shared.llm_caller.retry — fallback chain orchestration (M2 of 5).

Phase A worker-A2 · 2026-04-29 · Stage E.3 → llm_caller 收编.

API:
    DEFAULT_FALLBACK_CHAIN                    · ("deepseek", "dashscope") · 境内优先
    chat_with_fallback(system, user, ...)     · 主 fail → 切下一个 · 全失败抛
    chat_json_with_fallback(system, user, ...) · 同上 · JSON mode
    _resolve_chain(custom)                     · 优先级 custom > env > DEFAULT
    _try_each(chain, op_name, fn)              · 共用 fallback loop · 用于 chat 与 chat_json

Fallback chain (PIPL 合规 · 境内优先):
    DEFAULT_FALLBACK_CHAIN = ("deepseek", "dashscope")
    可通过 env LLM_FALLBACK_CHAIN 覆盖 · e.g. "deepseek,qwen,dashscope"
    moonshot (overseas) 不入默认 · 显式 LLM_PROVIDER=moonshot 才走

Note: get_provider / list_providers / _REGISTRY 在 shared.llm_caller.provider · 不在此模块.
"""
from __future__ import annotations

import logging
import os
from typing import Callable

from shared.llm_caller.provider import (
    LLMProvider,
    ProviderResult,
    ProviderUnavailableError,
    _REGISTRY,
)

logger = logging.getLogger(__name__)

# 默认 fallback chain (PIPL 合规 · 境内优先)
DEFAULT_FALLBACK_CHAIN: tuple[str, ...] = ("deepseek", "dashscope")


def _resolve_chain(custom: list[str] | None = None) -> list[str]:
    """优先级: custom > env LLM_FALLBACK_CHAIN > DEFAULT_FALLBACK_CHAIN."""
    if custom:
        return list(custom)
    env = os.environ.get("LLM_FALLBACK_CHAIN", "").strip()
    if env:
        return [s.strip() for s in env.split(",") if s.strip() in _REGISTRY]
    return list(DEFAULT_FALLBACK_CHAIN)


def _try_each(
    chain: list[str],
    op_name: str,
    fn: Callable[[LLMProvider], ProviderResult],
) -> ProviderResult:
    """共用 fallback loop · 主 fail → 切下一个 · op_name 仅 logging.

    Args:
        chain:    provider name list · 顺序执行
        op_name:  操作名 (chat / chat_json) · 仅 logging
        fn:       (provider) → ProviderResult · 由调用方提供

    Returns:
        首个 success 的 ProviderResult · metadata 含 fallback_chain + fallback_tried.

    Raises:
        ProviderUnavailableError: 全失败时抛 · message 含 chain + tried 详情.
    """
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
            logger.warning("[shared.llm_caller] %s %s failed: %s", op_name, name, e)
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
    """普通 chat · 主 fail → 自动切下一个 · audit 通过 metadata.fallback_tried 可见."""
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
    """JSON mode + fallback chain · 同 chat_with_fallback · 走 chat_json."""
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
]
