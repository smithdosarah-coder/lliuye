# -*- coding: utf-8 -*-
"""SLO 4 · Task D · 6 agent template path before/after 对照 (LLM-free).

Runs deterministic template paths that were tuned in B1-B6 commits
(channel/credit/alert/compliance/report/riskctrl) and captures
sample outputs to verify rubric pass-fail anchors hit.

Usage:
    py scripts/slo4_verify_template_path.py

Output:
    docs/working/slo4-template-path-samples-2026-05-11.md (markdown report)

NOT a substitute for admin 真号 E2E:
- This only exercises fallback / template paths (LLM unavailable scenario)
- Real LLM path requires DEEPSEEK_API_KEY (SLO 1 dependency) + admin auth (SLO 2)
- Full E2E artifacts (6 docx / json / 决策书 sample) blocked on SLO 1/2 ship
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Rubric pass-fail anchors per docs/contracts/agent-output-rubric-2026-05-11.md
# Each agent: {forbid: [phrases that must NOT appear], require: [regex patterns ≥ N must match]}
RUBRIC_ANCHORS: dict[str, dict[str, Any]] = {
    "channel": {
        "forbid": ["匹配度较高", "见银行产品手册", "可以了解一下", "贷款产品，利率很低"],
        "require_any": [r"专精特新|高新|小巨人", r"\d+\s*万", r"工作日|本周内"],
        "min_require_hit": 3,
    },
    "credit": {
        "forbid": ["综合评分.*建议放款", "四维评分：财务"],
        "require_any": [
            r"财务\s+\d+\s+分\s*\(",
            r"(优秀|良好|合格|薄弱|不达标)",
            r"红灯|黄灯|绿灯",
            r"实际\s+\d",
        ],
        "min_require_hit": 3,
    },
    "alert": {
        "forbid": ["需关注经营趋势", "需关注偿债能力", "需关注变更原因及影响"],
        "require_any": [r"客户经理.*\d+\s*[d天]\s*内", r"现场|电话|核查|核档", r"24h|3d|7d|30d|本周"],
        "min_require_hit": 2,
    },
    "compliance": {
        "forbid": ["模板兜底建议", "确保字段满足新规要求", "合规专家复核"],
        "require_any": [r"暂停|强制整改|监测|法律部 review", r"\d+d\s*内|立即", r"责任部门|业务部门|合规官"],
        "min_require_hit": 2,
    },
    "report": {
        "forbid": ["行业前景广阔", "经营状况良好", "市场地位稳固"],
        "require_any": [r"行业参考卡片", r"政策参考卡片", r"evidence_date|出处"],
        "min_require_hit": 1,  # 只有 anchors 字典非空时才会注入
    },
    "riskctrl": {
        "forbid": ["策略区分能力较强", "策略区分能力一般", "策略区分能力较弱.*建议优化"],
        "require_any": [
            r"同业基准\s+0\.35-0\.50",
            r"(优秀档|健康区间|不建议直接上线|不可上线)",
            r"可上线|定期回测|检查阈值|加新特征|重抽样|样本量",
        ],
        "min_require_hit": 2,
    },
}


def _score_sample(agent: str, sample: str) -> dict[str, Any]:
    """Apply rubric anchors to sample · return {forbidden_hit, require_hits, pass}."""
    anchors = RUBRIC_ANCHORS.get(agent, {})
    forbid = anchors.get("forbid", [])
    require_any = anchors.get("require_any", [])
    min_hit = int(anchors.get("min_require_hit", 0))
    forbidden_hit = [p for p in forbid if re.search(p, sample)]
    require_hits = [r for r in require_any if re.search(r, sample)]
    passed = (not forbidden_hit) and (len(require_hits) >= min_hit)
    return {
        "agent": agent,
        "forbidden_hit": forbidden_hit,
        "require_hits": require_hits,
        "require_required_min": min_hit,
        "passed": passed,
    }


# ---------------------------------------------------------------------------
# Per-agent template path invocation
# ---------------------------------------------------------------------------


def sample_channel() -> str:
    from agent_channel.product_recommender import ProductRecommender
    from shared.kb_scan.models import HitItem, ScanTarget, RiskLevel, IdealProfile

    target = ScanTarget(
        target_id="cand_001",
        target_type="company",
        payload={
            "company_name": "杭州精密电子有限公司",
            "industry": "制造业",
            "sub_industry": "电子元件",
            "scale": "中型",
            "revenue_latest": "15000",
            "main_business": "精密电子元件",
            "tags": ["专精特新", "中标-杭州地铁 7 号线"],
        },
    )
    hit = HitItem(
        hit_id="HIT_001",
        level=RiskLevel.GREEN,
        score=0.85,
        target=target,
        extras={
            "recommended_products": [
                {"channel_name": "保理 / 应收质押融资", "category": "供应链金融", "max_amount": "2000万"},
            ],
        },
    )
    ideal = IdealProfile(profile_id="IP_001", name="制造业·中标信号", policy_context="")
    return ProductRecommender._template_pitch(hit, ideal)


def sample_credit() -> str:
    from agent_credit.advisor_formatter import AdvisorFormatter
    from agent_credit.scoring_model_corporate import CorporateScoringResult
    from agent_credit.rule_engine_v2 import RedLineHit

    af = AdvisorFormatter()
    scoring = CorporateScoringResult(
        composite_score=75,
        financial_score=72,
        industry_score=78,
        operational_score=76,
        guarantee_score=74,
        risk_grade="B",
        sub_scores={"财务": 72, "行业": 78, "经营": 76, "担保": 74},
    )
    hits = [
        RedLineHit(
            rule_id="corp_rl_002",
            rule_name="资产负债率红线",
            category="财务",
            threshold=0.8,
            actual_value=0.82,
            severity="yellow",
            description="资产负债率超 80% 警戒线",
        ),
    ]
    return af._template_reason_corporate(
        "杭州精密电子有限公司", scoring, hits, "通过", 3000, 36
    )


def sample_alert() -> str:
    from agent_alert import alert_engine

    sig = alert_engine._check_debt_ratio(
        {"text": "资产负债率：72%"}, search_text=""
    )
    return sig.description if sig else "(no signal)"


def sample_compliance() -> str:
    from agent_compliance.scan_engine import _template_revisions

    violation = {
        "rule_id": "POL-001",
        "rule_article": "银保监〔2025〕12 号第 3 条",
        "event_id": "EVT-X1",
        "event_type": "loan",
        "severity": "critical",
        "reason": {"conflict_field": "kyc_completed"},
    }
    out = _template_revisions(violation)
    return json.dumps(out, ensure_ascii=False, indent=2)


def sample_report() -> str:
    from v16_op_handlers import _build_material_summary_for_rewrite

    class _Mats:
        def __init__(self) -> None:
            self.financial = {"prompt_block": "营收 12000 万 · 同比增长 14.9%"}
            self.kb = {"facts": {"company_name": "xx 制造"}, "raw_statements": []}
            self.anchors = {
                "industry_cards": [
                    {"title": "电子元件行业", "summary": "2025 国产替代加速 · 中长期景气 · 政策支持 70 亿减税"}
                ],
                "policy_cards": [
                    {
                        "title": "工信部 [2025] 36 号 半导体支持",
                        "summary": "对国产替代企业最高补贴 30%",
                        "evidence_date": "2025-08-15",
                        "source": "工信部官网",
                    }
                ],
            }

        @property
        def facts(self) -> dict:
            return self.kb.get("facts", {})

    return _build_material_summary_for_rewrite(_Mats(), max_chars=4000)


def sample_riskctrl() -> str:
    from agent_riskctrl.metrics import format_metrics_report

    metrics = {
        "ks": 0.42,
        "auc": 0.78,
        "pass_rate": 0.75,
    }
    return format_metrics_report(metrics)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    samplers = {
        "channel": sample_channel,
        "credit": sample_credit,
        "alert": sample_alert,
        "compliance": sample_compliance,
        "report": sample_report,
        "riskctrl": sample_riskctrl,
    }

    results: list[dict[str, Any]] = []
    samples: dict[str, str] = {}
    for agent, sampler in samplers.items():
        try:
            sample = sampler()
        except (RuntimeError, ValueError, TypeError, AttributeError, KeyError, ImportError) as exc:
            sample = f"[ERROR · {type(exc).__name__}: {exc}]"
        samples[agent] = sample
        results.append(_score_sample(agent, sample))

    # write markdown report
    out_path = PROJECT_ROOT / "docs" / "working" / "slo4-template-path-samples-2026-05-11.md"
    lines = ["# SLO 4 · Task D · 6 Agent Template Path Before/After (LLM-free verify)", ""]
    lines.append("> **Scope**: 仅 template / fallback path · LLM 不可用时的 deterministic 路径")
    lines.append("> **Blocker**: admin 真号 E2E (含 LLM 路径) 需 SLO 1 (DEEPSEEK key) + SLO 2 (admin auth)")
    lines.append("> **Rubric**: docs/contracts/agent-output-rubric-2026-05-11.md")
    lines.append("")
    overall_pass = sum(1 for r in results if r["passed"])
    lines.append(f"## Summary · {overall_pass}/6 agent template path pass rubric anchors")
    lines.append("")
    lines.append("| Agent | Passed | Forbidden hit | Require hits / min |")
    lines.append("|---|---|---|---|")
    for r in results:
        forbidden = "✅ none" if not r["forbidden_hit"] else f"❌ {r['forbidden_hit']}"
        req = f"{len(r['require_hits'])}/{r['require_required_min']}"
        lines.append(f"| {r['agent']} | {'✅' if r['passed'] else '❌'} | {forbidden} | {req} |")
    lines.append("")
    for r in results:
        agent = r["agent"]
        lines.append(f"## {agent}")
        lines.append("")
        lines.append("### Sample output (template path)")
        lines.append("")
        lines.append("```")
        lines.append(samples[agent])
        lines.append("```")
        lines.append("")
        lines.append(f"- Passed: {'✅' if r['passed'] else '❌'}")
        if r["forbidden_hit"]:
            lines.append(f"- ❌ Forbidden phrases hit: {r['forbidden_hit']}")
        else:
            lines.append("- ✅ Forbidden phrases: none")
        lines.append(f"- Required anchors hit: {r['require_hits']} ({len(r['require_hits'])}/{r['require_required_min']})")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"summary: {overall_pass}/6 agent template path pass rubric anchors")
    for r in results:
        print(f"  {r['agent']}: {'PASS' if r['passed'] else 'FAIL'}")
    return 0 if overall_pass == 6 else 1


if __name__ == "__main__":
    sys.exit(main())
