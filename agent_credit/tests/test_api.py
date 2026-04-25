"""agent_credit.api FastAPI 端点冒烟测试。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from agent_credit.api import app

client = TestClient(app)


def test_handoff_demo_corporate_returns_profile():
    r = client.get("/api/credit/handoff/demo/corporate")
    assert r.status_code == 200
    body = r.json()
    assert body["segment"] == "corporate"
    assert "profile" in body and body["profile"]
    assert body["profile"].get("business_line") == "corporate"


def test_handoff_demo_retail_returns_profile():
    r = client.get("/api/credit/handoff/demo/retail")
    assert r.status_code == 200
    body = r.json()
    assert body["segment"] == "retail"
    assert body["profile"].get("business_line") == "retail"


def test_handoff_demo_rejects_bad_segment():
    r = client.get("/api/credit/handoff/demo/sme")
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["error"]["code"] == "VALIDATION_FAILED"


def test_export_docx_rejects_empty():
    r = client.post("/api/credit/export_docx", json={"advice": {}})
    assert r.status_code == 400


def test_export_docx_produces_wordml_bytes():
    advice = {
        "advice_id": "t1",
        "segment": "corporate",
        "subject_name": "SmokeCo",
        "decision": "批准",
        "approved_amount": 300,
        "approved_term_months": 12,
        "interest_rate": 0.045,
        "rate_benchmark": "LPR+50BP",
        "composite_score": 80,
        "risk_grade": "A",
        "top_reason_codes": [
            {"code": "R_CORP_FINANCIAL_STRONG", "title": "财务健康",
             "severity": "green", "description": "ok"}
        ],
    }
    r = client.post("/api/credit/export_docx", json={"advice": advice})
    assert r.status_code == 200
    assert "wordprocessingml" in r.headers.get("content-type", "")
    assert len(r.content) > 3000
    cd = r.headers.get("content-disposition", "")
    assert "filename*=UTF-8''" in cd
