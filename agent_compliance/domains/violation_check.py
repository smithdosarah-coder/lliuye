# -*- coding: utf-8 -*-
"""违规判定域 —— 矩阵扫描 + 合规自检 checklist 打分。"""

from __future__ import annotations

from ..compliance_checker import ComplianceReport, check_compliance as _check_compliance
from ..matrix_matcher import MatrixMatcher


def violation_check_checklist(*args, **kwargs) -> ComplianceReport:
    """合规自检清单检查（违规判定域：条目化检查）。

    透传到 `compliance_checker.check_compliance(...)`。
    """
    return _check_compliance(*args, **kwargs)


def violation_check_matrix(rules: list, events: list[dict], *,
                           use_llm: bool = False, llm_judge=None, **kwargs):
    """政策条款 × 业务制度矩阵扫描出违规记录（违规判定域：矩阵匹配主入口）。"""
    matcher = MatrixMatcher(use_llm=use_llm, llm_judge=llm_judge)
    return matcher.match(rules, events, **kwargs)
