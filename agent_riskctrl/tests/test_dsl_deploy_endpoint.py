# -*- coding: utf-8 -*-
"""tests/agent_riskctrl/test_dsl_deploy_endpoint.py — V2 fix (codex major 1).

POST /api/riskctrl/dsl/deploy production caller for record_dsl_deploy.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from agent_riskctrl.api import app
    return TestClient(app)


def test_dsl_deploy_basic_records_and_returns_id(client):
    body = {
        "ruleset_id": "rs_endpoint_001",
        "dsl_version": "v1.2.0",
        "rule_count": 5,
        "affected_segments": ["科创", "对公财务"],
        "backtest_summary": {
            "ks_peak": 0.32,
            "auc": 0.71,
            "bad_rate": 0.041,
            "profit_total_wan": 318.5,
        },
        "approver_user_id": "u_chenkai",
    }
    resp = client.post("/api/riskctrl/dsl/deploy", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ruleset_id"] == "rs_endpoint_001"
    assert data["dsl_version"] == "v1.2.0"
    assert "decision_id" in data
    assert data["decision_id"]
    # 默认 trigger_alert_rebuild + trigger_credit_rubric_sync = True
    assert "§6.5" in " ".join(data["handoff_triggers"])
    assert "§6.6" in " ".join(data["handoff_triggers"])
    assert "deployed_at" in data
    # ledger_persisted (default ledger 真写) · 在 test env 应该 True
    assert "ledger_persisted" in data


def test_dsl_deploy_without_approver_works(client):
    body = {
        "ruleset_id": "rs_endpoint_002",
        "dsl_version": "v1.0.0",
        "rule_count": 1,
        "affected_segments": [],
        "backtest_summary": {},
    }
    resp = client.post("/api/riskctrl/dsl/deploy", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision_id"]


def test_dsl_deploy_can_disable_handoff_triggers(client):
    body = {
        "ruleset_id": "rs_endpoint_003",
        "dsl_version": "v1.0.0",
        "rule_count": 1,
        "affected_segments": [],
        "backtest_summary": {},
        "trigger_alert_rebuild": False,
        "trigger_credit_rubric_sync": False,
    }
    resp = client.post("/api/riskctrl/dsl/deploy", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["handoff_triggers"] == []


def test_dsl_deploy_invalid_body_returns_422(client):
    # 缺 required fields
    resp = client.post("/api/riskctrl/dsl/deploy", json={"ruleset_id": "x"})
    assert resp.status_code == 422
