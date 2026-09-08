# -*- coding: utf-8 -*-
"""B7 · 形态模式下会话过期后导出仍可用（访客搁置页面 >30 分钟再点导出）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api_server
from agent_report import api as report_api
from agent_report.session_store import store


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.delenv("ALLOW_LEGACY_DEMO_TOKEN", raising=False)
    return TestClient(api_server.app)


def _login(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={"user_id": "u_liuye", "password": "LIUYE"})
    assert response.status_code == 200, response.text


def _seed(path: Path) -> None:
    path.write_text(json.dumps({
        "event": "done",
        "profile": {"company_name": "形态模式测试企业"},
        "sections": [{"id": "chapter_1_background", "title": "一、企业背景", "content": "只读会话正文", "status": "done"}],
        "qc": {"passed": True, "fatal_fail": False},
        "stats": {},
        "pending_questions": [],
    }, ensure_ascii=False), encoding="utf-8")


def test_export_after_session_expiry_rehydrates_in_form_mode(monkeypatch, tmp_path, client):
    monkeypatch.setenv("DEMO_FORM_MODE", "1")
    _login(client)
    seed_file = tmp_path / "report-default-session.json"
    _seed(seed_file)
    monkeypatch.setattr(report_api, "DEMO_FORM_SESSION_FILE", seed_file)

    hydrated = client.get("/api/report/demo/default")
    assert hydrated.status_code == 200, hydrated.text
    session_id = hydrated.json()["session_id"]

    # 模拟 30 分钟 GC：会话从内存消失
    store.delete(session_id)
    assert store.get(session_id) is None

    exported = client.post("/api/report/export_docx", json={"session_id": session_id})
    assert exported.status_code == 200, exported.text
    assert "wordprocessingml.document" in exported.headers["content-type"]


def test_export_after_expiry_still_fails_when_form_mode_off(monkeypatch, tmp_path, client):
    monkeypatch.delenv("DEMO_FORM_MODE", raising=False)
    _login(client)
    exported = client.post("/api/report/export_docx", json={"session_id": "gone-session"})
    assert exported.status_code == 400, exported.text
