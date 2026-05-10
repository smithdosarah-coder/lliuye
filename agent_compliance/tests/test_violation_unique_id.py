# -*- coding: utf-8 -*-
"""Violation unique id · ALL IN Phase B step 5 (2026-05-09).

per candidate-identity-contract.md v1.1 §3 + ensure_candidate_id helper:
compliance hit.id 按 client + client_uscc 派生 · cand_<idx> 兜底.
"""
from __future__ import annotations

import pytest

from agent_compliance.scan_engine import (
    _ensure_violation_ids,
    _extract_client_fields,
)


# ---------------------------------------------------------------------------
# _extract_client_fields · 多 alias 容错
# ---------------------------------------------------------------------------


def test_extract_client_fields_from_client_alias():
    v = {"event_fields": {"client": "腾讯科技", "amount": 1000}}
    name, uscc = _extract_client_fields(v)
    assert name == "腾讯科技"
    assert uscc == ""


def test_extract_client_fields_from_chinese_alias():
    v = {"event_fields": {"企业名": "海康威视", "金额": 5000}}
    name, uscc = _extract_client_fields(v)
    assert name == "海康威视"


def test_extract_client_fields_uscc_alias():
    v = {"event_fields": {"client": "腾讯", "USCC": "91440300708461136T"}}
    name, uscc = _extract_client_fields(v)
    assert name == "腾讯"
    assert uscc == "91440300708461136T"


def test_extract_client_fields_no_event_fields():
    v = {"violation_id": "VIO-001"}
    name, uscc = _extract_client_fields(v)
    assert name == ""
    assert uscc == ""


def test_extract_client_fields_skips_non_str():
    v = {"event_fields": {"client": 12345, "customer": "华为"}}  # client 是 int 跳过
    name, uscc = _extract_client_fields(v)
    assert name == "华为"


# ---------------------------------------------------------------------------
# _ensure_violation_ids · 端到端 candidate-identity-contract 合规
# ---------------------------------------------------------------------------


def test_ensure_ids_uscc_path():
    """has USCC → uscc_<USCC> id."""
    violations = [
        {
            "violation_id": "VIO-001",
            "event_fields": {"client": "腾讯科技", "USCC": "91440300708461136T"},
        }
    ]
    _ensure_violation_ids(violations)
    assert violations[0]["id"] == "uscc_91440300708461136T"
    assert violations[0]["client"] == "腾讯科技"
    assert violations[0]["client_uscc"] == "91440300708461136T"


def test_ensure_ids_name_only_path():
    """有 client name 但无 USCC → name_<md5前12位>."""
    violations = [
        {
            "violation_id": "VIO-001",
            "event_fields": {"client": "海康威视"},
        }
    ]
    _ensure_violation_ids(violations)
    assert violations[0]["id"].startswith("name_")
    assert len(violations[0]["id"]) == len("name_") + 12


def test_ensure_ids_fallback_cand_idx():
    """无 client / 无 USCC → cand_<idx:03d>."""
    violations = [
        {"violation_id": "VIO-001", "event_fields": {"amount": 100}},
        {"violation_id": "VIO-002", "event_fields": {"amount": 200}},
    ]
    _ensure_violation_ids(violations)
    assert violations[0]["id"] == "cand_000"
    assert violations[1]["id"] == "cand_001"


def test_ensure_ids_unique_within_list():
    """同 client name 多 violation · helper 自动加 _<idx> 后缀确保 unique."""
    violations = [
        {"violation_id": "VIO-001", "event_fields": {"client": "腾讯"}},
        {"violation_id": "VIO-002", "event_fields": {"client": "腾讯"}},  # 同 client
    ]
    _ensure_violation_ids(violations)
    ids = [v["id"] for v in violations]
    assert len(set(ids)) == 2  # unique


def test_ensure_ids_keeps_violation_id_backwards_compat():
    """新 id 字段不覆盖旧 violation_id (前端可继续按 violation_id read)."""
    violations = [
        {
            "violation_id": "VIO-042",
            "event_fields": {"client": "腾讯", "USCC": "91440300708461136T"},
        }
    ]
    _ensure_violation_ids(violations)
    assert violations[0]["violation_id"] == "VIO-042"
    assert violations[0]["id"] == "uscc_91440300708461136T"


def test_ensure_ids_empty_list():
    """空 list 不抛."""
    violations: list[dict] = []
    _ensure_violation_ids(violations)
    assert violations == []
