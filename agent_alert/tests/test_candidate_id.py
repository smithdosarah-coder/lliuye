# -*- coding: utf-8 -*-
"""ALL IN Phase B step 5 · alert.id 派生 unit test.

per candidate-identity-contract v1.1 §3 alert 行 + §10 单测覆盖.

验证 _ensure_alert_emit_ids in-place 加 id 字段 · 派生规则:
- USCC 通过 → uscc_<USCC>
- name 有 / USCC 缺 → name_<md5前12位>
- 都缺 → cand_<idx:03d>
"""
from __future__ import annotations

import re

from agent_alert.api import _ensure_alert_emit_ids
from shared.entity_resolver import verify_candidate_ids


def test_ensure_alert_ids_uscc_path():
    """在贷客户带 USCC → id 派生 uscc_<USCC>."""
    by_grade = {
        "red": [
            {"company_name": "测试客户A", "uscc": "91440300708461136T"},
        ],
        "yellow": [],
        "green": [],
    }
    top_cases = [
        {"customer": "测试客户A", "uscc": "91440300708461136T"},
    ]
    _ensure_alert_emit_ids(by_grade, top_cases)
    assert by_grade["red"][0]["id"] == "uscc_91440300708461136T"
    assert top_cases[0]["id"] == "uscc_91440300708461136T"


def test_ensure_alert_ids_name_md5_fallback():
    """USCC 缺 / name 有 → id 派生 name_<md5前12>."""
    by_grade = {
        "red": [{"company_name": "某不知名客户", "uscc": ""}],
        "yellow": [],
        "green": [],
    }
    top_cases = []
    _ensure_alert_emit_ids(by_grade, top_cases)
    cid = by_grade["red"][0]["id"]
    assert cid.startswith("name_")
    assert re.match(r"^name_[a-f0-9]{12}(_\d+)?$", cid), f"format mismatch: {cid}"


def test_ensure_alert_ids_idx_fallback():
    """USCC + name 都缺 → cand_<idx:03d>."""
    by_grade = {
        "red": [{"company_name": "", "uscc": ""}],
        "yellow": [],
        "green": [],
    }
    top_cases = []
    _ensure_alert_emit_ids(by_grade, top_cases)
    assert by_grade["red"][0]["id"] == "cand_000"


def test_ensure_alert_ids_unique_within_list():
    """同 list 内同 USCC 出现 2 次 → 后者加 _<idx> 后缀."""
    by_grade = {
        "red": [
            {"company_name": "客户A", "uscc": "91440300708461136T"},
            {"company_name": "客户A 副本", "uscc": "91440300708461136T"},
        ],
        "yellow": [],
        "green": [],
    }
    top_cases = []
    _ensure_alert_emit_ids(by_grade, top_cases)
    ids = [h["id"] for h in by_grade["red"]]
    assert ids[0] == "uscc_91440300708461136T"
    assert ids[1] == "uscc_91440300708461136T_1"  # 冲突 + idx 后缀
    # verify 全合规
    assert verify_candidate_ids(by_grade["red"]) == []


def test_ensure_alert_ids_cross_grade_independent():
    """red / yellow / green 各自 unique · 跨 grade 同 USCC 不冲突 (业务上不应出现 · 但合 contract)."""
    by_grade = {
        "red": [{"company_name": "客户A", "uscc": "91440300708461136T"}],
        "yellow": [{"company_name": "客户A", "uscc": "91440300708461136T"}],
        "green": [],
    }
    top_cases = [{"customer": "客户A", "uscc": "91440300708461136T"}]
    _ensure_alert_emit_ids(by_grade, top_cases)
    # red[0] · yellow[0] · top_cases[0] 各 list 内独立 unique
    assert by_grade["red"][0]["id"] == "uscc_91440300708461136T"
    assert by_grade["yellow"][0]["id"] == "uscc_91440300708461136T"
    assert top_cases[0]["id"] == "uscc_91440300708461136T"


def test_ensure_alert_ids_no_regression_placeholder():
    """禁出 regression placeholder ('未获取' / '[object Object]' / null / undefined / '')."""
    by_grade = {
        "red": [
            {"company_name": "客户A", "uscc": "91440300708461136T"},
            {"company_name": "客户B", "uscc": ""},
            {"company_name": "", "uscc": ""},
        ],
        "yellow": [],
        "green": [],
    }
    top_cases = []
    _ensure_alert_emit_ids(by_grade, top_cases)
    assert verify_candidate_ids(by_grade["red"]) == []


def test_ensure_alert_ids_preserves_existing_legitimate_id():
    """现有合法 id 保留 · 不覆盖 (helper §7)."""
    by_grade = {
        "red": [
            {"company_name": "客户A", "uscc": "91440300708461136T", "id": "manual_id_42"},
        ],
        "yellow": [],
        "green": [],
    }
    top_cases = []
    _ensure_alert_emit_ids(by_grade, top_cases)
    assert by_grade["red"][0]["id"] == "manual_id_42"  # 保留现有 · 不覆盖
