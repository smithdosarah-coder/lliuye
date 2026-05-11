# -*- coding: utf-8 -*-
"""agent_alert · 输出 QC 闸门 thin shim (B.3.4 P0-R1 · 2026-05-11)

per docs/contracts/shared-output-validator-v1.0.md v1.0

Agent4 预警的 Disposition / 客户榜单文本输出前过 placeholder_guard,
占位符残留即阻断 (硬模式) 或软降级标 "未能自动填写"。

实现 (factory wrapper · shared.output_validator):
- shared/output_validator.py 单点 · 5 Agent 共用 · 行为完全一致
- AGENT / validate_text / soft_clean / assert_clean / PlaceholderViolation re-export
- 保留 public symbols 不破 production import path

供 api.py / eval / replay 直接调用。
"""
from __future__ import annotations

from shared.output_validator import make_output_validator
from shared.qc import PlaceholderViolation  # re-export for backward compat

_validator = make_output_validator("agent_alert")

AGENT = _validator.agent_id
validate_text = _validator.validate_text
soft_clean = _validator.soft_clean
assert_clean = _validator.assert_clean

__all__ = ["AGENT", "validate_text", "soft_clean", "assert_clean", "PlaceholderViolation"]
