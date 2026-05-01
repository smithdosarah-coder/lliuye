# -*- coding: utf-8 -*-
"""Phase B BE10 · /api/feedback 同步写 audit_service.LLMCall trail.

验证: POST /api/feedback 后 admin GET /api/audit/llm_calls?endpoint=/api/feedback
能查到 modify 流水 (含 user_id / agent_id / prompt=original_output / response=user_correction)。
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def isolated_audit(tmp_path: Path, monkeypatch):
    """每条测试独占一个空 audit sqlite + 干净 feedback dir + reset default_recorder."""
    audit_db = tmp_path / "audit_isolated.db"
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AUDIT_DB_PATH", str(audit_db))
    monkeypatch.setenv("ENCRYPT_AT_REST", "false")  # plaintext 便于断言

    import audit_service.recorder as recorder_mod
    recorder_mod.set_default_recorder(None)  # 清 singleton, 让 monkeypatched env 生效

    # api_server 已 import 过 → reload 让 PROJECT_ROOT 等保持，但 audit recorder 走新 db
    import api_server  # noqa: F401
    importlib.reload(api_server)

    # 把 feedback 写入路径切到 tmp · monkeypatch PROJECT_ROOT.data 不方便 · 直接 patch 目录
    monkeypatch.setattr(api_server, "PROJECT_ROOT", tmp_path, raising=True)

    yield audit_db, tmp_path, api_server

    recorder_mod.set_default_recorder(None)


def test_feedback_post_records_audit_modify_event(isolated_audit):
    """POST /api/feedback → 1) 写 jsonl 2) 写 audit LLMCall (endpoint=/api/feedback)."""
    audit_db, root, api_server = isolated_audit
    from fastapi.testclient import TestClient

    with TestClient(api_server.app) as client:
        resp = client.post("/api/feedback", json={
            "agent": "credit",
            "session_id": "sess-test-001",
            "original_output": {"额度建议": 500, "期限": "12 月"},
            "user_correction": {"额度建议": 600, "期限": "18 月"},
            "correction_reason": "现金流余量足以支撑更长期限",
            "user_id": "rm-001",
        })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"

    # JSONL 真写了
    jsonl_files = list((root / "data" / "feedback").glob("*.jsonl"))
    assert len(jsonl_files) == 1
    line = jsonl_files[0].read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["agent"] == "credit"
    assert rec["user_correction"]["额度建议"] == 600

    # Audit log 真写了
    from audit_service.recorder import default_recorder
    rows = default_recorder().query(agent_id="credit", limit=10)
    feedback_rows = [r for r in rows if r["endpoint"] == "/api/feedback"]
    assert len(feedback_rows) == 1, f"expected 1 audit row, got {len(feedback_rows)}: {rows}"
    row = feedback_rows[0]
    assert row["agent_id"] == "credit"
    assert row["user_id"] == "rm-001"
    assert row["model"] == "user-feedback"
    # prompt = original_output JSON · response = user_correction JSON
    prompt_obj = json.loads(row["prompt"])
    response_obj = json.loads(row["response"])
    assert prompt_obj["额度建议"] == 500
    assert response_obj["额度建议"] == 600
    # correction_reason 走 error 字段 (复用现有 schema · 不新建表)
    assert row["error"] == "现金流余量足以支撑更长期限"


def test_feedback_invalid_agent_returns_400(isolated_audit):
    """非白名单 agent 返 400, 不写 jsonl 不写 audit."""
    _, root, api_server = isolated_audit
    from fastapi.testclient import TestClient

    with TestClient(api_server.app) as client:
        resp = client.post("/api/feedback", json={
            "agent": "unknown",
            "session_id": "sess-x",
            "original_output": {},
            "user_correction": {},
        })
    assert resp.status_code == 400

    from audit_service.recorder import default_recorder
    assert default_recorder().count() == 0
    assert not (root / "data" / "feedback").exists() or not list(
        (root / "data" / "feedback").glob("*.jsonl"),
    )


def test_feedback_audit_silent_fail_does_not_break_jsonl(isolated_audit, monkeypatch):
    """audit 写挂时主流程仍 200 + jsonl 不丢 (审贷员反馈不能因 audit 故障丢)."""
    _, root, api_server = isolated_audit
    from fastapi.testclient import TestClient

    # 让 default_recorder 抛异常
    import audit_service.recorder as recorder_mod
    class _BoomRecorder:
        def record(self, _call): raise RuntimeError("simulated audit failure")
    monkeypatch.setattr(recorder_mod, "default_recorder", lambda: _BoomRecorder())

    with TestClient(api_server.app) as client:
        resp = client.post("/api/feedback", json={
            "agent": "report",
            "session_id": "sess-test-002",
            "original_output": {"风险意见": "可贷"},
            "user_correction": {"风险意见": "审慎"},
            "correction_reason": "再核流水",
        })
    assert resp.status_code == 200
    jsonl_files = list((root / "data" / "feedback").glob("*.jsonl"))
    assert len(jsonl_files) == 1
