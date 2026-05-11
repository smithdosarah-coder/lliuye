# -*- coding: utf-8 -*-
"""agent_credit · 输出 QC 闸门 thin shim (B.3.4 P0-R1 · 2026-05-11)

per docs/contracts/shared-output-validator-v1.0.md v1.0

Agent3 授信的 DecisionAdvice 文本 / payload 输出前过 placeholder_guard.
api.py 已直接做 soft_clean; 本模块为外部 (eval / replay / 写回 Agent6 的
text 块) 提供同名入口.

实现走 shared/output_validator.py 单点 · 5 Agent 共用 · 行为完全一致.
"""
from __future__ import annotations

from shared.output_validator import make_output_validator
from shared.qc import PlaceholderViolation  # re-export for backward compat

_validator = make_output_validator("agent_credit")

AGENT = _validator.agent_id
validate_text = _validator.validate_text
soft_clean = _validator.soft_clean
assert_clean = _validator.assert_clean

__all__ = ["AGENT", "validate_text", "soft_clean", "assert_clean", "PlaceholderViolation"]
