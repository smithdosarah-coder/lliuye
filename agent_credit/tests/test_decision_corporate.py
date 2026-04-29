# -*- coding: utf-8 -*-
"""Tests for POST /api/credit/decision (stage_tab=corporate · v4.0).

Coverage:
  - mock=true SSE 流验 7 阶段事件序列 · advice payload 含 4 维评分
  - 缺 report_json + preset_name → SSE error event (空白启动 protocol)
  - corporate stage 维度元数据 (4 维 + 4 grade · 直读 _STAGE_DIMENSIONS · 路由已下架)
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from agent_credit.api import app
    return TestClient(app)


def _parse_sse(body: str) -> list[dict]:
    events: list[dict] = []
    for block in body.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line[5:].strip()))
                except json.JSONDecodeError:
                    pass
    return events


def test_decision_corporate_mock_sse_pipeline(client):
    """mock=true → fixture SSE events · 7 阶段 + advice."""
    resp = client.post(
        "/api/credit/decision",
        json={"stage_tab": "corporate", "mock": True},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    # 必含 profile_loaded / scoring_done / rule_done / case_done / advising_done / done
    stages = [e.get("stage") for e in events if e.get("event") == "stage"]
    assert "feature_done" in stages
    assert "scoring_done" in stages
    assert "rule_done" in stages
    assert "case_done" in stages
    assert "advising_done" in stages

    # advising_done payload 含 4 维评分 + 决策
    advising = [e for e in events if e.get("event") == "stage" and e.get("stage") == "advising_done"][0]
    advice = advising["payload"]
    assert advice["decision"] in ("批准", "有条件批准", "拒绝")
    assert advice["composite_score"] >= 0
    assert advice["risk_grade"] in ("A", "B", "C", "D")
    assert advice["stage_tab"] == "corporate"
    assert advice["approved_amount"] > 0
    assert "[mock]" in advice["decision_reason"]

    # scoring_done sub_scores 含 4 维度
    scoring = [e for e in events if e.get("event") == "stage" and e.get("stage") == "scoring_done"][0]
    sub_scores = scoring["payload"]["sub_scores"]
    assert set(sub_scores.keys()) == {"financial", "industry", "operational", "guarantee"}


def test_decision_corporate_missing_input_emits_error(client):
    """空白启动 protocol: 既无 report_json 也无 preset_name + mock=false → SSE error event."""
    resp = client.post(
        "/api/credit/decision",
        json={"stage_tab": "corporate", "mock": False},
    )
    assert resp.status_code == 200  # SSE 总是 200 · 错误在 event 里
    events = _parse_sse(resp.text)
    err_events = [e for e in events if e.get("event") == "error"]
    assert len(err_events) >= 1
    assert "report_json" in err_events[0]["message"] or "preset_name" in err_events[0]["message"]


def test_stage_dimensions_corporate_metadata():
    """corporate stage_tab metadata · 4 维 + 4 grade.

    `/api/credit/presets` 路由已下架 (batch 4)·改读 `_STAGE_DIMENSIONS` 直查
    内部数据,保 stage 维度的契约稳定。
    """
    from agent_credit.api import _STAGE_DIMENSIONS
    corp = _STAGE_DIMENSIONS["corporate"]
    assert corp["stage_tab"] == "corporate"
    assert corp["label"] == "对公授信"
    assert corp["amount_range_wan"] == [50, 5000]
    assert len(corp["scoring_dimensions"]) == 4
    weights = sum(d["weight"] for d in corp["scoring_dimensions"])
    assert abs(weights - 1.0) < 0.001
    assert len(corp["risk_grades"]) == 4
    assert corp["red_line_count"] == 30


def test_decision_corporate_invalid_stage_tab(client):
    """stage_tab 非法 → 400 (上游校验)."""
    resp = client.post(
        "/api/credit/decision",
        json={"stage_tab": "garbage", "mock": True},
    )
    assert resp.status_code == 400
    assert "stage_tab" in resp.json()["detail"]
