# -*- coding: utf-8 -*-
"""Agent5 合规 · Evidence-First 三阶段管线（CLAUDE.md §3.3）

生成目标：对单条政策变更 → 存量业务制度矩阵扫描结果生成合规摘要。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.evidence import (
    AuditFinding,
    EvidenceBundle,
    EvidenceFirstPipeline,
    EvidenceItem,
    GroundedDraft,
    UNFILLED_MARKER,
)


@dataclass
class ComplianceSummaryContext:
    policy_title: str = ""
    policy_requirements: list = field(default_factory=list)
    matrix_violations: list = field(default_factory=list)
    defects: list = field(default_factory=list)


class ComplianceSummaryPipeline(EvidenceFirstPipeline[ComplianceSummaryContext]):
    name = "agent_compliance.summary"

    def collect(self, ctx: ComplianceSummaryContext) -> EvidenceBundle:
        bundle = EvidenceBundle()

        if ctx.policy_title:
            bundle.add(EvidenceItem(
                source="policy",
                snippet=f"政策：{ctx.policy_title}",
                ref_id="policy_title",
                confidence=1.0,
            ))
        else:
            bundle.mark_missing("policy_title")

        for i, req in enumerate(ctx.policy_requirements or []):
            text = _get(req, "text") or _get(req, "content") or ""
            category = _get(req, "category") or "misc"
            bundle.add(EvidenceItem(
                source="policy_parse",
                snippet=text[:120],
                ref_id=f"req_{i}",
                confidence=0.9,
                meta={"category": category},
            ))

        for i, v in enumerate(ctx.matrix_violations or []):
            rule_id = _get(v, "rule_id") or f"R{i}"
            severity = _get(v, "severity") or "warn"
            bundle.add(EvidenceItem(
                source="violation_check",
                snippet=f"{rule_id}@{severity}",
                ref_id=f"viol_{i}",
                confidence=0.92,
                meta={"severity": severity, "rule_id": rule_id},
            ))

        for i, d in enumerate(ctx.defects or []):
            cat = _get(d, "category") or ""
            sev = _get(d, "severity") or ""
            bundle.add(EvidenceItem(
                source="defect_classify",
                snippet=f"{cat}@{sev}",
                ref_id=f"def_{i}",
                confidence=0.88,
                meta={"category": cat, "severity": sev},
            ))

        return bundle

    def generate_grounded(
        self, ctx: ComplianceSummaryContext, bundle: EvidenceBundle
    ) -> GroundedDraft:
        citations: list[str] = []
        unfilled: list[str] = []

        pt = bundle.by_ref("policy_title")
        if pt is None:
            return GroundedDraft(
                content=UNFILLED_MARKER,
                citations=[],
                unfilled_fields=["policy_title"],
            )
        citations.append("policy_title")

        reqs = [it for it in bundle.items if it.ref_id.startswith("req_")]
        viols = [it for it in bundle.items if it.ref_id.startswith("viol_")]
        defs = [it for it in bundle.items if it.ref_id.startswith("def_")]

        severe_count = sum(1 for v in viols if v.meta.get("severity") == "严重")
        citations.extend(v.ref_id for v in viols[:3])
        citations.extend(d.ref_id for d in defs[:2])

        bits = [
            f"新增要求 {len(reqs)} 条" if reqs else "政策条款缺失，需补充",
            f"矩阵扫描命中 {len(viols)} 条违规（其中严重 {severe_count}）" if viols else "矩阵扫描无命中",
            f"缺陷 {len(defs)} 条" if defs else "",
        ]

        content = f"政策「{ctx.policy_title}」合规扫描：" + "，".join(b for b in bits if b) + "。"

        if not reqs:
            unfilled.append("policy_requirements")

        return GroundedDraft(content=content, citations=citations, unfilled_fields=unfilled)

    def self_audit(
        self,
        ctx: ComplianceSummaryContext,
        bundle: EvidenceBundle,
        draft: GroundedDraft,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        viols = [it for it in bundle.items if it.ref_id.startswith("viol_")]
        severe = [v for v in viols if v.meta.get("severity") == "严重"]
        if severe and "严重" not in draft.content:
            findings.append(AuditFinding(
                level="warn",
                code="severe_not_flagged",
                message=f"有 {len(severe)} 条严重违规但摘要未体现严重字样",
            ))

        if not ctx.policy_title:
            findings.append(AuditFinding(
                level="block",
                code="missing_policy",
                message="缺政策标题，无法生成合规摘要",
            ))

        return findings


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
