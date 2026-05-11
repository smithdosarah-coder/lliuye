# -*- coding: utf-8 -*-
"""agent_channel canary · LIUYE_AGENT_CHANNEL_SHARED_CONFIDENCE flag gate (B.3.4 P0-R1).

per docs/contracts/shared-evidence-confidence-policy-v1.0.md §3 (flag-gate strategy)

验:
- flag OFF (default): 信号 confidence = 0.8 if url else 0.5 (旧静态值)
- flag ON: 信号 confidence = shared.evidence.confidence_policy.quality_bundle (freshness×source)

注: flag 是 module-level 常量 (启动时 read env once · 不支持 runtime monkeypatch).
    本测试通过 importlib.reload 切换 · 隔离副作用.
"""
from __future__ import annotations

import importlib
import os

import pytest


CANARY_FLAG = "LIUYE_AGENT_CHANNEL_SHARED_CONFIDENCE"


def _reload_pipeline_with_flag(value: str | None):
    """Reload agent_channel.evidence_pipeline with given flag value · returns module."""
    if value is None:
        os.environ.pop(CANARY_FLAG, None)
    else:
        os.environ[CANARY_FLAG] = value
    import agent_channel.evidence_pipeline as ep
    return importlib.reload(ep)


@pytest.fixture
def signal_with_url_and_today():
    """Signal with url + today's date (max freshness · "high" source level)."""
    from datetime import date
    return {
        "signal_type": "news",
        "title": "客户上市",
        "url": "https://example.com/news",
        "date": date.today().isoformat(),
    }


@pytest.fixture
def context_with_signal(signal_with_url_and_today):
    from agent_channel.evidence_pipeline import ChannelPitchContext
    return ChannelPitchContext(
        candidate={"company_name": "测试客户"},
        signals=[signal_with_url_and_today],
        products=[],
    )


def _get_signal_confidence(pipeline_cls, ctx):
    """Run collect · return signal evidence confidence."""
    pipe = pipeline_cls()
    bundle = pipe.collect(ctx)
    sig_items = [it for it in bundle.items if it.ref_id.startswith("sig_")]
    assert len(sig_items) == 1
    return sig_items[0].confidence


class TestCanaryFlagGate:
    def test_flag_off_uses_static_confidence(self, context_with_signal):
        ep = _reload_pipeline_with_flag(None)
        confidence = _get_signal_confidence(ep.ChannelPitchPipeline, context_with_signal)
        # url 存在 · 静态 0.8
        assert confidence == 0.8

    def test_flag_off_no_url_uses_0_5(self):
        from agent_channel.evidence_pipeline import ChannelPitchContext
        ep = _reload_pipeline_with_flag(None)
        ctx = ChannelPitchContext(
            candidate={"company_name": "测试"},
            signals=[{"signal_type": "news", "title": "无 url", "date": "2026-05-11"}],
            products=[],
        )
        confidence = _get_signal_confidence(ep.ChannelPitchPipeline, ctx)
        # url 缺 · 静态 0.5
        assert confidence == 0.5

    def test_flag_on_uses_shared_quality_bundle(self, context_with_signal):
        ep = _reload_pipeline_with_flag("true")
        confidence = _get_signal_confidence(ep.ChannelPitchPipeline, context_with_signal)
        # url + today + "high" → 0.95 × 1.0 = 0.95
        assert confidence == pytest.approx(0.95, abs=1e-3)

    def test_flag_on_no_url_uses_med(self):
        from agent_channel.evidence_pipeline import ChannelPitchContext
        from datetime import date
        ep = _reload_pipeline_with_flag("true")
        ctx = ChannelPitchContext(
            candidate={"company_name": "测试"},
            signals=[{"signal_type": "news", "title": "无 url 但今天", "date": date.today().isoformat()}],
            products=[],
        )
        confidence = _get_signal_confidence(ep.ChannelPitchPipeline, ctx)
        # 无 url + today + "med" → 0.70 × 1.0 = 0.70
        assert confidence == pytest.approx(0.70, abs=1e-3)

    def test_flag_on_old_signal_decays(self):
        from agent_channel.evidence_pipeline import ChannelPitchContext
        from datetime import date, timedelta
        ep = _reload_pipeline_with_flag("true")
        old_date = (date.today() - timedelta(days=10)).isoformat()
        ctx = ChannelPitchContext(
            candidate={"company_name": "测试"},
            signals=[{"signal_type": "news", "title": "10天前", "url": "https://x", "date": old_date}],
            products=[],
        )
        confidence = _get_signal_confidence(ep.ChannelPitchPipeline, ctx)
        # url + 10天前(freshness=0) + "high" → 0.95 × 0.5 = 0.475
        assert confidence == pytest.approx(0.475, abs=1e-3)

    def test_flag_recognizes_truthy_values(self, context_with_signal):
        for v in ("true", "True", "TRUE", "  true  "):
            ep = _reload_pipeline_with_flag(v)
            assert ep._USE_SHARED_CONFIDENCE is True, f"flag value {v!r} not recognized"

    def test_flag_default_is_off(self, context_with_signal):
        for v in (None, "false", "0", "no", "False"):
            ep = _reload_pipeline_with_flag(v)
            assert ep._USE_SHARED_CONFIDENCE is False, f"flag value {v!r} should be off"


def teardown_module(module):
    """Restore default flag state after this test module runs."""
    os.environ.pop(CANARY_FLAG, None)
    import agent_channel.evidence_pipeline as ep
    importlib.reload(ep)
