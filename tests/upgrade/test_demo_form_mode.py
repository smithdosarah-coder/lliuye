# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader

from agent_report import api as report_api
from agent_report.api import app
from agent_report.session_store import store
from agent_report.v16_runner import _material_manifest, _profile_from_client_metadata
from agent_report.word_export import export
from auth_service.dependencies import COOKIE_NAME
from auth_service.jwt_util import issue
from scripts.seed_demo_form_session import DEMO_MATERIALS


@pytest.fixture
def client():
    test_client = TestClient(app)
    test_client.cookies.set(COOKIE_NAME, issue("u_test", "admin"))
    return test_client


def _seed_payload() -> dict:
    return {
        "event": "done",
        "pipeline": "v16",
        "profile": {
            "company_name": "蓝汀家电连锁（浙江）有限公司",
            "unified_credit_code": "91330782MA2XXXX022",
        },
        "sections": [{
            "id": "chapter_1_background",
            "title": "一、企业背景",
            "content": "蓝汀家电正文",
            "status": "done",
        }],
        "materials": [{"id": f"m-{index}", "name": name} for index, name in enumerate(DEMO_MATERIALS)],
        "timeline": [],
        "conversation": [{
            "id": "seed-template-message",
            "at": "2026-09-07T18:00:00+08:00",
            "kind": "system-event",
            "content": "已选用模板 · 对公成稿 A",
        }],
        "template": {"id": "tpl-corporate-a", "name": "对公成稿 A"},
        "qc": {
            "passed": False,
            "fatal_fail": True,
            "dimensions": [{"name": "申报方案硬字段", "raw_score": 3.08, "pass_threshold": 5.0}],
        },
        "stats": {},
        "pending_questions": [],
        "source_docx": "samples/经纬测绘_对公成稿A.docx",
    }


def test_demo_run_is_blocked_only_when_demo_form_mode_enabled(monkeypatch, client):
    monkeypatch.setenv("DEMO_FORM_MODE", "1")
    blocked = client.post("/api/report/demo/run", json={"sample_id": "DP002_蓝汀家电"})
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["error"] == {
        "code": "DEMO_FORM_GENERATION_DISABLED",
        "message": "演示环境已停用生成接口 · 下方为已完成的示例会话",
    }

    monkeypatch.setenv("DEMO_FORM_MODE", "0")
    regression = client.post("/api/report/demo/run", json={"sample_id": "bad"})
    assert regression.status_code == 400
    assert regression.json()["detail"]["error"]["code"] == "SAMPLE_ID_INVALID"


def test_default_session_hydrates_cold_start_and_exports_current_profile(monkeypatch, tmp_path, client):
    seed_file = tmp_path / "report-default-session.json"
    seed_file.write_text(json.dumps(_seed_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(report_api, "DEMO_FORM_SESSION_FILE", seed_file)
    monkeypatch.setenv("DEMO_FORM_MODE", "1")

    response = client.get("/api/report/demo/default")
    assert response.status_code == 200, response.text
    done = response.json()
    sid = done["session_id"]
    assert done["report_id"] == sid
    assert done["profile"]["company_name"].startswith("蓝汀家电")
    assert len(done["materials"]) == 7
    assert done["template"]["name"] == "对公成稿 A"
    assert store.get(sid)["done_payload"]["sections"][0]["content"] == "蓝汀家电正文"

    try:
        exported = client.post("/api/report/export_docx", json={
            "session_id": sid,
            "profile": {"company_name": "鼎盛商贸有限公司"},
            "sections": [{"id": "bad", "title": "坏数据", "content": "鼎盛正文"}],
        })
        assert exported.status_code == 200, exported.text
        with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
            headers = "".join(
                archive.read(name).decode("utf-8")
                for name in archive.namelist()
                if name.startswith("word/header")
            )
        assert xml.count("鼎盛") == 0
        assert xml.count("蓝汀") >= 1
        assert "91330782MA2XXXX022" in xml
        assert "蓝汀家电连锁（浙江）有限公司" in headers
        assert "鼎盛" not in headers

        exported_pdf = client.post("/api/report/export_pdf", json={
            "session_id": sid,
            "profile": {"company_name": "鼎盛商贸有限公司"},
            "sections": [{"id": "bad", "title": "坏数据", "content": "鼎盛正文"}],
        })
        assert exported_pdf.status_code == 200, exported_pdf.text
        pdf_text = "".join(
            page.extract_text() or ""
            for page in PdfReader(io.BytesIO(exported_pdf.content)).pages
        )
        assert "蓝汀家电连锁（浙江）有限公司" in pdf_text
        assert "鼎盛" not in pdf_text
        assert datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d") in pdf_text
    finally:
        store.delete(sid)


def test_run_scoped_client_metadata_owns_profile_identity():
    profile = _profile_from_client_metadata(
        {
            "CLIENT_FULL_NAME": "蓝汀家电连锁（浙江）有限公司",
            "CLIENT_USCC": "91330782MA2XXXX022",
            "CLIENT_LEGAL_REP": "陈立嘉",
        },
        fallback_report_id="经纬测绘_对公成稿A",
    )
    assert profile["company_name"] == "蓝汀家电连锁（浙江）有限公司"
    assert profile["unified_credit_code"] == "91330782MA2XXXX022"
    assert "鼎盛" not in json.dumps(profile, ensure_ascii=False)


def test_material_manifest_reports_only_files_used_by_session(tmp_path):
    for index, name in enumerate(DEMO_MATERIALS):
        (tmp_path / name).write_bytes(f"material-{index}".encode())
    (tmp_path / "client_metadata.json").write_text("{}", encoding="utf-8")
    manifest = _material_manifest(tmp_path)
    assert len(manifest) == 7
    assert {row["name"] for row in manifest} == set(DEMO_MATERIALS)
    assert all(row["parsed"] is True for row in manifest)


def test_docx_export_uses_explicit_asia_shanghai_date():
    payload = {
        "profile": {"company_name": "蓝汀家电"},
        "sections": [{"id": "s1", "title": "正文", "content": "内容"}],
        "qc": {"passed": True},
    }
    document = Document(io.BytesIO(export(payload)))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    shanghai_date = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    assert f"日期：{shanghai_date}" in text
