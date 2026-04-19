# -*- coding: utf-8 -*-
"""
evaluation.runner.adapters.agent4_alert — Agent4 贷中预警评估 adapter

Phase 0 只覆盖可确定性计算的指标:
  [common]
    - task_completion_rate — 100 家客户扫描完成率
    - evidence_rate        — 红/黄灯客户证据字段非空率
    - hallucination_rate   — 白名单外 entity_id 占比（虚构客户/事件）
    - tool_success_rate    — 工具调用 stub success/total
  [domain]
    - grade_distribution_sanity — 红 < 5% 且 绿 > 70% → 1.0 / 0.0
    - scan_latency_p95          — 单次扫描耗时 P95（分钟）

Phase C 指标（cross_hit_precision / recall_on_known_bad）本阶段返回
value=None, method="manual"，照 agent6_report.py 的 stub 模式。不假装能跑。

Fixture 协议（agent_alert/tests/fixtures/phase0_scan_sample.json）:
  {
    "whitelist_entity_ids": [...],
    "customers": [
      {"entity_id": "E0001", "grade": "red|yellow|green",
       "evidence": [...], "scan_time_ms": 450.0, "status": "completed"},
      ...
    ],
    "tool_calls": {"total": 450, "success": 435}
  }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..base_evaluator import REPO_ROOT, BaseEvaluator
from ..registry import register_evaluator
from ..schemas import EvalRun, MetricOutcome


DEFAULT_RUNTIME = REPO_ROOT / "evaluation" / "manual" / "4_20260419.yaml"
DEFAULT_FIXTURE = REPO_ROOT / "agent_alert" / "tests" / "fixtures" / "phase0_scan_sample.json"


def _load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            return yaml.safe_load(f) or {}
        return json.load(f)


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(int(len(ordered) * 0.95), len(ordered) - 1)
    return ordered[idx]


@register_evaluator("alert")
class Agent4AlertEvaluator(BaseEvaluator):
    agent_id = "alert"
    config_name = "agent4_alert.yaml"

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        # 优先级：run.artifacts[0] > DEFAULT_RUNTIME (runtime dump) > DEFAULT_FIXTURE (回归锚)
        if run.artifacts:
            art_path = Path(run.artifacts[0])
            if not art_path.is_absolute():
                art_path = REPO_ROOT / art_path
        elif DEFAULT_RUNTIME.exists():
            art_path = DEFAULT_RUNTIME
        else:
            art_path = DEFAULT_FIXTURE

        if not art_path.exists():
            return {
                "artifact_path": str(art_path),
                "error": f"artifact missing: {art_path}",
                "customers": [],
                "whitelist": [],
                "tool_calls": {},
            }

        payload = _load_payload(art_path)

        return {
            "artifact_path": str(art_path),
            "customers": payload.get("customers", []),
            "whitelist": payload.get("whitelist_entity_ids", []),
            "tool_calls": payload.get("tool_calls", {}),
        }

    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        customers: list[dict] = artifacts.get("customers") or []
        whitelist: list[str] = artifacts.get("whitelist") or []
        tool_calls: dict = artifacts.get("tool_calls") or {}
        art_path = artifacts.get("artifact_path")
        out: list[MetricOutcome] = []

        total = len(customers) or 1

        # --- task_completion_rate ---
        completed = sum(1 for c in customers if c.get("status") == "completed")
        out.append(
            self.mark(
                "task_completion_rate",
                completed / total if customers else 0.0,
                method="deterministic",
                evidence=[art_path] if art_path else [],
                note=f"{completed}/{len(customers)} customers status==completed",
                kind="common",
            )
        )

        # --- evidence_rate ---
        red_yellow = [c for c in customers if c.get("grade") in ("red", "yellow")]
        with_evidence = sum(1 for c in red_yellow if c.get("evidence"))
        if red_yellow:
            out.append(
                self.mark(
                    "evidence_rate",
                    with_evidence / len(red_yellow),
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{with_evidence}/{len(red_yellow)} red|yellow customers have non-empty evidence",
                    kind="common",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="evidence_rate",
                    value=None,
                    target=self._lookup_target("evidence_rate", "common") or "n/a",
                    passed=None,
                    method="heuristic",
                    note="no red/yellow customers in fixture — cannot compute",
                )
            )

        # --- hallucination_rate ---
        if whitelist:
            whitelist_set = set(whitelist)
            out_of_whitelist = sum(
                1 for c in customers if c.get("entity_id") not in whitelist_set
            )
            out.append(
                self.mark(
                    "hallucination_rate",
                    out_of_whitelist / total if customers else 0.0,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{out_of_whitelist}/{len(customers)} entity_id outside whitelist",
                    kind="common",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="hallucination_rate",
                    value=None,
                    target=self._lookup_target("hallucination_rate", "common") or "n/a",
                    passed=None,
                    method="heuristic",
                    note="no whitelist provided — cannot detect hallucination",
                )
            )

        # --- tool_success_rate ---
        tc_total = tool_calls.get("total") or 0
        tc_success = tool_calls.get("success") or 0
        if tc_total > 0:
            out.append(
                self.mark(
                    "tool_success_rate",
                    tc_success / tc_total,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{tc_success}/{tc_total} tool calls succeeded",
                    kind="common",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="tool_success_rate",
                    value=None,
                    target=self._lookup_target("tool_success_rate", "common") or "n/a",
                    passed=None,
                    method="heuristic",
                    note="no tool_calls metadata in fixture",
                )
            )

        return out

    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        customers: list[dict] = artifacts.get("customers") or []
        art_path = artifacts.get("artifact_path")
        out: list[MetricOutcome] = []

        # --- cross_hit_precision — Phase C stub ---
        out.append(
            MetricOutcome(
                name="cross_hit_precision",
                value=None,
                target=self._lookup_target("cross_hit_precision", "domain") or "n/a",
                passed=None,
                method="manual",
                note="Phase C stub — 需真实外部扫描数据 + 内部交易标注才能算",
            )
        )

        # --- recall_on_known_bad — Phase C stub ---
        out.append(
            MetricOutcome(
                name="recall_on_known_bad",
                value=None,
                target=self._lookup_target("recall_on_known_bad", "domain") or "n/a",
                passed=None,
                method="manual",
                note="Phase C stub — 需已知问题客户标注库",
            )
        )

        # --- grade_distribution_sanity ---
        if customers:
            total = len(customers)
            red = sum(1 for c in customers if c.get("grade") == "red")
            green = sum(1 for c in customers if c.get("grade") == "green")
            red_ratio = red / total
            green_ratio = green / total
            sane = red_ratio < 0.05 and green_ratio > 0.70
            # target in yaml 是 "pass", evaluate_target 不会解析, 手工打 passed
            out.append(
                MetricOutcome(
                    name="grade_distribution_sanity",
                    value=1.0 if sane else 0.0,
                    target=self._lookup_target("grade_distribution_sanity", "domain") or "pass",
                    passed=sane,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"red={red_ratio:.2%} (<5%), green={green_ratio:.2%} (>70%)",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="grade_distribution_sanity",
                    value=None,
                    target=self._lookup_target("grade_distribution_sanity", "domain") or "pass",
                    passed=None,
                    method="heuristic",
                    note="no customers — cannot compute grade distribution",
                )
            )

        # --- scan_latency_p95 (分钟) ---
        latencies_ms = [
            float(c.get("scan_time_ms", 0))
            for c in customers
            if isinstance(c.get("scan_time_ms"), (int, float))
        ]
        if latencies_ms:
            p95_ms = _p95(latencies_ms)
            p95_min = p95_ms / 60_000.0
            out.append(
                self.mark(
                    "scan_latency_p95",
                    p95_min,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"P95={p95_ms:.1f}ms ({p95_min:.4f} min) over {len(latencies_ms)} customers",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="scan_latency_p95",
                    value=None,
                    target=self._lookup_target("scan_latency_p95", "domain") or "n/a",
                    passed=None,
                    method="heuristic",
                    note="no scan_time_ms in fixture",
                )
            )

        return out
