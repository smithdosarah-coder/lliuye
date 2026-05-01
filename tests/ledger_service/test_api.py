# -*- coding: utf-8 -*-
"""ledger_service.api endpoint tests · BE7 (Phase B-3 · 2026-05-01).

Auth: bypass via FastAPI dependency_overrides on auth_service.require_user
(same trick the audit_service tests use). Tests run with admin role
unless explicitly overridden.

Hard guarantees per spec §3:
- 5 endpoints respond at the documented paths and shapes
- Admin-only access enforced (403 for non-admin)
- Path/query validation (400 on bad jurisdiction / action)
- 404 on missing decision_id
- Zip export carries manifest + per-decision JSON
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_service.dependencies import require_user  # noqa: E402
from ledger_service.api import register_ledger_routes  # noqa: E402
from shared.decision_ledger import (  # noqa: E402
    DecisionLedger,
    LEDGER_SCHEMA_VERSION,
    record_decision,
    set_default_ledger,
)


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    """Mounts the ledger router with require_user overridden to admin."""
    db_path = tmp_path / "ledger_api.sqlite"
    monkeypatch.setenv("LIUYE_LEDGER_DB_PATH", str(db_path))
    set_default_ledger(DecisionLedger(db_path))

    app = FastAPI()
    register_ledger_routes(app)

    async def _admin():
        return {"sub": "tester", "role": "admin"}

    app.dependency_overrides[require_user] = _admin
    yield TestClient(app), app
    set_default_ledger(None)


@pytest.fixture
def seeded_ids(admin_client):
    client, _ = admin_client
    ids: dict[str, str] = {}
    ids["credit_hq"] = record_decision(
        agent_id="credit", endpoint="/api/credit/decision",
        input_payload={"company": "测试", "amount": 800},
        output_payload={"decision": "批准", "approved": 600},
        evidence_chain={"schema_version": "1.0.0", "nodes": []},
        subject_name="测试公司",
    )
    ids["report_hq"] = record_decision(
        agent_id="report", endpoint="/api/report/v16/fill",
        input_payload={"r": 1}, output_payload={"r": "ok"},
        evidence_chain={},
    )
    ids["credit_yin"] = record_decision(
        agent_id="credit", endpoint="/api/credit/decision",
        input_payload={"v": 2}, output_payload={"d": "拒绝"},
        evidence_chain={}, jurisdiction="银",
    )
    return ids


# ---------------------------------------------------------------------------
# 1. GET /api/ledger/decision/{id}
# ---------------------------------------------------------------------------


def test_get_decision_ok(admin_client, seeded_ids):
    client, _ = admin_client
    r = client.get(f"/api/ledger/decision/{seeded_ids['credit_hq']}")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == LEDGER_SCHEMA_VERSION
    assert body["decision"]["agent_id"] == "credit"
    assert body["decision"]["jurisdiction"] == "HQ"


def test_get_decision_404(admin_client):
    client, _ = admin_client
    r = client.get("/api/ledger/decision/no-such-id")
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "NOT_FOUND"


def test_get_decision_admin_only(admin_client, seeded_ids):
    client, app = admin_client

    async def _user():
        return {"sub": "tester", "role": "user"}

    app.dependency_overrides[require_user] = _user
    r = client.get(f"/api/ledger/decision/{seeded_ids['credit_hq']}")
    assert r.status_code == 403
    assert r.json()["detail"]["error"]["code"] == "ACCESS_DENIED"


# ---------------------------------------------------------------------------
# 2. GET /api/ledger/agent/{agent_id}
# ---------------------------------------------------------------------------


def test_list_by_agent_returns_paginated(admin_client, seeded_ids):
    client, _ = admin_client
    r = client.get("/api/ledger/agent/credit")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2  # credit_hq + credit_yin
    assert len(body["items"]) == 2
    assert body["limit"] == 100
    assert body["offset"] == 0


def test_list_by_agent_unknown_returns_empty(admin_client, seeded_ids):
    client, _ = admin_client
    r = client.get("/api/ledger/agent/nonexistent")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_list_by_agent_limit_clamps(admin_client):
    client, _ = admin_client
    # limit > 500 rejected by Query(le=500)
    r = client.get("/api/ledger/agent/credit?limit=10000")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 3. GET /api/ledger/jurisdiction/{jurisdiction}
# ---------------------------------------------------------------------------


def test_list_by_jurisdiction_filters(admin_client, seeded_ids):
    client, _ = admin_client
    r = client.get("/api/ledger/jurisdiction/HQ")
    assert r.json()["total"] == 2  # credit_hq + report_hq
    r2 = client.get("/api/ledger/jurisdiction/银")
    assert r2.json()["total"] == 1  # credit_yin


def test_list_by_jurisdiction_invalid_400(admin_client):
    client, _ = admin_client
    r = client.get("/api/ledger/jurisdiction/USA")
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "VALIDATION_FAILED"


# ---------------------------------------------------------------------------
# 4. GET /api/ledger/audit_export
# ---------------------------------------------------------------------------


def test_audit_export_returns_zip(admin_client, seeded_ids):
    client, _ = admin_client
    r = client.get("/api/ledger/audit_export?jurisdiction=HQ")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert r.headers["x-ledger-schema-version"] == LEDGER_SCHEMA_VERSION
    assert "attachment" in r.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(r.content), mode="r") as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["count"] == 2  # 2 HQ rows
        assert manifest["filter"]["jurisdiction"] == "HQ"


def test_audit_export_requires_jurisdiction(admin_client):
    client, _ = admin_client
    r = client.get("/api/ledger/audit_export")
    assert r.status_code == 422  # missing required query param


def test_audit_export_invalid_jurisdiction_400(admin_client):
    client, _ = admin_client
    r = client.get("/api/ledger/audit_export?jurisdiction=USA")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 5. POST /api/ledger/{decision_id}/review
# ---------------------------------------------------------------------------


def test_submit_review_ok(admin_client, seeded_ids):
    client, _ = admin_client
    did = seeded_ids["credit_hq"]
    r = client.post(
        f"/api/ledger/{did}/review",
        json={"reviewer_id": "reviewer42", "action": "approve"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision_id"] == did
    assert body["reviewer_id"] == "reviewer42"
    assert body["action"] == "approve"
    # Re-fetch and confirm persisted
    follow_up = client.get(f"/api/ledger/decision/{did}").json()
    assert follow_up["decision"]["reviewer_id"] == "reviewer42"
    assert follow_up["decision"]["reviewer_action"] == "approve"


def test_submit_review_404_for_missing_id(admin_client):
    client, _ = admin_client
    r = client.post(
        "/api/ledger/nope/review",
        json={"reviewer_id": "r1", "action": "approve"},
    )
    assert r.status_code == 404


def test_submit_review_invalid_action_400(admin_client, seeded_ids):
    client, _ = admin_client
    did = seeded_ids["credit_hq"]
    r = client.post(
        f"/api/ledger/{did}/review",
        json={"reviewer_id": "r1", "action": "suplex"},
    )
    assert r.status_code == 400


def test_submit_review_admin_only(admin_client, seeded_ids):
    client, app = admin_client

    async def _user():
        return {"sub": "tester", "role": "user"}

    app.dependency_overrides[require_user] = _user
    did = seeded_ids["credit_hq"]
    r = client.post(
        f"/api/ledger/{did}/review",
        json={"reviewer_id": "r1", "action": "approve"},
    )
    assert r.status_code == 403
