# -*- coding: utf-8 -*-
"""
evaluation.runner — 跨 Agent 评估 Runner

架构参考:
  docs/contracts/rfc/20260418-evaluation-runner.md

分层:
  - schemas: Pydantic 契约 (EvalRun / EvalResult / MetricOutcome)
  - base_evaluator: 抽象基类 + common metrics 默认实现
  - registry: adapter 注册表 (lazy load, Phase B 逐步填充)
  - adapters/<agent>.py: 各 Agent 专属评估实现
  - cli: `python -m evaluation.runner --agent <id>` 入口

Phase A 已落地:
  - 框架 (schemas / base / registry / cli)
  - agent6_report adapter (halluc / evidence / template_leakage / financial_ratio_consistency)

Phase B 委派子 CLI 实现:
  - channel / riskctrl / credit / alert / compliance 5 个 adapter

Phase C (主 CLI):
  - CI 接入, 阈值阻断 PR 合并
"""

from .schemas import EvalRun, EvalResult, MetricOutcome, Verdict
from .base_evaluator import BaseEvaluator
from .registry import register_evaluator, get_evaluator, list_registered

__all__ = [
    "EvalRun",
    "EvalResult",
    "MetricOutcome",
    "Verdict",
    "BaseEvaluator",
    "register_evaluator",
    "get_evaluator",
    "list_registered",
]

__version__ = "0.1.0-phase-a"
