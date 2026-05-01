# -*- coding: utf-8 -*-
"""Phase B BE10 · blocker_threshold gate 单元测试.

验证:
  1. blocker_threshold 缺失 → 不触发 (向下兼容)
  2. value=None → 不触发 (无法判定 ≠ 触发)
  3. 越大越好 metric: value < threshold → 触发 (e.g. evidence_rate=0.5 vs threshold=0.7)
  4. 越小越好 metric: value > threshold → 触发 (e.g. hallucination_rate=0.10 vs threshold=0.05)
  5. 触发时 EvalResult.blockers 含 metric name + any_blocker=True
  6. CLI --gate 触发时退出码 3
"""
from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from evaluation.runner.base_evaluator import BaseEvaluator
from evaluation.runner.schemas import EvalRun, MetricOutcome


class _StubEvaluator(BaseEvaluator):
    agent_id = "stub"
    config_name = "_test_blocker_stub.yaml"

    def __init__(self, yaml_path: Path, fixed_values: dict[str, float | None]) -> None:
        self.config_path = yaml_path
        self.config = self._load_config()
        self._fixed = fixed_values

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        return {}

    def compute_common_metrics(self, _artifacts: dict[str, Any]) -> list[MetricOutcome]:
        out = []
        for m_cfg in self._metrics_config("common"):
            out.append(self.mark(
                m_cfg["name"],
                self._fixed.get(m_cfg["name"]),
                method="deterministic",
                kind="common",
            ))
        return out

    def compute_domain_metrics(self, _artifacts: dict[str, Any]) -> list[MetricOutcome]:
        out = []
        for m_cfg in self._metrics_config("domain"):
            out.append(self.mark(
                m_cfg["name"],
                self._fixed.get(m_cfg["name"]),
                method="deterministic",
                kind="domain",
            ))
        return out


def _write_yaml(tmp: Path) -> Path:
    p = tmp / "_test_blocker_stub.yaml"
    p.write_text(textwrap.dedent("""
        agent_id: stub
        baseline:
          pending_metrics: []
        metrics:
          common:
            - name: evidence_rate
              target: ">= 0.95"
              baseline_target: 0.95
              blocker_threshold: 0.70
            - name: hallucination_rate
              target: "<= 0.02"
              baseline_target: 0.02
              blocker_threshold: 0.05
          domain:
            - name: field_completeness
              target: ">= 0.90"
              baseline_target: 0.90
              # blocker_threshold absent → 该指标无 publish gate
            - name: signal_diversity_score
              target: ">= 1"
              baseline_target: 1.0
              blocker_threshold: 0.5
    """).strip(), encoding="utf-8")
    return p


class BlockerGateTest(unittest.TestCase):
    def test_threshold_absent_does_not_trigger(self):
        with self._tmp_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {"field_completeness": 0.0})  # 极低 但 无 threshold
            result = ev.run(EvalRun(agent_id="stub"))
        for m in result.domain_metrics:
            if m.name == "field_completeness":
                self.assertFalse(m.blocker_triggered)
                self.assertIsNone(m.blocker_threshold)

    def test_value_none_does_not_trigger(self):
        with self._tmp_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {"evidence_rate": None})
            result = ev.run(EvalRun(agent_id="stub"))
        for m in result.common_metrics:
            if m.name == "evidence_rate":
                self.assertIsNone(m.value)
                self.assertFalse(m.blocker_triggered)
                self.assertEqual(m.blocker_threshold, 0.70)

    def test_higher_better_below_threshold_triggers(self):
        # evidence_rate=0.5 < blocker_threshold 0.70 → 触发
        with self._tmp_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.5,
                "hallucination_rate": 0.0,
                "field_completeness": 0.95,
                "signal_diversity_score": 1.5,
            })
            result = ev.run(EvalRun(agent_id="stub"))
        names = result.blockers
        self.assertIn("evidence_rate", names)
        self.assertTrue(result.any_blocker)

    def test_lower_better_above_threshold_triggers(self):
        # hallucination_rate=0.10 > blocker_threshold 0.05 → 触发
        with self._tmp_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.99,
                "hallucination_rate": 0.10,
                "field_completeness": 0.95,
                "signal_diversity_score": 1.5,
            })
            result = ev.run(EvalRun(agent_id="stub"))
        self.assertIn("hallucination_rate", result.blockers)
        self.assertTrue(result.any_blocker)

    def test_all_passing_no_blockers(self):
        with self._tmp_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.99,
                "hallucination_rate": 0.0,
                "field_completeness": 0.95,
                "signal_diversity_score": 1.5,
            })
            result = ev.run(EvalRun(agent_id="stub"))
        self.assertEqual(result.blockers, [])
        self.assertFalse(result.any_blocker)

    def test_cli_gate_returns_3_on_blocker(self):
        from evaluation.runner.cli import main as cli_main
        from evaluation.runner.registry import register_evaluator

        with self._tmp_yaml() as yaml_path:
            ev = _StubEvaluator(yaml_path, {
                "evidence_rate": 0.5,  # 触发
                "hallucination_rate": 0.0,
                "field_completeness": 0.95,
                "signal_diversity_score": 1.5,
            })

            with patch("evaluation.runner.cli.get_evaluator", return_value=ev):
                rc_no_gate = cli_main(["--agent", "stub"])
                rc_gate = cli_main(["--agent", "stub", "--gate"])

        self.assertNotEqual(rc_no_gate, 3, "未启用 --gate 不应退出 3")
        self.assertEqual(rc_gate, 3, "blocker 触发时 --gate 必须退出 3")

    def _tmp_yaml(self):
        from contextlib import contextmanager
        from tempfile import TemporaryDirectory

        @contextmanager
        def _ctx():
            with TemporaryDirectory() as td:
                yield _write_yaml(Path(td))
        return _ctx()


if __name__ == "__main__":
    unittest.main()
