# -*- coding: utf-8 -*-
"""shared.llm_caller.provider — LLM provider abstraction (M1 of 5).

Phase A worker-A2 · 收编 Stage E.3 (2026-04-29):
  来源:
    · shared/llm/base.py            · LLMProvider Protocol + ProviderResult + ProviderUnavailableError
    · shared/llm/providers/_common  · _LLMClientWrapper (wraps root llm.LLMClient)
    · shared/llm/providers/{deepseek, dashscope, qwen, moonshot}  · 4 thin sub-class
  原物理文件保留为 re-export shim · channel_signal.py:311 import 不破。

设计原则 (PIPL 合规):
  · 境内 LLM 默认: deepseek / dashscope / qwen 全 region="cn"
  · 境外标记: moonshot via NVIDIA proxy → region="overseas" (audit 时 PIPL 慎用)
  · 复用 root llm.LLMClient · config.MODEL_CONFIG 已配 4 provider · 无重写 SDK 调用
  · Protocol 不绑 SDK · 上层只见接口

Boundary:
  · root llm.LLMClient 保留 (caller 1 keep · 6+ 处 production import 不动)
  · agent_*/api.py 旧 callers 不动 (A4 territory)
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# 项目根入 sys.path · 让 from llm import LLMClient / from config import 可解析
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ProviderUnavailableError(RuntimeError):
    """主 LLM 不可用 · 触发 fallback chain · audit 记 error · 不直抛 client side."""


# ---------------------------------------------------------------------------
# ProviderResult dataclass
# ---------------------------------------------------------------------------


@dataclass
class ProviderResult:
    """统一 LLM 调用返回 shape · audit / fallback metadata 在此挂."""

    content: str = ""
    json_payload: dict | list | None = None
    provider_name: str = ""
    model: str = ""
    region: str = "cn"  # cn (境内 PIPL 合规) / overseas (跨境 · audit 标)
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached: bool = False
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# LLMProvider Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    """LLM provider Protocol · 所有 impl 满足此接口 · router 按名调."""

    name: str
    region: str  # "cn" 境内 / "overseas" 境外

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
        """检 api_key 是否在 env · 启动时筛 fallback chain · 不真调 API."""
        ...


# ---------------------------------------------------------------------------
# _LLMClientWrapper · 委托 root llm.LLMClient (复用 cache + provider config)
# ---------------------------------------------------------------------------


class _LLMClientWrapper:
    """Common wrapper · 满足 LLMProvider Protocol · 4 provider impl 仅设 name/region/llm_provider_key.

    底层走 root llm.LLMClient · 复用 cache + supports_json_mode + max_tokens config.
    各 provider 实例化时不 init client · lazy 在 chat() 内 _new_client (避免无 key 启动失败).
    """

    name: str = ""
    region: str = "cn"
    llm_provider_key: str = ""  # 与 config.MODEL_CONFIG key 对齐

    def is_available(self) -> bool:
        """检 env 中对应 api_key_env 有值 · 用于 fallback chain 启动筛."""
        from config import MODEL_CONFIG  # noqa: PLC0415
        conf = MODEL_CONFIG.get(self.llm_provider_key)
        if not conf:
            return False
        env_name = conf.get("api_key_env", "")
        if not env_name:
            return False
        return bool(os.environ.get(env_name, "").strip())

    def _new_client(self, api_key: str = ""):
        """Lazy 实例化 root llm.LLMClient · 失败抛 ProviderUnavailableError."""
        from llm import LLMClient  # noqa: PLC0415
        try:
            return LLMClient(provider=self.llm_provider_key, api_key=api_key)
        except Exception as e:
            raise ProviderUnavailableError(
                f"LLMClient init failed for {self.name}: {e}",
            ) from e

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        api_key: str = "",
    ) -> ProviderResult:
        client = self._new_client(api_key)
        try:
            text = client.simple_chat(system, user, temperature=temperature)
        except Exception as e:
            raise ProviderUnavailableError(
                f"{self.name} chat failed: {type(e).__name__}: {e}",
            ) from e
        return ProviderResult(
            content=text or "",
            provider_name=self.name,
            model=getattr(client, "model", ""),
            region=self.region,
        )

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: str = "",
        temperature: float | None = None,
        api_key: str = "",
    ) -> ProviderResult:
        client = self._new_client(api_key)
        try:
            payload: Any = client.chat_json(
                system_prompt=system,
                user_content=user,
                schema_hint=schema_hint,
                temperature=temperature,
            )
        except Exception as e:
            raise ProviderUnavailableError(
                f"{self.name} chat_json failed: {type(e).__name__}: {e}",
            ) from e
        if isinstance(payload, (dict, list)):
            json_payload: dict | list | None = payload
        else:
            json_payload = None
        return ProviderResult(
            content="",
            json_payload=json_payload,
            provider_name=self.name,
            model=getattr(client, "model", ""),
            region=self.region,
        )


# ---------------------------------------------------------------------------
# 4 provider classes (consolidated · 替代原 providers/{deepseek,dashscope,qwen,moonshot}.py)
# ---------------------------------------------------------------------------


class DeepSeekProvider(_LLMClientWrapper):
    """DeepSeek 官方 API (境内 · PIPL 合规默认主用 provider).

    Model: deepseek-chat (config.MODEL_CONFIG["deepseek"]).
    """

    name = "deepseek"
    region = "cn"
    llm_provider_key = "deepseek"


class DashScopeProvider(_LLMClientWrapper):
    """阿里云 DashScope OpenAI 兼容 (境内 · PIPL 合规备份 provider).

    主 DeepSeek fail 时 router fallback 到这里 · 仍境内 · 不出境.
    Model: qwen-max (config.MODEL_CONFIG["qwen_cloud"]).
    """

    name = "dashscope"
    region = "cn"
    llm_provider_key = "qwen_cloud"


class QwenProvider(_LLMClientWrapper):
    """Qwen via DashScope (境内 · PIPL 合规) · alias of DashScopeProvider.

    DashScope 提供 qwen-max model · "qwen" 是 model 维度 · "dashscope" 是 platform 维度.
    两者指向同一 backend · alias 兼容 onboarding W-A2 字面要求.
    """

    name = "qwen"
    region = "cn"
    llm_provider_key = "qwen_cloud"


class MoonshotProvider(_LLMClientWrapper):
    """Moonshot Kimi via NVIDIA proxy (region="overseas" · PIPL 慎用).

    NVIDIA 代理路径 · 物理 hop 可能跨境 · audit 标 overseas.
    默认 fallback chain 不含 · 显式 LLM_PROVIDER=moonshot 才走.
    """

    name = "moonshot"
    region = "overseas"  # NVIDIA proxy · 物理跨境 · PIPL 合规需评估
    llm_provider_key = "kimi-k2.5"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


_REGISTRY: dict[str, LLMProvider] = {
    "deepseek": DeepSeekProvider(),
    "dashscope": DashScopeProvider(),
    "qwen": QwenProvider(),
    "moonshot": MoonshotProvider(),
}


def get_provider(name: str | None = None) -> LLMProvider:
    """Factory · 取 name (or env LLM_PROVIDER · or "deepseek" 默认).

    Raises:
        ProviderUnavailableError: name 不在 _REGISTRY.
    """
    target = name or os.environ.get("LLM_PROVIDER", "").strip() or "deepseek"
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


__all__ = [
    "DashScopeProvider",
    "DeepSeekProvider",
    "LLMProvider",
    "MoonshotProvider",
    "ProviderResult",
    "ProviderUnavailableError",
    "QwenProvider",
    "_LLMClientWrapper",
    "_REGISTRY",
    "get_provider",
    "list_providers",
]
