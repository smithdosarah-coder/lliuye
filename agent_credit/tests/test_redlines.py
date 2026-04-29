# -*- coding: utf-8 -*-
"""Tests for 红线判定 · POST /api/credit/decision rule_done event shape.

红线规则 schema (per docs/contracts/agent-credit-spec.md §5.3):
  { rule_id, rule_name, is_hard, can_waive, severity, actual_value, threshold, waiver_conditions }

3 stage_tab 各自不同红线 (corporate 30 / small_business 20 / retail 20).
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


def _get_rule_done_payload(client, stage_tab: str) -> list[dict]:
    resp = client.post(
        "/api/credit/decision",
        json={"stage_tab": stage_tab, "mock": True},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    rule = [e for e in events if e.get("event") == "stage" and e.get("stage") == "rule_done"][0]
    return rule["payload"]


@pytest.mark.parametrize("stage_tab", ["corporate", "small_business", "retail"])
def test_redline_event_shape(client, stage_tab):
    """rule_done payload 含必要字段 · 各 stage_tab 至少 1 条 mock 红线."""
    hits = _get_rule_done_payload(client, stage_tab)
    assert isinstance(hits, list)
    assert len(hits) >= 1
    for h in hits:
        assert "rule_id" in h
        assert "rule_name" in h
        assert "is_hard" in h
        assert "can_waive" in h
        assert "severity" in h
        assert h["severity"] in ("low", "medium", "high", "critical", "red", "yellow")
        assert "actual_value" in h
        assert "threshold" in h


def test_redline_corporate_specific(client):
    """corporate mock fixture 含'关联交易占比' rule (业务红线模板示例)."""
    hits = _get_rule_done_payload(client, "corporate")
    rule_names = [h["rule_name"] for h in hits]
    assert "关联交易占比" in rule_names
    rule = next(h for h in hits if h["rule_name"] == "关联交易占比")
    assert rule["actual_value"] == 0.32
    assert rule["threshold"] == 0.30
    assert rule["can_waive"] is True


def test_redline_retail_specific(client):
    """retail 红线对'近 12 月逾期次数'敏感."""
    hits = _get_rule_done_payload(client, "retail")
    rule_names = [h["rule_name"] for h in hits]
    assert any("逾期" in n for n in rule_names)


def test_redline_count_metadata():
    """`_STAGE_DIMENSIONS` 中 red_line_count 与产品 spec 一致 (corp 30 / sb 20 / retail 20).

    /api/credit/presets 路由已下架 (batch 4)·改读 _STAGE_DIMENSIONS 直查。
    """
    from agent_credit.api import _STAGE_DIMENSIONS
    assert _STAGE_DIMENSIONS["corporate"]["red_line_count"] == 30
    assert _STAGE_DIMENSIONS["small_business"]["red_line_count"] == 20
    assert _STAGE_DIMENSIONS["retail"]["red_line_count"] == 20
