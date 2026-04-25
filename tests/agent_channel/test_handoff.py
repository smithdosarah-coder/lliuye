"""POST /api/channel/handoff 冒烟测试 — 契约见 docs/contracts/channel_to_credit_handoff.md。

关键断言：
- UUID v4 session_id / profile_id
- 文件落盘到 data/handoff/channel_to_credit/{session_id}/{profile_id}.json
- JSON 含 candidate_profile + enterprise_profile 两层
- 非 UUID v4 / 空列表 → 400 + VALIDATION_FAILED
"""
from __future__ import annotations

import json
import re

from fastapi.testclient import TestClient

from agent_channel import api as api_mod
from agent_channel.api import app

UUID_V4_RE = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$"
)


def _candidate(name: str = "浙江 A") -> dict:
    return {
        "name": name,
        "uscc": "913301020000000011",
        "registeredCapital": "1000 万",
        "signalScore": 55,
        "signalCount": 2,
        "signalTypes": ["bidding", "growth"],
        "signals": [
            {"type": "bidding", "title": "中标", "detail": "",
             "date": "2026-03-01", "source": "chinabidding",
             "url": "https://chinabidding.cn/x"},
            {"type": "growth", "title": "扩产", "detail": "",
             "date": "2026-02-01", "source": "gov.cn",
             "url": "https://env.gov.cn/y"},
        ],
        "recommendedProducts": ["流动资金贷款"],
        "dataSources": [{"label": "chinabidding", "hint": ""}],
    }


def test_handoff_writes_files_and_returns_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "_HANDOFF_ROOT", tmp_path)
    client = TestClient(app)
    resp = client.post(
        "/api/channel/handoff",
        json={
            "candidates": [_candidate("浙江 A"), _candidate("浙江 B")],
            "business_line": "corporate",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert UUID_V4_RE.match(body["session_id"])
    assert body["count"] == 2
    assert len(body["profile_ids"]) == 2
    for pid in body["profile_ids"]:
        assert UUID_V4_RE.match(pid)

    # 文件落盘校验
    session_dir = tmp_path / body["session_id"]
    assert session_dir.exists()
    files = list(session_dir.glob("*.json"))
    assert len(files) == 2
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert "candidate_profile" in data
    assert "enterprise_profile" in data
    # Agent3 消费路径严格子集
    assert data["enterprise_profile"]["company_name"] in {"浙江 A", "浙江 B"}


def test_handoff_rejects_empty_candidates(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "_HANDOFF_ROOT", tmp_path)
    client = TestClient(app)
    resp = client.post("/api/channel/handoff", json={"candidates": []})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"]["code"] == "VALIDATION_FAILED"


def test_handoff_rejects_bad_session_id(tmp_path, monkeypatch):
    """防目录穿越：session_id 非 UUID v4 → 400。"""
    monkeypatch.setattr(api_mod, "_HANDOFF_ROOT", tmp_path)
    client = TestClient(app)
    resp = client.post(
        "/api/channel/handoff",
        json={
            "session_id": "../etc/passwd",
            "candidates": [_candidate()],
        },
    )
    assert resp.status_code == 400
    err = resp.json()["detail"]["error"]
    assert err["code"] == "VALIDATION_FAILED"
    assert err["details"]["field"] == "session_id"


def test_handoff_honors_provided_session_id(tmp_path, monkeypatch):
    monkeypatch.setattr(api_mod, "_HANDOFF_ROOT", tmp_path)
    client = TestClient(app)
    fixed = "7f4c7a2d-c2f5-4c8e-9d2a-b3e6f1a0c9d7"
    resp = client.post(
        "/api/channel/handoff",
        json={"session_id": fixed, "candidates": [_candidate()]},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == fixed
    assert (tmp_path / fixed).exists()
