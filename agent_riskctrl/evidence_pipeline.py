# -*- coding: utf-8 -*-
"""Agent2 风控 · Evidence-First 三阶段管线（CLAUDE.md §3.3）

生成目标：对一组回测指标输出一段策略解读（KS / 通过率 / 坏账率 + 规则可解释性）。
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
class RiskctrlCommentaryContext:
    ruleset_name: str = ""
    metrics: dict = field(default_factory=dict)
    """{ks, psi, pass_rate, bad_rate, confusion: {...}}"""
    per_rule_fp: list = field(default_factory=list)
    """逐条规则的 FP/TN 分布。"""


class RiskctrlCommentaryPipeline(EvidenceFirstPipeline[RiskctrlCommentaryContext]):
    name = "agent_riskctrl.commentary"

    def collect(self, ctx: RiskctrlCommentaryContext) -> EvidenceBundle:
        bundle = EvidenceBundle()

        if ctx.ruleset_name:
            bundle.add(EvidenceItem(
                source="input",
                snippet=f"规则集：{ctx.ruleset_name}",
                ref_id="ruleset_name",
                confidence=1.0,
            ))
        else:
            bundle.mark_missing("ruleset_name")

        m = ctx.metrics or {}
        for key in ("ks", "pass_rate", "bad_rate", "psi"):
            val = m.get(key)
            if val is not None:
                bundle.add(EvidenceItem(
                    source="metrics_analyze",
                    snippet=f"{key}={val}",
                    ref_id=f"metric_{key}",
                    confidence=1.0,
                    meta={"metric": key, "value": val},
                ))
            else:
                bundle.mark_missing(key)

        for i, pr in enumerate(ctx.per_rule_fp or []):
            rid = _get(pr, "rule_id") or f"R{i}"
            fp = _get(pr, "fp_rate")
            bundle.add(EvidenceItem(
                source="backtest",
                snippet=f"{rid} FP={fp}",
                ref_id=f"rule_{i}",
                confidence=0.9,
                meta={"rule_id": rid, "fp_rate": fp},
            ))

        return bundle

    def generate_grounded(
        self, ctx: RiskctrlCommentaryContext, bundle: EvidenceBundle
    ) -> GroundedDraft:
        citations: list[str] = []
        unfilled: list[str] = []

        name = bundle.by_ref("ruleset_name")
        if name is None:
            unfilled.append("ruleset_name")
            return GroundedDraft(content=UNFILLED_MARKER, citations=[], unfilled_fields=unfilled)
        citations.append("ruleset_name")

        ks = bundle.by_ref("metric_ks")
        pass_rate = bundle.by_ref("metric_pass_rate")
        bad_rate = bundle.by_ref("metric_bad_rate")

        parts: list[str] = []
        if ks:
            parts.append(f"KS={ks.meta['value']}")
            citations.append("metric_ks")
        else:
            parts.append(f"KS={UNFILLED_MARKER}")
            unfilled.append("ks")
        if pass_rate:
            parts.append(f"通过率={pass_rate.meta['value']}")
            citations.append("metric_pass_rate")
        else:
            unfilled.append("pass_rate")
        if bad_rate:
            parts.append(f"坏账率={bad_rate.meta['value']}")
            citations.append("metric_bad_rate")
        else:
            unfilled.append("bad_rate")

        content = f"规则集「{ctx.ruleset_name}」回测：{'，'.join(parts)}。"
        return GroundedDraft(content=content, citations=citations, unfilled_fields=unfilled)

    def self_audit(
        self,
        ctx: RiskctrlCommentaryContext,
        bundle: EvidenceBundle,
        draft: GroundedDraft,
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        ks = bundle.by_ref("metric_ks")
        if ks is not None:
            v = ks.meta.get("value")
            try:
                if float(v) < 0.2 and "弱" not in draft.content and "差" not in draft.content:
                    findings.append(AuditFinding(
                        level="info",
                        code="low_ks_not_flagged",
                        message=f"KS={v} 偏低但摘要未提示区分度弱",
                    ))
            except (TypeError, ValueError):
                pass

        if "ks" in draft.unfilled_fields and "pass_rate" in draft.unfilled_fields:
            findings.append(AuditFinding(
                level="block",
                code="core_metrics_missing",
                message="KS 与通过率同时缺失，无法生成有效回测解读",
            ))

        return findings


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
