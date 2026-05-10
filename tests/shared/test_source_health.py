# -*- coding: utf-8 -*-
"""shared.source_health 单测 · 共性架构 #3."""
from __future__ import annotations

import time

import pytest

from shared.source_health import (
    HealthReport,
    SourceHealth,
    SourceRegistration,
    default_health,
)


@pytest.fixture
def health():
    return SourceHealth()


def _reg(source_id="tavily", tier=4, sla=3000, auth="api_key", expiry=None):
    return SourceRegistration(
        source_id=source_id, tier=tier, sla_p99_ms=sla,
        auth_method=auth, auth_expiry=expiry,
    )


class TestRegister:
    def test_register_records(self, health):
        health.register(_reg())
        assert "tavily" in health.list_registered()

    def test_register_overwrite(self, health):
        health.register(_reg(sla=3000))
        health.register(_reg(sla=5000))
        rpt = health.check("tavily")
        assert rpt.sla_p99_target_ms == 5000

    def test_invalid_tier(self, health):
        with pytest.raises(ValueError):
            health.register(_reg(tier=5))

    def test_empty_id(self, health):
        with pytest.raises(ValueError):
            health.register(_reg(source_id=""))


class TestRecordCall:
    def test_record_unknown_silent(self, health):
        # 未注册 source · silent · 不 raise
        health.record_call("nope", latency_ms=100, success=True)

    def test_record_appends(self, health):
        health.register(_reg())
        for _ in range(3):
            health.record_call("tavily", latency_ms=200, success=True)
        rpt = health.check("tavily")
        assert rpt.total_calls_24h == 3

    def test_record_caps_max(self, health):
        health.register(_reg())
        for _ in range(2000):
            health.record_call("tavily", latency_ms=100, success=True)
        rpt = health.check("tavily")
        assert rpt.total_calls_24h <= health.MAX_CALL_RECORDS


class TestCheck:
    def test_unknown_raises(self, health):
        with pytest.raises(KeyError):
            health.check("nope")

    def test_no_calls_healthy_default(self, health):
        # 0 调用 · success_rate 视作 1.0 · auth ok · → healthy
        health.register(_reg())
        rpt = health.check("tavily")
        assert rpt.healthy
        assert rpt.score == 100.0
        assert rpt.total_calls_24h == 0
        assert rpt.last_call_ts is None

    def test_low_success_rate_unhealthy(self, health):
        health.register(_reg())
        for _ in range(8):
            health.record_call("tavily", latency_ms=100, success=False, error_code="500")
        for _ in range(2):
            health.record_call("tavily", latency_ms=100, success=True)
        rpt = health.check("tavily")
        assert not rpt.healthy
        assert rpt.success_rate_24h == 0.2
        assert any("成功率" in n for n in rpt.notes)
        assert rpt.score < 50

    def test_sla_breach(self, health):
        health.register(_reg(sla=200))
        for _ in range(5):
            health.record_call("tavily", latency_ms=500, success=True)
        rpt = health.check("tavily")
        assert rpt.sla_p99_breached
        assert any("SLA" in n for n in rpt.notes)
        assert rpt.score < 100  # 70% 折扣

    def test_expired_auth(self, health):
        # auth 过期
        health.register(_reg(expiry=time.time() - 10))
        rpt = health.check("tavily")
        assert rpt.auth_status == "expired"
        assert not rpt.healthy
        assert rpt.score < 100

    def test_internal_auth_always_ok(self, health):
        health.register(_reg(auth="internal", expiry=None))
        rpt = health.check("tavily")
        assert rpt.auth_status == "ok"

    def test_p50_p99_calculated(self, health):
        health.register(_reg(sla=10_000))
        latencies = [50, 100, 200, 300, 1000]
        for ms in latencies:
            health.record_call("tavily", latency_ms=ms, success=True)
        rpt = health.check("tavily")
        assert rpt.p50_latency_ms == 200
        assert rpt.p99_latency_ms == 1000  # < 100 个样本时取 max


class TestCheckAll:
    def test_check_all_returns_dict(self, health):
        health.register(_reg(source_id="tavily"))
        health.register(_reg(source_id="gsxt", tier=2, sla=5000, auth="cookie"))
        all_rpt = health.check_all()
        assert set(all_rpt.keys()) == {"tavily", "gsxt"}

    def test_list_unhealthy(self, health):
        health.register(_reg(source_id="ok_one"))
        health.register(_reg(source_id="bad_one", expiry=time.time() - 1))
        unhealthy = health.list_unhealthy()
        assert unhealthy == ["bad_one"]


class TestStaleness:
    def test_stale_after_threshold(self, health):
        health.register(_reg())
        # 注入一个 7 小时前的 call
        health.record_call("tavily", latency_ms=100, success=True)
        health._calls["tavily"][0].ts = time.time() - 7 * 3600
        rpt = health.check("tavily")
        assert any("僵死" in n or "未被调用" in n for n in rpt.notes)


class TestReportSerialization:
    def test_to_dict_keys(self, health):
        health.register(_reg())
        rpt = health.check("tavily")
        d = rpt.to_dict()
        assert "source_id" in d
        assert "healthy" in d
        assert "score" in d
        assert "tier" in d


class TestDefaultHealth:
    def test_singleton(self):
        h1 = default_health()
        h2 = default_health()
        assert h1 is h2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
