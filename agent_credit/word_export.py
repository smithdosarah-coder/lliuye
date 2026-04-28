# -*- coding: utf-8 -*-
"""agent_credit.word_export — 决策建议书 docx 导出 (Stage C onboarding W-C2-A2 boundary).

Thin wrapper · 实质实装在 ``decision_letter_docx`` (Wave 2 P3F 已 land · Q-038 留原位).
本模块仅暴露 onboarding 字面要求的 ``agent_credit/word_export.py`` 命名 · 内部转调
``decision_letter_docx.{build_filename, export}`` · 不重复实装。

监管底线: 禁海外 API · 全部本地 python-docx 渲染.
"""
from __future__ import annotations

from typing import Any

from agent_credit.decision_letter_docx import (
    build_filename as _build_filename,
    export as _export,
)


def build_filename(advice: dict[str, Any]) -> str:
    """决策建议书文件名 · 形如 `决策建议书_鼎盛商贸_2026-04-28.docx`."""
    return _build_filename(advice)


def export(advice: dict[str, Any]) -> bytes:
    """渲染 docx · 返 bytes (FastAPI Response 直接 attach)."""
    return _export(advice)


__all__ = ["build_filename", "export"]
