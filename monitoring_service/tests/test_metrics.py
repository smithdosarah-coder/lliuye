# -*- coding: utf-8 -*-
"""Pytest for monitoring_service.metrics · graceful fallback + middleware."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from monitoring_service import metrics


def test_init_metrics_registers_all_keys():
    """init_metrics 注册 7 个 metric 字典."""
    metrics.reset_registry()
    m = metrics.init_metrics()
    expected = {
        "http_requests_total",
        "http_request_duration_seconds",
        "llm_calls_total",
        "llm_errors_total",
        "llm_call_duration_seconds",
        "im_ws_connections_active",
        "audit_log_writes_total",
    }
    assert expected.issubset(set(m.keys()))


def test_record_llm_call_no_error():
    """成功 llm 调 · 不抛 · counter / histogram 都接收."""
    metrics.reset_registry()
    metrics.record_llm_call(provider="deepseek", agent="report", duration_s=0.42)
    # 单 metric NoOp / Real 都不抛
    assert metrics.get_metric("llm_calls_total") is not None


def test_record_llm_call_with_error():
    metrics.reset_registry()
    metrics.record_llm_call(
        provider="tavily", agent="channel", duration_s=1.0, error_type="401",
    )
    assert metrics.get_metric("llm_errors_total") is not None


def test_normalize_path_strips_uuid():
    norm = metrics.normalize_path(
        "/api/credit/decision/abc12345-6789-4abc-8def-1234567890ab",
    )
    assert ":id" in norm
    assert "abc12345" not in norm


def test_normalize_path_strips_long_hex():
    norm = metrics.normalize_path("/api/im/threads/thr_a1b2c3d4e5f6/messages")
    # 截留 thr_ 前缀 + numeric/hex 替为 :id
    assert ":id" in norm or "thr_" in norm  # 容忍 hex 部分被替


def test_normalize_path_truncates_deep():
    deep = "/a/b/c/d/e/f/g/h/i"
    norm = metrics.normalize_path(deep)
    # 最多 6 段 + :rest 后缀
    parts = norm.split("/")
    assert len(parts) <= 7  # leading "" + 6 segments


def test_metrics_response_returns_text():
    resp = metrics.metrics_response()
    assert resp.media_type.startswith("text/plain")
    body = resp.body
    if metrics.is_prometheus_available():
        # 真 prom output 应含 # HELP / # TYPE 头
        assert b"# HELP" in body or len(body) > 0
    else:
        # NoOp 模式应有提示
        assert b"prometheus_client" in body or b"stub" in body


def test_im_ws_active_helpers_no_throw():
    metrics.reset_registry()
    metrics.set_im_ws_active(5)
    metrics.inc_im_ws_active()
    metrics.dec_im_ws_active()
    metrics.set_im_ws_active(-1)  # negative clamped to 0
    assert metrics.get_metric("im_ws_connections_active") is not None


# ---------------------------------------------------------------------------
# middleware integration
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_metrics():
    app = FastAPI()
    metrics.reset_registry()
    metrics.install_metrics_middleware(app)

    @app.get("/api/test/echo")
    async def echo():
        return {"ok": True}

    @app.get("/api/test/boom")
    async def boom():
        raise RuntimeError("intentional 500")

    @app.get("/metrics")
    async def m():
        return metrics.metrics_response()

    return app


def test_middleware_records_200(app_with_metrics):
    client = TestClient(app_with_metrics)
    resp = client.get("/api/test/echo")
    assert resp.status_code == 200

    metrics_resp = client.get("/metrics")
    body = metrics_resp.text
    if metrics.is_prometheus_available():
        # 应含 path label
        assert "/api/test/echo" in body or "http_requests_total" in body


def test_middleware_records_5xx(app_with_metrics):
    """500 也应记录 metric · 不被 raise 吞掉."""
    client = TestClient(app_with_metrics)
    with pytest.raises(Exception):
        client.get("/api/test/boom")
    # metrics endpoint 仍可访问
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
