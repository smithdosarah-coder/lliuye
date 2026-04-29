# -*- coding: utf-8 -*-
"""tests/shared/test_llm_caller.py — Phase A worker-A2 (M8 of 9).

Coverage:
  · provider · Protocol 满足 / region tagging / is_available env-driven /
                registry / get_provider / list_providers
  · retry    · DEFAULT_FALLBACK_CHAIN / _resolve_chain custom>env>default /
                chat_with_fallback main fail → backup success /
                ProviderUnavailableError 全失败 / fallback metadata 挂
  · audit    · with_audit ctx silent-fail / AuditHandle.attach 抽 tokens / 异常透传 /
                extract_audit_extras / record_llm_call no-op when audit_service 缺
  · prompts  · build_chat_messages / with_json_schema_hint / with_few_shot /
                truncate_for_context
  · client   · LLMCaller(audit_enabled) ctx / 模块级 chat / chat_json
  · backward compat · shared.llm.* shim 全 export · channel_signal-style import
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

# Canonical (Phase A) import path
from shared.llm_caller import (
    DEFAULT_FALLBACK_CHAIN,
    AuditHandle,
    DashScopeProvider,
    DeepSeekProvider,
    LLMCaller,
    LLMProvider,
    MoonshotProvider,
    ProviderResult,
    ProviderUnavailableError,
    QwenProvider,
    build_chat_messages,
    chat,
    chat_json,
    chat_json_with_fallback,
    chat_with_fallback,
    extract_audit_extras,
    get_provider,
    list_providers,
    record_llm_call,
    truncate_for_context,
    with_audit,
    with_few_shot,
    with_json_schema_hint,
)

# ============================================================================
# provider · Protocol + 4 providers + registry
# ============================================================================


def test_4_provider_satisfy_protocol():
    """4 provider 都 isinstance(LLMProvider) Protocol."""
    for cls in (DeepSeekProvider, DashScopeProvider, QwenProvider, MoonshotProvider):
        p = cls()
        assert isinstance(p, LLMProvider)
        assert p.name
        assert p.region in ("cn", "overseas")


def test_region_cn_3_provider():
    """deepseek / dashscope / qwen 全境内 (PIPL 合规)."""
    assert DeepSeekProvider().region == "cn"
    assert DashScopeProvider().region == "cn"
    assert QwenProvider().region == "cn"


def test_region_overseas_moonshot():
    """Moonshot via NVIDIA proxy → 标 overseas · PIPL 慎用."""
    assert MoonshotProvider().region == "overseas"


def test_qwen_alias_dashscope():
    """qwen 是 dashscope alias · llm_provider_key 一致."""
    assert QwenProvider().llm_provider_key == DashScopeProvider().llm_provider_key


def test_get_provider_default_deepseek():
    """LLM_PROVIDER 未设 → 默认 deepseek."""
    with patch.dict(os.environ, {"LLM_PROVIDER": ""}, clear=False):
        p = get_provider()
        assert p.name == "deepseek"


def test_get_provider_explicit_dashscope():
    """显式取 dashscope."""
    p = get_provider("dashscope")
    assert p.name == "dashscope"


def test_get_provider_unknown_raises():
    """unknown name → ProviderUnavailableError."""
    with pytest.raises(ProviderUnavailableError):
        get_provider("unknown_provider")


def test_list_providers_returns_4():
    """list_providers 返 4 provider · region + available 全标."""
    result = list_providers()
    names = {p["name"] for p in result}
    assert names == {"deepseek", "dashscope", "qwen", "moonshot"}
    for p in result:
        assert "region" in p
        assert "available" in p


def test_is_available_with_key():
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
        assert DeepSeekProvider().is_available() is True


def test_is_available_no_key():
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False):
        assert DeepSeekProvider().is_available() is False


def test_is_available_dashscope_separate_key():
    """DashScope 用 DASHSCOPE_API_KEY · 不与 DEEPSEEK 混淆."""
    env = {"DEEPSEEK_API_KEY": "ds", "DASHSCOPE_API_KEY": ""}
    with patch.dict(os.environ, env, clear=False):
        assert DashScopeProvider().is_available() is False


# ============================================================================
# retry · fallback chain
# ============================================================================


def test_default_fallback_chain_cn_first():
    """境内优先 · DEFAULT_FALLBACK_CHAIN[0] = deepseek."""
    assert DEFAULT_FALLBACK_CHAIN[0] == "deepseek"
    assert "dashscope" in DEFAULT_FALLBACK_CHAIN


def test_chat_with_fallback_no_keys_raises():
    """所有 provider 都没 key → ProviderUnavailableError."""
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
    assert "fallback_chain" in result.metadata
    assert any("deepseek" in s for s in result.metadata.get("fallback_tried", []))


def test_chat_json_with_fallback_smoke(monkeypatch):
    """chat_json 同 fallback path."""
    monkeypatch.setattr(DeepSeekProvider, "is_available", lambda self: False)
    fake = ProviderResult(
        json_payload={"key": "value"},
        provider_name="dashscope",
        region="cn",
    )
    monkeypatch.setattr(DashScopeProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DashScopeProvider, "chat_json", lambda self, *a, **kw: fake)

    result = chat_json_with_fallback(
        "s", "u", chain=["deepseek", "dashscope"],
    )
    assert result.json_payload == {"key": "value"}
    assert result.provider_name == "dashscope"


def test_resolve_chain_via_env(monkeypatch):
    """LLM_FALLBACK_CHAIN env 覆盖默认."""
    monkeypatch.setenv("LLM_FALLBACK_CHAIN", "qwen,deepseek")
    monkeypatch.setattr(QwenProvider, "is_available", lambda self: True)
    fake = ProviderResult(content="qwen ok", provider_name="qwen", region="cn")
    monkeypatch.setattr(QwenProvider, "chat", lambda self, *a, **kw: fake)

    result = chat_with_fallback("s", "u")
    assert result.provider_name == "qwen"
    assert result.metadata.get("fallback_chain") == ["qwen", "deepseek"]


# V2 fix · codex review issue 1 · explicit api_key bypass is_available env check
def test_chat_with_fallback_explicit_key_bypasses_env(monkeypatch):
    """显式 api_key 非空时 · _try_each bypass is_available env check · 仍试 provider."""
    # env keys 全空 · is_available() 全 False · 但显式 api_key 应让 chain 仍试
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    monkeypatch.setenv("NVIDIA_API_KEY", "")

    fake = ProviderResult(content="ok via explicit key", provider_name="deepseek", region="cn")
    monkeypatch.setattr(DeepSeekProvider, "chat", lambda self, *a, **kw: fake)

    # 显式 api_key 非空 → bypass env check → 仍调 provider.chat
    result = chat_with_fallback(
        "s", "u",
        api_key="sk-explicit-test-key",
        chain=["deepseek"],
    )
    assert result.content == "ok via explicit key"
    assert result.provider_name == "deepseek"


def test_chat_with_fallback_no_explicit_key_skips_no_env(monkeypatch):
    """对照: 无显式 key + 无 env → is_available False → 全 skip → raise."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    monkeypatch.setenv("NVIDIA_API_KEY", "")

    with pytest.raises(ProviderUnavailableError, match="all providers fail"):
        chat_with_fallback("s", "u", chain=["deepseek", "dashscope"])


