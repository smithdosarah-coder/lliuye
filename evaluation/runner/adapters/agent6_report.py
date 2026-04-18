# -*- coding: utf-8 -*-
"""
evaluation.runner.adapters.agent6_report — Agent6 报告助手评估 adapter

Phase A 只覆盖可确定性计算的指标:
  [domain]
    - template_leakage_rate   — SequenceMatcher vs samples/ 基线的段落级相似度
    - unfilled_marker_accuracy — 占位符残留 + "未能自动填写" 标记一致性
  [common]
    - task_completion_rate    — docx 是否正常打开、段落数 > 0

其余指标 (evidence_rate / hallucination_rate / financial_ratio_consistency /
section_length_calibration / quality_score_total) 本阶段返回 None, method=manual
或 heuristic, 等 Phase B 接 LLM-judge / financial_analyzer runtime。
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from docx import Document

from ..base_evaluator import REPO_ROOT, BaseEvaluator
from ..registry import register_evaluator
from ..schemas import EvalRun, MetricOutcome


SAMPLES_DIR = REPO_ROOT / "samples"
SIMILARITY_HIT = 0.85           # 段落视作"模板泄漏"的 SequenceMatcher 阈值
PLACEHOLDER_PAT = re.compile(r"\{\{[^}]+\}\}|XXX|xxx|【[^】]*】")
UNFILLED_MARK = "未能自动填写"


def _read_paragraphs(path: Path) -> list[str]:
    doc = Document(str(path))
    out = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            out.append(t)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                t = (cell.text or "").strip()
                if t:
                    out.append(t)
    return out


def _baseline_for(artifact: Path) -> Path | None:
    """按文件名骨架找对应的 samples/ 基线."""
    stem = artifact.stem
    # strip 常见 v16/_v15/_test 后缀
    core = re.sub(r"_v\d+$|_test.*$", "", stem)
    for candidate in SAMPLES_DIR.glob("*.docx"):
        if candidate.stem in core or core in candidate.stem:
            return candidate
    return None


@register_evaluator("report")
class Agent6ReportEvaluator(BaseEvaluator):
    agent_id = "report"
    config_name = "agent6_report.yaml"

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        if not run.artifacts:
            return {"paragraphs": [], "artifact_path": None, "baseline_path": None}
        art_path = Path(run.artifacts[0])
        if not art_path.is_absolute():
            art_path = REPO_ROOT / art_path
        if not art_path.exists():
            return {
                "paragraphs": [],
                "artifact_path": str(art_path),
                "baseline_path": None,
                "error": f"artifact missing: {art_path}",
            }
        paragraphs = _read_paragraphs(art_path)
        baseline_path = _baseline_for(art_path)
        baseline_paragraphs = _read_paragraphs(baseline_path) if baseline_path else []
        return {
            "paragraphs": paragraphs,
            "artifact_path": str(art_path),
            "baseline_path": str(baseline_path) if baseline_path else None,
            "baseline_paragraphs": baseline_paragraphs,
        }

    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        paragraphs = artifacts.get("paragraphs") or []
        art_path = artifacts.get("artifact_path")

        # task_completion_rate: 能打开 + 段落数非零 ⇒ 1.0, 否则 0.0
        task_completion = 1.0 if paragraphs else 0.0
        out: list[MetricOutcome] = [
            self.mark(
                "task_completion_rate",
                task_completion,
                method="deterministic",
                evidence=[art_path] if art_path else [],
                note=f"{len(paragraphs)} paragraphs",
                kind="common",
            )
        ]

        # 其余 common 指标这一阶段不可自动化, 走 stub
        for name in ("field_completeness", "evidence_rate", "hallucination_rate", "tool_success_rate"):
            out.append(
                MetricOutcome(
                    name=name,
                    value=None,
                    target=self._lookup_target(name, "common") or "n/a",
                    passed=None,
                    method="manual",
                    note="Phase A stub — 待 Phase B 接 LLM-judge / 证据链扫描",
                )
            )
        return out

    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        paragraphs: list[str] = artifacts.get("paragraphs") or []
        baseline_paragraphs: list[str] = artifacts.get("baseline_paragraphs") or []
        art_path = artifacts.get("artifact_path")
        base_path = artifacts.get("baseline_path")

        out: list[MetricOutcome] = []

        # --- template_leakage_rate ---
        if paragraphs and baseline_paragraphs:
            leaks = 0
            for p in paragraphs:
                best = 0.0
                for bp in baseline_paragraphs:
                    r = SequenceMatcher(None, p, bp).ratio()
                    if r > best:
                        best = r
                        if best >= SIMILARITY_HIT:
                            break
                if best >= SIMILARITY_HIT:
                    leaks += 1
            leakage = leaks / max(len(paragraphs), 1)
            out.append(
                self.mark(
                    "template_leakage_rate",
                    leakage,
                    method="deterministic",
                    evidence=[base_path] if base_path else [],
                    note=f"{leaks}/{len(paragraphs)} paragraphs >= {SIMILARITY_HIT} vs baseline",
                )
            )
        else:
            out.append(
                MetricOutcome(
                    name="template_leakage_rate",
                    value=None,
                    target=self._lookup_target("template_leakage_rate", "domain") or "n/a",
                    passed=None,
                    method="heuristic",
                    note="缺 artifact 或 baseline, 跳过",
                )
            )

        # --- unfilled_marker_accuracy ---
        placeholder_hits = sum(bool(PLACEHOLDER_PAT.search(p)) for p in paragraphs)
        unfilled_marks = sum(UNFILLED_MARK in p for p in paragraphs)
        total = len(paragraphs) or 1
        # 简化公式: 1 - 异常率 (占位符残留视为漏标, 无占位符但有 unfilled_mark 视为正常)
        abnormal = placeholder_hits
        accuracy = 1.0 - abnormal / total
        out.append(
            self.mark(
                "unfilled_marker_accuracy",
                max(0.0, min(1.0, accuracy)),
                method="heuristic",
                evidence=[art_path] if art_path else [],
                note=f"placeholder_residue={placeholder_hits}, unfilled_marks={unfilled_marks}",
            )
        )

        # --- 其余 domain 指标本阶段 stub ---
        for name in ("financial_ratio_consistency", "section_length_calibration", "quality_score_total"):
            out.append(
                MetricOutcome(
                    name=name,
                    value=None,
                    target=self._lookup_target(name, "domain") or "n/a",
                    passed=None,
                    method="manual",
                    note="Phase A stub — 需 financial_analyzer / 真人范文库 / quality_scorer runtime",
                )
            )

        return out
