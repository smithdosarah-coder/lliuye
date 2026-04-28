# -*- coding: utf-8 -*-
"""shared.llm tests · Protocol + 4 provider + router fallback chain."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from shared.llm.base import (
    LLMProvider,
    ProviderResult,
    ProviderUnavailableError,
)
from shared.llm.providers.dashscope import DashScopeProvider
from shared.llm.providers.deepseek import DeepSeekProvider
from shared.llm.providers.moonshot import MoonshotProvider
from shared.llm.providers.qwen import QwenProvider
from shared.llm.router import (
    DEFAULT_FALLBACK_CHAIN,
    chat_json_with_fallback,
    chat_with_fallback,
    get_provider,
    list_providers,
)


# ============================================================================
# Provider basics
# ============================================================================


def test_4_provider_satisfy_protocol():
    """4 provider 都 isinstance(LLMProvider) Protocol."""
    for cls in (DeepSeekProvider, DashScopeProvider, QwenProvider, MoonshotProvider):
        p = cls()
        assert isinstance(p, LLMProvider)
        assert p.name
        assert p.region in ("cn", "overseas")


def test_deepseek_region_cn():
    assert DeepSeekProvider().region == "cn"


def test_dashscope_region_cn():
    assert DashScopeProvider().region == "cn"


def test_qwen_alias_region_cn():
    """qwen 是 dashscope alias · 也境内."""
    assert QwenProvider().region == "cn"
    assert QwenProvider().llm_provider_key == DashScopeProvider().llm_provider_key


def test_moonshot_region_overseas():
    """Moonshot via NVIDIA proxy · 标 overseas · PIPL 慎用."""
    assert MoonshotProvider().region == "overseas"


# ============================================================================
# Registry / get_provider
# ============================================================================


def test_get_provider_default_deepseek():
    """默认 LLM_PROVIDER 未设 → fallback chain[0] = deepseek."""
    with patch.dict(os.environ, {"LLM_PROVIDER": ""}, clear=False):
        p = get_provider()
        assert p.name == "deepseek"


def test_get_provider_explicit_dashscope():
    p = get_provider("dashscope")
    assert p.name == "dashscope"


def test_get_provider_unknown_raises():
    with pytest.raises(ProviderUnavailableError):
        get_provider("unknown_provider")


def test_list_providers_returns_4():
    result = list_providers()
    names = {p["name"] for p in result}
    assert names == {"deepseek", "dashscope", "qwen", "moonshot"}
    # region 标记完整
    for p in result:
        assert "region" in p
        assert "available" in p


# ============================================================================
# is_available · env-key driven (no API call)
# ============================================================================


def test_is_available_with_key():
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
        assert DeepSeekProvider().is_available() is True


def test_is_available_no_key():
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
        assert DeepSeekProvider().is_available() is False


def test_is_available_dashscope_separate_key():
    """DashScope 用 DASHSCOPE_API_KEY · 不与 DEEPSEEK_API_KEY 混淆."""
    env = {"DEEPSEEK_API_KEY": "ds", "DASHSCOPE_API_KEY": ""}
    with patch.dict(os.environ, env, clear=False):
        assert DashScopeProvider().is_available() is False


# ============================================================================
# Fallback chain · 主 fail → 切备份
# ============================================================================


def test_default_fallback_chain_cn_first():
    """境内优先 · DEFAULT_FALLBACK_CHAIN 第一是 deepseek."""
    assert DEFAULT_FALLBACK_CHAIN[0] == "deepseek"
    assert "dashscope" in DEFAULT_FALLBACK_CHAIN


def test_chat_with_fallback_no_keys_raises():
    """所有 provider 都没 key → ProviderUnavailableError 抛."""
    no_keys = {
        "DEEPSEEK_API_KEY": "",
        "DASHSCOPE_API_KEY": "",
        "NVIDIA_API_KEY": "",
    }
    with patch.dict(os.environ, no_keys, clear=False):
        with pytest.raises(ProviderUnavailableError, match="all providers fail"):
            chat_with_fallback("system", "user", chain=["deepseek", "dashscope"])


def test_chat_with_fallback_main_fail_backup_success(monkeypatch):
    """主 deepseek error → 自动切 dashscope success · result 含 fallback metadata."""
    fake_response = ProviderResult(
        content="fallback ok",
        provider_name="dashscope",
        region="cn",
    )

    def deepseek_fail(self, *a, **kw):
        raise ProviderUnavailableError("simulated deepseek down")

    def dashscope_ok(self, *a, **kw):
        return fake_response

    monkeypatch.setattr(DeepSeekProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DashScopeProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DeepSeekProvider, "chat", deepseek_fail)
    monkeypatch.setattr(DashScopeProvider, "chat", dashscope_ok)

    result = chat_with_fallback(
        "s", "u", chain=["deepseek", "dashscope"],
    )
    assert result.content == "fallback ok"
    assert result.provider_name == "dashscope"
    # metadata 标 fallback 链 · 显示 deepseek 试过 (err)
    assert "fallback_chain" in result.metadata
    assert any("deepseek" in s for s in result.metadata.get("fallback_tried", []))


def test_chat_json_with_fallback_smoke(monkeypatch):
    """chat_json fallback 链同 chat · 验 path 通."""

    def deepseek_unavail(self):
        return False

    fake_json = ProviderResult(
        json_payload={"key": "value"},
        provider_name="dashscope",
        region="cn",
    )

    def dashscope_chat_json(self, *a, **kw):
        return fake_json

    monkeypatch.setattr(DeepSeekProvider, "is_available", deepseek_unavail)
    monkeypatch.setattr(DashScopeProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DashScopeProvider, "chat_json", dashscope_chat_json)

    result = chat_json_with_fallback(
        "s", "u", chain=["deepseek", "dashscope"],
    )
    assert result.json_payload == {"key": "value"}
    assert result.provider_name == "dashscope"


def test_resolve_chain_via_env(monkeypatch):
    """LLM_FALLBACK_CHAIN env override · 验 router 读 env."""
    monkeypatch.setenv("LLM_FALLBACK_CHAIN", "qwen,deepseek")
    monkeypatch.setattr(QwenProvider, "is_available", lambda self: True)

    fake = ProviderResult(content="qwen ok", provider_name="qwen", region="cn")
    monkeypatch.setattr(QwenProvider, "chat", lambda self, *a, **kw: fake)

    result = chat_with_fallback("s", "u")
    assert result.provider_name == "qwen"
    assert result.metadata.get("fallback_chain") == ["qwen", "deepseek"]
