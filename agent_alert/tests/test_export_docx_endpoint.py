# -*- coding: utf-8 -*-
"""POST /api/alert/export_docx · TestClient smoke (W-FIX2 修 bug #6).

锁定:
  - happy path · 返 200 + Content-Type docx + Content-Disposition attachment
  - filename* RFC 6266 编码 (中文文件名兼容)
  - 空 cases · 仍返 docx (不是 400/500)
  - body 是真 docx (zip 头 PK\x03\x04)
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from agent_alert.api import app  # noqa: E402
from auth_service.dependencies import COOKIE_NAME  # noqa: E402
from auth_service.jwt_util import issue  # noqa: E402

client = TestClient(app)
# admin cookie · pass require_action gate (Phase B Sprint 3 V3-FIX 2026-05-05)
# alert.export action gated · 旧 test 没 cookie 返 401 · 加 admin (全 action 全 agent OK)
client.cookies.set(COOKIE_NAME, issue("u_test", "admin"))


def test_export_docx_happy_path():
    """正常请求 · 返 200 + docx body."""
    res = client.post("/api/alert/export_docx", json={
        "session_id": "test-001",
        "summary": "测试扫描总览",
        "cases": [
            {
                "customer": "测试客户A",
                "risk_level": "red",
                "triggers": ["征信 M3+"],
                "amount": "1.2 亿",
                "advice": "建议立即处置",
            },
        ],
        "scan_range": "在贷 · 全量",
        "stage": "已完成",
        "totals": {"red": 1, "yellow": 0, "green": 0},
    })
    assert res.status_code == 200
    assert "wordprocessingml" in res.headers["content-type"]
    cd = res.headers.get("content-disposition", "")
    assert cd.startswith("attachment")
    assert "filename*=UTF-8''" in cd
    # 真 docx (zip 头)
    assert res.content[:4] == b"PK\x03\x04"


def test_export_docx_empty_cases_still_succeeds():
    """空 cases · 不报 400 · 仍返 docx (报告示空清单)."""
    res = client.post("/api/alert/export_docx", json={
        "session_id": "empty-1",
        "cases": [],
    })
    assert res.status_code == 200
    assert res.content[:4] == b"PK\x03\x04"


def test_export_docx_minimal_payload():
    """全 default · 不抛 · 200."""
    res = client.post("/api/alert/export_docx", json={})
    assert res.status_code == 200
    assert res.content[:4] == b"PK\x03\x04"


def test_export_docx_chinese_session_id_encoded():
    """中文 session_id · Content-Disposition filename* 应正确 url-encoded."""
    res = client.post("/api/alert/export_docx", json={
        "session_id": "中文会话",
        "cases": [],
    })
    assert res.status_code == 200
    cd = res.headers.get("content-disposition", "")
    # url-encoded 中文不会出现裸字符 (应是 %E4%B8%AD 等)
    assert "filename*=UTF-8''" in cd
