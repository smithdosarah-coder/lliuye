# -*- coding: utf-8 -*-
"""Pytest for monitoring_service.health · component checks · graceful degrade."""
from __future__ import annotations

import asyncio

import pytest

from monitoring_service import health


def test_check_metrics_returns_status():
    s = health.check_metrics()
    assert s["component"] == "metrics"
    assert s["status"] in {"ok", "skipped"}


def test_check_sentry_returns_status():
    s = health.check_sentry()
    assert s["component"] == "sentry"
    assert s["status"] in {"ok", "skipped", "degraded"}


def test_check_sqlite_audit_returns_status():
    s = health.check_sqlite_audit()
    assert s["component"] == "sqlite_audit"
    assert s["status"] in {"ok", "degraded", "down"}


def test_check_sqlite_im_returns_status():
    s = health.check_sqlite_im()
    assert s["component"] == "sqlite_im"
    assert s["status"] in {"ok", "degraded", "down"}


def test_check_compliance_storage_ok():
    s = health.check_compliance_storage()
    assert s["component"] == "storage"
    assert s["status"] == "ok"
    assert "compliance_sessions" in s
    assert "alert_sessions" in s


def test_check_agent_routes_with_app():
    """传真 FastAPI app · 应找到 6 Agent routes."""
    import api_server  # noqa: WPS433
    s = health.check_agent_routes(api_server.app)
    assert s["component"] == "agents"
    assert s["status"] in {"ok", "degraded"}
    assert "coverage" in s
    # at least channel + report should match
    assert s["coverage"]["agent_channel"]["ok"] is True
    assert s["coverage"]["agent_report"]["ok"] is True


def test_check_agent_routes_no_app():
    s = health.check_agent_routes(None)
    assert s["status"] == "degraded"


def test_run_extended_health_default_no_external():
    """默认 ping_external=False · DeepSeek + Tavily 标 skipped."""
    import api_server  # noqa: WPS433
    result = asyncio.run(health.run_extended_health(api_server.app))
    assert result["status"] in {"ok", "degraded", "down"}
    assert result["ping_external"] is False
    assert "components" in result
    assert "summary" in result
    components_by_name = {c.get("component"): c for c in result["components"]}
    assert "llm_deepseek" in components_by_name
    assert components_by_name["llm_deepseek"]["status"] == "skipped"


def test_run_extended_health_aggregates_status():
    import api_server  # noqa: WPS433
    result = asyncio.run(health.run_extended_health(api_server.app))
    summary = result["summary"]
    assert summary["total"] == len(result["components"])
    assert summary["ok"] + summary["degraded"] + summary["down"] + summary["skipped"] == summary["total"]


def test_extended_health_components_all_have_component_key():
    import api_server  # noqa: WPS433
    result = asyncio.run(health.run_extended_health(api_server.app))
    for c in result["components"]:
        assert "component" in c
        assert "status" in c


def test_aggregate_status_picks_worst():
    checks = [
        {"component": "a", "status": "ok"},
        {"component": "b", "status": "degraded"},
        {"component": "c", "status": "down"},
    ]
    assert health._aggregate_status(checks) == "down"

    checks2 = [
        {"component": "a", "status": "ok"},
        {"component": "b", "status": "skipped"},
    ]
    assert health._aggregate_status(checks2) == "ok"

    checks3 = [
        {"component": "a", "status": "ok"},
        {"component": "b", "status": "degraded"},
    ]
    assert health._aggregate_status(checks3) == "degraded"
