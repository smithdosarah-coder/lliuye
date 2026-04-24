# -*- coding: utf-8 -*-
"""缺陷分类域 —— 严重/重要/一般分级 + 强制项判定 + 整改计划生成。"""

from __future__ import annotations

from ..compliance_checker import CheckItem
from ..defect_classifier import (
    Defect,
    _is_mandatory_violation as _is_mandatory_violation_impl,
    classify_defects as _classify_defects,
    generate_improvement_plan as _generate_improvement_plan,
)


def defect_classify_severity(failed_items: list[CheckItem]) -> list[Defect]:
    """把失败检查项分类为 Defect + 分级（缺陷分类域：主入口）。"""
    return _classify_defects(failed_items)


def defect_classify_is_mandatory(item: CheckItem) -> bool:
    """判定该检查项是否踩强制性要求（缺陷分类域：强制项判定）。"""
    return _is_mandatory_violation_impl(item)


def defect_classify_improvement_plan(defects: list[Defect]) -> str:
    """基于缺陷清单产出整改计划 Markdown（缺陷分类域：整改计划）。"""
    return _generate_improvement_plan(defects)