def test_chat_with_fallback_explicit_key_still_falls_back(monkeypatch):
    """显式 api_key 时 · 主 provider chat 抛 ProviderUnavailableError · 仍切 fallback."""
    # env 全空
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")

    def deepseek_fail(self, *a, **kw):
        raise ProviderUnavailableError("explicit key invalid for deepseek")

    fake_dashscope = ProviderResult(
        content="dashscope ok",
        provider_name="dashscope",
        region="cn",
    )
    monkeypatch.setattr(DeepSeekProvider, "chat", deepseek_fail)
    monkeypatch.setattr(DashScopeProvider, "chat", lambda self, *a, **kw: fake_dashscope)

    result = chat_with_fallback(
        "s", "u",
        api_key="sk-explicit-test",
        chain=["deepseek", "dashscope"],
    )
    assert result.provider_name == "dashscope"
    # fallback metadata 记 deepseek tried + err
    assert any("deepseek" in s for s in result.metadata.get("fallback_tried", []))


# ============================================================================
# audit · with_audit ctx + AuditHandle + extract_audit_extras
# ============================================================================


def test_extract_audit_extras_full():
    """ProviderResult 全字段 → 全部进 extras (含 metadata 加 meta_ 前缀)."""
    r = ProviderResult(
        content="hi",
        provider_name="deepseek",
        model="deepseek-chat",
        region="cn",
        input_tokens=10,
        output_tokens=20,
        cached=True,
        metadata={"fallback_chain": ["deepseek"]},
    )
    ex = extract_audit_extras(r)
    assert ex["input_tokens"] == 10
    assert ex["output_tokens"] == 20
    assert ex["model"] == "deepseek-chat"
    assert ex["provider_name"] == "deepseek"
    assert ex["region"] == "cn"
    assert ex["cached"] is True
    assert ex["meta_fallback_chain"] == ["deepseek"]


