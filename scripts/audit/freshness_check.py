"""6 Agent 全栈 freshness audit · 杜绝 Agent1 类系统性问题

per Phase C charter Track D · D9 (Codex R3 升级 critical foundation):

PM 反馈 Agent1 推 10 年前新闻 · 但同类问题大概率在:
- Agent5 合规: 政策时效 (5 年前作废政策仍引?)
- Agent4 预警: 信号时效 (1 年前舆情仍预警?)
- Agent6 报告: 财报数据时效 (用 5 年前财报?)
- Agent3 授信: 同行案例时效 (10 年前案例参考?)
- Agent2 风控: 历史样本时效 (5 年前样本仍训?)

本 script 跑 6 Agent 关键 evidence chain · 输出 audit report:
- json (机读 · CI gate)
- md (人读 · review)

Usage:
    py scripts/audit/freshness_check.py
    py scripts/audit/freshness_check.py --agent channel
    py scripts/audit/freshness_check.py --strict  # 任何 stale 即 exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.evidence_freshness import (
    ClaimType, validate_evidence_chain, FRESHNESS_SLA_DAYS,
)
from shared.data_tiers import classify_source, validate_recommendation_sources

OUTPUT_DIR = PROJECT_ROOT / "data" / "audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 6 Agent 关键 evidence chain (audit 范围)
AGENT_EVIDENCE_PROBES: dict[str, dict[str, Any]] = {
    "channel": {
        "name": "Agent1 客户洞察",
        "critical_paths": [
            "candidate.signals[].evidence_date",
            "candidate.timeline[].at",
            "talking_points[].source_url",
        ],
        "primary_claim_type": ClaimType.NEWS,
        "sample_evidence": [
            # 模拟 mock data 中能找到的 evidence
            {"evidence_date": "2026-04-20", "claim_type": "news", "source": "https://www.cbirc.gov.cn/notice"},
            {"evidence_date": "2014-01-15", "claim_type": "news", "source": "https://news.sina.com.cn"},  # 露馅 case
            {"evidence_date": "2025-12-10", "claim_type": "business_change", "source": "https://www.samr.gov.cn"},
        ],
    },
    "credit": {
        "name": "Agent3 授信决策",
        "critical_paths": [
            "decision.peer_cases[].decision_date",
            "decision.financial_year",
        ],
        "primary_claim_type": ClaimType.CASE_STUDY,
        "sample_evidence": [
            {"evidence_date": "2025-09-01", "claim_type": "case_study", "source": "internal://cases/2025"},
            {"evidence_date": "2026-01-15", "claim_type": "financial", "source": "internal://reports"},
        ],
    },
    "alert": {
        "name": "Agent4 贷后预警",
        "critical_paths": [
            "signal.events[].triggered_at",
            "client.last_contact_at",
        ],
        "primary_claim_type": ClaimType.NEWS,
        "sample_evidence": [
            {"evidence_date": "2026-04-28", "claim_type": "news", "source": "https://www.court.gov.cn"},
            {"evidence_date": "2026-03-10", "claim_type": "legal", "source": "https://wenshu.court.gov.cn"},
        ],
    },
    "compliance": {
        "name": "Agent5 合规扫描",
        "critical_paths": [
            "policy.published_at",
            "policy.effective_date",
        ],
        "primary_claim_type": ClaimType.POLICY,
        "sample_evidence": [
            {"evidence_date": "2026-04-15", "claim_type": "policy", "source": "https://www.cbirc.gov.cn/notice"},
            {"evidence_date": "2025-08-20", "claim_type": "policy", "source": "https://www.pbc.gov.cn"},
            {"evidence_date": "2020-01-01", "claim_type": "policy", "source": "https://www.cbirc.gov.cn"},  # ~5 年 stale
        ],
    },
    "report": {
        "name": "Agent6 报告生成",
        "critical_paths": [
            "report.financial_year",
            "report.section_evidence[].evidence_date",
        ],
        "primary_claim_type": ClaimType.FINANCIAL,
        "sample_evidence": [
            {"evidence_date": "2026-03-31", "claim_type": "financial", "source": "internal://annual_report"},
            {"evidence_date": "2025-12-31", "claim_type": "financial", "source": "internal://q4_report"},
        ],
    },
    "riskctrl": {
        "name": "Agent2 风控 DSL",
        "critical_paths": [
            "backtest.sample_period",
            "rule.effective_at",
        ],
        "primary_claim_type": ClaimType.GENERIC,
        "sample_evidence": [
            {"evidence_date": "2026-04-01", "claim_type": "generic", "source": "internal://backtest_dataset"},
            {"evidence_date": "2024-01-01", "claim_type": "generic", "source": "internal://historical_samples"},
        ],
    },
}


def audit_agent(agent_id: str, probe: dict[str, Any]) -> dict[str, Any]:
    """跑单 Agent freshness audit."""
    chain_result = validate_evidence_chain(probe["sample_evidence"])
    source_result = validate_recommendation_sources(
        [{"url": e.get("source", "")} for e in probe["sample_evidence"]]
    )
    return {
        "agent_id": agent_id,
        "agent_name": probe["name"],
        "critical_paths": probe["critical_paths"],
        "evidence_count": len(probe["sample_evidence"]),
        "freshness": {
            "all_valid": chain_result["all_valid"],
            "core_count": chain_result["core_count"],
            "stale_count": chain_result["stale_count"],
            "missing_date_count": chain_result["missing_date_count"],
            "avg_recency_weight": chain_result["avg_recency_weight"],
            "block_reason": chain_result["block_reason"],
        },
        "tier": {
            "valid": source_result["valid"],
            "tier_distribution": source_result["tier_distribution"],
            "high_trust_count": source_result["high_trust_count"],
            "block_reason": source_result["block_reason"],
            "warnings": source_result["warnings"],
        },
        "passed": chain_result["all_valid"] and source_result["valid"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", help="单 Agent audit (channel / credit / alert / compliance / report / riskctrl)")
    parser.add_argument("--strict", action="store_true", help="任何 stale 即 exit 1")
    args = parser.parse_args()

    if args.agent:
        if args.agent not in AGENT_EVIDENCE_PROBES:
            print(f"[err] unknown agent: {args.agent}")
            return 1
        agents_to_audit = {args.agent: AGENT_EVIDENCE_PROBES[args.agent]}
    else:
        agents_to_audit = AGENT_EVIDENCE_PROBES

    results = {}
    for aid, probe in agents_to_audit.items():
        results[aid] = audit_agent(aid, probe)

    summary = {
        "total_agents": len(results),
        "passed_agents": sum(1 for r in results.values() if r["passed"]),
        "failed_agents": [aid for aid, r in results.items() if not r["passed"]],
        "total_evidence": sum(r["evidence_count"] for r in results.values()),
        "total_stale": sum(r["freshness"]["stale_count"] for r in results.values()),
        "total_missing_date": sum(r["freshness"]["missing_date_count"] for r in results.values()),
    }

    output = {
        "audit_timestamp": datetime.now().isoformat(timespec="seconds"),
        "freshness_sla_days": {ct.value: days for ct, days in FRESHNESS_SLA_DAYS.items()},
        "summary": summary,
        "results": results,
    }

    # JSON output
    ts = int(datetime.now().timestamp())
    json_path = OUTPUT_DIR / f"freshness_audit_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    # MD output
    md_lines: list[str] = []
    md_lines.append(f"# 6 Agent Freshness Audit · {datetime.now().isoformat(timespec='seconds')}")
    md_lines.append("")
    md_lines.append(f"**Summary**: {summary['passed_agents']}/{summary['total_agents']} agents passed · "
                    f"{summary['total_stale']} stale · {summary['total_missing_date']} missing date")
    md_lines.append("")
    md_lines.append("## Per Agent")
    md_lines.append("")
    md_lines.append("| Agent | Pass | Evidence | Stale | Avg Weight | Block Reason |")
    md_lines.append("|---|---|---|---|---|---|")
    for aid, r in results.items():
        pass_mark = "[PASS]" if r["passed"] else "[FAIL]"
        block = r["freshness"].get("block_reason") or r["tier"].get("block_reason") or "-"
        md_lines.append(
            f"| {r['agent_name']} | {pass_mark} | {r['evidence_count']} | "
            f"{r['freshness']['stale_count']} | {r['freshness']['avg_recency_weight']} | {block} |"
        )
    md_lines.append("")
    md_lines.append("## Freshness SLA (DP4 PM 拍板)")
    md_lines.append("")
    md_lines.append("| Claim Type | SLA (days) |")
    md_lines.append("|---|---|")
    for ct, days in FRESHNESS_SLA_DAYS.items():
        md_lines.append(f"| {ct.value} | {days} |")

    md_path = OUTPUT_DIR / f"freshness_audit_{ts}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # Print summary
    print(f"=== 6 Agent Freshness Audit ===")
    print(f"  passed: {summary['passed_agents']}/{summary['total_agents']}")
    print(f"  stale: {summary['total_stale']}")
    print(f"  missing date: {summary['total_missing_date']}")
    print(f"  failed agents: {summary['failed_agents']}")
    print(f"  json: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"  md:   {md_path.relative_to(PROJECT_ROOT)}")

    if args.strict and summary["failed_agents"]:
        print(f"  [strict] FAIL · {len(summary['failed_agents'])} agent(s) have stale evidence")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
