# -*- coding: utf-8 -*-
"""政策解析域 —— 监管政策文件 → 结构化要求 + 分类 + 最新政策扫描。"""

from __future__ import annotations

from typing import Callable

from ..policy_parser import (
    PolicyDocument,
    PolicyRequirement,
    categorize_requirements as _categorize_requirements,
    parse_policy as _parse_policy,
)
from ..policy_scanner import scan_latest_policies as _scan_latest_policies


def policy_parse_document(policy_text: str, llm_fn: Callable) -> PolicyDocument:
    """政策原文 → 结构化 PolicyDocument（政策解析域：主入口）。"""
    return _parse_policy(policy_text, llm_fn)


def policy_parse_scan_latest(query: str = "", limit: int = 10, llm_fn=None) -> list[dict]:
    """按查询条件扫描最新政策列表（政策解析域：政策雷达）。"""
    return _scan_latest_policies(query=query, limit=limit, llm_fn=llm_fn)


def policy_parse_categorize(requirements: list[PolicyRequirement]) -> dict[str, list[PolicyRequirement]]:
    """把条款按类别聚合（政策解析域：归类）。"""
    return _categorize_requirements(requirements)
