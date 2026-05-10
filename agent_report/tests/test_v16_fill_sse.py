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


def test_should_use_mock_no_key_raises_in_all_in():
    """ALL IN Phase B (per AGENT_IDENTITY-report.md §6 step 3 红线 1):
    has_dee_pseek_key=False + explicit_mock=False → raise (拒 silent fallback mock)."""
    with pytest.raises(RuntimeError) as excinfo:
        should_use_mock_v16(
            classified_json=Path("/tmp/exists.json"),
            has_dee_pseek_key=False,
            explicit_mock=False,
        )
    assert "DEEPSEEK_API_KEY" in str(excinfo.value)
    assert "silent" in str(excinfo.value).lower() or "拒" in str(excinfo.value)


def test_should_use_mock_no_classified_json_raises_in_all_in(tmp_path):
    """ALL IN Phase B: classified_json 不存在 + explicit_mock=False → raise (拒 silent fallback mock)."""
    nonexist = tmp_path / "absent.json"
    with pytest.raises(RuntimeError) as excinfo:
        should_use_mock_v16(
            classified_json=nonexist,
            has_dee_pseek_key=True,
            explicit_mock=False,
        )
    assert "classified" in str(excinfo.value).lower()
    assert "v16_classifier" in str(excinfo.value).lower() or "silent" in str(excinfo.value).lower()


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
    """ALL IN Phase B (per AGENT_IDENTITY-report.md §6 step 3 红线 1):
    真路径触发 · classifier 缺 → emit error event (拒 silent fallback mock 接管)."""
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
    # ALL IN: error event 替代 mock 接管 · v16_runner.should_use_mock_v16 raise → api.py emit error
    errors = [e for e in events if e["event"] == "error"]
    assert len(errors) >= 1, f"期望 error event · 实际 events: {[e['event'] for e in events]}"
    err_data = errors[0]["data"]
    assert err_data.get("code") == "V16_REAL_PATH_FAILED"
    # 不应有 done · classifier 缺 → silent fallback 拒 → 流终止
    dones = [e for e in events if e["event"] == "done"]
    assert len(dones) == 0, "ALL IN 拒 silent fallback · 不应 emit done"


def test_v16_fill_explicit_mock_done_has_entity_key(client):
    """ALL IN Phase B step 6 (per entity-resolution-contract v1.1 §5):
    mock_v16_stream done payload profile.entity_key 必出 · 含 uscc / name_normalized / confidence."""
    resp = client.post(
        "/api/report/v16/fill",
        json={"report_id": "entity-key-test", "mock": True},
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    done = [e for e in events if e["event"] == "done"][0]["data"]

    profile = done.get("profile") or {}
    assert "entity_key" in profile, "profile.entity_key 缺失 · 跨 agent handoff 主键不稳"
    ek = profile["entity_key"]
    # entity_key 三字段全 (per shared/entity_resolver/resolver.py:EntityKey)
    assert "uscc" in ek
    assert "name_normalized" in ek
    assert "confidence" in ek
    # mock 路径 USCC anchored · confidence 应 == 1.0
    assert ek["confidence"] == 1.0, f"USCC anchored 应 confidence=1.0 · got {ek['confidence']}"
    assert len(ek["uscc"]) == 18, f"USCC 必 18 位 · got len={len(ek['uscc'])}"
    assert ek["name_normalized"]  # non-empty


def test_v16_fill_explicit_mock_sections_have_unique_id(client):
    """ALL IN Phase B step 5 (per candidate-identity-contract v1.1 §3 + §4.2):
    mock_v16_stream done payload sections / pending_questions / evidences 全经 ensure_list_unique_ids ·
    每条必含 id 字段 · 同 list unique · 防 regression placeholder."""
    resp = client.post(
        "/api/report/v16/fill",
        json={"report_id": "mock-id-test", "mock": True},
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    done = [e for e in events if e["event"] == "done"][0]["data"]

    REGRESSION_PLACEHOLDER = {"", "未获取", "[object Object]", "null", "undefined", None}

    # sections id check
    sections = done.get("sections") or []
    assert len(sections) == 4
    section_ids = [s.get("id") for s in sections]
    for sid in section_ids:
        assert sid not in REGRESSION_PLACEHOLDER, f"section id regression: {sid!r}"
    assert len(set(section_ids)) == len(section_ids), f"sections id 重复: {section_ids}"

    # pending_questions id check
    pendings = done.get("pending_questions") or []
    pending_ids = [p.get("id") for p in pendings]
    for pid in pending_ids:
        assert pid not in REGRESSION_PLACEHOLDER, f"pending id regression: {pid!r}"
    assert len(set(pending_ids)) == len(pending_ids), f"pending id 重复: {pending_ids}"

    # evidences id check (step 4 + step 5)
    evidences = done.get("evidences") or []
    assert len(evidences) >= 3, "step 4 mock 至少 3 条 evidence 示范"
    ev_ids = [e.get("evidence_id") for e in evidences]
    for eid in ev_ids:
        assert eid not in REGRESSION_PLACEHOLDER, f"evidence id regression: {eid!r}"
    assert len(set(ev_ids)) == len(ev_ids), f"evidence id 重复: {ev_ids}"
    # claim_id 必关联 section.id (跨表引用一致性)
    valid_claim_ids = set(section_ids)
    for ev in evidences:
        assert ev.get("claim_id") in valid_claim_ids, (
            f"evidence claim_id {ev.get('claim_id')!r} 未关联到任何 section"
        )
