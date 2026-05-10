# -*- coding: utf-8 -*-
"""Pytest for agent_alert.scan_engine · Tavily fallback + run_scan_and_persist.

不调真 LLM · 不调真 Tavily · 全用 mock provider + monkeypatch.
"""
from __future__ import annotations

import json

import pytest

from agent_alert import scan_engine


# ---------------------------------------------------------------------------
# Tavily 401 fallback · build_alert_provider
# ---------------------------------------------------------------------------


def test_build_alert_provider_force_mock():
    provider, mode = scan_engine.build_alert_provider(force_mock=True)
    assert mode == "demo_forced"
    assert provider.provider_name == "mock"


def test_build_alert_provider_tavily_disabled(monkeypatch):
    """ALERT_USE_TAVILY=0 显式关 → demo · 标 tavily_disabled.

    ALL IN Phase B step 3 (2026-05-09): 默认 ALERT_USE_TAVILY=1 (真接 web) ·
    显式 0 才 disable. 旧 default=0 不再适用.
    """
    monkeypatch.setenv("ALERT_USE_TAVILY", "0")
    provider, mode = scan_engine.build_alert_provider()
    assert mode == "tavily_disabled"
    assert provider.provider_name == "mock"


def test_build_alert_provider_key_missing(monkeypatch):
    """ALERT_USE_TAVILY=1 但 TAVILY_API_KEY 缺 → 回退 demo · 标 tavily_key_missing."""
    monkeypatch.setenv("ALERT_USE_TAVILY", "1")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    provider, mode = scan_engine.build_alert_provider()
    assert mode == "tavily_key_missing"
    assert provider.provider_name == "mock"


def test_build_alert_provider_web_live(monkeypatch):
    """ALERT_USE_TAVILY=1 + TAVILY_API_KEY 存在 → web_live (尚未 smoke · 调用时再 fallback)."""
    monkeypatch.setenv("ALERT_USE_TAVILY", "1")
    monkeypatch.setenv("TAVILY_API_KEY", "fake-key-for-test")
    provider, mode = scan_engine.build_alert_provider()
    assert mode == "web_live"
    assert provider.provider_name == "web"


def test_build_alert_provider_web_fallback_on_init_error(monkeypatch):
    """build_search_provider 抛错 → 自动降级 mock · mode 含错误类型."""
    monkeypatch.setenv("ALERT_USE_TAVILY", "1")
    monkeypatch.setenv("TAVILY_API_KEY", "k")

    from shared.kb_scan import search_provider as sp_mod

    original = sp_mod.build_search_provider

    def _broken(demo_mode=None, **kwargs):
        if demo_mode is False:
            raise RuntimeError("simulated init failure")
        return original(demo_mode=True)

    monkeypatch.setattr(sp_mod, "build_search_provider", _broken)
    provider, mode = scan_engine.build_alert_provider()
    assert mode.startswith("web_fallback_RuntimeError")
    assert provider.provider_name == "mock"


# ---------------------------------------------------------------------------
# run_scan_and_persist · 完整路径（端到端使用预置场景 demo_data/agent_alert）
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_alert_dir(tmp_path, monkeypatch):
    """把持久化目录指到 tmp_path · 避免污染真实 data/alert/."""
    alert_dir = tmp_path / "alert"
    sessions_dir = alert_dir / "sessions"
    monkeypatch.setattr(scan_engine, "ALERT_DATA_DIR", alert_dir)
    monkeypatch.setattr(scan_engine, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(scan_engine, "LATEST_POINTER", alert_dir / "latest.json")
    return alert_dir


def test_run_scan_and_persist_end_to_end(isolated_alert_dir, monkeypatch):
    """跑完整 scan · 验事件流 + 持久化 + 红黄绿计数 ≥ 0."""
    # force_mock=True 让 provider 必走 demo · 不依赖 Tavily
    events = []
    session_id = ""
    gen = scan_engine.run_scan_and_persist(
        scenario_key="",  # 默认场景
        force_mock=True,
        api_key="dummy",
    )
    try:
        while True:
            events.append(next(gen))
    except StopIteration as stop:
        session_id = stop.value or ""

    # 至少有 search_provider 事件 + scan 事件
    types = [e.get("type") for e in events if isinstance(e, dict)]
    assert any(t == "tool_result" for t in types), f"no tool_result event: {types}"
    assert any(t == "session" for t in types), f"no session event: {types}"

    # session_id 已经写盘
    session_evt = next(e for e in events if e.get("type") == "session")
    sid = session_evt["session_id"]
    assert sid
    assert session_id == sid

    # 持久化文件存在
    assert (isolated_alert_dir / "sessions" / f"{sid}.json").is_file()
    assert (isolated_alert_dir / "latest.json").is_file()

    # latest pointer 指向同一 session
    pointer = json.loads((isolated_alert_dir / "latest.json").read_text(encoding="utf-8"))
    assert pointer["session_id"] == sid

    # hit_list payload schema 验
    payload = json.loads((isolated_alert_dir / "sessions" / f"{sid}.json").read_text(encoding="utf-8"))
    assert payload["session_id"] == sid
    assert payload["mode"] == "demo_forced"
    assert "hit_list" in payload
    hl = payload["hit_list"]
    assert hl["agent_name"] == "alert"
    assert isinstance(hl["hits"], list)
    # 红黄绿计数 + total
    assert hl["red_count"] + hl["yellow_count"] + hl["green_count"] == hl["total_hit"]


def test_persist_hitlist_explicit_session_id(isolated_alert_dir):
    """显式传 session_id · 落盘文件名一致 · latest pointer 也指向它."""
    from shared.kb_scan.models import HitList

    hit_list = HitList(list_id="lst_test", agent_name="alert",
                       red_count=1, yellow_count=2, green_count=3,
                       total_hit=6, total_scanned=6)
    sid = scan_engine.persist_hitlist(
        hit_list, dispositions={}, session_id="explicit-sid-001",
        mode_label="demo_forced", scenario_key="test",
    )
    assert sid == "explicit-sid-001"

    file = isolated_alert_dir / "sessions" / "explicit-sid-001.json"
    assert file.is_file()
    pointer = json.loads((isolated_alert_dir / "latest.json").read_text(encoding="utf-8"))
    assert pointer["session_id"] == "explicit-sid-001"
