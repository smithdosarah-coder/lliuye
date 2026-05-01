# -*- coding: utf-8 -*-
"""Phase B Sprint 2 决策 3 · per-metric PARTIAL 维度 (4-state).

per-metric:
  PASS    : value ≥ 0.95 × baseline_target (越大越好) / value ≤ 1.05 × bt (越小越好)
  PARTIAL : value ≥ 0.80 × bt (越大) / value ≤ 1.20 × bt (越小)
  FAIL    : 否则
  SKIP    : value=None 或 baseline_target 缺失

CLI exit:
  0 = 全 PASS (含 SKIP)
  1 = 任一 PARTIAL 或 FAIL
  2 = adapter 异常
  3 = blocker (--gate)
"""
from __future__ import annotations

import textwrap
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from evaluation.runner.base_evaluator import BaseEvaluator, _classify_status
from evaluation.runner.schemas import EvalRun, MetricOutcome


class _StubEvaluator(BaseEvaluator):
    agent_id = "stub"
    config_name = "_test_partial.yaml"

    def __init__(self, yaml_path: Path, fixed_values: dict[str, float | None]) -> None:
        self.config_path = yaml_path
        self.config = self._load_config()
        self._fixed = fixed_values

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        return {}

    def compute_common_metrics(self, _a) -> list[MetricOutcome]:
        return [
            self.mark(m["name"], self._fixed.get(m["name"]),
                     method="deterministic", kind="common")
            for m in self._metrics_config("common")
        ]

    def compute_domain_metrics(self, _a) -> list[MetricOutcome]:
        return [
            self.mark(m["name"], self._fixed.get(m["name"]),
                     method="deterministic", kind="domain")
            for m in self._metrics_config("domain")
        ]


def _write_yaml(tmp: Path) -> Path:
    p = tmp / "_test_partial.yaml"
    p.write_text(textwrap.dedent("""
        agent_id: stub
        baseline:
          pending_metrics: []
        metrics:
          common:
            - name: evidence_rate
              target: ">= 0.95"
              baseline_target: 0.95
            - name: hallucination_rate
              target: "<= 0.02"
              baseline_target: 0.02
          domain:
            - name: field_completeness
              target: ">= 0.90"
              baseline_target: 0.90
            - name: ratio_consistency
              target: ">= 0.99"
              baseline_target: 0.99
    """).strip(), encoding="utf-8")
    return p


@contextmanager
def _ctx_yaml():
    with TemporaryDirectory() as td:
        yield _write_yaml(Path(td))


# ---------------------------------------------------------------------------
# pure _classify_status (无 IO)
# ---------------------------------------------------------------------------

class ClassifyStatusTest(unittest.TestCase):
    def test_higher_better_pass(self):
        # 0.95 × 0.95 = 0.9025
        self.assertEqual(_classify_status(0.95, 0.95, ">= 0.95"), "PASS")
        self.assertEqual(_classify_status(0.91, 0.95, ">= 0.95"), "PASS")  # 0.95×0.95=0.9025

    def test_higher_better_partial(self):
        # 0.80 × 0.95 = 0.76 ≤ value < 0.9025
        self.assertEqual(_classify_status(0.80, 0.95, ">= 0.95"), "PARTIAL")
        self.assertEqual(_classify_status(0.78, 0.95, ">= 0.95"), "PARTIAL")

    def test_higher_better_fail(self):
        self.assertEqual(_classify_status(0.5, 0.95, ">= 0.95"), "FAIL")
        self.assertEqual(_classify_status(0.0, 0.95, ">= 0.95"), "FAIL")

    def test_lower_better_pass(self):
        # 1.05 × 0.02 = 0.021
        self.assertEqual(_classify_status(0.02, 0.02, "<= 0.02"), "PASS")
        self.assertEqual(_classify_status(0.021, 0.02, "<= 0.02"), "PASS")

    def test_lower_better_partial(self):
        # 1.05 × 0.02 = 0.021 < value ≤ 1.20 × 0.02 = 0.024
        self.assertEqual(_classify_status(0.023, 0.02, "<= 0.02"), "PARTIAL")

    def test_lower_better_fail(self):
        self.assertEqual(_classify_status(0.10, 0.02, "<= 0.02"), "FAIL")

    def test_skip_value_none(self):
        self.assertEqual(_classify_status(None, 0.95, ">= 0.95"), "SKIP")

    def test_skip_baseline_none(self):
        self.assertEqual(_classify_status(0.5, None, ">= 0.95"), "SKIP")


