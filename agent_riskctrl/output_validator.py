# -*- coding: utf-8 -*-
"""agent_riskctrl · 输出 QC 闸门 (Product Hardening Batch 1 · Task B)

Agent2 风控的 DSL / backtest 报告文本输出前过 placeholder_guard,
占位符残留即阻断 (硬模式) 或软降级标"未能自动填写"。

供 Task C 的 agent_riskctrl/api.py 直接调用。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from shared.qc import (  # noqa: E402
    PlaceholderViolation,
    assert_clean,
    mark_unfilled,
    scan,
)

AGENT = "agent_riskctrl"


def validate_text(text: str) -> None:
    """硬阻断: 命中即抛 PlaceholderViolation。"""
    assert_clean(text or "", agent=AGENT)


def soft_clean(payload: Any) -> tuple[Any, list[str]]:
    """递归把字符串字段里的占位符替换为标记, 返回 (cleaned, hit_kinds)。"""
    hits: list[str] = []

    def walk(v: Any) -> Any:
        if isinstance(v, str):
            local = scan(v)
            if local:
                hits.extend(h.kind for h in local)
                return mark_unfilled(v)
            return v
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v

    return walk(payload), hits


__all__ = ["AGENT", "validate_text", "soft_clean", "PlaceholderViolation"]
