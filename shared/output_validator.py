# -*- coding: utf-8 -*-
"""shared.output_validator · QC 闸门 factory (B.3.4 P0-R1 · 2026-05-11)

per docs/contracts/shared-output-validator-v1.0.md v1.0

抽 5 Agent (alert / channel / compliance / credit / riskctrl) 同构 output_validator.py
到单点 · 5 文件 51-55 行 → 1 个 factory 60 行 + 5 × ~10 行 thin shim.

设计 (per CLAUDE.md §3 + R7 verdict):
- shared invariant: 占位符扫描行为 + soft_clean 递归策略 (跨 5 Agent 一致)
- local adapter: agent_id 字段 (PlaceholderViolation.agent 用于日志/审计)
- 不动 shared.qc.placeholder_guard 底层
- 不动 agent_report/quality_blocker.py (5 维 QC · 留 Agent6 local)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shared.qc import (
    PlaceholderViolation,
    assert_clean as _qc_assert_clean,
    mark_unfilled,
    scan,
)

__all__ = [
    "OutputValidator",
    "make_output_validator",
    "PlaceholderViolation",
]


@dataclass(frozen=True)
class OutputValidator:
    """Per-agent thin wrapper · 行为完全等价于 5 Agent 旧 output_validator.py.

    使用:
        v = make_output_validator("agent_alert")
        v.validate_text(text)              # 硬阻断
        v.assert_clean(text)               # alias of validate_text
        cleaned, hits = v.soft_clean(payload)  # 软降级
    """

    agent_id: str

    def validate_text(self, text: str | None) -> None:
        """硬阻断 · 命中 placeholder 即抛 PlaceholderViolation.

        I1: 空字符串 / None 不抛异常.
        I2: 命中即抛 · PlaceholderViolation.agent = self.agent_id.
        """
        _qc_assert_clean(text or "", agent=self.agent_id)

    def assert_clean(self, text: str | None) -> None:
        """alias of validate_text · 兼容现有 import 习惯."""
        self.validate_text(text)

    def soft_clean(self, payload: Any) -> tuple[Any, list[str]]:
        """递归把字符串字段里的占位符替换为标记 · 返回 (cleaned, hit_kinds).

        I3: 递归 dict / list / str.
        I4: 非 str/dict/list (int/float/None/bool) 原样返回.
        I5: hit_kinds 不去重 · 顺序 = 遍历顺序.
        """
        return _walk(payload)


def make_output_validator(agent_id: str) -> OutputValidator:
    """Factory · 5 Agent 调用入口.

    Args:
        agent_id: e.g. "agent_alert" / "agent_channel" / "agent_compliance" /
                  "agent_credit" / "agent_riskctrl"

    Returns:
        OutputValidator 实例 (frozen · 可安全跨线程重用)
    """
    return OutputValidator(agent_id=agent_id)


def _walk(value: Any) -> tuple[Any, list[str]]:
    """递归 walker · 返回 (cleaned, hit_kinds)."""
    hits: list[str] = []

    def visit(v: Any) -> Any:
        if isinstance(v, str):
            local = scan(v)
            if local:
                hits.extend(h.kind for h in local)
                return mark_unfilled(v)
            return v
        if isinstance(v, dict):
            return {k: visit(x) for k, x in v.items()}
        if isinstance(v, list):
            return [visit(x) for x in v]
        return v

    cleaned = visit(value)
    return cleaned, hits
