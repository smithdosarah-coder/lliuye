# -*- coding: utf-8 -*-
"""Stage C.1 · POST /api/report/export_docx + GET /api/report/downloads/{report_id} 单测.

锁定:
  - export_docx 直接 payload 路径(profile + sections) → valid docx
  - export_docx 从 session 取数据(session_id) → valid docx · 含 sections 内容
  - 空 sections + 空 profile → 400 VALIDATION_FAILED
  - filename build 含 company name
  - 含 RFC 6266 中文文件名编码段
  - downloads/{report_id} alias · session 无 docx 路径返 404
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.api import app  # noqa: E402
from agent_report.session_store import store  # noqa: E402
from agent_report.word_export import build_filename, export  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read("word/document.xml").decode("utf-8")


def _full_payload() -> dict:
    return {
        "report_id": "test-export-001",
        "profile": {
            "company_name": "测试样本有限公司",
            "unified_credit_code": "913301020000000011",
            "industry": "精密零部件",
            "establishment_date": "2015-06-10",
            "registered_capital": "5000 万",
            "region": "浙江省杭州市",
            "main_business": "精密齿轮 / 轴承",
            "controller_name": "张三",
            "financial_anchors": {
                "revenue_latest": 280000000,
                "net_profit_latest": 15600000,
                "total_assets": 320000000,
                "period": "2024年度",
            },
        },
        "sections": [
            {
                "id": "chapter_1_background",
                "title": "一、企业背景",
                "content": "公司成立于 2015 年 · 注册资本 5000 万元 · 实控人张三持股 65%。",
                "status": "done",
                "word_count": 1200,
            },
            {
                "id": "chapter_2_operation",
                "title": "二、经营情况",
                "content": "主营精密零部件加工 · 近 3 年营收稳定增长。",
                "status": "done",
                "word_count": 1500,
            },
            {
                "id": "chapter_3_finance",
                "title": "三、财务分析",
                "content": "资产负债率 45% · 流动比率 1.6 · 经营现金流为正。",
                "status": "done",
                "word_count": 2200,
            },
        ],
        "stats": {"total_fields": 492, "auto_filled": 460, "unfilled": 32},
        "pending_questions": [
            {"id": "ext_1", "label": "外因 · 行业景气度",
             "recommended": "请补充近 6 个月行业关键变化"},
        ],
        "qc": {"passed": True, "score": 86.5, "fatal_fail": False, "halluc_count": 0},
        "business_line": "corporate",
        "client_manager": "王哲",
    }


# ============================================================================
# Direct export() lib calls
# ============================================================================

def test_export_full_payload_is_valid_docx_zip():
    data = export(_full_payload())
    assert len(data) > 4000
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
    assert "word/document.xml" in names
    assert "[Content_Types].xml" in names


def test_export_full_payload_contains_company_and_chapters():
    data = export(_full_payload())
    text = _docx_text(data)
    assert "测试样本有限公司" in text
    assert "授信调查报告" in text
    assert "企业背景" in text
    assert "经营情况" in text
    assert "财务分析" in text
    # QC 概览 · client_manager
    assert "王哲" in text
    # disclaimer
    assert "本地渲染" in text
    assert "无数据出境" in text


def test_export_minimal_profile_only():
    payload = {
        "report_id": "min-001",
        "profile": {"company_name": "极简公司"},
        "sections": [],
    }
    data = export(payload)
    assert len(data) > 1500
    text = _docx_text(data)
    assert "极简公司" in text


def test_build_filename_uses_company_and_id():
    fn = build_filename(_full_payload())
    assert fn.endswith(".docx")
    assert "agent6_报告" in fn
    assert "测试样本有限公司" in fn
    assert "test-export-001" in fn


def test_build_filename_strips_illegal_chars():
    payload = {"profile": {"company_name": '客户/有\\限?公司"with"|illegal'},
               "report_id": "x*y:z"}
    fn = build_filename(payload)
    for bad in r'\/:*?"<>|':
        assert bad not in fn


# ============================================================================
# POST /api/report/export_docx · 端点
# ============================================================================

def test_endpoint_with_direct_payload(client):
    resp = client.post("/api/report/export_docx", json=_full_payload())
    assert resp.status_code == 200, resp.text
    ct = resp.headers["content-type"]
    assert "wordprocessingml.document" in ct
    cd = resp.headers["content-disposition"]
    assert "attachment" in cd
    assert "filename*=UTF-8''" in cd
    body = resp.content
    assert len(body) > 4000
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        assert "word/document.xml" in z.namelist()
    assert resp.headers["X-Agent6-Export-Type"] == "docx"
    assert int(resp.headers["X-Agent6-Export-Sections"]) == 3


def test_endpoint_with_session_id(client):
    """session 中预存数据 · endpoint 用 session_id 取."""
    sid = store.create({
        "enterprise_profile": _full_payload()["profile"],
        "done_payload": {
            "profile": _full_payload()["profile"],
            "sections": _full_payload()["sections"],
            "stats": _full_payload()["stats"],
        },
        "pending_questions": [],
    })
    try:
        resp = client.post("/api/report/export_docx",
                           json={"session_id": sid})
        assert resp.status_code == 200, resp.text
        body = resp.content
        assert len(body) > 4000
        # 内容包含 seeded session 的公司名
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        assert "测试样本有限公司" in xml
        assert "企业背景" in xml
    finally:
        store.delete(sid)


def test_endpoint_rejects_empty_payload(client):
    resp = client.post("/api/report/export_docx",
                       json={"session_id": "", "report_id": ""})
    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("error", {}).get("code") == "VALIDATION_FAILED"


# ============================================================================
# GET /api/report/downloads/{report_id} alias
# ============================================================================

def test_downloads_alias_404_when_session_missing(client):
    resp = client.get("/api/report/downloads/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert resp.status_code == 404


def test_downloads_alias_400_for_bad_id(client):
    resp = client.get("/api/report/downloads/not-a-uuid")
    # 400 (path 不匹配 UUID 格式) 或 404 都接受 · 这里用 400
    assert resp.status_code in (400, 404)


def test_downloads_alias_404_when_session_has_no_docx(client):
    """session 存在但 report_docx_path 不存在 → 404."""
    sid = store.create({"enterprise_profile": {}, "report_docx_path": None})
    try:
        resp = client.get(f"/api/report/downloads/{sid}")
        assert resp.status_code == 404
    finally:
        store.delete(sid)


def test_downloads_alias_returns_file_when_session_has_docx(client, tmp_path):
    """session 含 report_docx_path → 返实际文件."""
    # 渲一份真 docx 落 tmp
    docx_bytes = export(_full_payload())
    tmp_docx = tmp_path / "report_v16.docx"
    tmp_docx.write_bytes(docx_bytes)

    sid = store.create({"enterprise_profile": {}, "report_docx_path": str(tmp_docx)})
    try:
        resp = client.get(f"/api/report/downloads/{sid}")
        assert resp.status_code == 200
        assert "wordprocessingml.document" in resp.headers["content-type"]
        assert resp.content == docx_bytes
    finally:
        store.delete(sid)
