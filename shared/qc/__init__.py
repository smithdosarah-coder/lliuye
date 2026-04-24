# -*- coding: utf-8 -*-
"""shared.qc — 跨 Agent QC 闸门。

Product Hardening Batch 1 · Task B 引入 placeholder_guard, 用于在 5 个非
Agent6 智能体（channel / credit / alert / compliance / riskctrl）的最终
输出前扫描占位符残留 (CLAUDE.md §8 第 1 条闸门)。
"""

from .placeholder_guard import (
    PlaceholderHit,
    PlaceholderViolation,
    assert_clean,
    is_clean,
    mark_unfilled,
    scan,
)

__all__ = [
    "PlaceholderHit",
    "PlaceholderViolation",
    "assert_clean",
    "is_clean",
    "mark_unfilled",
    "scan",
]
