# -*- coding: utf-8 -*-
"""Agent5 合规巡检 - 合规比对引擎

将政策要求与业务操作记录逐条对比，生成合规检查报告。
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Callable
from pydantic import BaseModel, Field

from .policy_parser import PolicyDocument, PolicyRequirement
from .prompts import SYSTEM_COMPLIANCE_CHECK
from .internal_policy_indexer import InternalClause


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


# ---------------------------------------------------------------------------
# Batch 2 · cross_compare (新政策 vs 内部制度条款)
# ---------------------------------------------------------------------------

CONFLICT_TYPES = ("new_requirement", "upgraded_requirement", "revoked", "terminology_change")
CONFLICT_SEVERITIES = ("high", "medium", "low")


class PolicyRef(BaseModel):
    """外部新政策引用。"""
    new_policy_id: str                       # hash(url) 或 policy 编号
    title: str = ""
    source_url: str = ""
    publish_date: str = ""
    source_name: str = ""                    # gov_cn / pbc_gov / flk_npc / tavily


class InternalClauseRef(BaseModel):
    """内部制度条款引用。"""
    clause_id: str
    source_doc: str = ""
    section_title: str = ""
    business_scope: str = ""


class EvidenceRef(BaseModel):
    """冲突条目的 Evidence(复用而非 import shared.sources 以避免循环)."""
    source: str
    url: str = ""
    snippet: str = ""


class ConflictItem(BaseModel):
    """一条"新政策 vs 内部制度条款"冲突记录。

    对外契约:
      conflict_id = hash(new_policy_id, internal_clause_id, conflict_type)
      severity ∈ CONFLICT_SEVERITIES
      conflict_type ∈ CONFLICT_TYPES
      suggested_amendment:
          非空 → 必须在正文里引到 new_policy_ref 条款编号 + internal_clause_ref.clause_id
          不满足上述 → 强制置 "未能自动建议"(§3.3 Evidence-First 底线)
    """
    conflict_id: str
    severity: str = "medium"
    new_policy_ref: PolicyRef
    internal_clause_ref: InternalClauseRef
    conflict_type: str = "new_requirement"
    suggested_amendment: str = ""
    evidence: list[EvidenceRef] = Field(default_factory=list)


def _policy_item_to_ref(item: dict, source_url: str, source_name: str) -> PolicyRef:
    """将 Router/direct-tavily/gov_cn 返回的 item 统一转 PolicyRef。"""
    url = source_url or item.get("url", "") or item.get("source_url", "") or ""
    pid = item.get("policy_id") or item.get("id") or ""
    if not pid:
        pid = hashlib.md5((url or item.get("title", "") or "").encode("utf-8")).hexdigest()[:16]
    # publish_date 可能是 str / datetime.date / datetime.datetime / None — 统一 str 后切
    pub_raw = item.get("publish_date") or item.get("date") or ""
    pub_str = str(pub_raw) if pub_raw else ""
    return PolicyRef(
        new_policy_id=pid,
        title=(item.get("title") or "")[:200],
        source_url=url,
        publish_date=pub_str[:40],
        source_name=source_name or "",
    )


def _clause_to_ref(clause: InternalClause) -> InternalClauseRef:
    return InternalClauseRef(
        clause_id=clause.clause_id,
        source_doc=clause.source_doc,
        section_title=clause.section_title,
        business_scope=clause.business_scope,
    )


def _keyword_overlap(
    clause: InternalClause,
    policy_text: str,
) -> tuple[int, list[str]]:
    """keyword overlap 计数 + 命中清单。"""
    hits: list[str] = []
    for kw in clause.keywords:
        if kw and kw in policy_text:
            hits.append(kw)
    return len(hits), hits


def _classify_conflict(clause: InternalClause, policy_text: str, hits: list[str]) -> str:
    """基于规则推断 conflict_type(不走 LLM)。

    启发式:
      - 政策 text 含 "新增 / 新规 / 从 X 日起" + clause.content 有同主题 → new_requirement
      - 政策 text 含 "提高 / 加强 / 上调" → upgraded_requirement
      - 政策 text 含 "废止 / 取消 / 撤销" → revoked
      - 只有术语名改了(keyword 命中但 content 主题变更) → terminology_change
    默认 new_requirement。
    """
    if any(tok in policy_text for tok in ("废止", "取消", "撤销", "失效")):
        return "revoked"
    if any(tok in policy_text for tok in ("提高", "加强", "上调", "更严", "收紧")):
        return "upgraded_requirement"
    if any(tok in policy_text for tok in ("术语", "更名", "改称")):
        return "terminology_change"
    return "new_requirement"


def _classify_severity(conflict_type: str, overlap_count: int) -> str:
    if conflict_type in ("revoked", "upgraded_requirement"):
        return "high" if overlap_count >= 2 else "medium"
    if conflict_type == "terminology_change":
        return "low"
    return "medium" if overlap_count >= 2 else "low"


def _make_amendment(
    clause: InternalClause,
    policy_ref: PolicyRef,
    conflict_type: str,
    hits: list[str],
) -> str:
    """模板化建议(不 LLM 编,只拼接新政策编号 + 内部 clause 编号)。

    如果 policy_ref.title 或 source_url 缺失 → 返回"未能自动建议"(§3.3)。
    """
    if not policy_ref.source_url or not policy_ref.title:
        return "未能自动建议"
    prefix = {
        "new_requirement": "建议按",
        "upgraded_requirement": "建议升级至",
        "revoked": "建议废止",
        "terminology_change": "建议对齐术语至",
    }.get(conflict_type, "建议对齐至")
    hits_str = "、".join(hits[:3]) if hits else ""
    return (
        f"{prefix}「{policy_ref.title[:60]}」({policy_ref.new_policy_id})"
        f" 的新要求,对接内部条款 {clause.clause_id}"
        + (f";关注 {hits_str}" if hits_str else "")
    )


def _conflict_id(new_policy_id: str, clause_id: str, conflict_type: str) -> str:
    raw = f"{new_policy_id}|{clause_id}|{conflict_type}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def cross_compare(
    internal_clauses: list[InternalClause],
    external_policies: list[dict],
    min_overlap: int = 1,
) -> list[ConflictItem]:
    """逐条比对 internal clause × external policy,抽出冲突点。

    external_policies 每条约定字段:
        raw_item: dict       — 原始源返回(Router.scan_latest_policies 格式)
        source_url: str
        source_name: str

    去重: 同一 (new_policy_id, clause_id, conflict_type) 只出一条。

    规则匹配(不走 LLM):
        clause.keywords ∩ policy_text 的命中数 >= min_overlap → 产出冲突
    """
    seen_conflict_ids: set[str] = set()
    out: list[ConflictItem] = []

    for policy_wrap in external_policies:
        raw = policy_wrap.get("raw_item") if isinstance(policy_wrap, dict) else None
        if raw is None and isinstance(policy_wrap, dict):
            raw = policy_wrap
        if not isinstance(raw, dict):
            continue
        source_url = policy_wrap.get("source_url", "") if isinstance(policy_wrap, dict) else ""
        source_name = policy_wrap.get("source_name", "") if isinstance(policy_wrap, dict) else ""
        policy_ref = _policy_item_to_ref(raw, source_url, source_name)
        policy_text = (
            (raw.get("title") or "") + "\n"
            + (raw.get("snippet") or raw.get("content") or raw.get("summary") or "")
        )

        for clause in internal_clauses:
            overlap_count, hits = _keyword_overlap(clause, policy_text)
            if overlap_count < min_overlap:
                continue
            conflict_type = _classify_conflict(clause, policy_text, hits)
            cid = _conflict_id(policy_ref.new_policy_id, clause.clause_id, conflict_type)
            if cid in seen_conflict_ids:
                continue
            seen_conflict_ids.add(cid)
            severity = _classify_severity(conflict_type, overlap_count)
            suggested = _make_amendment(clause, policy_ref, conflict_type, hits)
            evidence = [EvidenceRef(
                source=source_name or policy_ref.source_name or "router",
                url=policy_ref.source_url,
                snippet=(policy_text[:260]).strip(),
            )]
            out.append(ConflictItem(
                conflict_id=cid,
                severity=severity,
                new_policy_ref=policy_ref,
                internal_clause_ref=_clause_to_ref(clause),
                conflict_type=conflict_type,
                suggested_amendment=suggested,
                evidence=evidence,
            ))
    return out


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
