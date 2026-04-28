# -*- coding: utf-8 -*-
"""Pytest for agent_alert.scan_engine · load_hitlist persistence + lookup.

不调真 LLM · 全部走 tmp_path 隔离.
"""
from __future__ import annotations

import json

import pytest

from agent_alert import scan_engine
from agent_alert.scan_engine import (
    HitListNotFoundError,
    load_hitlist,
    persist_hitlist,
)
from shared.kb_scan.models import (
    CompanyProfile,
    Evidence,
    HitItem,
    HitList,
    RiskLevel,
    ScanTarget,
)


@pytest.fixture
def isolated_alert_dir(tmp_path, monkeypatch):
    alert_dir = tmp_path / "alert"
    sessions_dir = alert_dir / "sessions"
    monkeypatch.setattr(scan_engine, "ALERT_DATA_DIR", alert_dir)
    monkeypatch.setattr(scan_engine, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(scan_engine, "LATEST_POINTER", alert_dir / "latest.json")
    return alert_dir


@pytest.fixture
def sample_hitlist():
    """构造 3 家客户的 HitList (1 红 + 1 黄 + 1 绿)."""
    def _mk(level, name, hid):
        return HitItem(
            hit_id=hid,
            level=level,
            score={RiskLevel.RED: 90.0, RiskLevel.YELLOW: 60.0, RiskLevel.GREEN: 20.0}[level],
            target=ScanTarget(
                target_id=hid,
                target_type="loan_customer",
                payload={"company_name": name, "industry": "制造业",
                         "region": "浙江省杭州市"},
            ),
            matched_rules=["FIN-002"] if level == RiskLevel.RED else [],
            reasons=[f"[外部 × FIN-002] {name} 净利润转负"]
            if level == RiskLevel.RED else [],
            evidences=[Evidence(source="裁判文书网", snippet="(2025)沪0115民初12345号",
                                url="https://example.com")] if level == RiskLevel.RED else [],
            extras={},
        )

    return HitList(
        list_id="test-lst-001",
        agent_name="alert",
        kb_summary="3 家测试客户",
        scan_summary="测试场景",
        total_scanned=3,
        total_hit=3,
        red_count=1,
        yellow_count=1,
        green_count=1,
        hits=[
            _mk(RiskLevel.RED, "华联精密制造有限公司", "LC10001"),
            _mk(RiskLevel.YELLOW, "盛达汽配有限公司", "LC10002"),
            _mk(RiskLevel.GREEN, "顺通物流有限公司", "LC10003"),
        ],
    )


# ---------------------------------------------------------------------------
# Test 1: persist + load roundtrip
# ---------------------------------------------------------------------------


def test_persist_and_load_roundtrip(isolated_alert_dir, sample_hitlist):
    sid = persist_hitlist(
        sample_hitlist, dispositions={"华联精密制造有限公司": {"actions": [], "notes": "test"}},
        mode_label="demo_forced", scenario_key="test_scenario",
    )
    assert sid

    payload = load_hitlist()  # latest
    assert payload["session_id"] == sid
    assert payload["mode"] == "demo_forced"
    assert payload["scenario_key"] == "test_scenario"
    assert payload["hit_list"]["red_count"] == 1
    assert payload["hit_list"]["yellow_count"] == 1
    assert payload["hit_list"]["green_count"] == 1
    assert len(payload["hit_list"]["hits"]) == 3
    assert "华联精密制造有限公司" in payload["dispositions"]


def test_load_by_explicit_session_id(isolated_alert_dir, sample_hitlist):
    """指定 session_id 不走 latest."""
    sid_a = persist_hitlist(sample_hitlist, dispositions={}, session_id="sid-a")
    sid_b = persist_hitlist(sample_hitlist, dispositions={}, session_id="sid-b")

    # latest 指向 sid-b
    latest = load_hitlist()
    assert latest["session_id"] == "sid-b"

    # 显式指 sid-a 仍能读
    explicit = load_hitlist(session_id="sid-a")
    assert explicit["session_id"] == "sid-a"


# ---------------------------------------------------------------------------
# Test 2: not found
# ---------------------------------------------------------------------------


def test_load_no_latest_raises(isolated_alert_dir):
    """从未跑过任何 scan · load_hitlist() 抛 HitListNotFoundError."""
    with pytest.raises(HitListNotFoundError):
        load_hitlist()


def test_load_unknown_session_raises(isolated_alert_dir, sample_hitlist):
    persist_hitlist(sample_hitlist, dispositions={}, session_id="ok-sid")
    with pytest.raises(HitListNotFoundError):
        load_hitlist(session_id="no-such-sid")
