# -*- coding: utf-8 -*-
"""Agent5 端到端 integration — coverage / FPR with fixture oracle policies。

2 条 fixture 新政策 + oracle 冲突清单 → 跑 cross_compare → 算 coverage + fpr,
写盘供 evaluation adapter 消费。

用 fixture policies 保证可复现(不依赖外网 gov_cn 稳定度)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_compliance.compliance_checker import cross_compare
from agent_compliance.internal_policy_indexer import (
    build_internal_clause_index,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
ARTIFACT_PATH = ROOT / "evaluation" / "manual" / "5_policy_compare_metrics.json"


def _load_oracle() -> dict:
    with (FIXTURE_DIR / "oracle_conflicts.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_end_to_end_coverage_fpr():
    base = ROOT / "data" / "mock" / "compliance-kb"
    if not base.is_dir():
        pytest.skip("data/mock/compliance-kb 缺失,integration 测试跳过")
    clauses = build_internal_clause_index(base)
    assert clauses, "internal clauses 空, integration test 无法跑"

    oracle = _load_oracle()
    fixture_policies = [
        {
            "raw_item": {
                "title": pol["title"],
                "snippet": pol["snippet"],
                "policy_id": pol["policy_id"],
                "publish_date": pol["publish_date"],
            },
            "source_url": pol["source_url"],
            "source_name": "fixture",
        }
        for pol in oracle["policies"]
    ]

    conflicts = cross_compare(clauses, fixture_policies, min_overlap=1)

    # ---- coverage: oracle 命中数 / oracle 总数 ----
    oracle_count = len(oracle["oracle_conflicts"])
    oracle_hit = 0
    for oc in oracle["oracle_conflicts"]:
        for c in conflicts:
            if c.new_policy_ref.new_policy_id != oc["policy_id"]:
                continue
            if c.internal_clause_ref.business_scope != oc["clause_business_scope"]:
                continue
            # content / keywords 命中关键词
            if oc["clause_keyword"] in " ".join(
                [c.internal_clause_ref.section_title] +
                (c.evidence[0].snippet.split() if c.evidence else [])
            ) or any(
                oc["clause_keyword"] in k
                for k in _clause_keywords_by_id(clauses, c.internal_clause_ref.clause_id)
            ):
                oracle_hit += 1
                break
    coverage = oracle_hit / max(1, oracle_count)

    # ---- fpr: 报告了多少 conflict 不属于 oracle ----
    # 近似:同 (policy_id, business_scope) 不在 oracle → false positive
    oracle_pairs = {
        (o["policy_id"], o["clause_business_scope"])
        for o in oracle["oracle_conflicts"]
    }
    false_positive = sum(
        1 for c in conflicts
        if (c.new_policy_ref.new_policy_id,
            c.internal_clause_ref.business_scope) not in oracle_pairs
    )
    reported_total = max(1, len(conflicts))
    fpr = false_positive / reported_total

    # 写盘给 adapter 消费
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(
            {
                "coverage": round(coverage, 4),
                "false_positive_rate": round(fpr, 4),
                "oracle_total": oracle_count,
                "oracle_hit": oracle_hit,
                "reported_total": reported_total,
                "false_positive": false_positive,
                "computed_at": "2026-04-24",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # onboarding 硬阈值:绿区锚基线 coverage >= 0.6, fpr <= 0.3
    assert coverage >= 0.6, f"coverage = {coverage:.4f} < 0.6 (hit={oracle_hit}/{oracle_count})"
    assert fpr <= 0.3, f"fpr = {fpr:.4f} > 0.3 (fp={false_positive}/{reported_total})"


def _clause_keywords_by_id(clauses: list, clause_id: str) -> list[str]:
    for c in clauses:
        if c.clause_id == clause_id:
            return c.keywords
    return []