# ---------------------------------------------------------------------------
# end-to-end: run() populates buckets · exit codes 正确
# ---------------------------------------------------------------------------

class PartialBucketsAndExitTest(unittest.TestCase):
    def test_all_pass_exit_0(self):
        with _ctx_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.99,
                "hallucination_rate": 0.0,
                "field_completeness": 0.95,
                "ratio_consistency": 1.0,
            })
            r = ev.run(EvalRun(agent_id="stub"))
            self.assertEqual(r.partial_metrics, [])
            self.assertEqual(r.failed_metrics, [])
            self.assertEqual(r.skipped_metrics, [])
            for m in r.common_metrics + r.domain_metrics:
                self.assertEqual(m.status, "PASS")

    def test_one_partial_one_pass(self):
        with _ctx_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.99,
                "hallucination_rate": 0.0,
                "field_completeness": 0.80,  # 0.80 ≥ 0.80×0.90=0.72 < 0.95×0.90=0.855 → PARTIAL
                "ratio_consistency": 1.0,
            })
            r = ev.run(EvalRun(agent_id="stub"))
            self.assertEqual(r.partial_metrics, ["field_completeness"])
            self.assertEqual(r.failed_metrics, [])

    def test_fail_dominant(self):
        with _ctx_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.99,
                "hallucination_rate": 0.0,
                "field_completeness": 0.50,  # < 0.72 → FAIL
                "ratio_consistency": 0.85,    # 0.85 < 0.80×0.99=0.792? no 0.792 < 0.85 < 0.95×0.99=0.94 → PARTIAL
            })
            r = ev.run(EvalRun(agent_id="stub"))
            self.assertIn("field_completeness", r.failed_metrics)
            self.assertIn("ratio_consistency", r.partial_metrics)

    def test_skip_when_value_none(self):
        with _ctx_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {"evidence_rate": None})
            r = ev.run(EvalRun(agent_id="stub"))
            self.assertIn("evidence_rate", r.skipped_metrics)

    def test_cli_exit_partial_returns_1(self):
        from evaluation.runner.cli import main as cli_main
        with _ctx_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.85,  # PARTIAL (≥ 0.7615 < 0.9025)
                "hallucination_rate": 0.0,
                "field_completeness": 0.95,
                "ratio_consistency": 1.0,
            })
            with patch("evaluation.runner.cli.get_evaluator", return_value=ev):
                rc = cli_main(["--agent", "stub"])
        self.assertEqual(rc, 1)

    def test_cli_exit_all_pass_returns_0(self):
        from evaluation.runner.cli import main as cli_main
        with _ctx_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.99,
                "hallucination_rate": 0.0,
                "field_completeness": 0.95,
                "ratio_consistency": 1.0,
            })
            with patch("evaluation.runner.cli.get_evaluator", return_value=ev):
                rc = cli_main(["--agent", "stub"])
        self.assertEqual(rc, 0)

    def test_cli_exit_skip_only_returns_0(self):
        """全 SKIP (无 baseline_target / 无 value) → exit 0 视作可放行 (与 dispatch 决策 3 一致)."""
        from evaluation.runner.cli import main as cli_main
        with _ctx_yaml() as yaml_path:
            # 全 None → 全 SKIP · 无 PARTIAL/FAIL
            ev = _StubEvaluator(yaml_path, {})
            with patch("evaluation.runner.cli.get_evaluator", return_value=ev):
                rc = cli_main(["--agent", "stub"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
