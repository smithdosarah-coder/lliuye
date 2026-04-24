# -*- coding: utf-8 -*-
"""Agent5 合规 · 工具域入口（CLAUDE.md §3.2）

四个子域：政策解析 / 业务矩阵 / 违规判定 / 缺陷分类。
编排层保留在 `agent_compliance.agent.ComplianceRadarAgent`（policy_parse →
business_matrix → violation_check → defect_classify）。
"""

from .policy_parse import (
    policy_parse_document,
    policy_parse_scan_latest,
    policy_parse_categorize,
)
from .business_matrix import (
    business_matrix_build_rules,
    business_matrix_extract_events,
)
from .violation_check import (
    violation_check_checklist,
    violation_check_matrix,
)
from .defect_classify import (
    defect_classify_severity,
    defect_classify_is_mandatory,
    defect_classify_improvement_plan,
)

__all__ = [
    # 政策解析域
    "policy_parse_document",
    "policy_parse_scan_latest",
    "policy_parse_categorize",
    # 业务矩阵域
    "business_matrix_build_rules",
    "business_matrix_extract_events",
    # 违规判定域
    "violation_check_checklist",
    "violation_check_matrix",
    # 缺陷分类域
    "defect_classify_severity",
    "defect_classify_is_mandatory",
    "defect_classify_improvement_plan",
]
