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

A-025 · YAML schema 兼容层:
  每条指标支持新老双字段 (desc/target/description/method/baseline_target/blocker_threshold).
  _lookup_target 优先读老 target 字符串 (向后兼容), 无则从 baseline_target + name 方向推导.
  _normalize_metric 统一视图供 adapter / report 消费.
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
        all_metrics = common + domain
        # Phase B BE10 · 标 blocker_triggered (改 metric in-place · pydantic frozen=False)
        self._mark_blockers(all_metrics)
        verdict = self._verdict(all_metrics)
        blockers = [m.name for m in all_metrics if m.blocker_triggered]
        duration = time.perf_counter() - t0
        result = EvalResult(
            run=run,
            common_metrics=common,
            domain_metrics=domain,
            verdict=verdict,
            blockers=blockers,
            duration_seconds=duration,
        )
        self._persist(result)
        return result

    def _mark_blockers(self, metrics: list[MetricOutcome]) -> None:
        """Phase B BE10 · 比对每条 metric value vs YAML blocker_threshold.

        - blocker_threshold 缺失 → 跳过 (该指标无 publish gate)
        - value=None → 跳过 (无法判定 · 不算触发)
        - 方向: hint 命中 _LOWER_IS_BETTER_HINTS → value > threshold 触发;
                       否则 → value < threshold 触发 (越大越好)
        - blocker_threshold 默认应比 baseline_target 宽一档 (per evaluation/README.md §28)
        """
        # 按 name 索引 yaml metric (含 common + domain)
        cfg_by_name: dict[str, dict] = {}
        for kind in ("common", "domain"):
            for m_cfg in self._metrics_config(kind):
                cfg_by_name[m_cfg["name"]] = m_cfg

        for m in metrics:
            cfg = cfg_by_name.get(m.name)
            if not cfg:
                continue
            threshold = cfg.get("blocker_threshold")
            if threshold is None:
                continue
            try:
                threshold_f = float(threshold)
            except (TypeError, ValueError):
                continue
            m.blocker_threshold = threshold_f
            if m.value is None:
                continue
            lower_is_better = any(h in m.name for h in _LOWER_IS_BETTER_HINTS)
            triggered = (m.value > threshold_f) if lower_is_better else (m.value < threshold_f)
            m.blocker_triggered = bool(triggered)

    def _verdict(self, metrics: list[MetricOutcome]) -> Verdict:
        pending = set(self.config.get("baseline", {}).get("pending_metrics", []))
        effective = [m for m in metrics if m.name not in pending]
        resolved = [m for m in effective if m.passed is not None]
        if not resolved:
            return "PARTIAL"
        if all(m.passed for m in resolved):
            return "PASS" if len(resolved) == len(effective) else "PARTIAL"
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
        """查某条指标的 target 字符串.

        A-025 fallback 顺序:
          1. 老 `target` 字符串字段 (向后兼容, agent2/4/6 adapter 零改动)
          2. 从 `baseline_target` (数字) + name 推导方向生成 ">= X" / "<= X"
             - name 命中 _LOWER_IS_BETTER_HINTS → "<= baseline_target"
             - 否则默认 ">= baseline_target"
          3. 返回 None (adapter 侧做 stub)
        """
        for m in self._metrics_config(kind):
            if m.get("name") == name:
                legacy = m.get("target")
                if isinstance(legacy, str) and legacy.strip():
                    return legacy
                return _derive_target_from_new_schema(m)
        return None

    @staticmethod
    def _normalize_metric(m: dict) -> dict:
        """A-025 §3 · 指标双字段归一化视图.

        返回 dict 同时带新字段, 供 rubric 渲染 / report 消费.
        老 YAML 无新字段时 fallback 到老字段.
        """
        return {
            "name": m["name"],
            "description": m.get("description") or m.get("desc") or "",
            "method": m.get("method") or "",
            "baseline_target": (
                m.get("baseline_target")
                if "baseline_target" in m
                else _parse_legacy_target_to_float(m.get("target", ""))
            ),
            "blocker_threshold": m.get("blocker_threshold"),
            "target": m.get("target") or _derive_target_from_new_schema(m) or "n/a",
        }


# --- A-025 helpers (module-level, 无状态, 便于测试) --- #

# 命中任一子串 → 该指标"越小越好", 推导 "<= baseline_target"
_LOWER_IS_BETTER_HINTS = (
    "hallucination",
    "leakage",
    "false_positive",
    "fpr_spread",
    "spread",
    "deviation",
    "latency",
    "unresolvable",
    "defect_rate",
)


def _parse_legacy_target_to_float(target: str) -> float | None:
    """把老 target 字符串 (\">= 0.9\" / \"<= 0.02\" / \"pass\") 解析为 float 或 None."""
    if not isinstance(target, str):
        return None
    m = _TARGET_RE.match(target.strip())
    if not m:
        return None
    op, rhs_raw = m.group(1), m.group(2).strip()
    if op == "in":
        return None
    try:
        return float(rhs_raw)
    except ValueError:
        return None


def _derive_target_from_new_schema(m: dict) -> str | None:
    """无老 target 字段时, 用 baseline_target + name 推导 target 字符串."""
    bt = m.get("baseline_target")
    if not isinstance(bt, (int, float)):
        return None
    name = str(m.get("name", ""))
    if any(h in name for h in _LOWER_IS_BETTER_HINTS):
        return f"<= {bt}"
    return f">= {bt}"


def load_baseline_artifacts(path: str | Path) -> dict[str, Any]:
    """Utility for adapters needing to read a JSON sidecar artifact."""
    p = Path(path)
    if not p.exists():
        return {}
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return {"raw": p.read_text(encoding="utf-8", errors="ignore")}