def test_extract_audit_extras_minimal():
    """ProviderResult 默认值 → 仅 region (默认 'cn') 进 extras · 其它字段缺省时不输出."""
    r = ProviderResult()
    ex = extract_audit_extras(r)
    # region 默认 "cn" · PIPL 标记总在 · 其它字段全 None / "" / False / {} 不输出
    assert ex == {"region": "cn"}


def test_with_audit_silent_fail_no_audit_service():
    """audit_service 缺失时 with_audit 不抛 · 业务正常返 (silent fail)."""
    # 不 mock · 只验 silent fail · 即使真 audit_service 在场也应正常返
    with with_audit(agent_id="test", endpoint="/test") as h:
        assert isinstance(h, AuditHandle)
        assert h.t0 > 0


def test_with_audit_attach_extracts():
    """AuditHandle.attach(result) 抽 ProviderResult fields."""
    r = ProviderResult(
        content="x",
        provider_name="qwen",
        model="qwen-max",
        region="cn",
        input_tokens=5,
    )
    with with_audit(agent_id="alert", endpoint="/api/alert/scan") as h:
        h.attach(r)
        assert h.model == "qwen-max"
        assert h.extras["provider_name"] == "qwen"
        assert h.extras["input_tokens"] == 5


def test_with_audit_exception_passthrough():
    """with_audit 异常透传 · finally 仍落 audit (silent fail)."""

    class _CustomError(Exception):
        pass

    with pytest.raises(_CustomError):
        with with_audit(agent_id="x", endpoint="/x"):
            raise _CustomError("boom")


def test_record_llm_call_silent():
    """record_llm_call audit_service 缺失时 no-op · 不抛."""
    record_llm_call(
        agent_id="x", endpoint="/x", model="m",
        latency_ms=10, error=None, extras=None,
    )


# ============================================================================
# prompts · 4 utilities
# ============================================================================


def test_build_chat_messages_shape():
    m = build_chat_messages("sys", "usr")
    assert m == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]


def test_build_chat_messages_empty():
    """空串不抛 · 形状一致."""
    m = build_chat_messages("", "")
    assert len(m) == 2
    assert m[0]["content"] == ""


def test_with_json_schema_hint_appends():
    s = with_json_schema_hint("be helpful", '{"x": int}')
    assert "be helpful" in s
    assert '{"x": int}' in s
    assert "严格合法 JSON" in s


def test_with_json_schema_hint_empty_passthrough():
    """空 hint → 原 system 直返."""
    assert with_json_schema_hint("be helpful", "") == "be helpful"


def test_with_few_shot_renders():
    s = with_few_shot(
        "base",
        [{"input": "a", "output": "b", "reason": "r"}],
        max_n=5,
    )
    assert "base" in s
    assert "示例 1" in s
    assert "原因: r" in s


def test_with_few_shot_empty_passthrough():
    assert with_few_shot("base", None) == "base"
    assert with_few_shot("base", []) == "base"


def test_truncate_for_context_long():
    t = truncate_for_context("a" * 100, 30)
    assert "已截断" in t


def test_truncate_for_context_short():
    assert truncate_for_context("short", 100) == "short"


def test_truncate_for_context_disabled():
    assert truncate_for_context("any", 0) == "any"


# ============================================================================
# client · LLMCaller facade
# ============================================================================


def test_llm_caller_audit_enabled_when_agent_id_set():
    c = LLMCaller(agent_id="channel", endpoint="/test")
    assert c._audit is True


