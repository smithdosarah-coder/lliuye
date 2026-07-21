# -*- coding: utf-8 -*-
"""快速验证 Agent5 v2.0 的真实矩阵扫描产出。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_compliance.knowledge_base import ComplianceKnowledgeBase
from agent_compliance.rule_set_builder import RuleSetBuilder
from agent_compliance.event_extractor import EventExtractor
from agent_compliance.matrix_matcher import MatrixMatcher
from agent_compliance.ledger_exporter import (
    export_ledger_excel, export_remediation_word,
)


def main():
    kb = ComplianceKnowledgeBase.from_scenario("internet_loan")
    print("=== KB ===")
    print(kb.summary())
    print("clauses:", len(kb.clauses),
          "policy_clauses:", len(kb.policy_clauses),
          "internal_clauses:", len(kb.internal_clauses))
    print("business_tables:", {k: len(v) for k, v in kb.business_tables.items()})

    rules = RuleSetBuilder().build(kb)
    print(f"\n=== rules = {len(rules)} ===")
    from collections import Counter
    by_src = Counter(r.source_doc for r in rules)
    print("by_source:", dict(by_src))

    events = EventExtractor().extract(kb)
    by_type = Counter(e["event_type"] for e in events)
    print(f"\n=== events = {len(events)} === by_type={dict(by_type)}")

    matcher = MatrixMatcher(use_llm=False)
    ledger = matcher.match(rules, events)
    print(f"\n=== MATCH RESULT ===")
    print(f"cells = {ledger.cell_count}  hits(raw) = {ledger.hit_count}")
    print(f"severe={len(ledger.severe)}  normal={len(ledger.normal)}  observation={len(ledger.observation)}")
    print(f"duration = {ledger.duration_seconds:.2f}s")
    print("\n-- severe rule titles --")
    for v in ledger.severe:
        eids = [e["event_id"] for e in v.events]
        print(f"  {v.violation_id} {v.rule.rule_id} {v.rule.title}  events={eids}")

    assert len(ledger.severe) == 5, f"expected 5 severe, got {len(ledger.severe)}"
    assert len(ledger.normal) == 1, f"expected 1 normal, got {len(ledger.normal)}"
    assert len(ledger.observation) == 1, f"expected 1 observation, got {len(ledger.observation)}"
    print("\n[OK] 5/1/1 hits produced by real rules")

    # 导出 smoke
    xlsx = export_ledger_excel(ledger, rules, events,
                                output_dir=str(PROJECT_ROOT / "outputs"),
                                scenario_title="互联网贷款合规专项巡检")
    print(f"\nexcel: {xlsx}")
    docx = export_remediation_word(ledger,
                                    output_dir=str(PROJECT_ROOT / "outputs"),
                                    scenario_title="互联网贷款合规专项巡检",
                                    kb_summary=kb.summary())
    print(f"docx: {docx}")


if __name__ == "__main__":
    main()
