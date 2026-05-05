# -*- coding: utf-8 -*-
"""POST /api/channel/conversion + GET /api/channel/conversion/{rm_id}/{candidate_id} 测试.

per onboarding · BE1 Step 4 · data/feedback/<rm_id>/<candidate_id>.jsonl 写入.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_channel import conversion_tracker
from agent_channel.api import app


@pytest.fixture
def temp_feedback_root(monkeypatch):
    """每个测试用临时目录 · 不污染真 data/feedback/."""
    with tempfile.TemporaryDirectory() as td:
        monkeypatch.setattr(conversion_tracker, "_FEEDBACK_ROOT", Path(td))
        yield Path(td)


def test_conversion_record_contacted_writes_jsonl(temp_feedback_root):
    client = TestClient(app)
    payload = {
        "candidate_id": "cand_001",
        "rm_id":        "wang_zhe",
        "stage":        "contacted",
        "notes":        "首次电话已拨打",
        "next_action":  "下周二二访",
    }
    resp = client.post("/api/channel/conversion", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["candidate_id"] == "cand_001"
    assert body["stage"] == "contacted"
    assert "timestamp" in body
    # 文件落盘
    out = temp_feedback_root / "wang_zhe" / "cand_001.jsonl"
    assert out.exists()
    assert "首次电话已拨打" in out.read_text(encoding="utf-8")


def test_conversion_won_requires_amount(temp_feedback_root):
    """won stage · amount_yuan 必填 > 0."""
    client = TestClient(app)
    resp = client.post("/api/channel/conversion", json={
        "candidate_id": "cand_002",
        "rm_id":        "wang_zhe",
        "stage":        "won",
        # 缺 amount_yuan
    })
    assert resp.status_code == 400
    assert "VALIDATION_FAILED" in resp.text


def test_conversion_won_with_amount_ok(temp_feedback_root):
    client = TestClient(app)
    resp = client.post("/api/channel/conversion", json={
        "candidate_id": "cand_003",
        "rm_id":        "wang_zhe",
        "stage":        "won",
        "amount_yuan":  5000000,
    })
    assert resp.status_code == 200


def test_conversion_invalid_rm_id_path_traversal(temp_feedback_root):
    """rm_id 含 path traversal 字符 → 400."""
    client = TestClient(app)
    resp = client.post("/api/channel/conversion", json={
        "candidate_id": "cand_004",
        "rm_id":        "../etc/passwd",
        "stage":        "contacted",
    })
    assert resp.status_code == 400


def test_conversion_invalid_stage(temp_feedback_root):
    client = TestClient(app)
    resp = client.post("/api/channel/conversion", json={
        "candidate_id": "cand_005",
        "rm_id":        "wang_zhe",
        "stage":        "made_up_stage",
    })
    assert resp.status_code == 400


def test_conversion_list_returns_chain(temp_feedback_root):
    """连写多 stage · GET 返按插入序的链."""
    client = TestClient(app)
    rm = "rm_li"
    cid = "cand_chain"
    for stage in ("contacted", "quoted", "won"):
        body = {"candidate_id": cid, "rm_id": rm, "stage": stage}
        if stage == "won":
            body["amount_yuan"] = 8000000
        client.post("/api/channel/conversion", json=body)
    resp = client.get(f"/api/channel/conversion/{rm}/{cid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    stages = [e["stage"] for e in body["events"]]
    assert stages == ["contacted", "quoted", "won"]


def test_conversion_list_missing_returns_empty(temp_feedback_root):
    client = TestClient(app)
    resp = client.get("/api/channel/conversion/rm_unknown/cand_unknown")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
