# -*- coding: utf-8 -*-
"""
evaluation.runner.adapters.agent2_riskctrl — Agent2 风控策略评估 adapter

Phase 0 确定性指标覆盖:
  [common]
    - task_completion_rate    — outputs_successful / inputs_total
    - evidence_rate           — 带回测字段(ks/approve_rate/bad_rate)的规则占比
    - hallucination_rate      — 规则字段 ∉ 样本 schema 的比例
    - tool_success_rate       — 回测/指标工具调用 success / total
  [domain]
    - false_positive_rate     — FP / (FP + TN)
    - ks_improvement          — Phase C stub (需人工基线对照组)
    - rule_interpretability   — Phase C stub (需人工评分或 LLM-judge)

Artifact 约定:
  run.artifacts 为空 → 默认读 agent_riskctrl/tests/fixtures/baseline_v1/
  run.artifacts[0] 为目录 → 以该目录为 fixture 根
  run.artifacts[0] 为 .json → 以其所在目录为 fixture 根
Fixture 根下需含:
  rules.json         — {inputs_total, outputs_successful, ruleset: {rules: [...]}}
  sample_schema.json — {columns: [...], label_column: str}
  backtest.json      — {tool_calls: [{status}], confusion_matrix: {TP,FP,TN,FN}}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..base_evaluator import REPO_ROOT, BaseEvaluator
from ..registry import register_evaluator
from ..schemas import EvalRun, MetricOutcome


RUNTIME_LATEST_DIR = REPO_ROOT / "evaluation" / "runtime" / "2_latest"
FIXTURE_BASELINE_V1_DIR = REPO_ROOT / "agent_riskctrl" / "tests" / "fixtures" / "baseline_v1"
EVIDENCE_KEYS = ("ks", "approve_rate", "bad_rate")


def _read_json(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _resolve_fixture_dir(run: EvalRun) -> tuple[Path, str]:
    """三级 fallback:
      1. run.artifacts[0] 显式指定（dir 或 file 所在 dir）
      2. evaluation/runtime/2_latest/ （scripts/run_agent2_baseline.py 产物）
      3. agent_riskctrl/tests/fixtures/baseline_v1/ （回归锚，非当期生产基线）

    Returns: (dir, source_tag) — source_tag 入 errors/note 便于 review 溯源
    """
    if run.artifacts:
        first = Path(run.artifacts[0])
        if not first.is_absolute():
            first = REPO_ROOT / first
        return (first if first.is_dir() else first.parent, "artifacts_arg")
    if RUNTIME_LATEST_DIR.is_dir() and (RUNTIME_LATEST_DIR / "rules.json").exists():
        return (RUNTIME_LATEST_DIR, "runtime_latest")
    return (FIXTURE_BASELINE_V1_DIR, "fixture_baseline_v1_regression_anchor")


@register_evaluator("riskctrl")
class Agent2RiskCtrlEvaluator(BaseEvaluator):
    agent_id = "riskctrl"
    config_name = "agent2_riskctrl.yaml"

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        fx_dir, source_tag = _resolve_fixture_dir(run)
        rules_path = fx_dir / "rules.json"
        schema_path = fx_dir / "sample_schema.json"
        backtest_path = fx_dir / "backtest.json"

        artifacts: dict[str, Any] = {
            "fixture_dir": str(fx_dir),
            "fixture_source": source_tag,
            "rules_path": str(rules_path),
            "schema_path": str(schema_path),
            "backtest_path": str(backtest_path),
            "errors": [],
        }

        for key, path in (
            ("rules", rules_path),
            ("schema", schema_path),
            ("backtest", backtest_path),
        ):
            if not path.exists():
                artifacts["errors"].append(f"{key} missing: {path}")
                artifacts[key] = None
                continue
            try:
                artifacts[key] = _read_json(path)
            except (json.JSONDecodeError, OSError) as e:
                artifacts["errors"].append(f"{key} load error: {e}")
                artifacts[key] = None
        return artifacts

    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        rules_doc = artifacts.get("rules") or {}
        schema_doc = artifacts.get("schema") or {}
        backtest_doc = artifacts.get("backtest") or {}

        rules: list[dict] = (rules_doc.get("ruleset") or {}).get("rules") or []
        schema_columns = set(schema_doc.get("columns") or [])
        rules_path = artifacts.get("rules_path")
        schema_path = artifacts.get("schema_path")
        backtest_path = artifacts.get("backtest_path")

        out: list[MetricOutcome] = []

        # --- task_completion_rate ---
        inputs_total = rules_doc.get("inputs_total")
        outputs_successful = rules_doc.get("outputs_successful")
        if isinstance(inputs_total, int) and inputs_total > 0 and isinstance(outputs_successful, int):
            tc_rate = max(0.0, min(1.0, outputs_successful / inputs_total))
            out.append(
                self.mark(
                    "task_completion_rate",
                    tc_rate,
                    method="deterministic",
                    evidence=[rules_path] if rules_path else [],
                    note=f"{outputs_successful}/{inputs_total} DSL 输出成功",
                    kind="common",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="task_completion_rate",
                    value=None,
                    target=self._lookup_target("task_completion_rate", "common") or "n/a",
                    passed=None,
                    method="deterministic",
                    note="rules.json 缺 inputs_total / outputs_successful",
                )
            )

        # --- evidence_rate ---
        if rules:
            with_evidence = sum(
                1
                for r in rules
                if isinstance(r.get("backtest"), dict)
                and any(k in r["backtest"] for k in EVIDENCE_KEYS)
            )
            er = with_evidence / len(rules)
            out.append(
                self.mark(
                    "evidence_rate",
                    er,
                    method="deterministic",
                    evidence=[rules_path] if rules_path else [],
                    note=f"{with_evidence}/{len(rules)} 规则含 ks/approve_rate/bad_rate",
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
                    method="deterministic",
                    note="rules.json 无 rules",
                )
            )

        # --- hallucination_rate ---
        total_fields = 0
        hallucinated = 0
        for r in rules:
            for c in r.get("conditions") or []:
                f = str(c.get("field") or "").strip()
                if not f:
                    continue
                total_fields += 1
                if schema_columns and f not in schema_columns:
                    hallucinated += 1
        if total_fields > 0 and schema_columns:
            hr = hallucinated / total_fields
            out.append(
                self.mark(
                    "hallucination_rate",
                    hr,
                    method="deterministic",
                    evidence=[schema_path] if schema_path else [],
                    note=f"{hallucinated}/{total_fields} 字段 ∉ schema.columns",
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
                    method="deterministic",
                    note="规则字段 / schema.columns 为空",
                )
            )

        # --- tool_success_rate ---
        tool_calls = backtest_doc.get("tool_calls") or []
        if tool_calls:
            ok = sum(1 for t in tool_calls if str(t.get("status", "")).lower() == "success")
            tsr = ok / len(tool_calls)
            out.append(
                self.mark(
                    "tool_success_rate",
                    tsr,
                    method="deterministic",
                    evidence=[backtest_path] if backtest_path else [],
                    note=f"{ok}/{len(tool_calls)} 工具调用成功",
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
                    method="deterministic",
                    note="backtest.json 无 tool_calls",
                )
            )

        return out

    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        backtest_doc = artifacts.get("backtest") or {}
        rules_doc = artifacts.get("rules") or {}
        backtest_path = artifacts.get("backtest_path")
        rules_path = artifacts.get("rules_path")

        out: list[MetricOutcome] = []

        # --- false_positive_rate ---
        cm = backtest_doc.get("confusion_matrix") or {}
        fp = cm.get("FP")
        tn = cm.get("TN")
        if isinstance(fp, (int, float)) and isinstance(tn, (int, float)) and (fp + tn) > 0:
            fpr = fp / (fp + tn)
            out.append(
                self.mark(
                    "false_positive_rate",
                    fpr,
                    method="deterministic",
                    evidence=[backtest_path] if backtest_path else [],
                    note=f"FP={fp}, TN={tn}, FPR={fpr:.4f}",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="false_positive_rate",
                    value=None,
                    target=self._lookup_target("false_positive_rate", "domain") or "n/a",
                    passed=None,
                    method="deterministic",
                    note="backtest.confusion_matrix 缺 FP / TN",
                )
            )

        # --- per_rule_fpr_spread (A-019 @ c947906: 总体方差 σ² ≤ 0.03) ---
        # fprs 从 rules.json 的每条规则 backtest.FP/TN 取；FP+TN=0 → N/A skip。
        # 少于 2 条有效规则 → spread 不适用（value=None, pending-style passed=None）。
        rules: list[dict] = (rules_doc.get("ruleset") or {}).get("rules") or []
        fprs: list[float] = []
        skipped_rule_ids: list[str] = []
        for r in rules:
            bt = r.get("backtest") or {}
            fp_i = bt.get("FP")
            tn_i = bt.get("TN")
            if (
                isinstance(fp_i, (int, float))
                and isinstance(tn_i, (int, float))
                and (fp_i + tn_i) > 0
            ):
                fprs.append(fp_i / (fp_i + tn_i))
            else:
                skipped_rule_ids.append(str(r.get("rule_id") or ""))

        if len(fprs) < 2:
            out.append(
                MetricOutcome(
                    name="per_rule_fpr_spread",
                    value=None,
                    target=self._lookup_target("per_rule_fpr_spread", "domain") or "n/a",
                    passed=None,
                    method="deterministic",
                    note=f"有效规则不足 2 条（共 {len(rules)} 规则，skip={len(skipped_rule_ids)}）；spread 不适用",
                )
            )
        else:
            mean = sum(fprs) / len(fprs)
            variance = sum((x - mean) ** 2 for x in fprs) / len(fprs)  # 总体方差，A-019 §公式
            out.append(
                self.mark(
                    "per_rule_fpr_spread",
                    variance,
                    method="deterministic",
                    evidence=[rules_path] if rules_path else [],
                    note=(
                        f"σ²={variance:.4f} over {len(fprs)} reject-rules FPR "
                        f"(mean={mean:.4f}, skip={len(skipped_rule_ids)} N/A 规则)"
                    ),
                )
            )

        # --- pending (A-013 白名单) · ks_improvement ---
        # note 字段与 yaml baseline.pending_reason 一字节级同义（便于 grep 追溯）
        out.append(
            MetricOutcome(
                name="ks_improvement",
                value=None,
                target=self._lookup_target("ks_improvement", "domain") or "n/a",
                passed=None,
                method="manual",
                note="Phase-2 runtime baseline_ruleset 对照组依赖 + LLM-judge 未实装",
            )
        )

        # --- pending (A-013 白名单) · rule_interpretability ---
        out.append(
            MetricOutcome(
                name="rule_interpretability",
                value=None,
                target=self._lookup_target("rule_interpretability", "domain") or "n/a",
                passed=None,
                method="manual",
                note="Phase-2 runtime baseline_ruleset 对照组依赖 + LLM-judge 未实装",
            )
        )

        return out
