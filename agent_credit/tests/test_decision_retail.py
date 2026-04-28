# -*- coding: utf-8 -*-
"""Tests for POST /api/credit/decision (stage_tab=retail · v4.0).

retail 评分卡 FICO 式 300-850 · 4 维度 (偿债/意愿/稳定/抵押) · 利率 LPR-10BP ~ LPR+50BP.
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


def test_decision_retail_mock_sse_fico(client):
    """retail mock SSE · advice 含 FICO 式评分 + retail 4 维."""
    resp = client.post(
        "/api/credit/decision",
        json={"stage_tab": "retail", "mock": True},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    advising = [e for e in events if e.get("event") == "stage" and e.get("stage") == "advising_done"][0]
    advice = advising["payload"]
    assert advice["stage_tab"] == "retail"
    # FICO 式评分 300-850
    assert 300 <= advice["composite_score"] <= 850
    # retail risk_grade 中文档位
    assert advice["risk_grade"] in ("优", "中优", "良好", "边界", "拒")
    # 利率档位 retail 应低于对公 (个人优质客户 LPR 浮动小)
    assert "LPR" in advice["rate_benchmark"]


def test_decision_retail_scoring_subscores(client):
    """retail scoring_done sub_scores 含 4 维 (ability/willingness/stability/collateral)."""
    resp = client.post(
        "/api/credit/decision",
        json={"stage_tab": "retail", "mock": True},
    )
    events = _parse_sse(resp.text)
    scoring = [e for e in events if e.get("event") == "stage" and e.get("stage") == "scoring_done"][0]
    sub_scores = scoring["payload"]["sub_scores"]
    assert set(sub_scores.keys()) == {"ability", "willingness", "stability", "collateral"}
    # FICO 式评分 sub_scores 也应在合理 range
    for v in sub_scores.values():
        assert v >= 0


def test_get_presets_retail_grades(client):
    """retail 5 个评级档位 · FICO 阈值 800/760/700/680."""
    resp = client.get("/api/credit/presets")
    data = resp.json()
    rt = next(s for s in data["stages"] if s["stage_tab"] == "retail")
    assert rt["label"] == "对私 / 零售"
    assert len(rt["risk_grades"]) == 5
    grade_youxiu = next(g for g in rt["risk_grades"] if g["grade"] == "优")
    assert grade_youxiu["min_score"] == 800
    grade_bianjie = next(g for g in rt["risk_grades"] if g["grade"] == "边界")
    assert grade_bianjie["min_score"] == 680
    weights = {d["axis_id"]: d["weight"] for d in rt["scoring_dimensions"]}
    assert weights["ability"] == 0.30
    assert weights["collateral"] == 0.20
