# -*- coding: utf-8 -*-
"""agent_compliance · 输出 QC 闸门 (Product Hardening Batch 1 · Task B)

Agent5 合规的政策候选/违规清单文本输出前过 placeholder_guard。
api.py 已直接做 soft_clean; 本模块为外部 (eval / replay) 提供同名入口。
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

AGENT = "agent_compliance"


def validate_text(text: str) -> None:
    assert_clean(text or "", agent=AGENT)


def soft_clean(payload: Any) -> tuple[Any, list[str]]:
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
