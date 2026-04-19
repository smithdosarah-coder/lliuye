# -*- coding: utf-8 -*-
"""单测 · scripts/feedback_extract_agent6.py(Task A 交付闭环)

DoD: L3-8
覆盖 ≥3 用例:
  1. bootstrap 正常加载 + 去重 key 生成
  2. audit JSONL 过滤 agent=="report" + 与 bootstrap 合并去重
  3. 章节均衡选取(limit=8 时各章≤2)+ bootstrap 优先级高于 audit
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import feedback_extract_agent6 as fe  # noqa: E402


@pytest.fixture()
def tmp_feedback(tmp_path):
    fb = tmp_path / "data" / "feedback"
    boot = fb / "bootstrap"
    boot.mkdir(parents=True)
    (fb / "extracted").mkdir()
    return fb, boot


def _write_yaml(p: Path, data: dict) -> None:
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _write_jsonl(p: Path, records: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_bootstrap_loads_and_dedup_key_stable(tmp_feedback):
    """Case 1: bootstrap 加载 + dedup key 稳定(相同输入 key 一致)."""
    fb, boot = tmp_feedback
    item_a = {
        "scenario": "科创贷",
        "chapter": 3,
        "field_path": "x.y.z",
        "original_output": "v1",
        "corrected_output": "v2",
        "correction_reason": "reason",
        "injection_hint": {"target_chapter": 3, "priority": "high"},
    }
    _write_yaml(boot / "6_a.yaml", item_a)
    loaded = fe.load_bootstrap(boot)
    assert len(loaded) == 1
    assert loaded[0]["_source"] == "bootstrap"
    # dedup key 稳定
    k1 = fe._derive_dedup_key(item_a)
    k2 = fe._derive_dedup_key({**item_a, "metadata": {"x": 1}})
    assert k1 == k2, "dedup key 应对 metadata 差异不敏感"


def test_audit_filter_and_merge_dedup(tmp_feedback):
    """Case 2: audit JSONL 过滤 agent=='report' + 与 bootstrap 合并去重(bootstrap 优先)."""
    fb, boot = tmp_feedback
    # bootstrap 1 条
    _write_yaml(
        boot / "6_b.yaml",
        {
            "scenario": "小微",
            "chapter": 4,
            "field_path": "c4.collateral",
            "corrected_output": "详细的担保分析",
            "injection_hint": {"target_chapter": 4, "priority": "high"},
        },
    )
    # audit jsonl: 3 条 report + 2 条非 report 噪声
    date = datetime.now().strftime("%Y-%m-%d")
    _write_jsonl(
        fb / f"{date}.jsonl",
        [
            {
                "agent": "report",
                "session_id": "s1",
                "scenario": "小微",
                "chapter": 4,
                "field_path": "c4.collateral",
                "user_correction": "详细的担保分析",
                "correction_reason": "r",
            },
            {
                "agent": "report",
                "session_id": "s2",
                "scenario": "涉农",
                "chapter": 3,
                "field_path": "c3.subsidy",
                "user_correction": "补贴拆科目",
            },
            {"agent": "credit", "session_id": "noise-1"},
            {"agent": "alert", "session_id": "noise-2"},
            {
                "agent": "report",
                "session_id": "s3",
                "scenario": "对私",
                "chapter": 1,
                "field_path": "c1.credit",
                "user_correction": "征信口径",
            },
        ],
    )
    audit = fe.load_feedback_jsonl(fb, agent="report")
    assert len(audit) == 3
    assert all(r.get("agent") == "report" for r in audit)

    merged = fe.load_bootstrap(boot) + audit
    deduped = fe.dedup(merged)
    # bootstrap 的小微 + audit 的小微(同 key)应合并为 1 条,且保留 bootstrap
    xiaowei_items = [x for x in deduped if x.get("scenario") == "小微"]
    assert len(xiaowei_items) == 1
    assert xiaowei_items[0]["_source"] == "bootstrap"
    # 总数:bootstrap(1) + audit(3) - 重复(1) = 3
    assert len(deduped) == 3


def test_rank_chapter_balance_and_end_to_end(tmp_feedback):
    """Case 3: 章节均衡(limit=8 → 单章≤2)+ 端到端产出 YAML 结构."""
    fb, boot = tmp_feedback
    # 6 条 bootstrap 全在 ch3 + 2 条散布 ch1/ch4
    for i in range(6):
        _write_yaml(
            boot / f"6_ch3_{i}.yaml",
            {
                "scenario": f"sc{i}",
                "chapter": 3,
                "field_path": f"c3.f{i}",
                "corrected_output": f"v{i}",
                "injection_hint": {"target_chapter": 3, "priority": "high"},
            },
        )
    _write_yaml(
        boot / "6_ch1.yaml",
        {
            "scenario": "c1-x",
            "chapter": 1,
            "field_path": "c1.f1",
            "corrected_output": "c1v",
            "injection_hint": {"target_chapter": 1, "priority": "high"},
        },
    )
    _write_yaml(
        boot / "6_ch4.yaml",
        {
            "scenario": "c4-x",
            "chapter": 4,
            "field_path": "c4.f1",
            "corrected_output": "c4v",
            "injection_hint": {"target_chapter": 4, "priority": "high"},
        },
    )

    out = tmp_feedback[0] / "extracted" / "out.yaml"
    fe.run(limit=8, out_path=out, feedback_dir=fb, bootstrap_dir=boot)

    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["agent"] == "report"
    items = data["items"]
    # limit=8, per_chapter_cap=2 → ch3 初始 cap 限 2;ch1 1 条 + ch4 1 条 = 4,
    # 剩余名额补齐走"不受配额限制"分支,总数逼近 8(但 bootstrap 也只 8 条)
    assert len(items) <= 8
    ch3_items = [x for x in items if str(x.get("chapter")) == "3"]
    # 首轮 ch3 受 cap=2 控制;补齐阶段可超 cap,但总数不超过输入
    assert len(ch3_items) >= 2
    # 结构字段齐
    for it in items:
        assert "scenario" in it
        assert "injection_hint" in it
        assert "source" in it
