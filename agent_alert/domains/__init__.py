# -*- coding: utf-8 -*-
"""Agent4 预警 · 工具域入口（CLAUDE.md §3.2）

四个子域：外部扫描 / 内部交易 / 双路交叉 / 处置建议。
CustomerScanner 的"逐客户扫描 → 交叉 → 分级 → 处置"编排仍放在 customer_scanner.py，
本子包只重导出原子能力并给跨域用户一个稳定命名入口。
"""

from .external_scan import (
    external_scan_customer,
    external_scan_policy_extract,
)
from .internal_txn import (
    internal_txn_evaluate,
    internal_txn_analyze_trends,
    internal_txn_detect_anomalies,
)
from .cross_match import (
    cross_match_customer,
    cross_match_infer_trigger_reasons,
)
from .disposition import (
    disposition_generate_plan,
    disposition_export_ledger,
)

__all__ = [
    # 外部扫描域
    "external_scan_customer",
    "external_scan_policy_extract",
    # 内部交易域
    "internal_txn_evaluate",
    "internal_txn_analyze_trends",
    "internal_txn_detect_anomalies",
    # 双路交叉域
    "cross_match_customer",
    "cross_match_infer_trigger_reasons",
    # 处置建议域
    "disposition_generate_plan",
    "disposition_export_ledger",
]
