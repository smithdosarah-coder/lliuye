# -*- coding: utf-8 -*-
"""
evaluation.runner.adapters.agent5_compliance — Agent5 合规巡检评估 adapter

B1 首轮 scope:
  - 无 runtime dump · 无人工 gold 政策条款集 · 无冲突真值集
  - 10 条指标全部 pending, method=manual, 标注具体依赖项
  - verdict → PARTIAL (base_evaluator 自动)

Phase 2 接入:
  - 消费 agent_compliance.policy_scanner runtime dump (解析条款 + 冲突点 + 证据链)
  - 业务方提供 gold 条款集 + 已知冲突清单 (policy_coverage / conflict_recall)
  - 缺陷分类真值 (defect_classification_accuracy)

Artifact 协议 (预留):
  run.artifacts[0] 为 runtime dump JSON · 格式:
    {
      "policy_file": "...",
      "extracted_clauses": [{"clause_id": "...", "text": "..."}],
      "gold_clauses": [{"clause_id": "...", "text": "..."}],
      "conflict_items": [{"policy_anchor": "...", "business_anchor": "...",
                          "severity": "严重|重要|一般", "suggestion": "...",
                          "evidence": [...]}],
      "gold_conflicts": [...],
      "gold_severity_map": {conflict_id: severity},
      "tool_calls": {"total": ..., "success": ...}
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..base_evaluator import REPO_ROOT, BaseEvaluator
from ..registry import register_evaluator
from ..schemas import EvalRun, MetricOutcome


DEFAULT_RUNTIME = REPO_ROOT / "evaluation" / "manual" / "5_latest.json"


@register_evaluator("compliance")
class Agent5ComplianceEvaluator(BaseEvaluator):
    agent_id = "compliance"
    config_name = "agent5_compliance.yaml"

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        if run.artifacts:
            art_path = Path(run.artifacts[0])
            if not art_path.is_absolute():
                art_path = REPO_ROOT / art_path
        elif DEFAULT_RUNTIME.exists():
            art_path = DEFAULT_RUNTIME
        else:
            return {
                "artifact_path": None,
                "error": "no runtime dump",
                "conflict_items": [],
                "extracted_clauses": [],
                "gold_clauses": [],
                "gold_conflicts": [],
                "gold_severity_map": {},
                "tool_calls": {},
            }

        try:
            payload = json.loads(art_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {
                "artifact_path": str(art_path),
                "error": f"load error: {e}",
                "conflict_items": [],
                "extracted_clauses": [],
                "gold_clauses": [],
                "gold_conflicts": [],
                "gold_severity_map": {},
                "tool_calls": {},
            }

        return {
            "artifact_path": str(art_path),
            "conflict_items": payload.get("conflict_items") or [],
            "extracted_clauses": payload.get("extracted_clauses") or [],
            "gold_clauses": payload.get("gold_clauses") or [],
            "gold_conflicts": payload.get("gold_conflicts") or [],
            "gold_severity_map": payload.get("gold_severity_map") or {},
            "tool_calls": payload.get("tool_calls") or {},
        }

    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        conflict_items: list[dict] = artifacts.get("conflict_items") or []
        tool_calls: dict = artifacts.get("tool_calls") or {}
        art_path = artifacts.get("artifact_path")

        out: list[MetricOutcome] = []

        if conflict_items:
            # field_completeness (policy_anchor/business_anchor/severity/suggestion)
            required = ("policy_anchor", "business_anchor", "severity", "suggestion")
            filled = sum(
                1 for c in conflict_items
                if all(c.get(k) not in (None, "", []) for k in required)
            )
            out.append(
                self.mark(
                    "field_completeness",
                    filled / len(conflict_items),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{filled}/{len(conflict_items)} 冲突项 4 键完整",
                    kind="common",
                )
            )
            # task_completion_rate — 1.0 if conflict list produced
            out.append(
                self.mark(
                    "task_completion_rate",
                    1.0,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{len(conflict_items)} 冲突点产出",
                    kind="common",
                )
            )
            # evidence_rate
            with_both = sum(
                1 for c in conflict_items
                if c.get("policy_anchor") and c.get("business_anchor")
            )
            out.append(
                self.mark(
                    "evidence_rate",
                    with_both / len(conflict_items),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{with_both}/{len(conflict_items)} 双锚齐全",
                    kind="common",
                )
            )
            # hallucination_rate — anchor 未匹配到原文 policy 的占比 (需 gold 原文, pending)
            out.append(
                self._pending(
                    "hallucination_rate",
                    "common",
                    "pending: 需政策/制度原文库做 anchor 可解析性校验",
                )
            )
        else:
            for n in ("field_completeness", "task_completion_rate", "evidence_rate", "hallucination_rate"):
                out.append(self._pending(n, "common", "无 runtime dump · 待 agent_compliance.policy_scanner 埋点"))

        # tool_success_rate
        tc_total = tool_calls.get("total") or 0
        tc_success = tool_calls.get("success") or 0
        if tc_total > 0:
            out.append(
                self.mark(
                    "tool_success_rate",
                    tc_success / tc_total,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{tc_success}/{tc_total} 工具调用成功",
                    kind="common",
                )
            )
        else:
            out.append(self._pending("tool_success_rate", "common", "无 tool_calls 元数据"))

        return out

    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        extracted: list[dict] = artifacts.get("extracted_clauses") or []
        gold_clauses: list[dict] = artifacts.get("gold_clauses") or []
        conflict_items: list[dict] = artifacts.get("conflict_items") or []
        gold_conflicts: list[dict] = artifacts.get("gold_conflicts") or []
        gold_severity_map: dict = artifacts.get("gold_severity_map") or {}
        art_path = artifacts.get("artifact_path")

        out: list[MetricOutcome] = []

        # policy_coverage — extracted 条款 recall over gold
        if extracted and gold_clauses:
            extracted_ids = {c.get("clause_id") for c in extracted}
            hit = sum(1 for g in gold_clauses if g.get("clause_id") in extracted_ids)
            out.append(
                self.mark(
                    "policy_coverage",
                    hit / len(gold_clauses),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{hit}/{len(gold_clauses)} gold clauses 被抽取",
                )
            )
        else:
            out.append(
                self._pending(
                    "policy_coverage",
                    "domain",
                    "pending: 需人工 gold 条款集 + agent5 runtime clause 抽取产出",
                )
            )

        # conflict_recall
        if conflict_items and gold_conflicts:
            # 用 (policy_anchor, business_anchor) tuple 作为冲突标识
            detected_keys = {
                (c.get("policy_anchor"), c.get("business_anchor")) for c in conflict_items
            }
            hit = sum(
                1
                for g in gold_conflicts
                if (g.get("policy_anchor"), g.get("business_anchor")) in detected_keys
            )
            out.append(
                self.mark(
                    "conflict_recall",
                    hit / len(gold_conflicts),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{hit}/{len(gold_conflicts)} gold conflicts 被识别",
                )
            )
        else:
            out.append(
                self._pending(
                    "conflict_recall",
                    "domain",
                    "pending: 需业务方已知冲突真值集 (gold_conflicts)",
                )
            )

        # defect_classification_accuracy
        if conflict_items and gold_severity_map:
            agree = 0
            countable = 0
            for c in conflict_items:
                cid = c.get("conflict_id")
                if cid in gold_severity_map:
                    countable += 1
                    if c.get("severity") == gold_severity_map[cid]:
                        agree += 1
            if countable:
                out.append(
                    self.mark(
                        "defect_classification_accuracy",
                        agree / countable,
                        method="deterministic",
                        evidence=[art_path] if art_path else [],
                        note=f"{agree}/{countable} severity 与 gold 一致",
                    )
                )
            else:
                out.append(
                    self._pending(
                        "defect_classification_accuracy",
                        "domain",
                        "pending: conflict_items 无 conflict_id 与 gold_severity_map 匹配",
                    )
                )
        else:
            out.append(
                self._pending(
                    "defect_classification_accuracy",
                    "domain",
                    "pending: 需人工缺陷严重度标注真值 (gold_severity_map)",
                )
            )

        # terminology_compliance — 需监管用语表 + 文本抽取
        out.append(
            self._pending(
                "terminology_compliance",
                "domain",
                "pending: Phase 2 需监管合规术语表 v1.0 + 冲突描述文本抽取",
            )
        )

        # evidence_completeness — 3 要素 (policy_anchor + business_anchor + diff_note)
        if conflict_items:
            with_3 = sum(
                1
                for c in conflict_items
                if c.get("policy_anchor")
                and c.get("business_anchor")
                and (c.get("diff_note") or c.get("evidence"))
            )
            out.append(
                self.mark(
                    "evidence_completeness",
                    with_3 / len(conflict_items),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{with_3}/{len(conflict_items)} 冲突点含 3 要素 (policy+business+diff/evidence)",
                )
            )
        else:
            out.append(
                self._pending(
                    "evidence_completeness",
                    "domain",
                    "无 runtime dump · 待 agent5 埋点",
                )
            )

        return out

    def _pending(self, name: str, kind: str, reason: str) -> MetricOutcome:
        return MetricOutcome(
            name=name,
            value=None,
            target=self._lookup_target(name, kind) or "n/a",
            passed=None,
            method="manual",
            note=reason,
        )


# ---------------------------------------------------------------------------
# Batch 2 · policy_compare metrics plug-in (integration test 产物消费)
# ---------------------------------------------------------------------------

DEFAULT_POLICY_COMPARE_METRICS = REPO_ROOT / "evaluation" / "manual" / "5_policy_compare_metrics.json"


def compute_policy_compare_metrics(
    run_dir: Path | str | None = None,
) -> list[MetricOutcome]:
    """从 Task C integration test 的 artifact 里解析 coverage / false_positive_rate。

    artifact 路径:
        run_dir/5_policy_compare_metrics.json (若 run_dir 指定)
        否则 REPO_ROOT/evaluation/manual/5_policy_compare_metrics.json
    """
    if run_dir is not None:
        art_path = Path(run_dir) / "5_policy_compare_metrics.json"
    else:
        art_path = DEFAULT_POLICY_COMPARE_METRICS

    spec = (
        ("coverage", ">= 0.6", lambda v: v >= 0.6),
        ("false_positive_rate", "<= 0.3", lambda v: v <= 0.3),
    )

    if not art_path.exists():
        return [
            MetricOutcome(
                name=name, value=None, target=target, passed=None,
                method="manual",
                note=f"pending: artifact 缺失 {art_path}",
            )
            for name, target, _ in spec
        ]

    try:
        payload = json.loads(art_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [
            MetricOutcome(
                name=name, value=None, target=target, passed=None,
                method="manual",
                note=f"pending: artifact 解析失败 {e}",
            )
            for name, target, _ in spec
        ]

    out: list[MetricOutcome] = []
    for name, target, gate in spec:
        v = payload.get(name)
        if v is None:
            out.append(MetricOutcome(
                name=name, value=None, target=target, passed=None,
                method="manual",
                note=f"pending: artifact 内缺字段 {name}",
            ))
            continue
        out.append(MetricOutcome(
            name=name, value=float(v), target=target, passed=bool(gate(v)),
            method="deterministic",
            evidence=[str(art_path)],
            note=f"computed by tests/agent_compliance/test_policy_compare_integration.py",
        ))
    return out
