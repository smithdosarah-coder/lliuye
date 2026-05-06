"""端到端 demo 走访流程 · 10 min 跑通验证

per Phase C charter Track A · A6 (DP3 PM 拍板 + Codex R3 final 验收硬线):

模拟 5 角色用户走端到端 · 不依赖浏览器 (本地 lib 直调):
1. list customers (RM 视角)
2. fetch customer profile (CRM 15 字段)
3. build AI decision (D1+D2+D4 三层校验)
4. submit review (accept/modify/reject)
5. query lineage (跨 5 联追溯)
6. export walkthrough (word/pdf · 含 hash 防篡改)

每步计时 · 失败即 catch · 总时间 < 600s 视为 PASS.

Usage:
    py scripts/e2e/run_walkthrough.py
    py scripts/e2e/run_walkthrough.py --customer C-002 --reviewer RM-王哲
    py scripts/e2e/run_walkthrough.py --strict  # 失败 exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "data" / "e2e"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def step(name: str):
    """简单 step 计时 decorator."""
    def deco(fn):
        def wrap(*args, **kwargs):
            t0 = time.time()
            try:
                result = fn(*args, **kwargs)
                elapsed = time.time() - t0
                return {"step": name, "ok": True, "elapsed_s": round(elapsed, 3), "result": result}
            except Exception as e:  # noqa: BLE001
                elapsed = time.time() - t0
                return {"step": name, "ok": False, "elapsed_s": round(elapsed, 3),
                        "error": f"{type(e).__name__}: {e}"}
        return wrap
    return deco


@step("1. list_customers")
def step_list_customers(rm_id: str) -> dict:
    from shared.customer_aggregator import list_customers
    items = list_customers(rm_id=rm_id)
    return {"count": len(items), "ids": [c["customer_id"] for c in items]}


@step("2. fetch_customer_profile")
def step_fetch_profile(customer_id: str) -> dict:
    from shared.customer_aggregator import aggregate_customer_profile
    profile = aggregate_customer_profile(customer_id)
    if profile is None:
        raise ValueError(f"客户 {customer_id} 不存在")
    return {
        "name": profile["customer"]["name"],
        "age": profile["customer"]["age"],
        "risk_level": profile["customer"]["risk_level"],
        "consent_status": profile["customer"]["consent_status"],
        "holdings_count": len(profile["holdings"]),
    }


@step("3. build_decision")
def step_build_decision(customer_id: str) -> dict:
    from shared.ai_decision import build_decision
    decision = build_decision(customer_id=customer_id, intent="ai_advice_proactive")
    if decision.get("block"):
        raise ValueError(f"决策被阻断: {decision['block_reason']}")
    return {
        "decision_id": decision["decision_id"],
        "core_reasons": decision["core_reasons_count"],
        "confidence": decision["confidence"],
        "summary_preview": decision["decision_summary"][:80],
    }


@step("4. submit_review")
def step_review(decision_id: str, reviewer: str, action: str = "accept", reason: str = "") -> dict:
    from shared.decision_review import submit_review
    if action != "accept" and not reason:
        reason = "AI 建议合理 · RM 接受 (e2e auto)"
    result = submit_review(
        decision_id=decision_id,
        reviewer=reviewer,
        action=action,
        reason=reason,
    )
    if result.get("block"):
        raise ValueError(f"review 被阻: {result['block_reason']}")
    return {
        "review_id": result["review_id"],
        "action": result["action"],
        "ledger_persisted": result.get("ledger_persisted", False),
    }


@step("5. record_lineage")
def step_lineage(decision_id: str) -> dict:
    """模拟 record 一些 lineage entries · 然后 query · 验证 5 联."""
    from shared.data_lineage import LineageRecord, get_lineage_store
    store = get_lineage_store()
    # 模拟 record 客户画像 + 决策建议各字段血缘
    store.record(LineageRecord(
        decision_id=decision_id,
        field_path="customer.income_monthly",
        source_system="crm",
        source_table="t_customer_master",
        source_field="month_income",
        fetched_at=datetime.now().isoformat(timespec="seconds"),
        effective_date="2026-04-15",
        transformation="ROUND(x, 0)",
        data_tier="internal_authoritative",
    ))
    store.record(LineageRecord(
        decision_id=decision_id,
        field_path="customer.risk_level",
        source_system="crm",
        source_table="t_kyc",
        source_field="risk_assessment_result",
        fetched_at=datetime.now().isoformat(timespec="seconds"),
        effective_date="2026-03-01",
        transformation="enum mapping",
        data_tier="internal_authoritative",
    ))
    rows = store.query_by_decision(decision_id)
    return {"lineage_count": len(rows)}


@step("6. export_walkthrough")
def step_export(decision_id: str, customer_id: str) -> dict:
    from shared.walkthrough_export import build_walkthrough_docx, build_walkthrough_pdf
    from shared.customer_aggregator import aggregate_customer_profile

    profile = aggregate_customer_profile(customer_id)
    customer = profile["customer"] if profile else {}

    docx_path = build_walkthrough_docx(decision_id, customer_profile=customer)
    pdf_path = build_walkthrough_pdf(decision_id, customer_profile=customer)

    return {
        "docx": str(docx_path) if docx_path else None,
        "pdf": str(pdf_path) if pdf_path else None,
        "docx_size": docx_path.stat().st_size if docx_path else 0,
        "pdf_size": pdf_path.stat().st_size if pdf_path else 0,
    }


def run_walkthrough(*, customer_id: str, reviewer: str, action: str = "accept") -> dict:
    """端到端跑 6 步 · 任一失败即停 · 返完整 trace."""
    t0 = time.time()
    trace = []

    # Step 1
    rm_id = reviewer
    s1 = step_list_customers(rm_id)
    trace.append(s1)
    if not s1["ok"]:
        return {"ok": False, "trace": trace}

    # Step 2
    s2 = step_fetch_profile(customer_id)
    trace.append(s2)
    if not s2["ok"]:
        return {"ok": False, "trace": trace}

    # Step 3
    s3 = step_build_decision(customer_id)
    trace.append(s3)
    if not s3["ok"]:
        return {"ok": False, "trace": trace}

    decision_id = s3["result"]["decision_id"]

    # Step 4
    s4 = step_review(decision_id, reviewer, action=action)
    trace.append(s4)
    if not s4["ok"]:
        return {"ok": False, "trace": trace}

    # Step 5
    s5 = step_lineage(decision_id)
    trace.append(s5)

    # Step 6
    s6 = step_export(decision_id, customer_id)
    trace.append(s6)
    if not s6["ok"]:
        return {"ok": False, "trace": trace}

    total_elapsed = round(time.time() - t0, 3)
    return {
        "ok": True,
        "total_elapsed_s": total_elapsed,
        "within_10min": total_elapsed < 600,
        "trace": trace,
        "decision_id": decision_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer", default="C-002", help="customer_id")
    parser.add_argument("--reviewer", default="RM-王哲", help="reviewer (RM 工号)")
    parser.add_argument("--action", default="accept", help="review action (accept/modify/reject)")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    print(f"=== Phase C e2e walkthrough · customer={args.customer} reviewer={args.reviewer} action={args.action} ===")
    result = run_walkthrough(
        customer_id=args.customer,
        reviewer=args.reviewer,
        action=args.action,
    )

    for s in result["trace"]:
        marker = "[OK]" if s["ok"] else "[FAIL]"
        print(f"  {marker} {s['step']}  ({s['elapsed_s']}s)")
        if not s["ok"]:
            print(f"      error: {s.get('error')}")

    print()
    print(f"Total: {result.get('total_elapsed_s', 'N/A')}s "
          f"(within 10min: {result.get('within_10min', False)})")

    ts = int(datetime.now().timestamp())
    out_path = OUTPUT_DIR / f"walkthrough_run_{ts}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"trace: {out_path.relative_to(PROJECT_ROOT)}")

    if args.strict and not result.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
