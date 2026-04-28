# -*- coding: utf-8 -*-
"""shared.llm.providers._common — shared base wrapping llm.LLMClient.

各 provider impl 都委托 llm.LLMClient (复用 cache + provider config + supports_json_mode).
本模块抽出共用 wrapper 函数 · 4 provider impl 走 thin sub-class.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.llm.base import LLMProvider, ProviderResult, ProviderUnavailableError


class _LLMClientWrapper:
    """Common wrapper · 满足 LLMProvider Protocol · 4 provider impl 仅设 name/region/llm_provider_key."""

    name: str = ""
    region: str = "cn"
    llm_provider_key: str = ""  # 与 config.MODEL_CONFIG key 对齐 (deepseek / qwen_cloud / kimi-k2.5 ...)

    def is_available(self) -> bool:
        from config import MODEL_CONFIG  # noqa: PLC0415
        conf = MODEL_CONFIG.get(self.llm_provider_key)
        if not conf:
            return False
        env_name = conf.get("api_key_env", "")
        if not env_name:
            return False
        return bool(os.environ.get(env_name, "").strip())

    def _new_client(self, api_key: str = ""):
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


__all__ = ["_LLMClientWrapper", "LLMProvider", "ProviderResult", "ProviderUnavailableError"]
