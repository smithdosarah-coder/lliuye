# -*- coding: utf-8 -*-
"""Stage C.1 · POST /api/report/v16/fill SSE 单测.

锁定:
  - 端点返 ``text/event-stream`` · 5 阶段 stage 事件 + 1 done
  - 显式 ``mock=true`` 走 ``mock_v16_stream`` (不依赖 DEEPSEEK_API_KEY)
  - done event 含 pipeline=v16 + qc + stats + sections
  - mock_pipeline=true (empty-state-design-protocol §5 demo 显式标)
  - should_use_mock_v16 决策矩阵
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.api import app  # noqa: E402
from agent_report.v16_runner import should_use_mock_v16  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


def _parse_sse_events(body: str) -> list[dict]:
    """解析 SSE body → list of {event, data: dict}."""
    out = []
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        evt = None
        data_str = None
        for line in chunk.splitlines():
            if line.startswith("event:"):
                evt = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
        if evt and data_str:
            try:
                out.append({"event": evt, "data": json.loads(data_str)})
            except json.JSONDecodeError:
                out.append({"event": evt, "data": data_str})
    return out


def test_v16_fill_explicit_mock_streams_5_stages_and_done(client):
    resp = client.post(
        "/api/report/v16/fill",
        json={"report_id": "mock-test-001", "mock": True},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse_events(resp.text)
    stages = [e for e in events if e["event"] == "stage"]
    dones = [e for e in events if e["event"] == "done"]

    # 5 stages
    assert len(stages) == 5, f"expected 5 stages · got {len(stages)}"
    stage_keys = [s["data"]["stage"] for s in stages]
    assert stage_keys == ["ingest", "extract", "infer", "write", "audit"]
    # 全部 pipeline=v16
    for s in stages:
        assert s["data"]["pipeline"] == "v16"
        assert 0.0 <= s["data"]["progress"] <= 1.0

    # 1 done
    assert len(dones) == 1
    done = dones[0]["data"]
    assert done["pipeline"] == "v16"
    assert done["mock_pipeline"] is True  # empty-state §5 显式 demo 标
    assert done["report_id"] == "mock-test-001"
    assert done["session_id"] == "mock-test-001"
    assert "qc" in done
    assert done["qc"]["passed"] is True
    assert "score" in done["qc"]
    assert "stats" in done
    assert "sections" in done
    assert len(done["sections"]) == 4  # 4 chapter
    assert "pending_questions" in done


def test_v16_fill_mock_chapters_have_4_canonical_ids(client):
    resp = client.post(
        "/api/report/v16/fill",
        json={"report_id": "mock-test-002", "mock": True},
    )
    events = _parse_sse_events(resp.text)
    done = [e for e in events if e["event"] == "done"][0]["data"]
    chapter_ids = [s["id"] for s in done["sections"]]
    assert chapter_ids == [
        "chapter_1_background",
        "chapter_2_operation",
        "chapter_3_finance",
        "chapter_4_conclusion",
    ]
    # 第 4 章未填(等 Agent3 回写)
    assert done["sections"][3]["status"] == "pending"


def test_should_use_mock_explicit_mock():
    use, reason = should_use_mock_v16(
        classified_json=Path("/tmp/whatever.json"),
        has_dee_pseek_key=True,
        explicit_mock=True,
    )
    assert use is True
    assert "explicit" in reason.lower()


def test_should_use_mock_no_key():
    use, reason = should_use_mock_v16(
        classified_json=Path("/tmp/exists.json"),
        has_dee_pseek_key=False,
        explicit_mock=False,
    )
    assert use is True
    assert "deepseek" in reason.lower() or "DEEPSEEK" in reason


def test_should_use_mock_no_classified_json(tmp_path):
    nonexist = tmp_path / "absent.json"
    use, reason = should_use_mock_v16(
        classified_json=nonexist,
        has_dee_pseek_key=True,
        explicit_mock=False,
    )
    assert use is True
    assert "classified" in reason.lower()


def test_should_use_real_when_all_present(tmp_path):
    classified = tmp_path / "v16_llm_classified.json"
    classified.write_text("{}", encoding="utf-8")
    use, reason = should_use_mock_v16(
        classified_json=classified,
        has_dee_pseek_key=True,
        explicit_mock=False,
    )
    assert use is False
    assert reason == "real_v16"


def test_v16_fill_real_path_without_classified_json_emits_error(client, tmp_path, monkeypatch):
    """真路径触发条件 · 但 classifier 缺 → mock 路径自动接管(see should_use_mock)."""
    # 模拟有 key 但走 explicit_mock=false · v16_runner 内部应识别 classifier 缺失 → 走 mock
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")
    resp = client.post(
        "/api/report/v16/fill",
        json={
            "report_id": "real-but-missing-classified",
            "classified_json": str(tmp_path / "absent.json"),
            "mock": False,
        },
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    # mock 接管 · 仍然有 5 stage + 1 done
    stages = [e for e in events if e["event"] == "stage"]
    dones = [e for e in events if e["event"] == "done"]
    assert len(stages) == 5
    assert len(dones) == 1
    assert dones[0]["data"]["mock_pipeline"] is True
