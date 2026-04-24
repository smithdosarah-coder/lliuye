# -*- coding: utf-8 -*-
"""Agent6 报告 · Evidence-First 三阶段管线（结构对齐版 · CLAUDE.md §3.3）

**本文件只做结构对齐**：让 Agent6 也符合 `shared.evidence.EvidenceFirstPipeline`
的三阶段接口，便于跨 Agent 以统一方式观测/测试。**不改 section_generator.py
的既有行为**（它已经是 Evidence-First 的实现范本，主管线仍走 v16_pipeline.py）。

使用场景：
- 跨 Agent uniform testing（比较 6 Agent 的 evidence_trail 结构是否一致）
- 未来 QC gate / observability 层可以按 pipeline.run() 的统一返回值订阅
- 不取代 section_generator.py 的主管线，只是把它抽象成可 subclass 的接口
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
class ReportSectionContext:
    """Agent6 单个 section 的输入 —— 对齐 section_generator 的调用签名。"""

    section_title: str = ""
    template_paragraphs: list = field(default_factory=list)
    """模板骨架段落。"""
    evidence_text: str = ""
    """material_kb / truth_fill 组装好的证据块字符串（Agent6 原生协议）。"""
    financial_anchors: str = ""
    """financial_analyzer.format_for_prompt() 的输出。"""
    industry_card: str = ""
    """industry_benchmark.format_for_prompt() 的输出。"""
    material_anchor: str = ""
    """material_anchor.format_for_prompt() 的输出。"""
    generated_text: str = ""
    """Phase 2 已生成的正文（若外部提供则直接进入 audit）。"""


class ReportSectionPipeline(EvidenceFirstPipeline[ReportSectionContext]):
    """Agent6 section 生成的结构化外壳 —— 委托到 section_generator 的现成 3 阶段。

    Phase 1: 从三件套（financial_anchors / industry_card / material_anchor）+ evidence_text 打包
    Phase 2: 若外部提供 generated_text 则直接使用；否则标 UNFILLED_MARKER
    Phase 3: 用 section_generator 的审计 prompt 思路做一轮数字反查

    **不调 LLM**（主管线走 v16_pipeline.py）；本类是 observability / 跨 Agent 一致性 wrapper。
    """

    name = "agent_report.section"

    def collect(self, ctx: ReportSectionContext) -> EvidenceBundle:
        bundle = EvidenceBundle()

        if ctx.section_title:
            bundle.add(EvidenceItem(
                source="section_input",
                snippet=f"节标题：{ctx.section_title}",
                ref_id="section_title",
                confidence=1.0,
            ))
        else:
            bundle.mark_missing("section_title")

        if ctx.financial_anchors:
            bundle.add(EvidenceItem(
                source="financial_analyzer",
                snippet=ctx.financial_anchors[:400],
                ref_id="financial_anchors",
                confidence=1.0,
                meta={"full_length": len(ctx.financial_anchors)},
            ))
        else:
            bundle.mark_missing("financial_anchors")

        if ctx.industry_card:
            bundle.add(EvidenceItem(
                source="industry_benchmark",
                snippet=ctx.industry_card[:400],
                ref_id="industry_card",
                confidence=0.9,
            ))

        if ctx.material_anchor:
            bundle.add(EvidenceItem(
                source="material_anchor",
                snippet=ctx.material_anchor[:400],
                ref_id="material_anchor",
                confidence=0.95,
            ))

        if ctx.evidence_text:
            bundle.add(EvidenceItem(
                source="truth_fill_kb",
                snippet=ctx.evidence_text[:400],
                ref_id="kb_evidence",
                confidence=0.9,
                meta={"full_length": len(ctx.evidence_text)},
            ))
        else:
            bundle.mark_missing("kb_evidence")

        return bundle

    def generate_grounded(
        self, ctx: ReportSectionContext, bundle: EvidenceBundle
    ) -> GroundedDraft:
        citations = [it.ref_id for it in bundle.items]
        if ctx.generated_text:
            return GroundedDraft(content=ctx.generated_text, citations=citations)
        return GroundedDraft(
            content=UNFILLED_MARKER,
            citations=citations,
            unfilled_fields=["generated_text"],
        )

    def self_audit(
        self,
        ctx: ReportSectionContext,
        bundle: EvidenceBundle,
        draft: GroundedDraft,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        if draft.content == UNFILLED_MARKER:
            findings.append(AuditFinding(
                level="block",
                code="no_generation",
                message="未提供 generated_text（主管线应由 v16_pipeline 填充）",
            ))
            return findings

        if not bundle.by_ref("financial_anchors") and any(ch.isdigit() for ch in draft.content):
            findings.append(AuditFinding(
                level="warn",
                code="numbers_without_financial_anchor",
                message="正文含数字但未挂接 financial_anchors 证据",
            ))

        return findings
