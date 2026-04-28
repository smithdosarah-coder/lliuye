# -*- coding: utf-8 -*-
"""Tests for POST /api/credit/export_docx (Stage C v4.0).

Coverage:
  - {advice} passthrough body · 真生成 docx bytes · header Content-Disposition 正确
  - {decision_id} 路径 · cache hit (mock cache 直插 advice) → docx
  - 404 · decision_id 不存在
  - 400 · 既无 decision_id 也无 advice
  - 400 · advice 缺 subject_name/decision
"""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from agent_credit.api import app
    return TestClient(app)


_DEMO_ADVICE: dict = {
    "advice_id": "test_advice_001",
    "segment": "corporate",
    "subject_name": "鼎盛商贸有限公司",
    "decision_time": "2026-04-28 14:00:00",
    "decision": "有条件批准",
    "approved_amount": 300,
    "approved_term_months": 36,
    "interest_rate": 0.065,
    "rate_benchmark": "LPR+85BP",
    "composite_score": 72,
    "risk_grade": "B",
    "conditions": ["关联交易审计说明", "季度应收账款账龄表"],
    "red_line_hits": [],
    "red_line_explanations": [],
    "decision_reason": "综合评分 72/100 · 四维分布均衡 · 建议有条件批准",
    "similar_cases_summary": "近期 5 例同类企业平均批 280 万 · 利率 LPR+78BP",
    "top_reason_codes": [],
}


def _is_docx_bytes(content: bytes) -> bool:
    """docx = zip 容器 · 含 [Content_Types].xml."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            return "[Content_Types].xml" in names and "word/document.xml" in names
    except zipfile.BadZipFile:
        return False


def test_export_docx_passthrough_advice(client):
    """body {advice} 直传 · 真生成 docx bytes."""
    resp = client.post("/api/credit/export_docx", json={"advice": _DEMO_ADVICE})
    assert resp.status_code == 200
    assert "officedocument" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    assert _is_docx_bytes(resp.content)
    assert resp.headers.get("X-Credit-Decision-Source") == "passthrough"


def test_export_docx_decision_id_cache_hit(client):
    """直接插 cache 走 decision_id 路径."""
    from agent_credit.api import _cache_advice
    decision_id = _cache_advice(_DEMO_ADVICE)
    resp = client.post("/api/credit/export_docx", json={"decision_id": decision_id})
    assert resp.status_code == 200
    assert _is_docx_bytes(resp.content)
    assert resp.headers.get("X-Credit-Decision-Source") == "cached"


def test_export_docx_decision_id_not_found(client):
    """不存在 decision_id → 404."""
    resp = client.post("/api/credit/export_docx", json={"decision_id": "dec_not_exist_xxx"})
    assert resp.status_code == 404
    assert "ttl_sec" in resp.json()["detail"]["error"]


def test_export_docx_missing_both_returns_400(client):
    """既无 decision_id 也无 advice → 400."""
    resp = client.post("/api/credit/export_docx", json={})
    assert resp.status_code == 400
    assert "decision_id" in resp.json()["detail"]["error"]["message"]


def test_export_docx_advice_missing_subject_returns_400(client):
    """advice 缺 subject_name 和 decision → 400."""
    bad_advice = {"interest_rate": 0.05}
    resp = client.post("/api/credit/export_docx", json={"advice": bad_advice})
    assert resp.status_code == 400


def test_export_docx_filename_chinese_encoded(client):
    """RFC 5987 中文文件名编码 (filename*=UTF-8''...)."""
    resp = client.post("/api/credit/export_docx", json={"advice": _DEMO_ADVICE})
    cd = resp.headers["content-disposition"]
    assert "filename*=UTF-8''" in cd
