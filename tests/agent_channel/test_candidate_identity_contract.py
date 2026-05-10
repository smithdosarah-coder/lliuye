# -*- coding: utf-8 -*-
"""Phase B.2 (PM 2026-05-10 §8) candidate-identity-contract v1.1 channel binding tests.

Per docs/contracts/candidate-identity-contract.md §3 channel row:
  channel | candidate (look-alike 候选) | candidate.id | ensure_list_unique_ids(candidates)

硬规 (per §1):
  - 每条必含 id (str · unique within list)
  - 不允许 ""/null/"未获取"/"[object Object]"
  - 同 list 内不允许 id 重复 (helper 自动加 _<idx> 后缀)

Phase B.2 改动: agent_channel/realtime_stream.py 不再 inline 派生 id ·
改用 ensure_list_unique_ids 走 make_unique_id 标准路径 (USCC GB 32100 校验 + name normalize)
"""
from __future__ import annotations

from shared.entity_resolver import ensure_list_unique_ids, verify_candidate_ids


def test_realtime_stream_uses_canonical_helper_not_inline_md5():
    """realtime_stream._build_final_output 不再 inline import hashlib · 走 helper."""
    from pathlib import Path
    rs_path = Path(__file__).resolve().parents[2] / "agent_channel" / "realtime_stream.py"
    content = rs_path.read_text(encoding="utf-8")

    # _build_final_output 内不再 import hashlib (Step 8 migrate to helper)
    bfo_idx = content.find("def _build_final_output")
    assert bfo_idx > 0
    next_def_idx = content.find("\ndef ", bfo_idx + 1)
    body = content[bfo_idx:next_def_idx]
    assert "import hashlib" not in body, (
        "Phase B.2 §8 · _build_final_output 不应再 inline import hashlib · "
        "走 ensure_list_unique_ids (per candidate-identity-contract v1.1 §4.2)"
    )
    assert "ensure_list_unique_ids" in body, (
        "Phase B.2 §8 · _build_final_output 必调 ensure_list_unique_ids · "
        "per contract v1.1 §3 channel row"
    )


def test_helper_emits_uscc_id_for_valid_uscc():
    """USCC 通过校验 → uscc_<USCC> id (per §2 优先级 1)."""
    cands = [{"name": "海康威视", "uscc": "91330185711315925G"}]
    ensure_list_unique_ids(cands)
    assert cands[0]["id"] == "uscc_91330185711315925G"


def test_helper_emits_name_md5_id_for_no_uscc():
    """无 USCC 但有 name → name_<md5前12位> (per §2 优先级 2)."""
    cands = [{"name": "某不知名小厂"}]
    ensure_list_unique_ids(cands)
    assert cands[0]["id"].startswith("name_")
    assert len(cands[0]["id"]) == 5 + 12  # "name_" + 12 hex


def test_helper_emits_idx_id_for_empty_dict():
    """空 dict (无 name 无 USCC) → cand_<idx:03d> (per §2 优先级 3)."""
    cands = [{}, {}, {}]
    ensure_list_unique_ids(cands)
    assert cands[0]["id"] == "cand_000"
    assert cands[1]["id"] == "cand_001"
    assert cands[2]["id"] == "cand_002"


def test_helper_dedups_same_list_with_suffix():
    """同 list 重复 id → 加 _<idx> 后缀 (per §2 冲突处理)."""
    # 两个同名公司 (无 USCC) · md5 hash 相同
    cands = [
        {"name": "腾讯科技"},
        {"name": "腾讯科技"},  # dup
        {"name": "腾讯科技"},  # dup
    ]
    ensure_list_unique_ids(cands)
    ids = [c["id"] for c in cands]
    # ids 全 unique
    assert len(set(ids)) == 3
    # 后两个加 _<idx> 后缀
    assert ids[1].endswith("_1")
    assert ids[2].endswith("_2")


def test_verify_no_violations_on_realistic_channel_payload():
    """模拟 channel realtime_stream 实际 emit 的 candidates · verify 0 violations."""
    cands = [
        {"name": "海康威视", "uscc": "91330185711315925G", "industry": "安防", "geo": "杭州"},
        {"name": "大华股份", "uscc": "91330185714931610T", "industry": "安防", "geo": "杭州"},
        {"name": "宇视科技", "industry": "安防", "geo": "杭州"},  # 无 USCC
        {"name": "海康威视", "uscc": "91330185711315925G"},  # dup full
        {},  # 空候选
    ]
    ensure_list_unique_ids(cands)
    violations = verify_candidate_ids(cands)
    assert violations == [], f"channel payload regression: {violations!r}"
    # 全条都有 id
    assert all(c.get("id") for c in cands)
    # 无 placeholder regression
    bad_values = {"", None, "未获取", "[object Object]", "null", "undefined"}
    assert all(c["id"] not in bad_values for c in cands)
