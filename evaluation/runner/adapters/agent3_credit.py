# -*- coding: utf-8 -*-
"""
evaluation.runner.adapters.agent3_credit — Agent3 授信决策评估 adapter

Phase 0 可确定性计算的指标 (消费 agent_credit/mock_data/):
  [common]
    - field_completeness   — 结构化字段 (composite_score/risk_grade/decision 等 10 键) 非空率
    - task_completion_rate — cases with full scoring pipeline (composite_score + decision) / total
    - evidence_rate        — cases with decision_reason 非空 / total (审批理由 = 证据)
    - hallucination_rate   — 自相矛盾率 (decision==拒绝 但 approved_amount > 0 等)
    - tool_success_rate    — stub (mock cases 无 runtime tool trace)
  [domain]
    - redline_detection_accuracy — decision∈{拒绝,有条件批准} 与 hit_red_lines 非空的一致率
    - credit_limit_reasonability — median |log10(requested/approved)| over approved>0

Phase 2 pending (需真值 / LLM-judge / financial_analyzer runtime):
  - ratio_calc_consistency / score_human_agreement / terminology_compliance

Artifact 协议:
  run.artifacts[0] 为 corporate_cases.json 路径 → 直接消费
  run.artifacts 为空 → 默认读 agent_credit/mock_data/corporate_cases.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ..base_evaluator import REPO_ROOT, BaseEvaluator
from ..registry import register_evaluator
from ..schemas import EvalRun, MetricOutcome


DEFAULT_FIXTURE = REPO_ROOT / "agent_credit" / "mock_data" / "corporate_cases.json"

REQUIRED_CASE_KEYS = (
    "case_id",
    "company_name",
    "industry",
    "composite_score",
    "risk_grade",
    "requested_amount",
    "approved_amount",
    "decision",
    "hit_red_lines",
    "decision_reason",
)

# decision 值集合 (用于 hallucination 判定 · decision 与 approved_amount 自相矛盾)
DECISION_REJECT = "拒绝"
DECISION_APPROVE = "批准"
DECISION_COND = "有条件批准"


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    ordered = sorted(xs)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


@register_evaluator("credit")
class Agent3CreditEvaluator(BaseEvaluator):
    agent_id = "credit"
    config_name = "agent3_credit.yaml"

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        if run.artifacts:
            art_path = Path(run.artifacts[0])
            if not art_path.is_absolute():
                art_path = REPO_ROOT / art_path
        else:
            art_path = DEFAULT_FIXTURE

        if not art_path.exists():
            return {
                "artifact_path": str(art_path),
                "error": f"artifact missing: {art_path}",
                "cases": [],
            }

        try:
            cases = json.loads(art_path.read_text(encoding="utf-8"))
            if not isinstance(cases, list):
                cases = []
        except (json.JSONDecodeError, OSError) as e:
            return {
                "artifact_path": str(art_path),
                "error": f"load error: {e}",
                "cases": [],
            }

        return {
            "artifact_path": str(art_path),
            "cases": cases,
        }

    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        cases: list[dict] = artifacts.get("cases") or []
        art_path = artifacts.get("artifact_path")
        out: list[MetricOutcome] = []
        total = len(cases) or 1

        # --- field_completeness ---
        if cases:
            filled_per_case = [
                sum(1 for k in REQUIRED_CASE_KEYS if c.get(k) not in (None, "", []))
                for c in cases
            ]
            completeness = sum(filled_per_case) / (len(cases) * len(REQUIRED_CASE_KEYS))
            out.append(
                self.mark(
                    "field_completeness",
                    completeness,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{sum(filled_per_case)}/{len(cases)*len(REQUIRED_CASE_KEYS)} 字段非空 ({len(REQUIRED_CASE_KEYS)} 键×{len(cases)} cases)",
                    kind="common",
                )
            )
        else:
            out.append(self._stub_metric_with_target("field_completeness", "common", "no cases"))

        # --- task_completion_rate (有 composite_score + decision) ---
        completed = sum(
            1
            for c in cases
            if isinstance(c.get("composite_score"), (int, float)) and c.get("decision")
        )
        out.append(
            self.mark(
                "task_completion_rate",
                completed / total if cases else 0.0,
                method="deterministic",
                evidence=[art_path] if art_path else [],
                note=f"{completed}/{len(cases)} cases 带 composite_score + decision",
                kind="common",
            )
            if cases
            else self._stub_metric_with_target("task_completion_rate", "common", "no cases")
        )

        # --- evidence_rate (decision_reason 非空) ---
        if cases:
            with_reason = sum(1 for c in cases if (c.get("decision_reason") or "").strip())
            out.append(
                self.mark(
                    "evidence_rate",
                    with_reason / total,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{with_reason}/{len(cases)} cases 带 decision_reason",
                    kind="common",
                )
            )
        else:
            out.append(self._stub_metric_with_target("evidence_rate", "common", "no cases"))

        # --- hallucination_rate (自相矛盾: decision=拒绝 但 approved_amount>0, 或 decision=批准 但 approved_amount=0) ---
        if cases:
            contradictions = 0
            for c in cases:
                dec = c.get("decision")
                amt = c.get("approved_amount")
                if not isinstance(amt, (int, float)):
                    continue
                if dec == DECISION_REJECT and amt > 0:
                    contradictions += 1
                elif dec == DECISION_APPROVE and amt <= 0:
                    contradictions += 1
            hr = contradictions / total
            out.append(
                self.mark(
                    "hallucination_rate",
                    hr,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{contradictions}/{len(cases)} cases decision↔approved_amount 自相矛盾",
                    kind="common",
                )
            )
        else:
            out.append(self._stub_metric_with_target("hallucination_rate", "common", "no cases"))

        # --- tool_success_rate stub (mock data 无 tool trace) ---
        out.append(
            MetricOutcome(
                name="tool_success_rate",
                value=None,
                target=self._lookup_target("tool_success_rate", "common") or "n/a",
                passed=None,
                method="manual",
                note="pending: mock cases 无 runtime tool_calls 元数据 · 待 Agent3 api.py 埋点后补",
            )
        )

        return out

    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        cases: list[dict] = artifacts.get("cases") or []
        art_path = artifacts.get("artifact_path")
        out: list[MetricOutcome] = []

        # --- redline_detection_accuracy (decision∈{拒绝,有条件批准} ⟺ hit_red_lines 非空 的一致率) ---
        # 严格 agreement: (拒绝 且 红线) 或 (批准 且 无红线) 视为"识别准"；有条件批准是灰区, 列入分母但不算准
        if cases:
            strict_agree = 0
            countable = 0
            for c in cases:
                dec = c.get("decision")
                rls = c.get("hit_red_lines") or []
                has_rl = len(rls) > 0
                if dec == DECISION_REJECT:
                    countable += 1
                    if has_rl:
                        strict_agree += 1
                elif dec == DECISION_APPROVE:
                    countable += 1
                    if not has_rl:
                        strict_agree += 1
                # 有条件批准不计入分母 (灰区)
            accuracy = strict_agree / countable if countable else 0.0
            out.append(
                self.mark(
                    "redline_detection_accuracy",
                    accuracy,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"{strict_agree}/{countable} (拒绝↔红线 或 批准↔无红线) · 有条件批准灰区剔除",
                )
            )
        else:
            out.append(self._stub_metric_with_target("redline_detection_accuracy", "domain", "no cases"))

        # --- credit_limit_reasonability (median |log10(requested/approved)| over approved>0) ---
        deviations: list[float] = []
        for c in cases:
            req = c.get("requested_amount")
            app = c.get("approved_amount")
            if (
                isinstance(req, (int, float))
                and isinstance(app, (int, float))
                and req > 0
                and app > 0
            ):
                deviations.append(abs(math.log10(req / app)))
        if deviations:
            med = _median(deviations)
            out.append(
                self.mark(
                    "credit_limit_reasonability",
                    med,
                    method="deterministic",
                    evidence=[art_path] if art_path else [],
                    note=f"median |log10(req/app)| = {med:.4f} over {len(deviations)} approved>0 cases",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="credit_limit_reasonability",
                    value=None,
                    target=self._lookup_target("credit_limit_reasonability", "domain") or "n/a",
                    passed=None,
                    method="heuristic",
                    note="无 approved>0 cases · 偏差不可计算",
                )
            )

        # --- pending: ratio_calc_consistency (需 Agent3 runtime 比率输出 vs financial_analyzer) ---
        out.append(
            MetricOutcome(
                name="ratio_calc_consistency",
                value=None,
                target=self._lookup_target("ratio_calc_consistency", "domain") or "n/a",
                passed=None,
                method="manual",
                note="pending: 需 Agent3 runtime 比率输出 + financial_analyzer 对照 · code-urgent §3.1 接入后可算",
            )
        )

        # --- pending: score_human_agreement (需人工复核真值) ---
        out.append(
            MetricOutcome(
                name="score_human_agreement",
                value=None,
                target=self._lookup_target("score_human_agreement", "domain") or "n/a",
                passed=None,
                method="manual",
                note="pending: Phase 2 需业务方人工复核真值集",
            )
        )

        # --- pending: terminology_compliance (需术语表 + 文本抽取) ---
        out.append(
            MetricOutcome(
                name="terminology_compliance",
                value=None,
                target=self._lookup_target("terminology_compliance", "domain") or "n/a",
                passed=None,
                method="manual",
                note="pending: Phase 2 需信贷术语表 v1.0 + 审批意见文本抽取",
            )
        )

        return out

    def _stub_metric_with_target(self, name: str, kind: str, reason: str) -> MetricOutcome:
        return MetricOutcome(
            name=name,
            value=None,
            target=self._lookup_target(name, kind) or "n/a",
            passed=None,
            method="heuristic",
            note=reason,
        )
