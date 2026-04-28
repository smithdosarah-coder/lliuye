# -*- coding: utf-8 -*-
"""Stage C.1 · POST /api/report/upload 单测.

锁定:
  - multipart 多 file 上传 · 落盘 ``data/kb/report/{report_id}/``
  - 返 ``{report_id, file_summary[], total_files, total_parsed_chars}``
  - 空 files → 400 VALIDATION_FAILED
  - report_id 是 UUID4 格式
  - file_summary 含 name / type / size_bytes / parsed_chars / parse_status
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.api import app  # noqa: E402
from agent_report.upload import cleanup_report_dir, upload_dir  # noqa: E402

UUID_V4_RE = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$"
)


@pytest.fixture
def client():
    return TestClient(app)


def test_upload_persists_files_and_returns_report_id(client):
    files = [
        ("files", ("test_material_1.txt", b"hello world test material",
                   "text/plain")),
        ("files", ("test_material_2.txt", b"second file content",
                   "text/plain")),
    ]
    resp = client.post("/api/report/upload", files=files,
                       params={"business_line": "corporate"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    rid = data["report_id"]
    try:
        assert UUID_V4_RE.match(rid), f"non-UUID4 report_id: {rid}"
        assert data["session_id"] == rid  # alias
        assert data["business_line"] == "corporate"
        assert data["total_files"] == 2
        assert data["total_parsed_chars"] >= 0
        # file_summary 形态
        assert len(data["file_summary"]) == 2
        for fs in data["file_summary"]:
            assert "name" in fs
            assert "type" in fs
            assert "size_bytes" in fs
            assert "parsed_chars" in fs
            assert "parse_status" in fs
        # 落盘检查 · upload_dir/{report_id}/ 存在 + 含 2 个文件
        d = upload_dir(rid)
        assert d.is_dir(), f"upload_dir 未创建: {d}"
        saved = sorted(p.name for p in d.iterdir() if p.is_file())
        assert "test_material_1.txt" in saved
        assert "test_material_2.txt" in saved
    finally:
        cleanup_report_dir(rid)


def test_upload_empty_files_rejects_400(client):
    resp = client.post("/api/report/upload",
                       params={"business_line": "corporate"})
    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("error", {}).get("code") == "VALIDATION_FAILED"


def test_upload_filename_collision_handles_with_suffix(client):
    """同名文件 2 次上传到同 report_id → 第 2 次重命名 (但端点每次 new report_id 不冲突)."""
    files1 = [("files", ("dup.txt", b"first", "text/plain"))]
    resp1 = client.post("/api/report/upload", files=files1)
    assert resp1.status_code == 200
    rid1 = resp1.json()["report_id"]
    try:
        files2 = [("files", ("dup.txt", b"second", "text/plain"))]
        resp2 = client.post("/api/report/upload", files=files2)
        assert resp2.status_code == 200
        rid2 = resp2.json()["report_id"]
        assert rid1 != rid2  # 每次 new report_id
    finally:
        cleanup_report_dir(rid1)
        cleanup_report_dir(resp2.json()["report_id"])


def test_upload_unsupported_ext_marks_skipped(client):
    files = [("files", ("test.bin", b"binary bin data", "application/octet-stream"))]
    resp = client.post("/api/report/upload", files=files)
    assert resp.status_code == 200
    rid = resp.json()["report_id"]
    try:
        fs = resp.json()["file_summary"][0]
        assert fs["parse_status"] == "skipped"
        assert fs["parsed_chars"] == 0
    finally:
        cleanup_report_dir(rid)


def test_upload_handles_chinese_filename(client):
    files = [("files", ("企业资料_2026.txt",
                        "企业基本信息测试".encode("utf-8"),
                        "text/plain"))]
    resp = client.post("/api/report/upload", files=files)
    assert resp.status_code == 200
    rid = resp.json()["report_id"]
    try:
        fs = resp.json()["file_summary"][0]
        # name 保留原中文(已 basename 处理)
        assert "企业资料" in fs["name"]
        assert fs["size_bytes"] > 0
    finally:
        cleanup_report_dir(rid)
