"""Sprint 6 D5 · 对照测试 (LLM grounded vs 规则模板) runner

per xlsx v2 3.1 verbatim "对照测试 (LLM grounded vs 规则模板) 5-10 case"

Usage:
    py scripts/eval/run_ab_compare.py --cases data/eval/be12_ab_cases.jsonl

Output:
    data/eval/ab_compare_<timestamp>.json — { case_id, llm_output, rule_output, win, reason }

Scaffold first · 真跑需调 BE12 LLM endpoint · 当前 scaffold 走 segment_router 验证 segment 命中
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVAL_DIR = PROJECT_ROOT / "data" / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def run_rule_route(candidate: dict) -> dict[str, Any]:
    """规则模板路: segment_router 静态分发 (Sprint 6 D3 ship · 确定性)."""
    import sys
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from agent_channel.segment_router import route_candidate
    return route_candidate(candidate)


def run_llm_route(candidate: dict) -> dict[str, Any]:
    """LLM grounded 路: BE12 personal_insight (Sprint 3 ship · 概率).

    Scaffold mode: stub return · 真跑需调 LLM endpoint
    """
    # TODO Sprint 6 D5 真跑: 调 /api/channel/personal_insight 取 talking_points
    return {
        "scaffold_mode": True,
        "note": "Sprint 6 D5 真跑接 BE12 endpoint",
        "expected_template": candidate.get("name", "—"),
    }


def compare_case(case: dict[str, Any]) -> dict[str, Any]:
    """单 case 跑两路 + diff · 判 win."""
    candidate = case["candidate"]
    expected_segment = case.get("expected_segment", "")

    rule_out = run_rule_route(candidate)
    llm_out = run_llm_route(candidate)

    actual_segment = rule_out.get("segment", {}).get("id", "")
    rule_segment_match = actual_segment == expected_segment

    return {
        "case_id": case["case_id"],
        "scenario": case["scenario"],
        "expected_segment": expected_segment,
        "rule_actual_segment": actual_segment,
        "rule_segment_match": rule_segment_match,
        "rule_recommended_products": [
            p["product_name"] for p in rule_out.get("recommended_products", [])
        ],
        "llm_scaffold": llm_out.get("scaffold_mode", False),
        "win": "rule" if rule_segment_match else "tie",
        "reason": (
            "规则模板 segment 命中 expected"
            if rule_segment_match
            else f"规则 segment 不一致 actual={actual_segment} vs expected={expected_segment}"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="data/eval/be12_ab_cases.jsonl")
    args = parser.parse_args()

    cases_path = PROJECT_ROOT / args.cases
    if not cases_path.exists():
        print(f"[err] cases not found: {cases_path}")
        return

    cases = load_cases(cases_path)
    print(f"[ab] loaded {len(cases)} cases")

    results = []
    for c in cases:
        r = compare_case(c)
        results.append(r)
        marker = "PASS" if r["rule_segment_match"] else "FAIL"
        print(f"  [{marker}] {r['case_id']} {r['scenario'][:30]} · segment={r['rule_actual_segment']}")

    pass_n = sum(1 for r in results if r["rule_segment_match"])
    pass_rate = pass_n / max(len(results), 1)

    output = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "cases_n": len(cases),
        "pass_n": pass_n,
        "pass_rate": round(pass_rate, 3),
        "results": results,
    }

    out_path = EVAL_DIR / f"ab_compare_{int(time.time())}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"=== A/B Compare (rule_route segment match) ===")
    print(f"  Pass: {pass_n}/{len(cases)} ({pass_rate:.1%})")
    print(f"  Output: {out_path.relative_to(PROJECT_ROOT)}")
    print()
    print("xlsx v2 3.1 SLA target: 对照测试 5-10 case · LLM 真跑 Sprint 6 D5")


if __name__ == "__main__":
    main()
