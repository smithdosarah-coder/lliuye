# -*- coding: utf-8 -*-
"""Pytest for agent_compliance.scan_engine · Tavily 401 fallback (Q-040 闭环).

复用 Alert pattern · 5 mode 全覆盖.
"""
from __future__ import annotations

import pytest

from agent_compliance import scan_engine


def test_force_mock_returns_demo_forced():
    provider, mode = scan_engine.build_compli_provider(force_mock=True)
    assert mode == "demo_forced"
    assert provider.provider_name == "mock"


def test_default_disabled(monkeypatch):
    """COMPLI_USE_TAVILY 未开 → mock + 标 tavily_disabled."""
    monkeypatch.delenv("COMPLI_USE_TAVILY", raising=False)
    provider, mode = scan_engine.build_compli_provider()
    assert mode == "tavily_disabled"
    assert provider.provider_name == "mock"


def test_key_missing(monkeypatch):
    """COMPLI_USE_TAVILY=1 但缺 TAVILY_API_KEY → mock + 标 tavily_key_missing."""
    monkeypatch.setenv("COMPLI_USE_TAVILY", "1")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    provider, mode = scan_engine.build_compli_provider()
    assert mode == "tavily_key_missing"
    assert provider.provider_name == "mock"


def test_web_live_when_both_set(monkeypatch):
    monkeypatch.setenv("COMPLI_USE_TAVILY", "1")
    monkeypatch.setenv("TAVILY_API_KEY", "fake-test-key")
    provider, mode = scan_engine.build_compli_provider()
    assert mode == "web_live"
    assert provider.provider_name == "web"


def test_web_fallback_on_init_error(monkeypatch):
    monkeypatch.setenv("COMPLI_USE_TAVILY", "1")
    monkeypatch.setenv("TAVILY_API_KEY", "k")

    from shared.kb_scan import search_provider as sp_mod
    original = sp_mod.build_search_provider

    def _broken(demo_mode=None, **kwargs):
        if demo_mode is False:
            raise RuntimeError("simulated init failure")
        return original(demo_mode=True)

    monkeypatch.setattr(sp_mod, "build_search_provider", _broken)
    provider, mode = scan_engine.build_compli_provider()
    assert mode.startswith("web_fallback_RuntimeError")
    assert provider.provider_name == "mock"


# ---------------------------------------------------------------------------
# llm caller wrapper · 缺 key 时返 None (走模板兜底)
# ---------------------------------------------------------------------------


def test_llm_caller_none_when_no_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert scan_engine.build_llm_caller() is None
    assert scan_engine.build_llm_json_caller() is None
