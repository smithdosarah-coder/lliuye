# -*- coding: utf-8 -*-
"""GET /api/channel/sources_health 冒烟测试 (BE1 Step 2)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from agent_channel.api import app


def test_sources_health_returns_three_providers():
    """tavily / akshare / qcc 三 provider 齐 · 含 status / configured / reason 字段."""
    client = TestClient(app)
    resp = client.get("/api/channel/sources_health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "providers" in body
    assert "live_search_available" in body
    assert "fallback_chain_active" in body
    assert "checked_at" in body
    names = {p["name"] for p in body["providers"]}
    assert names == {"tavily", "akshare", "qcc"}
    for p in body["providers"]:
        assert "configured" in p
        assert "status" in p
        assert "reason" in p
        assert p["status"] in {"ok", "degraded", "down"}


def test_sources_health_live_available_iff_any_ok():
    """live_search_available = any(p.status == 'ok') · 无 ok → fallback_chain_active=True."""
    client = TestClient(app)
    body = client.get("/api/channel/sources_health").json()
    any_ok = any(p["status"] == "ok" for p in body["providers"])
    assert body["live_search_available"] is any_ok
    assert body["fallback_chain_active"] is (not any_ok)
