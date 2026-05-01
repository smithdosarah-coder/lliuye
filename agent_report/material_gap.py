# -*- coding: utf-8 -*-
"""agent_report.material_gap — Sprint 1 BE3 主模块.

build_graph(inputs) -> dict
  消费 material_gap_inputs (per fixture shape · 仅 inputs 不含 graph) ·
  当场算 MaterialGapGraph (3 节点 + 2 边 + summary) · 纯函数确定性输出.

红线 (per docs/contracts/agent-report-material-gap.md §6):
  - 不重写 v16 pipeline (本 module 是 audit 阶段后置 wrapper · 由 v16_runner
    在 done_payload 注入前调)
  - 不引 ML / 不引 LLM 现场算 (per CLAUDE.md §3.1 确定性计算)
  - 同 inputs 多次调用 → 输出一致 (test_build_graph_deterministic 验)

Schema (per agent-report-material-gap.md §2):
  - 节点 3 类型: material / section / scoring_dimension
  - 边 2 类型:
    · provides (material→section) · severity blocking/advisory · affected_fields
    · affects (section→scoring_dim) · impact_magnitude 0-100 · reasoning
  - summary: missing_material_count / blocking_section_count /
    advisory_section_count / max_score_impact / affected_scoring_dimensions
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from agent_report.material_gap_rules import (
    GRAPH_VERSION,
    SECTION_TO_DIM_WEIGHTS,
    get_material_name,
    get_material_provides,
    get_scoring_dim_name,
    get_section_dim_weight,
    get_section_field_count,
    get_section_name,
)


# ============================================================================
# 主入口 · build_graph
# ============================================================================

def build_graph(
    inputs: dict[str, Any],
    *,
    report_id: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """从 material_gap_inputs 构造 MaterialGapGraph.

    Args:
        inputs: material_gap_inputs dict · shape per agent-report-material-gap.md §2.4:
            {
              "scenario_id": str,
              "difficulty_tier": "easy"|"medium"|"hard",
              "materials": [{"id", "name", "status": "present"|"partial"|"missing"}],
              "section_status": [{"id": "chapter_<n>_<name>", "status": "done"|"pending"|"partial"}],
              "cross_section_numbers": dict (hard 档专用 · 可空)
            }
        report_id: optional · 注入 graph.report_id (不强制)
        now: optional · 注入 graph.generated_at (test 用 · 默认 datetime.now)

    Returns:
        MaterialGapGraph dict (graph_version + nodes + edges + summary)
    """
    materials = list(inputs.get("materials") or [])
    section_status = list(inputs.get("section_status") or [])

    # ---- 1. 收集所有缺/部分 material (status != present) ----
    gap_materials = [
        m for m in materials
        if (m.get("status") or "").lower() in ("missing", "partial")
    ]

    # ---- 2. 收集本 graph 涉及的 section + scoring_dim ----
    involved_sections: dict[str, str] = {}   # section_id → status (从 section_status fallback)
    section_status_by_id = {
        s.get("id"): (s.get("status") or "").lower()
        for s in section_status
        if s.get("id")
    }

    # ---- 3. 构造 provides edges (material→section) + 汇总 section 受影响字段 ----
    provides_edges: list[dict[str, Any]] = []
    section_affected_fields: dict[str, set[str]] = {}    # section_id → set of fields
    section_severity: dict[str, str] = {}                # section_id → blocking/advisory

    for m in gap_materials:
        mid = m.get("id")
        if not mid:
            continue
        rules = get_material_provides(mid)
        if not rules:
            # 未知 material id · 不进 graph (不假阳)
            continue
        for section_id, severity, fields in rules:
            provides_edges.append({
                "type": "provides",
                "from_id": mid,
                "to_id": section_id,
                "severity": severity,
                "affected_fields": list(fields),
            })
            section_affected_fields.setdefault(section_id, set()).update(fields)
            # blocking 优先 · advisory 不覆盖既有 blocking
            if severity == "blocking" or section_severity.get(section_id) != "blocking":
                section_severity[section_id] = severity
            involved_sections[section_id] = section_status_by_id.get(section_id, "unknown")

    # ---- 4. 构造 affects edges (section→scoring_dim) + 计算 impact_magnitude ----
    affects_edges: list[dict[str, Any]] = []
    involved_dims: set[str] = set()

    for section_id, fields in section_affected_fields.items():
        section_total = get_section_field_count(section_id)
        if section_total <= 0:
            # ch4_conclusion 总字段=0 · 不参 magnitude (Agent3 决策回写区)
            continue
        affected_count = len(fields)
        # 该 section 关联的所有 scoring_dim · 逐个算 magnitude
        for dim_id in SECTION_TO_DIM_WEIGHTS.get(section_id, {}):
            weight = get_section_dim_weight(section_id, dim_id)
            if weight <= 0:
                continue
            magnitude = round(
                (affected_count / section_total) * weight * 100
            )
            magnitude = max(0, min(100, magnitude))
            if magnitude == 0:
                continue
            affects_edges.append({
                "type": "affects",
                "from_id": section_id,
                "to_id": dim_id,
                "impact_magnitude": magnitude,
                "reasoning": (
                    f"{get_section_name(section_id)} 缺 {affected_count}/{section_total} 字段 · "
                    f"对 {get_scoring_dim_name(dim_id)} 权重 {weight:.1f} · "
                    f"预期评分下行 {magnitude}"
                ),
            })
            involved_dims.add(dim_id)

    # ---- 5. 构造 nodes (material + section + scoring_dim) ----
    nodes: list[dict[str, Any]] = []

    # material nodes (仅 gap_materials · status != present)
    for m in gap_materials:
        mid = m.get("id")
        if not mid:
            continue
        nodes.append({
            "type": "material",
            "id": mid,
            "name": m.get("name") or get_material_name(mid),
            "status": (m.get("status") or "").lower(),
        })

    # section nodes (仅 involved_sections · 受 gap material 影响)
    for sid, sst in sorted(involved_sections.items()):
        nodes.append({
            "type": "section",
            "id": sid,
            "name": get_section_name(sid),
            "status": sst if sst != "unknown" else "pending",
        })

    # scoring_dimension nodes (仅 involved_dims)
    for dim in sorted(involved_dims):
        nodes.append({
            "type": "scoring_dimension",
            "id": dim,
            "name": get_scoring_dim_name(dim),
            "agent": "credit",
        })

    # ---- 6. summary 汇总 ----
    summary = _compute_summary(
        gap_materials=gap_materials,
        section_severity=section_severity,
        affects_edges=affects_edges,
        involved_dims=involved_dims,
    )

    # ---- 7. 时间戳 (CST · UTC+8 · 与既有 audit log 风格一致) ----
    if now is None:
        now = datetime.now(timezone(timedelta(hours=8)))
    generated_at = now.isoformat(timespec="seconds")

    return {
        "graph_version": GRAPH_VERSION,
        "report_id": report_id,
        "generated_at": generated_at,
        "nodes": nodes,
        "edges": provides_edges + affects_edges,
        "summary": summary,
    }


# ============================================================================
# Summary 汇总
# ============================================================================

def _compute_summary(
    *,
    gap_materials: list[dict],
    section_severity: dict[str, str],
    affects_edges: list[dict],
    involved_dims: set[str],
) -> dict[str, Any]:
    """汇总 missing 数 / blocking section 数 / max_score_impact / 受影响 dim list."""
    blocking_count = sum(1 for sev in section_severity.values() if sev == "blocking")
    advisory_count = sum(1 for sev in section_severity.values() if sev == "advisory")
    # max_score_impact = 所有 affects edges 的 impact_magnitude 累加 (上限 100)
    total_impact = sum(e.get("impact_magnitude", 0) for e in affects_edges)
    max_score_impact = max(0, min(100, total_impact))
    return {
        "missing_material_count": sum(
            1 for m in gap_materials if (m.get("status") or "").lower() == "missing"
        ),
        "partial_material_count": sum(
            1 for m in gap_materials if (m.get("status") or "").lower() == "partial"
        ),
        "blocking_section_count": blocking_count,
        "advisory_section_count": advisory_count,
        "max_score_impact": max_score_impact,
        "affected_scoring_dimensions": sorted(involved_dims),
    }


# ============================================================================
# Section impact 反向查询 (test + frontend MaterialPanel 用)
# ============================================================================

def section_impact_summary(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """从 graph 提"每 section 受影响概览" map · 给 frontend MaterialPanel 用.

    Returns:
        {section_id: {"affected_fields": [...], "severity": "blocking"|"advisory",
                      "score_impact_by_dim": {dim_id: magnitude}}}
    """
    out: dict[str, dict[str, Any]] = {}
    for edge in graph.get("edges", []):
        if edge.get("type") == "provides":
            sid = edge.get("to_id")
            if not sid:
                continue
            slot = out.setdefault(sid, {
                "affected_fields": [],
                "severity": "advisory",
                "score_impact_by_dim": {},
            })
            slot["affected_fields"] = sorted(set(
                slot["affected_fields"] + list(edge.get("affected_fields") or [])
            ))
            # blocking 覆盖 advisory · advisory 不覆盖 blocking
            if edge.get("severity") == "blocking":
                slot["severity"] = "blocking"
        elif edge.get("type") == "affects":
            sid = edge.get("from_id")
            dim = edge.get("to_id")
            mag = edge.get("impact_magnitude", 0)
            if not sid or not dim:
                continue
            slot = out.setdefault(sid, {
                "affected_fields": [],
                "severity": "advisory",
                "score_impact_by_dim": {},
            })
            slot["score_impact_by_dim"][dim] = mag
    return out


# ============================================================================
# Public entry: build from v16 done summary
# ============================================================================

def build_graph_from_v16_summary(
    v16_summary: dict[str, Any],
    *,
    material_gap_inputs: dict[str, Any] | None = None,
    report_id: str = "",
) -> dict[str, Any] | None:
    """v16_runner._run_v16_in_thread 注入 done_payload 前调本函数.

    优先级:
    1. material_gap_inputs 显式传入 (mock / fixture path · 由 mock_fixtures
       从 scenarios/<id>.json 加载)
    2. 否则从 v16_summary 推断 (real path · 现 v16 主管线无显式 material status ·
       Sprint 1 暂返 None · Phase B-3 fix-forward 接 material_kb scan output)

    Returns: graph dict 或 None (real path Sprint 1 · 不破 done_payload 既有形态)
    """
    if material_gap_inputs:
        return build_graph(material_gap_inputs, report_id=report_id)
    # Sprint 1 real path: v16_summary 无显式 material_status · 返 None
    # Phase B-3 fix-forward: 接 material_kb_scan_output 推断 missing/partial
    return None
