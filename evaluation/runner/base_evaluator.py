# -*- coding: utf-8 -*-
"""
evaluation.runner.base_evaluator — 抽象基类

adapter 只需实现:
  - load_artifacts(run) → 产出物字典 (dict[str, Any], 内容 adapter 自定义)
  - compute_domain_metrics(artifacts) → list[MetricOutcome]

common 指标 (5 个) 默认 stub, adapter 可 override 单个或全部. Stub 返回
value=None / passed=None / method="manual", 保证 result 结构不缺失.

target 解析支持:
  ">= 0.9"  "<= 0.02"  "> 0"  "< 1"  "== true"  "!= false"  "in [PASS,PARTIAL]"
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml

from .schemas import EvalRun, EvalResult, MetricOutcome, Verdict


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "evaluation" / "results"

_TARGET_RE = re.compile(r"^\s*(>=|<=|>|<|==|!=|in)\s*(.+?)\s*$")


class BaseEvaluator(ABC):
    agent_id: str = ""
    config_name: str = ""

    def __init__(self) -> None:
        if not self.agent_id or not self.config_name:
            raise ValueError(f"{type(self).__name__} must set agent_id + config_name class attrs")
        self.config_path = REPO_ROOT / "evaluation" / self.config_name
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"eval config missing: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @abstractmethod
    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        """从 outputs/ 或其他路径抓本次评估所需产出物."""

    @abstractmethod
    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        """Agent 专属指标."""

    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        """默认 stub. adapter 应 override 至少 evidence_rate / hallucination_rate."""
        common_cfg = self._metrics_config("common")
        return [self._stub_metric(m) for m in common_cfg]

    def _metrics_config(self, kind: str) -> list[dict]:
        return list(self.config.get("metrics", {}).get(kind, []))

    def _stub_metric(self, m_cfg: dict) -> MetricOutcome:
        return MetricOutcome(
            name=m_cfg["name"],
            value=None,
            target=m_cfg.get("target", "n/a"),
            passed=None,
            method="manual",
            note="base stub — adapter 未 override",
        )

    def run(self, run: EvalRun) -> EvalResult:
        t0 = time.perf_counter()
        artifacts = self.load_artifacts(run)
        common = self.compute_common_metrics(artifacts)
        domain = self.compute_domain_metrics(artifacts)
        verdict = self._verdict(common + domain)
        duration = time.perf_counter() - t0
        result = EvalResult(
            run=run,
            common_metrics=common,
            domain_metrics=domain,
            verdict=verdict,
            duration_seconds=duration,
        )
        self._persist(result)
        return result

    @staticmethod
    def _verdict(metrics: list[MetricOutcome]) -> Verdict:
        resolved = [m for m in metrics if m.passed is not None]
        if not resolved:
            return "PARTIAL"
        if all(m.passed for m in resolved):
            return "PASS" if len(resolved) == len(metrics) else "PARTIAL"
        if not any(m.passed for m in resolved):
            return "FAIL"
        return "FAIL" if any(not m.passed for m in resolved) else "PARTIAL"

    def _persist(self, result: EvalResult) -> Path:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        day_dir = RESULTS_DIR / result.run.timestamp[:10]
        day_dir.mkdir(parents=True, exist_ok=True)
        commit = result.run.commit or "dirty"
        out_path = day_dir / f"{result.run.agent_id}_{commit[:8]}.json"
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return out_path

    @staticmethod
    def evaluate_target(value: float | None, target: str) -> bool | None:
        """解析 target 表达式, 对 value 判定 pass. value=None 返回 None."""
        if value is None:
            return None
        m = _TARGET_RE.match(target)
        if not m:
            return None
        op, rhs_raw = m.group(1), m.group(2).strip()
        if op == "in":
            return False
        try:
            rhs = float(rhs_raw)
        except ValueError:
            return None
        if op == ">=":
            return value >= rhs
        if op == "<=":
            return value <= rhs
        if op == ">":
            return value > rhs
        if op == "<":
            return value < rhs
        if op == "==":
            return value == rhs
        if op == "!=":
            return value != rhs
        return None

    def mark(
        self,
        name: str,
        value: float | None,
        method: str = "deterministic",
        evidence: list[str] | None = None,
        note: str = "",
        kind: str = "domain",
    ) -> MetricOutcome:
        """按 config 里的 target 自动打分. adapter 用这个而不是裸构造 MetricOutcome."""
        target = self._lookup_target(name, kind)
        passed = self.evaluate_target(value, target) if target else None
        return MetricOutcome(
            name=name,
            value=value,
            target=target or "n/a",
            passed=passed,
            method=method,  # type: ignore[arg-type]
            evidence=evidence or [],
            note=note,
        )

    def _lookup_target(self, name: str, kind: str) -> str | None:
        for m in self._metrics_config(kind):
            if m.get("name") == name:
                return m.get("target")
        return None


def load_baseline_artifacts(path: str | Path) -> dict[str, Any]:
    """Utility for adapters needing to read a JSON sidecar artifact."""
    p = Path(path)
    if not p.exists():
        return {}
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return {"raw": p.read_text(encoding="utf-8", errors="ignore")}
