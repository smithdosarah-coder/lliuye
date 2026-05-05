# -*- coding: utf-8 -*-
"""Agent4 BE5.4 · fallback banner SSE 落地锁盘测试 (Phase B Sprint 2 · 2026-05-04).

锁定:
- _resolve_fallback_banner mode_label → banner dict 映射
- live mode 无 banner (None)
- 5 fallback 路径全 banner (demo_forced / tavily_disabled / tavily_key_missing /
  web_fallback_* / unknown)
- _build_done_envelope done event 含 fallback 字段
- demo path done event 也含 fallback (用户透明感知 mock_forced)

per docs/contracts/live-fallback-banner-spec.md v1.0:
- 任何 fallback 必显式 banner · 不静默 swap
- backend 提供机器+人话双层 metadata · frontend 渲染
- 不加新 SSE event 名 (forward-compat per sse-envelope §1.5)
"""
from __future__ import annotations

import pytest

from agent_alert.api import _build_done_envelope, _resolve_fallback_banner


# ---------------------------------------------------------------------------
# _resolve_fallback_banner
# ---------------------------------------------------------------------------


class TestResolveFallbackBanner:
    def test_web_live_no_banner(self):
        assert _resolve_fallback_banner("web_live") is None

    def test_demo_forced_info_banner(self):
        b = _resolve_fallback_banner("demo_forced")
        assert b is not None
        assert b["severity"] == "info"
        assert b["reason"] == "demo_forced"
        assert "演示模式" in b["message"]
        assert b["retried"] is False

    def test_tavily_disabled_warn_banner(self):
        b = _resolve_fallback_banner("tavily_disabled")
        assert b is not None
        assert b["severity"] == "warn"
        assert b["reason"] == "tavily_disabled"
        assert "ALERT_USE_TAVILY" in b["hint"]

    def test_tavily_key_missing_warn_banner(self):
        b = _resolve_fallback_banner("tavily_key_missing")
        assert b is not None
        assert b["severity"] == "warn"
        assert b["reason"] == "tavily_key_missing"
        assert "TAVILY_API_KEY" in b["hint"]

    def test_web_fallback_runtime_error(self):
        b = _resolve_fallback_banner("web_fallback_RuntimeError")
        assert b is not None
        assert b["severity"] == "error"
        assert b["reason"] == "web_fallback_RuntimeError"
        assert b["retried"] is True
        assert "RuntimeError" in b["message"]

    def test_web_fallback_with_value_error(self):
        b = _resolve_fallback_banner("web_fallback_ValueError")
        assert b is not None
        assert b["severity"] == "error"
        assert b["reason"] == "web_fallback_ValueError"

    def test_unknown_mode_label(self):
        b = _resolve_fallback_banner("nonsense_xyz")
        assert b is not None
        assert b["severity"] == "warn"
        assert b["reason"].startswith("unknown_mode_")

    def test_empty_mode_label(self):
        b = _resolve_fallback_banner("")
        assert b is not None
        assert b["reason"].startswith("unknown_mode_")

    def test_banner_required_keys(self):
        # 任意非 live banner · 必含 6 字段 · frontend 渲染契约
        for mode in (
            "demo_forced", "tavily_disabled", "tavily_key_missing",
            "web_fallback_RuntimeError", "unknown_x",
        ):
            b = _resolve_fallback_banner(mode)
            assert b is not None
            for k in ("source", "reason", "severity", "message", "hint", "retried"):
                assert k in b, f"{mode} banner missing {k}"

    def test_banner_severity_enum(self):
        # severity 必 ∈ {info, warn, error} · 前端 banner 配色 hook
        for mode in (
            "demo_forced", "tavily_disabled", "tavily_key_missing",
            "web_fallback_RuntimeError",
        ):
            b = _resolve_fallback_banner(mode)
            assert b["severity"] in ("info", "warn", "error")


# ---------------------------------------------------------------------------
# _build_done_envelope · fallback 注入
# ---------------------------------------------------------------------------


class _StubHitList:
    def __init__(self):
        self.hits = []
        self.red_count = 0
        self.yellow_count = 0
        self.green_count = 0
        self.total_scanned = 0


class TestDoneEnvelopeFallbackInjection:
    def test_live_mode_no_fallback_in_done(self):
        done = _build_done_envelope(
            hit_list=_StubHitList(),
            dispositions={},
            session_id="test-1",
            scenario_key="baseline",
            mode_label="web_live",
            kb_summary="kb ok",
        )
        assert done.get("event") == "done"
        assert "fallback" not in done

    def test_fallback_mode_injects_banner(self):
        done = _build_done_envelope(
            hit_list=_StubHitList(),
            dispositions={},
            session_id="test-2",
            scenario_key="baseline",
            mode_label="web_fallback_RuntimeError",
            kb_summary="kb ok",
        )
        assert "fallback" in done
        assert done["fallback"]["reason"] == "web_fallback_RuntimeError"
        assert done["fallback"]["severity"] == "error"

    def test_disabled_mode_injects_banner(self):
        done = _build_done_envelope(
            hit_list=_StubHitList(),
            dispositions={},
            session_id="test-3",
            scenario_key="baseline",
            mode_label="tavily_disabled",
            kb_summary="kb ok",
        )
        assert "fallback" in done
        assert done["fallback"]["severity"] == "warn"

    def test_demo_forced_injects_info_banner(self):
        done = _build_done_envelope(
            hit_list=_StubHitList(),
            dispositions={},
            session_id="demo-test",
            scenario_key="baseline",
            mode_label="demo_forced",
            kb_summary="demo · 不读 KB",
        )
        assert "fallback" in done
        assert done["fallback"]["severity"] == "info"

    def test_done_event_no_new_sse_event_name(self):
        # 锁定: 不加新 SSE event 名 (per sse-envelope §1.5)
        # 只在 done event 内加 `fallback` 字段
        done = _build_done_envelope(
            hit_list=_StubHitList(),
            dispositions={},
            session_id="test-x",
            scenario_key="baseline",
            mode_label="web_fallback_OSError",
            kb_summary="",
        )
        assert done["event"] == "done"  # 仍 done · 不是新 banner event

    def test_data_source_stays_consistent_with_fallback(self):
        # web_fallback_* → data_source mock_fallback + fallback banner 同步
        done = _build_done_envelope(
            hit_list=_StubHitList(),
            dispositions={},
            session_id="test",
            scenario_key="b",
            mode_label="web_fallback_NetworkError",
            kb_summary="",
        )
        assert done["data_source"] == "mock_fallback"
        assert done["fallback"]["reason"] == "web_fallback_NetworkError"
