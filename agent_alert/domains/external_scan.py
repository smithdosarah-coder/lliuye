# -*- coding: utf-8 -*-
"""外部扫描域 —— 裁判文书 / 工商变更 / 舆情监测 + 内部制度→规则抽取。"""

from __future__ import annotations

from pathlib import Path

from ..customer_scanner import CustomerScanner
from ..rule_extractor import InternalPolicyExtractor


def external_scan_customer(kb, *, search_provider=None, **kwargs) -> CustomerScanner:
    """构造面向在贷客户池的外部扫描器（外部扫描域：扫描器工厂）。

    返回已配置的 CustomerScanner，调用方用 `.scan()` 迭代进度或 `.scan_all()` 拿 HitList。
    """
    return CustomerScanner(kb=kb, search_provider=search_provider, **kwargs)


def external_scan_policy_extract(policy_path: str | Path, llm_client=None):
    """从内部管理制度文档抽取可执行规则（外部扫描域：规则抽取）。"""
    return InternalPolicyExtractor(llm_client=llm_client).extract(policy_path)
