# -*- coding: utf-8 -*-
"""Agent1 获客 · Evidence-First 三阶段管线（CLAUDE.md §3.3）

生成目标：一条候选企业的切入话术（pitch）。
  Phase 1: 从信号搜索结果 + 企业画像锚点收证据
  Phase 2: 走 LLM（或 fallback）生成话术，只用证据里的事实
  Phase 3: 反查话术里引用的企业名/信号/产品是否在证据中
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from shared.evidence import (
    AuditFinding,
    EvidenceBundle,
    EvidenceFirstPipeline,
    EvidenceItem,
    GroundedDraft,
    UNFILLED_MARKER,
)


@dataclass
class ChannelPitchContext:
    """Agent1 上下文 —— 一条候选企业 + 信号时间线 + 可选 LLM 句柄。"""

    candidate: dict
    """CompanyProfile dict，必含 company_name；可选 industry / size 等。"""
    signals: list[dict]
    """聚合后的信号时间线 [{signal_type, title, url, date, ...}, ...]。"""
    products: list[str]
    """推荐产品清单（已由 product_recommend 域算出）。"""
    llm: Callable | None = None
    """可选 LLM 调用器；None 时走模板兜底。"""


class ChannelPitchPipeline(EvidenceFirstPipeline[ChannelPitchContext]):
    """Agent1 话术生成管线。"""

    name = "agent_channel.pitch"

    def collect(self, context: ChannelPitchContext) -> EvidenceBundle:
        bundle = EvidenceBundle()

        cand = context.candidate or {}
        name = cand.get("company_name") or cand.get("name") or ""
        if name:
            bundle.add(EvidenceItem(
                source="candidate_profile",
                snippet=f"候选企业名：{name}",
                ref_id="cand_name",
                confidence=1.0,
                meta={"field": "company_name"},
            ))
        else:
            bundle.mark_missing("company_name")

        industry = cand.get("industry")
        if industry:
            bundle.add(EvidenceItem(
                source="candidate_profile",
                snippet=f"行业：{industry}",
                ref_id="cand_industry",
                confidence=0.9,
                meta={"field": "industry"},
            ))
        else:
            bundle.mark_missing("industry")

        for i, sig in enumerate(context.signals or []):
            stype = sig.get("signal_type") or sig.get("type") or "unknown"
            title = sig.get("title") or ""
            url = sig.get("url") or ""
            bundle.add(EvidenceItem(
                source=f"signal:{stype}",
                snippet=title or "(无摘要)",
                ref_id=f"sig_{i}",
                confidence=0.8 if url else 0.5,
                meta={"signal_type": stype, "url": url, "date": sig.get("date", "")},
            ))

        if not context.signals:
            bundle.mark_missing("signals")

        for i, prod in enumerate(context.products or []):
            bundle.add(EvidenceItem(
                source="product_recommender",
                snippet=prod,
                ref_id=f"prod_{i}",
                confidence=0.95,
                meta={"field": "recommended_product"},
            ))

        if not context.products:
            bundle.mark_missing("recommended_product")

        return bundle

    def generate_grounded(
        self, context: ChannelPitchContext, bundle: EvidenceBundle
    ) -> GroundedDraft:
        citations: list[str] = []
        unfilled: list[str] = []

        name_item = bundle.by_ref("cand_name")
        if name_item is None:
            return GroundedDraft(
                content=UNFILLED_MARKER,
                citations=[],
                unfilled_fields=["company_name"],
            )
        citations.append("cand_name")

        industry = bundle.by_ref("cand_industry")
        industry_txt = industry.meta.get("field") and industry.snippet if industry else UNFILLED_MARKER
        if industry:
            citations.append("cand_industry")
        else:
            unfilled.append("industry")

        signal_items = [it for it in bundle.items if it.ref_id.startswith("sig_")]
        product_items = [it for it in bundle.items if it.ref_id.startswith("prod_")]

        citations.extend(it.ref_id for it in signal_items[:3])
        citations.extend(it.ref_id for it in product_items[:2])

        if context.llm is not None:
            try:
                content = context.llm({
                    "candidate": context.candidate,
                    "signals": [it.meta for it in signal_items],
                    "products": [it.snippet for it in product_items],
                })
            except Exception:
                content = _template_pitch(name_item, signal_items, product_items, industry_txt)
        else:
            content = _template_pitch(name_item, signal_items, product_items, industry_txt)

        if not signal_items:
            unfilled.append("signals")
        if not product_items:
            unfilled.append("recommended_product")

        return GroundedDraft(content=content, citations=citations, unfilled_fields=unfilled)

    def self_audit(
        self,
        context: ChannelPitchContext,
        bundle: EvidenceBundle,
        draft: GroundedDraft,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        name_item = bundle.by_ref("cand_name")
        if name_item and name_item.snippet.split("：", 1)[-1] not in draft.content:
            findings.append(AuditFinding(
                level="warn",
                code="missing_company_name_in_pitch",
                message="话术中未出现候选企业名",
                related_ref="cand_name",
            ))

        if UNFILLED_MARKER in draft.content and "company_name" in draft.unfilled_fields:
            findings.append(AuditFinding(
                level="block",
                code="no_company_name",
                message="缺候选企业名，已标未能自动填写",
            ))

        return findings


def _template_pitch(
    name_item: EvidenceItem,
    signal_items: list[EvidenceItem],
    product_items: list[EvidenceItem],
    industry_txt: str,
) -> str:
    name = name_item.snippet.split("：", 1)[-1]
    top_sig = signal_items[0].snippet if signal_items else UNFILLED_MARKER
    top_prod = product_items[0].snippet if product_items else UNFILLED_MARKER
    return (
        f"【候选】{name}（{industry_txt}）近期关键信号：{top_sig}；"
        f"建议切入产品：{top_prod}。"
    )
