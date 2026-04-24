# -*- coding: utf-8 -*-
"""Agent5 合规巡检 - 合规比对引擎

将政策要求与业务操作记录逐条对比，生成合规检查报告。
"""

from __future__ import annotations

import json
import re
from typing import Callable
from pydantic import BaseModel, Field

from .policy_parser import PolicyDocument, PolicyRequirement
from .prompts import SYSTEM_COMPLIANCE_CHECK


class CheckItem(BaseModel):
    """单条检查结果"""
    req_id: str = Field(default="", description="对应的要求编号")
    requirement: str = Field(default="", description="要求描述")
    status: str = Field(default="fail", description="检查状态: pass/fail/partial/not_applicable")
    evidence: str = Field(default="", description="合规证据摘录")
    gap_description: str = Field(default="", description="不合规之处描述")


class ComplianceReport(BaseModel):
    """合规检查报告"""
    total_items: int = Field(default=0, description="检查项总数")
    passed: int = Field(default=0, description="通过数")
    failed: int = Field(default=0, description="不通过数")
    partial: int = Field(default=0, description="部分通过数")
    compliance_rate: float = Field(default=0.0, description="合规率(百分比)")
    items: list[CheckItem] = Field(default_factory=list, description="逐条检查结果")
    summary: str = Field(default="", description="总结摘要")


def check_compliance(
    policy: PolicyDocument,
    business_text: str,
    llm_fn: Callable,
) -> ComplianceReport:
    """用LLM逐条对比政策要求与业务操作记录。

    Args:
        policy: 已解析的政策文档
        business_text: 业务操作记录文本
        llm_fn: LLM调用回调，签名为 llm_fn(system, user, model_class, retries) -> BaseModel

    Returns:
        ComplianceReport: 合规检查报告
    """
    if not policy.requirements:
        return ComplianceReport(summary="未找到监管要求，无法执行合规检查。")

    # 构建要求清单文本
    req_lines = []
    for req in policy.requirements:
        req_lines.append(
            f"- {req.req_id} [{req.severity}] ({req.category}): {req.description}"
        )
    requirements_text = "\n".join(req_lines)

    # 截断过长的业务文本
    max_biz_len = 10000
    if len(business_text) > max_biz_len:
        keep_start = int(max_biz_len * 0.7)
        keep_end = max_biz_len - keep_start - 60
        business_text = (
            business_text[:keep_start]
            + f"\n\n... (省略约{len(business_text) - max_biz_len}字) ...\n\n"
            + business_text[-keep_end:]
        )

    user_prompt = (
        f"## 监管要求清单（共{len(policy.requirements)}条）\n\n"
        f"{requirements_text}\n\n"
        f"## 业务操作记录\n\n"
        f"{business_text}\n\n"
        "请逐条对比，给出合规检查结果。"
    )

    try:
        result = llm_fn(SYSTEM_COMPLIANCE_CHECK, user_prompt, ComplianceReport, retries=3)
        if isinstance(result, ComplianceReport):
            # 重新计算统计数据，确保准确
            _recalculate_stats(result)
            return result
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
        pass

    # 兜底：为每条要求生成默认的fail结果
    items = []
    for req in policy.requirements:
        items.append(CheckItem(
            req_id=req.req_id,
            requirement=req.description,
            status="fail",
            evidence="",
            gap_description="LLM合规检查失败，无法自动判定",
        ))
    report = ComplianceReport(items=items, summary="自动合规检查失败，请人工核查。")
    _recalculate_stats(report)
    return report


def _recalculate_stats(report: ComplianceReport) -> None:
    """根据 items 重新计算统计数据。"""
    report.total_items = len(report.items)
    report.passed = sum(1 for it in report.items if it.status == "pass")
    report.failed = sum(1 for it in report.items if it.status == "fail")
    report.partial = sum(1 for it in report.items if it.status == "partial")
    applicable = report.total_items - sum(1 for it in report.items if it.status == "not_applicable")
    if applicable > 0:
        report.compliance_rate = round((report.passed + report.partial * 0.5) / applicable * 100, 1)
    else:
        report.compliance_rate = 100.0


def format_checklist(report: ComplianceReport) -> str:
    """将合规检查报告格式化为可读的检查清单。

    Args:
        report: 合规检查报告

    Returns:
        str: Markdown格式的检查清单
    """
    STATUS_ICON = {
        "pass": "\u2705",       # ✅
        "fail": "\u274c",       # ❌
        "partial": "\u26a0\ufe0f",  # ⚠️
        "not_applicable": "\u2796",  # ➖
    }

    lines = [
        "## 合规检查清单",
        "",
        f"**合规率: {report.compliance_rate}%** | "
        f"通过: {report.passed} | 不通过: {report.failed} | "
        f"部分通过: {report.partial} | 总计: {report.total_items}",
        "",
        "| 状态 | 编号 | 检查项 | 证据/差距说明 |",
        "|:----:|------|--------|-------------|",
    ]

    for item in report.items:
        icon = STATUS_ICON.get(item.status, "?")
        detail = item.evidence if item.status == "pass" else item.gap_description
        # 截断过长的文本
        if len(detail) > 80:
            detail = detail[:77] + "..."
        lines.append(f"| {icon} | {item.req_id} | {item.requirement[:50]} | {detail} |")

    lines.append("")
    if report.summary:
        lines.append(f"**总结:** {report.summary}")
        lines.append("")

    return "\n".join(lines)
