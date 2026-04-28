# -*- coding: utf-8 -*-
"""shared.llm.base — LLMProvider Protocol + ProviderResult dataclass.

Protocol-driven · provider impl 实现这 2 method 即可.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ProviderUnavailableError(RuntimeError):
    """主 LLM 不可用 · 触发 fallback chain · 不抛 client side · audit 记 error."""


@dataclass
class ProviderResult:
    """统一 LLM 调用返回 shape."""

    content: str = ""
    json_payload: dict | list | None = None
    provider_name: str = ""
    model: str = ""
    region: str = "cn"  # cn (境内) / overseas (境外) · audit / PIPL 标记
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """LLM provider Protocol · 4 impl 满足这接口 · router 按名取一个 impl 调用.

    chat:      返纯文本 (simple_chat)
    chat_json: 返结构化 dict/list (chat_json with schema_hint)
    """

    name: str
    region: str  # "cn" 境内 / "overseas" 境外
    """provider 显示名 + 境内/境外标记 · audit 时 PIPL 合规判定."""

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        api_key: str = "",
    ) -> ProviderResult:
        """普通 simple chat · system + user prompt · 返 ProviderResult.content."""
        ...

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: str = "",
        temperature: float | None = None,
        api_key: str = "",
    ) -> ProviderResult:
        """JSON mode · supports_json_mode 走 response_format · 否则 prompt 强约束 + retry.

        返 ProviderResult.json_payload (dict | list).
        """
        ...

    def is_available(self) -> bool:
        """检 api_key 是否在 env · 不 actually 调 API · 启动时筛 fallback chain."""
        ...
