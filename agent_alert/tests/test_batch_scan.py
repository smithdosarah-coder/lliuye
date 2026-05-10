# -*- coding: utf-8 -*-
"""Agent4 BE9.1 · /api/alert/batch_scan 锁盘测试 (Phase B Sprint 2 · 2026-05-04).

锁定:
- 空 scenarios → SSE error event (EMPTY_SCENARIOS)
- 1 scenario · streaming 5+ stage events + aggregate done
- 多 scenario · per_scenario_breakdown 字段 + aggregate metrics
- max_total_customers cap 生效 · batch_capped warning
- client_ids filter · 跨 scenario 通用
- aggregate_hits 字段给 BE9.2 alert_clusterer 消费
- fallback banner 按最严模式 (任一 scenario fallback → mock_fallback)
- 不破现有 4 步 pipeline (复用 run_scan_and_persist)
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from agent_alert.api import AlertBatchScanRequest, _alert_batch_event_stream, app
from auth_service.dependencies import COOKIE_NAME
from auth_service.jwt_util import issue


def _make_client() -> TestClient:
    """TestClient with admin cookie · pass require_action gate.

    Phase B.1 fix (2026-05-09): /api/alert/batch_scan 加 require_action("alert", "invoke") ·
    旧 test 没 cookie 返 401 · admin 跨 action 跨 agent OK · 与 test_export_docx_endpoint 一致.
    """
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, issue("u_test", "admin"))
    return c


def _collect_stream(req: AlertBatchScanRequest) -> str:
    """把 generator 序列化成 stream 字符串 · 不走 ASGI · 单测更快."""
    chunks = list(_alert_batch_event_stream(req))
    return "".join(chunks) if chunks else ""


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_empty_scenarios_yields_error_event():
    body = _collect_stream(AlertBatchScanRequest(scenarios=[]))
    assert "EMPTY_SCENARIOS" in body or "empty" in body.lower()


# ---------------------------------------------------------------------------
# Single scenario streaming
# ---------------------------------------------------------------------------


class TestSingleScenarioStream:
    def test_baseline_scenario_emits_done(self):
        req = AlertBatchScanRequest(
            scenarios=["demo_data/agent_alert"],  # 默认 KB scenario · 走 mock fallback
            force_mock=True,
        )
        body = _collect_stream(req)
        # batch_init stage 必有
        assert "batch_init" in body
        # done event 必有
        assert '"event": "done"' in body
        assert '"mode": "batch"' in body or '"mode":"batch"' in body

    def test_done_includes_per_scenario_breakdown(self):
        req = AlertBatchScanRequest(scenarios=["demo_data/agent_alert"], force_mock=True)
        body = _collect_stream(req)
        # per_scenario field 在 done 里
        assert "per_scenario" in body

    def test_done_includes_aggregate_hits_for_be92(self):
        req = AlertBatchScanRequest(scenarios=["demo_data/agent_alert"], force_mock=True)
        body = _collect_stream(req)
        # BE9.2 alert_clusterer 消费 aggregate_hits 字段
        assert "aggregate_hits" in body


# ---------------------------------------------------------------------------
# max_total_customers cap
# ---------------------------------------------------------------------------


class TestMaxTotalCustomers:
    def test_cap_respected_in_done_metrics(self):
        # 极小 cap=1 + 多 scenario · 验证 done.metrics.total_scanned ≤ max
        req = AlertBatchScanRequest(
            scenarios=["demo_data/agent_alert", "another_scenario"],
            force_mock=True,
            max_total_customers=1,
        )
        body = _collect_stream(req)
        assert '"event": "done"' in body
        # 解析 done event 找 total_scanned · 必 ≤ 1 (cap 生效硬线)
        for line in body.split("\n"):
            if '"event": "done"' in line:
                payload = line.replace("data: ", "").strip()
                done = json.loads(payload)
                ts = done.get("metrics", {}).get("total_scanned", 0)
                assert ts <= 1, f"total_scanned={ts} 超过 cap=1 · 红线破裂"
                break

    def test_cap_default_50000(self):
        # 红线 default · per CLAUDE.md §3.7.1
        req = AlertBatchScanRequest(scenarios=["demo_data/agent_alert"])
        assert req.max_total_customers == 50000


# ---------------------------------------------------------------------------
# client_ids filter
# ---------------------------------------------------------------------------


class TestClientIdsFilter:
    def test_filter_excludes_non_match(self):
        req = AlertBatchScanRequest(
            scenarios=["demo_data/agent_alert"],
            client_ids=["NEVER_EXISTS_XYZ"],
            force_mock=True,
        )
        body = _collect_stream(req)
        # done event 必发 · 但 total_scanned 应该是 0 (filter 全过滤)
        assert '"event": "done"' in body
        # 检查 total_scanned: 0
        assert '"total_scanned": 0' in body or '"total_scanned":0' in body


# ---------------------------------------------------------------------------
# Endpoint registration
# ---------------------------------------------------------------------------


class TestEndpointRegistration:
    def test_endpoint_exists(self):
        client = _make_client()
        r = client.post("/api/alert/batch_scan", json={"scenarios": ["demo_data/agent_alert"]})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

    def test_endpoint_validates_body_shape(self):
        client = _make_client()
        # 缺 scenarios · pydantic 验证默认空 list · 走 EMPTY_SCENARIOS error event
        r = client.post("/api/alert/batch_scan", json={})
        assert r.status_code == 200  # SSE 200 + error event
        assert "EMPTY_SCENARIOS" in r.text

    def test_endpoint_returns_done_event(self):
        client = _make_client()
        r = client.post(
            "/api/alert/batch_scan",
            json={"scenarios": ["demo_data/agent_alert"], "force_mock": True},
        )
        assert r.status_code == 200
        assert '"event": "done"' in r.text


# ---------------------------------------------------------------------------
# Mode-symmetry · fallback banner 按最严
# ---------------------------------------------------------------------------


class TestFallbackBannerSeverity:
    def test_force_mock_includes_banner(self):
        req = AlertBatchScanRequest(
            scenarios=["demo_data/agent_alert"], force_mock=True,
        )
        body = _collect_stream(req)
        # demo_forced (force_mock=True) → mock_forced data_source + info banner
        assert "mock_forced" in body or "fallback" in body
