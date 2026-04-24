# -*- coding: utf-8 -*-
"""Agent3 授信 · Evidence-First 三阶段管线（CLAUDE.md §3.3）

生成目标：一份授信决策意见摘要（AdvisorFormatter 输出前的锚定草稿）。
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
class CreditDecisionContext:
    """Agent3 上下文 —— 已算出的评分/红线/案例 + 申请事项。"""

    profile: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)
    scoring: Any | None = None
    """CorporateScoringResult 或 RetailScoringResult 或 dict。"""
    rule_hits: list = field(default_factory=list)
    """红线命中列表（RedLineHit 或 dict）。"""
    cases: list = field(default_factory=list)
    segment: str = "corporate"
    request: dict = field(default_factory=dict)
    """申请金额/期限/用途。"""


class CreditDecisionPipeline(EvidenceFirstPipeline[CreditDecisionContext]):
    """Agent3 决策摘要管线。"""

    name = "agent_credit.decision_summary"

    def collect(self, ctx: CreditDecisionContext) -> EvidenceBundle:
        bundle = EvidenceBundle()

        profile = ctx.profile or {}
        company_name = profile.get("company_name") or profile.get("customer_name")
        if company_name:
            bundle.add(EvidenceItem(
                source="profile",
                snippet=f"客户名称：{company_name}",
                ref_id="customer_name",
                confidence=1.0,
            ))
        else:
            bundle.mark_missing("customer_name")

        scoring = ctx.scoring
        composite = None
        if scoring is not None:
            composite = _get(scoring, "composite_score") or _get(scoring, "overall_score")
            if composite is not None:
                bundle.add(EvidenceItem(
                    source="scoring_calc",
                    snippet=f"综合评分：{composite}",
                    ref_id="composite_score",
                    confidence=1.0,
                    meta={"value": composite},
                ))
        if composite is None:
            bundle.mark_missing("composite_score")

        for i, hit in enumerate(ctx.rule_hits or []):
            rule_id = _get(hit, "rule_id") or f"R{i}"
            title = _get(hit, "rule_title") or _get(hit, "title") or ""
            severity = _get(hit, "severity") or "unknown"
            bundle.add(EvidenceItem(
                source="redline_check",
                snippet=f"{rule_id}:{title}",
                ref_id=f"hit_{i}",
                confidence=0.95,
                meta={"severity": severity, "rule_id": rule_id},
            ))

        for i, case in enumerate((ctx.cases or [])[:3]):
            cid = _get(case, "case_id") or f"C{i}"
            summary = _get(case, "summary") or ""
            bundle.add(EvidenceItem(
                source="case_retriever",
                snippet=f"{cid}:{summary}"[:120],
                ref_id=f"case_{i}",
                confidence=0.8,
            ))

        req = ctx.request or {}
        if req.get("amount"):
            bundle.add(EvidenceItem(
                source="request",
                snippet=f"申请额度：{req['amount']} 万",
                ref_id="req_amount",
                confidence=1.0,
                meta={"value": req["amount"]},
            ))
        else:
            bundle.mark_missing("req_amount")

        return bundle

    def generate_grounded(
        self, ctx: CreditDecisionContext, bundle: EvidenceBundle
    ) -> GroundedDraft:
        citations: list[str] = []
        unfilled: list[str] = []

        name = bundle.by_ref("customer_name")
        score = bundle.by_ref("composite_score")
        amount = bundle.by_ref("req_amount")
        hits = [it for it in bundle.items if it.ref_id.startswith("hit_")]

        name_txt = name.snippet.split("：", 1)[-1] if name else UNFILLED_MARKER
        if name:
            citations.append("customer_name")
        else:
            unfilled.append("customer_name")

        score_txt = str(score.meta.get("value")) if score else UNFILLED_MARKER
        if score:
            citations.append("composite_score")
        else:
            unfilled.append("composite_score")

        amount_txt = str(amount.meta.get("value")) if amount else UNFILLED_MARKER
        if amount:
            citations.append("req_amount")
        else:
            unfilled.append("req_amount")

        if hits:
            hit_phrase = f"触发 {len(hits)} 条红线"
            citations.extend(h.ref_id for h in hits[:3])
        else:
            hit_phrase = "未触发红线"

        content = (
            f"客户 {name_txt}（{ctx.segment}）申请额度 {amount_txt} 万，"
            f"综合评分 {score_txt}，{hit_phrase}。"
        )

        return GroundedDraft(content=content, citations=citations, unfilled_fields=unfilled)

    def self_audit(
        self,
        ctx: CreditDecisionContext,
        bundle: EvidenceBundle,
        draft: GroundedDraft,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        score = bundle.by_ref("composite_score")
        if score is not None:
            v = str(score.meta.get("value"))
            if v not in draft.content and v != "None":
                findings.append(AuditFinding(
                    level="warn",
                    code="score_not_cited",
                    message="综合评分在证据中但未出现在草稿中",
                    related_ref="composite_score",
                ))

        if "customer_name" in draft.unfilled_fields and "composite_score" in draft.unfilled_fields:
            findings.append(AuditFinding(
                level="block",
                code="core_fields_missing",
                message="客户名与评分同时缺失，无法生成有效决策摘要",
            ))

        return findings


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
