# -*- coding: utf-8 -*-
"""E2E 测试 · /api/feedback 反馈飞轮落盘 (DoD L3-8)

校验:
  1. POST /api/feedback 正常落盘到 data/feedback/YYYY-MM-DD.jsonl
  2. schema 与 CLAUDE.md §6 四环数据飞轮第 3 环对齐
  3. 非法 agent 拒收 (400)
  4. /api/feedback/stats 统计反馈条数正确

运行:
  py -m pytest agent_report/tests/test_feedback_e2e.py -v
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import api_server  # noqa: E402


# 数据飞轮第 3 环约定字段(CLAUDE.md §6)
EXPECTED_FIELDS = {
    "timestamp",
    "agent",
    "session_id",
    "user_id",
    "original_output",
    "user_correction",
    "correction_reason",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """用临时 PROJECT_ROOT 做 I/O 隔离,不污染真实 data/feedback/."""
    monkeypatch.setattr(api_server, "PROJECT_ROOT", tmp_path)
    return TestClient(api_server.app)


def _today_jsonl(root: Path) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    return root / "data" / "feedback" / f"{date}.jsonl"


def test_feedback_roundtrip_writes_jsonl(client, tmp_path):
    """POST /api/feedback → JSONL 落盘 + schema 对齐."""
    payload = {
        "agent": "report",
        "session_id": "sess-e2e-001",
        "original_output": {"field_path": "chapter_3_finance.revenue", "value": "100"},
        "user_correction": {"field_path": "chapter_3_finance.revenue", "value": "120"},
        "correction_reason": "单位错填,原材料为 120 万元",
        "user_id": "mock_wangzhe",
    }

    resp = client.post("/api/feedback", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    rel = body["path"]
    assert rel.replace("\\", "/").startswith("data/feedback/")

    # JSONL 已落盘
    path = _today_jsonl(tmp_path)
    assert path.is_file(), f"feedback jsonl not created at {path}"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    # schema 对齐
    assert EXPECTED_FIELDS.issubset(record.keys()), \
        f"missing fields: {EXPECTED_FIELDS - set(record.keys())}"
    assert record["agent"] == "report"
    assert record["session_id"] == "sess-e2e-001"
    assert record["user_id"] == "mock_wangzhe"
    assert record["correction_reason"].startswith("单位错填")


def test_feedback_multi_entries_append(client, tmp_path):
    """多次 POST 按行追加,不覆盖."""
    base = {
        "agent": "report",
        "session_id": "sess-e2e-002",
        "original_output": {"v": 1},
        "user_correction": {"v": 2},
        "correction_reason": "r1",
    }
    for i in range(3):
        r = client.post("/api/feedback", json={**base, "session_id": f"sess-{i}"})
        assert r.status_code == 200

    lines = _today_jsonl(tmp_path).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    sids = [json.loads(l)["session_id"] for l in lines]
    assert sids == ["sess-0", "sess-1", "sess-2"]


def test_feedback_rejects_unknown_agent(client):
    """非白名单 agent → 400."""
    bad = {
        "agent": "unknown_x",
        "session_id": "s",
        "original_output": {},
        "user_correction": {},
    }
    resp = client.post("/api/feedback", json=bad)
    assert resp.status_code == 400
    assert "agent must be one of" in resp.json()["detail"]


def test_feedback_stats_counts_correctly(client, tmp_path):
    """/api/feedback/stats 统计 total/by_agent/by_date 正确."""
    for agent in ["report", "credit", "report"]:
        resp = client.post("/api/feedback", json={
            "agent": agent,
            "session_id": f"s-{agent}",
            "original_output": {},
            "user_correction": {},
        })
        assert resp.status_code == 200

    stats = client.get("/api/feedback/stats").json()
    assert stats["total"] == 3
    assert stats["by_agent"].get("report") == 2
    assert stats["by_agent"].get("credit") == 1
    today = datetime.now().strftime("%Y-%m-%d")
    assert stats["by_date"].get(today) == 3


def test_feedback_all_six_agents_accepted(client):
    """六个 Agent 白名单都能收."""
    for agent in ["channel", "credit", "alert", "compliance", "report", "riskctrl"]:
        r = client.post("/api/feedback", json={
            "agent": agent,
            "session_id": f"{agent}-s",
            "original_output": {},
            "user_correction": {},
        })
        assert r.status_code == 200, f"agent={agent} rejected: {r.text}"
