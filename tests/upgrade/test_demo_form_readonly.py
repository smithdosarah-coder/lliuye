# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api_server
from agent_report import api as report_api
from agent_report.session_store import store
from auth_service.dependencies import COOKIE_NAME
from auth_service.jwt_util import issue


READONLY_ERROR = {
    "detail": {
        "error": {
            "code": "DEMO_FORM_READONLY",
            "message": "演示环境为只读形态 · 已停用生成、上传与写入",
        },
    },
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.delenv("ALLOW_LEGACY_DEMO_TOKEN", raising=False)
    return TestClient(api_server.app)


def _login(client: TestClient, user_id: str = "u_liuye", password: str = "LIUYE"):
    response = client.post(
        "/api/auth/login",
        json={"user_id": user_id, "password": password},
    )
    assert response.status_code == 200, response.text
    return response


def _seed_payload(path: Path) -> None:
    path.write_text(
        json.dumps({
            "event": "done",
            "profile": {"company_name": "形态模式测试企业"},
            "sections": [{
                "id": "chapter_1_background",
                "title": "一、企业背景",
                "content": "只读会话正文",
                "status": "done",
            }],
            "qc": {"passed": True, "fatal_fail": False},
            "stats": {},
            "pending_questions": [],
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def test_demo_form_mode_blocks_mutations_but_allows_auth_and_exports(
    monkeypatch,
    tmp_path,
    client,
):
    monkeypatch.setenv("DEMO_FORM_MODE", "1")
    _login(client)

    blocked_requests = [
        client.post("/api/report/demo/run", json={"sample_id": "DP002_蓝汀家电"}),
        client.post("/api/report/refine_section", json={}),
        client.post("/api/report/upload"),
        client.post("/api/im/send", json={"message": "hello"}),
    ]
    for response in blocked_requests:
        assert response.status_code == 403, response.text
        assert response.json() == READONLY_ERROR

    seed_file = tmp_path / "report-default-session.json"
    _seed_payload(seed_file)
    monkeypatch.setattr(report_api, "DEMO_FORM_SESSION_FILE", seed_file)
    hydrated = client.get("/api/report/demo/default")
    assert hydrated.status_code == 200, hydrated.text

    session_id = hydrated.json()["session_id"]
    try:
        exported_docx = client.post(
            "/api/report/export_docx",
            json={"session_id": session_id},
        )
        assert exported_docx.status_code == 200, exported_docx.text
        assert "wordprocessingml.document" in exported_docx.headers["content-type"]

        exported_pdf = client.post(
            "/api/report/export_pdf",
            json={"session_id": session_id},
        )
        assert exported_pdf.status_code == 200, exported_pdf.text
        assert exported_pdf.headers["content-type"].startswith("application/pdf")
    finally:
        store.delete(session_id)


def test_demo_form_mode_off_preserves_existing_route_behavior(monkeypatch, client):
    monkeypatch.setenv("DEMO_FORM_MODE", "0")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    _login(client)

    cases = [
        client.post("/api/report/demo/run", json={"sample_id": "bad"}),
        client.post("/api/report/refine_section", json={}),
        client.post("/api/report/upload"),
        client.post("/api/im/send", json={"message": "hello"}),
    ]
    assert [response.status_code for response in cases] == [400, 422, 400, 503]
    assert all(response.status_code != 403 for response in cases)


def test_legacy_demo_token_is_opt_in_and_forced_off_in_form_mode(monkeypatch, client):
    client.cookies.clear()
    headers = {"Authorization": "Bearer demo-u_wangzhe"}

    monkeypatch.setenv("DEMO_FORM_MODE", "0")
    monkeypatch.delenv("ALLOW_LEGACY_DEMO_TOKEN", raising=False)
    default_denied = client.get("/api/im/threads", headers=headers)
    assert default_denied.status_code == 401

    monkeypatch.setenv("ALLOW_LEGACY_DEMO_TOKEN", "1")
    explicitly_enabled = client.get("/api/im/threads", headers=headers)
    assert explicitly_enabled.status_code == 200, explicitly_enabled.text

    monkeypatch.setenv("DEMO_FORM_MODE", "1")
    form_mode_denied = client.get("/api/im/threads", headers=headers)
    assert form_mode_denied.status_code == 401


def test_downloads_require_login_and_owner_session(monkeypatch, tmp_path, client):
    monkeypatch.setenv("DEMO_FORM_MODE", "0")
    docx_bytes = b"owned-docx"
    alias_file = tmp_path / "owned.docx"
    alias_file.write_bytes(docx_bytes)
    session_id = store.create({
        "owner_user_id": "u_liuye",
        "report_docx_path": str(alias_file),
    })

    sessions_dir = tmp_path / "sessions"
    session_dir = sessions_dir / session_id
    session_dir.mkdir(parents=True)
    named_file = session_dir / "named.docx"
    named_file.write_bytes(docx_bytes)
    monkeypatch.setattr(report_api, "SESSIONS_DIR", sessions_dir)

    alias_url = f"/api/report/downloads/{session_id}"
    named_url = f"/api/report/downloads/{session_id}/named.docx"
    try:
        client.cookies.clear()
        assert client.get(alias_url).status_code == 401
        assert client.get(named_url).status_code == 401

        client.cookies.set(COOKIE_NAME, issue("u_wangzhe", "rm"))
        assert client.get(alias_url).status_code == 404
        assert client.get(named_url).status_code == 404

        client.cookies.set(COOKIE_NAME, issue("u_liuye", "admin"))
        alias_response = client.get(alias_url)
        named_response = client.get(named_url)
        assert alias_response.status_code == 200, alias_response.text
        assert named_response.status_code == 200, named_response.text
        assert alias_response.content == docx_bytes
        assert named_response.content == docx_bytes

        missing = client.get(
            "/api/report/downloads/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/missing.docx"
        )
        assert missing.status_code == 404
    finally:
        store.delete(session_id)


def test_export_allowlist_still_enforces_session_owner(monkeypatch, client):
    monkeypatch.setenv("DEMO_FORM_MODE", "1")
    session_id = store.create({
        "owner_user_id": "u_liuye",
        "enterprise_profile": {"company_name": "属主隔离测试企业"},
        "done_payload": {
            "sections": [{
                "id": "chapter_1_background",
                "title": "一、企业背景",
                "content": "仅属主可导出的正文",
                "status": "done",
            }],
            "qc": {"passed": True, "fatal_fail": False},
            "stats": {},
            "pending_questions": [],
        },
        "qc_payload": {"passed": True, "fatal_fail": False},
    })

    try:
        client.cookies.set(COOKIE_NAME, issue("u_wangzhe", "rm"))
        for endpoint in ("/api/report/export_docx", "/api/report/export_pdf"):
            denied = client.post(endpoint, json={"session_id": session_id})
            assert denied.status_code == 404, denied.text

        client.cookies.set(COOKIE_NAME, issue("u_liuye", "admin"))
        docx = client.post("/api/report/export_docx", json={"session_id": session_id})
        pdf = client.post("/api/report/export_pdf", json={"session_id": session_id})
        assert docx.status_code == 200, docx.text
        assert pdf.status_code == 200, pdf.text
    finally:
        store.delete(session_id)
