# -*- coding: utf-8 -*-
"""Agent4 预警 · Evidence-First 三阶段管线（CLAUDE.md §3.3）

生成目标：对单个在贷客户输出预警摘要（红/黄/绿 + 触发理由）。
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

# BE5 (Phase B Sprint 2 · 2026-05-04): 把 confidence 从静态 0.75/0.5 升级为
# freshness × source_confidence 综合 · 旧/低置信信号自动降权。
from .signal_quality import quality_bundle


@dataclass
class AlertSummaryContext:
    customer_name: str = ""
    external_hits: list = field(default_factory=list)
    """外部扫描命中（裁判文书/工商变更/舆情）。"""
    internal_signals: list = field(default_factory=list)
    """内部指标异常（AlertSignal dict 或对象）。"""
    cross_hits: list = field(default_factory=list)
    """CrossMatcher 双路交叉结果（RuleHit 或 dict）。"""


class AlertSummaryPipeline(EvidenceFirstPipeline[AlertSummaryContext]):
    name = "agent_alert.summary"

    def collect(self, ctx: AlertSummaryContext) -> EvidenceBundle:
        bundle = EvidenceBundle()

        if ctx.customer_name:
            bundle.add(EvidenceItem(
                source="input",
                snippet=f"客户名：{ctx.customer_name}",
                ref_id="customer_name",
                confidence=1.0,
            ))
        else:
            bundle.mark_missing("customer_name")

        for i, hit in enumerate(ctx.external_hits or []):
            title = _get(hit, "title") or _get(hit, "summary") or ""
            url = _get(hit, "url") or ""
            # BE5: 用 quality_bundle 替静态 0.75/0.5 · freshness × source_confidence
            published_at = (
                _get(hit, "published_at")
                or _get(hit, "observed_at")
                or _get(hit, "date")
            )
            source_label = _get(hit, "source") or _get(hit, "source_label") or ""
            qb = quality_bundle(
                rule_id=_get(hit, "rule_id") or "",
                route="external",
                observed_at=published_at,
                source_label=source_label,
                source_url=url,
            )
            bundle.add(EvidenceItem(
                source="external_scan",
                snippet=title[:120],
                ref_id=f"ext_{i}",
                confidence=qb["confidence"],
                meta={"url": url, **qb},
            ))

        for i, sig in enumerate(ctx.internal_signals or []):
            level = _get(sig, "level") or ""
            desc = _get(sig, "description") or _get(sig, "metric") or ""
            observed_at = _get(sig, "observed_at") or _get(sig, "date")
            qb = quality_bundle(
                rule_id=_get(sig, "rule_id") or "",
                route="internal",
                observed_at=observed_at,
                source_type="internal_txn",
            )
            bundle.add(EvidenceItem(
                source="internal_txn",
                snippet=f"[{level}] {desc}"[:120],
                ref_id=f"int_{i}",
                confidence=qb["confidence"],
                meta={"level": level, **qb},
            ))

        for i, h in enumerate(ctx.cross_hits or []):
            rule_id = _get(h, "rule_id") or f"R{i}"
            route = _get(h, "route") or ""
            observed_at = _get(h, "observed_at") or _get(h, "date")
            source_label = _get(h, "source") or _get(h, "evidence_source") or ""
            source_url = _get(h, "url") or _get(h, "evidence_url") or ""
            qb = quality_bundle(
                rule_id=rule_id,
                route=route,
                observed_at=observed_at,
                source_label=source_label,
                source_url=source_url,
            )
            bundle.add(EvidenceItem(
                source="cross_match",
                snippet=f"{rule_id}@{route}",
                ref_id=f"xh_{i}",
                confidence=qb["confidence"],
                meta={"route": route, **qb},
            ))

        return bundle

    def generate_grounded(
        self, ctx: AlertSummaryContext, bundle: EvidenceBundle
    ) -> GroundedDraft:
        citations: list[str] = []
        unfilled: list[str] = []

        name = bundle.by_ref("customer_name")
        if name is None:
            return GroundedDraft(
                content=UNFILLED_MARKER,
                citations=[],
                unfilled_fields=["customer_name"],
            )
        citations.append("customer_name")

        ext = [it for it in bundle.items if it.ref_id.startswith("ext_")]
        inn = [it for it in bundle.items if it.ref_id.startswith("int_")]
        xh = [it for it in bundle.items if it.ref_id.startswith("xh_")]

        level = "绿灯"
        if xh:
            level = "红灯" if len(xh) >= 2 else "黄灯"

        bits = []
        if ext:
            bits.append(f"外部命中 {len(ext)} 条")
            citations.extend(it.ref_id for it in ext[:2])
        if inn:
            bits.append(f"内部指标异常 {len(inn)} 条")
            citations.extend(it.ref_id for it in inn[:2])
        if xh:
            bits.append(f"双路交叉 {len(xh)} 条")
            citations.extend(it.ref_id for it in xh[:2])
        if not bits:
            bits.append("无异常信号")
            unfilled.append("signals")

        content = f"客户「{ctx.customer_name}」 {level}：{'；'.join(bits)}。"

        return GroundedDraft(content=content, citations=citations, unfilled_fields=unfilled)

    def self_audit(
        self,
        ctx: AlertSummaryContext,
        bundle: EvidenceBundle,
        draft: GroundedDraft,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        xh = [it for it in bundle.items if it.ref_id.startswith("xh_")]
        if len(xh) >= 2 and "红灯" not in draft.content:
            findings.append(AuditFinding(
                level="warn",
                code="red_level_mismatch",
                message="双路交叉命中 ≥2 条但未标红灯",
            ))

        if not ctx.customer_name:
            findings.append(AuditFinding(
                level="block",
                code="missing_customer",
                message="缺客户名，无法生成预警摘要",
            ))

        return findings


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
