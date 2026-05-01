# -*- coding: utf-8 -*-
"""单测 · Phase B Sprint 1 BE3 · Agent6 material gap + cross-section coherence.

DoD (per docs/onboarding/B4-report.md §1 + docs/contracts/agent-report-material-gap.md):
- material_gap.build_graph 同 inputs 输出确定 (纯函数)
- 3 fixture 仅 inputs · 不含 material_gap_graph 字段 (反 5 原则 §3.5 #5 fail-fast 防回归)
- cross_section_coherence 跨章节数字 drift 检测 + 第 5 维 quality_blocker 集成
- handoff_section_supplement scaffold ack (Sprint 1 received not processed)
- quality_blocker.run_blocker(sections=None) 向下兼容 (老 caller 不破)

10 case:
  反 5 原则 (1):
    1. test_fixture_no_graph_field
  build_graph (3):
    2. test_build_graph_deterministic
    3. test_build_graph_correctness_easy
    4. test_build_graph_correctness_medium
    5. test_build_graph_correctness_hard
  section_impact (1):
    6. test_section_impact_summary
  cross_section_coherence (2):
    7. test_quality_blocker_sections_none_backward_compat
    8. test_quality_blocker_cross_section_drift
  handoff scaffold (2):
    9. test_handoff_scaffold_ack_event
    10. test_handoff_invalid_gap_section_422
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SCENARIO_DIR = PROJECT_ROOT / "data" / "mock" / "workspace" / "report" / "scenarios"
SCENARIO_IDS = ("easy", "medium", "hard")


def _load_fixture(scenario_id: str) -> dict:
    path = SCENARIO_DIR / f"{scenario_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ============================================================================
# 1. 反 5 原则 §3.5 #5 · fail-fast 防回归 (per Codex 插入点 1 V2 Q3)
# ============================================================================


def test_fixture_no_graph_field():
    """3 fixture 全无 material_gap_graph / section_impact / max_score_impact 等
    computed output 字段 (graph 由 build_graph 当场算 · 不预埋答案)。

    fail-fast: 任何 fixture 含 graph 字段视作回归 · CI 立刻 block.
    """
    forbidden_keys = {
        "material_gap_graph",
        "section_impact",
        "max_score_impact",
        "affected_scoring_dimensions",
    }
    for sid in SCENARIO_IDS:
        data = _load_fixture(sid)
        present = forbidden_keys & set(data.keys())
        assert not present, (
            f"{sid}.json 含 computed output 预埋字段: {present} · "
            f"违反反 5 原则 §3.5 #5 (fixture 仅 inputs · graph 是当场算) · "
            f"修: 删字段 + 改 build_graph 当场计算"
        )
        # 也禁 inputs 段含答案字段
        inputs = data.get("material_gap_inputs", {})
        assert "max_score_impact" not in inputs, f"{sid} material_gap_inputs 含 max_score_impact 预埋"
        assert "graph" not in inputs, f"{sid} material_gap_inputs 含 graph 预埋"


# ============================================================================
# 2. build_graph 纯函数确定性
# ============================================================================


def test_build_graph_deterministic():
    """同 inputs 多次 build_graph 输出一致 (纯函数 · 无 side effect · 无随机).

    锁定 now 参数 (默认走 datetime.now → 不一致 · test 用固定 datetime).
    """
    from agent_report.material_gap import build_graph
    inputs = _load_fixture("medium")["material_gap_inputs"]
    fixed_now = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    g1 = build_graph(inputs, report_id="test-001", now=fixed_now)
    g2 = build_graph(inputs, report_id="test-001", now=fixed_now)
    g3 = build_graph(inputs, report_id="test-001", now=fixed_now)
    assert g1 == g2 == g3, "build_graph 同 inputs 多次输出不一致 · 违反纯函数确定性"


# ============================================================================
# 3-5. 3 fixture 实算 max_score_impact 落预期范围
# ============================================================================


def test_build_graph_correctness_easy():
    """easy: 1 missing advisory (controller) · max_score_impact 12 · 2 dim."""
    from agent_report.material_gap import build_graph
    inputs = _load_fixture("easy")["material_gap_inputs"]
    g = build_graph(inputs, report_id="rep-easy")
    s = g["summary"]
    assert s["missing_material_count"] == 1, f"easy missing 应 1 实 {s['missing_material_count']}"
    assert s["max_score_impact"] <= 20, f"easy max_score_impact 应 ≤20 实 {s['max_score_impact']}"
    # 至少 industry + operational (controller→ch1 advisory 命中)
    assert {"industry", "operational"}.issubset(set(s["affected_scoring_dimensions"]))
    assert s["blocking_section_count"] == 0, "easy 全 advisory · blocking_section 应 0"


def test_build_graph_correctness_medium():
    """medium: 3 missing + 3 partial · max_score_impact ≥50 · 4 dim 全命中."""
    from agent_report.material_gap import build_graph
    inputs = _load_fixture("medium")["material_gap_inputs"]
    g = build_graph(inputs, report_id="rep-med")
    s = g["summary"]
    assert s["missing_material_count"] == 3
    assert s["partial_material_count"] == 3
    assert s["max_score_impact"] >= 50, f"medium max_score_impact 应 ≥50 实 {s['max_score_impact']}"
    assert set(s["affected_scoring_dimensions"]) == {
        "financial", "guarantee", "industry", "operational"
    }, "medium 应命中全 4 dim"
    assert s["blocking_section_count"] >= 2


def test_build_graph_correctness_hard():
    """hard: 8 missing + cross-section conflict · max_score_impact ≥80 (cap 100)."""
    from agent_report.material_gap import build_graph
    inputs = _load_fixture("hard")["material_gap_inputs"]
    g = build_graph(inputs, report_id="rep-hard")
    s = g["summary"]
    assert s["missing_material_count"] >= 7
    assert s["max_score_impact"] >= 80, f"hard max_score_impact 应 ≥80 实 {s['max_score_impact']}"
    assert s["max_score_impact"] <= 100, "max_score_impact cap 100"
    assert set(s["affected_scoring_dimensions"]) == {
        "financial", "guarantee", "industry", "operational"
    }
    # cross_section_numbers 也是 inputs 的一部分 · 但 graph 本身不消费它 (graph 只看 material status)
    # cross_section drift 由 quality_blocker 第 5 维独立验 (test 7-8)
    assert "revenue" in inputs.get("cross_section_numbers", {})


# ============================================================================
# 6. section_impact 反查
# ============================================================================


def test_section_impact_summary():
    """section_impact_summary(graph) 返 {section: {affected_fields, severity, score_impact_by_dim}}."""
    from agent_report.material_gap import build_graph, section_impact_summary
    inputs = _load_fixture("medium")["material_gap_inputs"]
    g = build_graph(inputs, report_id="rep-med")
    summary = section_impact_summary(g)
    # medium 应至少触 ch1 + ch2 + ch3 (3 个 blocking section)
    assert "chapter_2_operation" in summary
    assert "chapter_3_finance" in summary
    ch3 = summary["chapter_3_finance"]
    assert "affected_fields" in ch3
    assert "severity" in ch3
    assert "score_impact_by_dim" in ch3
    # ch3 应触 financial + guarantee 两个 dim
    assert "financial" in ch3["score_impact_by_dim"]
    assert "guarantee" in ch3["score_impact_by_dim"]


# ============================================================================
# 7-8. quality_blocker 第 5 维 (cross_section_coherence) · 向下兼容 + 触发
# ============================================================================


def test_quality_blocker_sections_none_backward_compat():
    """run_blocker(sections=None) 跳过第 5 维 · 既有 4 维行为不变 (向下兼容)."""
    from agent_report.quality_blocker import run_blocker
    text = "公司主营业务为汽车制造 · 营收 1000 万元。"
    # sections=None (默认)
    v1 = run_blocker(text, financial_anchor=None, expect_evidence=False)
    assert "4 维" in v1.summary, "sections=None summary 应说 4 维"
    # sections=[] 空 list 不触
    v2 = run_blocker(text, expect_evidence=False, sections=[])
    assert "4 维" in v2.summary, "sections=[] summary 应说 4 维"
    # cross_section_coherence 维度 不在 fail_dims (没跑)
    assert "cross_section_coherence" not in (v1.fail_dimensions + v2.fail_dimensions)


def test_quality_blocker_cross_section_drift():
    """sections 含跨章节冲突 · 触发第 5 维 BLOCK."""
    from agent_report.quality_blocker import run_blocker
    sections = [
        {"id": "chapter_2_operation",
         "content": "2024 年营业收入 5000 万元 · 主营汽车。"},
        {"id": "chapter_3_finance",
         "content": "营业收入 10000 万元 · 净利率 8%。"},
    ]
    v = run_blocker(text="主营汽车", expect_evidence=False, sections=sections)
    assert v.blocked, "跨章节 5000 vs 10000 万元 50% drift · 应 BLOCK"
    assert "cross_section_coherence" in v.fail_dimensions
    # 至少 1 个 issue 是 value_drift:revenue
    drift_issues = [i for i in v.issues if i.code.startswith("value_drift:")]
    assert len(drift_issues) >= 1
    assert any("revenue" in i.code for i in drift_issues)


# ============================================================================
# 9-10. handoff_section_supplement scaffold (Sprint 1 ack received not processed)
# ============================================================================


def test_handoff_scaffold_ack_event():
    """valid §6.2 payload → SSE stream emit started + ack event (scaffold_mode=true)."""
    from agent_report.handoff_section_supplement import (
        SectionSupplementRequest,
        handle_section_supplement,
    )
    req = SectionSupplementRequest(
        schema_version="1.0",
        intent_type="report_gap_supplement",
        source_agent="credit",
        target_agent="report",
        report_id="rep-001",
        gap_sections=["chapter_2_operation", "upstream_top5"],
        requesting_decision_id="dec-001",
        urgency="blocking",
    )

    async def collect():
        events = []
        async for ev in handle_section_supplement(req):
            events.append(ev)
        return events

    events = asyncio.run(collect())
    assert len(events) == 2, f"应 emit 2 events (started + ack) · 实 {len(events)}"
    assert "section_supplement_started" in events[0]
    assert "section_supplement_ack" in events[1]
    # Sprint 1 关键: ack 含 scaffold_mode + supplement_status=scaffold_ack +
    # partial_section_run_pending = "Phase B-3"
    assert "scaffold_mode" in events[1]
    assert "scaffold_ack" in events[1]
    assert "Phase B-3" in events[1]
    # 不含 done event (Sprint 1 = ack received not processed · B-3 才升级 done)
    full = "".join(events)
    assert "section_supplement_done" not in full, (
        "Sprint 1 不应 emit done event (会误导 frontend 触发 Agent3 re-score) · "
        "等 Phase B-3 fix-forward 实装 partial section run 后才升级 done"
    )


def test_handoff_invalid_gap_section_422():
    """gap_sections 含未知 key → Pydantic ValidationError → caller 应返 422."""
    from pydantic import ValidationError

    from agent_report.handoff_section_supplement import SectionSupplementRequest

    with pytest.raises(ValidationError) as exc:
        SectionSupplementRequest(
            schema_version="1.0",
            intent_type="report_gap_supplement",
            source_agent="credit",
            target_agent="report",
            report_id="rep-001",
            gap_sections=["chapter_99_unknown"],   # ← 未知 key
            requesting_decision_id="dec-001",
            urgency="advisory",
        )
    err_str = str(exc.value)
    assert "chapter_99_unknown" in err_str
    assert "未知 key" in err_str or "must" in err_str.lower() or "value error" in err_str.lower()
