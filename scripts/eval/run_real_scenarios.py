"""真实场景测试集 runner

per Phase C charter Track D · D6 · 真实金融案例 (脱敏 · 含脏/老/异常数据):

业务专家 walkthrough · CI 跑过才 ship.

Usage:
    py scripts/eval/run_real_scenarios.py
    py scripts/eval/run_real_scenarios.py --strict  # any case fail → exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.evidence_freshness import validate_evidence_chain
from shared.data_tiers import validate_recommendation_sources

CASES_PATH = PROJECT_ROOT / "data" / "eval" / "real_scenario_cases.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "data" / "eval"


def load_cases() -> list[dict]:
    cases = []
    with CASES_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def run_case(case: dict) -> dict:
    """跑单 case · 校验 expected outcome."""
    profile = case.get("customer_profile", {})
    expected_block = case.get("expected_block", False)
    consent = profile.get("consent_status", "granted")

    actual_block = False
    actual_reasons = []

    # 1. PIPL check
    if consent != "granted":
        actual_block = True
        actual_reasons.append(f"consent={consent}")

    # 2. external evidence (if any) · D1+D2 校验
    external = case.get("external_evidence", [])
    if external:
        # D2 freshness
        chain_result = validate_evidence_chain(external)
        if chain_result["block_reason"]:
            actual_block = True
            actual_reasons.append(f"freshness: {chain_result['block_reason']}")
        # D1 tier
        source_result = validate_recommendation_sources(
            [{"url": e.get("source", "")} for e in external]
        )
        if not source_result["valid"]:
            actual_block = True
            actual_reasons.append(f"tier: {source_result['block_reason']}")

    matched = actual_block == expected_block
    return {
        "case_id": case["case_id"],
        "scenario": case["scenario"],
        "expected_block": expected_block,
        "actual_block": actual_block,
        "actual_reasons": actual_reasons,
        "matched": matched,
        "business_expert_pass_criteria": case.get("business_expert_pass_criteria", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    cases = load_cases()
    print(f"Running {len(cases)} real scenario cases...")
    results = [run_case(c) for c in cases]

    pass_n = sum(1 for r in results if r["matched"])
    fail_n = len(cases) - pass_n

    output = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "total": len(cases),
        "pass": pass_n,
        "fail": fail_n,
        "pass_rate": round(pass_n / max(len(cases), 1), 3),
        "results": results,
    }

    ts = int(datetime.now().timestamp())
    out_path = OUTPUT_DIR / f"real_scenarios_run_{ts}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"=== Real Scenario Test Run ===")
    for r in results:
        marker = "[PASS]" if r["matched"] else "[FAIL]"
        print(f"  {marker} {r['case_id']} · {r['scenario'][:40]}")
        if not r["matched"]:
            print(f"    expected_block={r['expected_block']} · actual_block={r['actual_block']}")
            print(f"    reasons: {r['actual_reasons']}")
    print()
    print(f"  Pass: {pass_n}/{len(cases)} ({output['pass_rate']:.1%})")
    print(f"  Output: {out_path.relative_to(PROJECT_ROOT)}")

    if args.strict and fail_n > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
