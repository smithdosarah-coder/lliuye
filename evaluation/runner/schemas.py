# -*- coding: utf-8 -*-
"""
evaluation.runner.schemas — Pydantic 契约

统一所有 Agent 评估产出的数据结构. 改签名 = adapter 全部 break,
属红区候选 (RFC 20260418-evaluation-runner §8 已埋点).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Any

from pydantic import BaseModel, Field, ConfigDict


MetricMethod = Literal["deterministic", "llm-judge", "heuristic", "manual"]
# Sprint 2 决策 3 加 SKIP 维度 · per-metric 4 状态: PASS / PARTIAL / FAIL / SKIP
MetricStatus = Literal["PASS", "PARTIAL", "FAIL", "SKIP"]
Verdict = Literal["PASS", "FAIL", "PARTIAL"]


class MetricOutcome(BaseModel):
    """单条指标的评估结果."""

    model_config = ConfigDict(frozen=False)

    name: str = Field(..., description="指标名, 与 YAML 里 metrics.*.name 一致")
    value: float | None = Field(None, description="None = 无法计算 (数据缺失 / adapter 未实现)")
    target: str = Field(..., description='原文 target 表达式, 如 ">= 0.90" / "<= 0.02"')
    passed: bool | None = Field(None, description="None = 无法判定")
    method: MetricMethod = Field(..., description="如何算出的")
    evidence: list[str] = Field(default_factory=list, description="证据路径 / 段落 ID / URL")
    note: str = Field("", description="补充说明, 失败原因或方法细节")
    blocker_threshold: float | None = Field(
        None, description="跨此线阻断发布 (Phase B BE10 · 比 baseline_target 宽一档)",
    )
    blocker_triggered: bool = Field(
        False, description="value 跨过 blocker_threshold = True (CI gate 阻断)",
    )
    # Sprint 2 决策 3 · per-metric PARTIAL 维度
    status: MetricStatus = Field(
        "SKIP",
        description=(
            "PASS=value≥0.95×baseline / PARTIAL=[0.80,0.95)×baseline / "
            "FAIL=<0.80×baseline / SKIP=value None or no baseline_target"
        ),
    )
    baseline_target: float | None = Field(
        None, description="用于 PARTIAL 维度阈值计算 (PASS=0.95×bt · PARTIAL=0.80×bt)",
    )


class EvalRun(BaseModel):
    """单次评估运行的输入描述."""

    agent_id: str = Field(..., description='"channel" / "riskctrl" / "credit" / "alert" / "compliance" / "report"')
    commit: str | None = Field(None, description="git HEAD hash, None 表示 dirty tree")
    artifacts: list[str] = Field(default_factory=list, description="待评估产出物路径 (相对 repo root 或绝对)")
    compare_baseline: bool = Field(False, description="是否与 yaml.baseline.result 对比")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: dict[str, Any] = Field(default_factory=dict, description="adapter 自定义附加输入")


class EvalResult(BaseModel):
    """单次评估运行的产出."""

    run: EvalRun
    common_metrics: list[MetricOutcome] = Field(default_factory=list)
    domain_metrics: list[MetricOutcome] = Field(default_factory=list)
    verdict: Verdict = Field(..., description="PASS = 全过; FAIL = 任一 common 或 domain 过线闸门未过; PARTIAL = 混")
    runner_version: str = Field("0.1.0-phase-a")
    duration_seconds: float = Field(..., description="从 load_artifacts 到 save 的总耗时")
    blockers: list[str] = Field(
        default_factory=list,
        description="跨过 blocker_threshold 的指标名 list (Phase B BE10 · CI gate 阻断发布)",
    )
    partial_metrics: list[str] = Field(
        default_factory=list,
        description="status=PARTIAL 的 metric name list (Sprint 2 决策 3 · PM 评审用)",
    )
    failed_metrics: list[str] = Field(
        default_factory=list,
        description="status=FAIL 的 metric name list (Sprint 2 决策 3 · 必修)",
    )
    skipped_metrics: list[str] = Field(
        default_factory=list,
        description="status=SKIP 的 metric name list (value=None 或缺 baseline_target)",
    )

    @property
    def any_blocker(self) -> bool:
        """是否有任何 blocker 触发 (CLI --gate 退出码 3 用)."""
        return bool(self.blockers)

    @property
    def any_fail(self) -> bool:
        """是否有 status=FAIL (Sprint 2 决策 3 · 必修 · 不可豁免与 blocker 不同 · exit 1)."""
        return bool(self.failed_metrics)

    def summary_table(self) -> str:
        """Plain-text 表格, stdout 用."""
        lines = [
            f"=== {self.run.agent_id} · {self.verdict} · {self.duration_seconds:.1f}s ===",
            f"    commit: {self.run.commit or 'DIRTY'}  artifacts: {len(self.run.artifacts)}",
            "",
            "    [Common]",
        ]
        for m in self.common_metrics:
            lines.append(self._row(m))
        lines.append("")
        lines.append("    [Domain]")
        for m in self.domain_metrics:
            lines.append(self._row(m))
        return "\n".join(lines)

    @staticmethod
    def _row(m: MetricOutcome) -> str:
        val = "N/A" if m.value is None else f"{m.value:.4f}"
        # Sprint 2 决策 3 · 4-state 色标
        marker_map = {
            "PASS": "OK",     # 绿
            "PARTIAL": "~~",  # 黄
            "FAIL": "X ",     # 橙/红
            "SKIP": "??",     # 灰
        }
        pass_mark = marker_map.get(m.status, "??")
        blk = " [BLOCKER]" if m.blocker_triggered else ""
        return f"      {pass_mark} {m.name:<35} {val:>10}  (target {m.target}){blk}"