def test_llm_caller_audit_disabled_no_agent_id():
    c = LLMCaller()
    assert c._audit is False


def test_llm_caller_audit_explicitly_disabled():
    c = LLMCaller(agent_id="channel", audit_enabled=False)
    assert c._audit is False


def test_llm_caller_chat_routes_to_fallback(monkeypatch):
    """LLMCaller.chat 真走 chat_with_fallback · audit 无 agent_id 不启."""
    fake = ProviderResult(content="ok", provider_name="deepseek", region="cn")
    monkeypatch.setattr(DeepSeekProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DeepSeekProvider, "chat", lambda self, *a, **kw: fake)

    c = LLMCaller(chain=["deepseek"])
    result = c.chat("s", "u")
    assert result.content == "ok"


def test_llm_caller_chat_json_routes(monkeypatch):
    fake = ProviderResult(json_payload={"a": 1}, provider_name="deepseek")
    monkeypatch.setattr(DeepSeekProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DeepSeekProvider, "chat_json", lambda self, *a, **kw: fake)

    c = LLMCaller(chain=["deepseek"])
    result = c.chat_json("s", "u", schema_hint="{}")
    assert result.json_payload == {"a": 1}


def test_module_level_chat(monkeypatch):
    fake = ProviderResult(content="m", provider_name="deepseek")
    monkeypatch.setattr(DeepSeekProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DeepSeekProvider, "chat", lambda self, *a, **kw: fake)

    result = chat("s", "u", chain=["deepseek"])
    assert result.content == "m"


def test_module_level_chat_json(monkeypatch):
    fake = ProviderResult(json_payload=[1, 2], provider_name="deepseek")
    monkeypatch.setattr(DeepSeekProvider, "is_available", lambda self: True)
    monkeypatch.setattr(DeepSeekProvider, "chat_json", lambda self, *a, **kw: fake)

    result = chat_json("s", "u", chain=["deepseek"])
    assert result.json_payload == [1, 2]


# ============================================================================
# backward compat · shared.llm.* shim
# ============================================================================


def test_shared_llm_shim_imports():
    """shared.llm.* shim 仍 export 完整 API · channel_signal.py:311 等不破."""
    from shared.llm import (  # noqa: PLC0415
        DEFAULT_FALLBACK_CHAIN as shim_chain,
        LLMProvider as shim_protocol,
        ProviderResult as shim_result,
        ProviderUnavailableError as shim_err,
        chat_json_with_fallback as shim_chat_json,
        chat_with_fallback as shim_chat,
        get_provider as shim_get,
        list_providers as shim_list,
    )

    assert shim_chain == DEFAULT_FALLBACK_CHAIN
    assert shim_protocol is LLMProvider
    assert shim_result is ProviderResult
    assert shim_err is ProviderUnavailableError
    assert shim_chat is chat_with_fallback
    assert shim_chat_json is chat_json_with_fallback
    assert shim_get is get_provider
    assert shim_list is list_providers


def test_shared_llm_router_shim_imports():
    """from shared.llm.router import chat_with_fallback (channel_signal.py:311)."""
    from shared.llm.router import chat_with_fallback as shim_chat  # noqa: PLC0415
    assert shim_chat is chat_with_fallback


def test_shared_llm_base_shim_imports():
    """from shared.llm.base import LLMProvider (legacy callsite)."""
    from shared.llm.base import (  # noqa: PLC0415
        LLMProvider as shim_proto,
        ProviderResult as shim_res,
    )
    assert shim_proto is LLMProvider
    assert shim_res is ProviderResult


def test_shared_llm_provider_shim_imports():
    """from shared.llm.providers.deepseek import DeepSeekProvider."""
    from shared.llm.providers.deepseek import DeepSeekProvider as shim_ds  # noqa: PLC0415
    from shared.llm.providers.dashscope import DashScopeProvider as shim_ds2  # noqa: PLC0415
    from shared.llm.providers.qwen import QwenProvider as shim_qw  # noqa: PLC0415
    from shared.llm.providers.moonshot import MoonshotProvider as shim_mo  # noqa: PLC0415
    assert shim_ds is DeepSeekProvider
    assert shim_ds2 is DashScopeProvider
    assert shim_qw is QwenProvider
    assert shim_mo is MoonshotProvider
