# -*- coding: utf-8 -*-
"""Pytest for word_export · 修订意见书 docx 渲染 + load_scan_result."""
from __future__ import annotations

import json

import pytest

from agent_compliance import scan_engine
from agent_compliance.scan_engine import (
    ScanResultNotFoundError,
    load_scan_result,
    persist_scan_result,
)
from agent_compliance.word_export import (
    build_revision_docx,
    build_revision_filename,
)


@pytest.fixture
def isolated_compli_dir(tmp_path, monkeypatch):
    compli_dir = tmp_path / "compliance"
    sessions_dir = compli_dir / "sessions"
    monkeypatch.setattr(scan_engine, "COMPLI_DATA_DIR", compli_dir)
    monkeypatch.setattr(scan_engine, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(scan_engine, "LATEST_POINTER", compli_dir / "latest.json")
    return compli_dir


@pytest.fixture
def fake_scan_payload():
    return {
        "scan_id": "test-scan-001",
        "generated_at": "2026-04-28T13:00:00",
        "mode": "demo_forced",
        "rule_count": 2,
        "event_count": 2,
        "cell_count": 4,
        "rules": [
            {"rule_id": "POL-001", "article": "第六条", "category": "期限",
             "condition": "期限 ≤ 12 月", "threshold": {"max_months": 12}, "severity_hint": "critical"},
            {"rule_id": "POL-002", "article": "第三条", "category": "出资比例",
             "condition": "出资比例 ≥ 30%", "threshold": {"min_bank_share_ratio": 0.30}, "severity_hint": "critical"},
        ],
        "events": [
            {"event_id": "LN001", "event_type": "loan", "fields": {"months": 18, "purpose": "消费"}},
            {"event_id": "COOP001", "event_type": "cooperation", "fields": {"bank_share": 0.15}},
        ],
        "matrix": [["violate", "not_applicable"], ["not_applicable", "violate"]],
        "violations": [
            {
                "violation_id": "VIO-001",
                "rule_id": "POL-001", "rule_article": "第六条",
                "rule_condition": "期限 ≤ 12 月",
                "event_id": "LN001", "event_type": "loan",
                "severity": "critical",
                "evidence": "months=18 超阈值",
                "match_reason": "事件 LN001 months=18 > 上限 12",
                "revisions": [
                    {"category": "改", "title": "缩短贷款期限",
                     "text": "把贷款期限调整到 12 个月以内"},
                    {"category": "强", "title": "强化期限审查",
                     "text": "建立期限合规审查机制"},
                ],
            },
            {
                "violation_id": "VIO-002",
                "rule_id": "POL-002", "rule_article": "第三条",
                "rule_condition": "出资比例 ≥ 30%",
                "event_id": "COOP001", "event_type": "cooperation",
                "severity": "critical",
                "evidence": "bank_share=0.15 低于 0.30",
                "match_reason": "事件 COOP001 bank_share=0.15 < 下限 0.30",
                "revisions": [
                    {"category": "补", "title": "补充出资比例条款",
                     "text": "新增出资比例不低于 30% 的硬性条款"},
                ],
            },
        ],
        "stats": {
            "rule_count": 2, "event_count": 2, "cell_count": 4,
            "violation_count": 2,
            "severe_count": 2, "normal_count": 0, "observation_count": 0,
        },
    }


# ---------------------------------------------------------------------------
# build_revision_docx · 字节流 + 含 docx 标志位
# ---------------------------------------------------------------------------


def test_build_docx_returns_bytes(fake_scan_payload):
    data = build_revision_docx(fake_scan_payload)
    assert isinstance(data, bytes)
    assert len(data) > 1000
    # docx 是 zip · 头是 PK
    assert data[:2] == b"PK"


def test_build_docx_filename_includes_scan_id(fake_scan_payload):
    fname = build_revision_filename(fake_scan_payload)
    assert "test-scan-001" in fname
    assert fname.endswith(".docx")


def test_build_docx_handles_empty_violations():
    """无 violations · 三类 panel 显示「（本类无修订建议）」."""
    payload = {
        "scan_id": "empty-1",
        "generated_at": "2026-04-28T00:00",
        "rules": [],
        "events": [],
        "violations": [],
        "stats": {"rule_count": 0, "event_count": 0, "cell_count": 0,
                  "violation_count": 0, "severe_count": 0, "normal_count": 0, "observation_count": 0},
    }
    data = build_revision_docx(payload)
    assert isinstance(data, bytes)
    assert len(data) > 500


# ---------------------------------------------------------------------------
# persist + load_scan_result roundtrip
# ---------------------------------------------------------------------------


def test_persist_load_roundtrip(isolated_compli_dir, fake_scan_payload):
    sid = persist_scan_result(fake_scan_payload, scan_id="roundtrip-001")
    assert sid == "roundtrip-001"
    loaded = load_scan_result()
    assert loaded["scan_id"] == sid
    assert loaded["stats"]["violation_count"] == 2
    # 显式 scan_id 也读得到
    explicit = load_scan_result(scan_id="roundtrip-001")
    assert explicit["scan_id"] == "roundtrip-001"


def test_load_no_latest_raises(isolated_compli_dir):
    with pytest.raises(ScanResultNotFoundError):
        load_scan_result()


def test_load_unknown_id_raises(isolated_compli_dir, fake_scan_payload):
    persist_scan_result(fake_scan_payload, scan_id="exists-1")
    with pytest.raises(ScanResultNotFoundError):
        load_scan_result(scan_id="no-such-id")


# ---------------------------------------------------------------------------
# end-to-end: persist → build_docx
# ---------------------------------------------------------------------------


def test_e2e_persist_then_export(isolated_compli_dir, fake_scan_payload):
    sid = persist_scan_result(fake_scan_payload, scan_id="e2e-001")
    payload = load_scan_result(scan_id=sid)
    data = build_revision_docx(payload, title="E2E 测试修订意见书")
    assert isinstance(data, bytes)
    assert data[:2] == b"PK"
