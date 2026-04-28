# -*- coding: utf-8 -*-
"""Tests for POST /api/credit/decision (stage_tab=small_business · v4.0).

small_business 后端走 corporate ScoringModel · 但 stage_tab 标记 + 评分维度权重 + 阈值不同
(per /api/credit/presets payload).
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


def test_decision_small_business_mock_sse(client):
    """mock=true · stage_tab=small_business · 验 advice 含 stage_tab 标记 + 阈值放宽."""
    resp = client.post(
        "/api/credit/decision",
        json={"stage_tab": "small_business", "mock": True},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    # advising_done 含 stage_tab=small_business
    advising = [e for e in events if e.get("event") == "stage" and e.get("stage") == "advising_done"][0]
    advice = advising["payload"]
    assert advice["stage_tab"] == "small_business"
    # 利率档位 LPR+200BP (小微高于对公 LPR+85BP)
    assert "LPR+200BP" in advice["rate_benchmark"]
    # approved_amount 在 small_business 区间 [10, 500]
    assert 10 <= advice["approved_amount"] <= 500


def test_get_presets_small_business_weights(client):
    """small_business 抵押权重 0.30 (对公 0.25 · 弱化行业到 0.10)."""
    resp = client.get("/api/credit/presets")
    assert resp.status_code == 200
    data = resp.json()
    sb = next(s for s in data["stages"] if s["stage_tab"] == "small_business")
    assert sb["label"] == "普惠 / 小微"
    assert sb["amount_range_wan"] == [10, 500]
    weights = {d["axis_id"]: d["weight"] for d in sb["scoring_dimensions"]}
    assert weights["guarantee"] == 0.30  # 抵押权重高于对公
    assert weights["industry"] == 0.10   # 行业权重低于对公
    assert sb["red_line_count"] == 20    # 红线数量小于对公 30
    assert "继承对公" in sb["note"] or "小微" in sb["note"]


def test_decision_small_business_grade_threshold_loose(client):
    """small_business 阈值放宽 5 分 (A=75 vs corporate A=80)."""
    resp = client.get("/api/credit/presets")
    data = resp.json()
    sb = next(s for s in data["stages"] if s["stage_tab"] == "small_business")
    grade_a = next(g for g in sb["risk_grades"] if g["grade"] == "A")
    assert grade_a["min_score"] == 75
    grade_c = next(g for g in sb["risk_grades"] if g["grade"] == "C")
    assert grade_c["min_score"] == 45  # corporate C=50 · sb 放宽到 45
