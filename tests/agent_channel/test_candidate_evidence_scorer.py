# -*- coding: utf-8 -*-
"""候选证据评分器单测 (BE1 Step 1) + pipeline annotate 集成 (BE1 真业务).

per CLAUDE.md §3.1 (确定性 LLM 不算 score) + §3.7.2 (Q-041 4 字段不破).
"""
from __future__ import annotations

from agent_channel.candidate_evidence_scorer import (
    annotate_candidates_with_evidence,
    load_internal_kb,
    score_candidate,
    score_candidates,
)


_INTERNAL_KB_SAMPLE = [
    {"row_id": 1, "name": "晶能新材料", "industry": "新能源·锂电材料", "scale": "中型", "region": "华东·苏州"},
    {"row_id": 2, "name": "辰云半导体",  "industry": "半导体·芯片设计",   "scale": "中型", "region": "华东·上海"},
    {"row_id": 3, "name": "禾盛智造",   "industry": "高端装备·工业母机",   "scale": "中型", "region": "华东·无锡"},
]


def test_score_candidate_high_industry_match():
    """候选行业与 KB 中 ≥ 1 条相似 · industry tier 至少 low."""
    cand = {
        "name": "测试新能源公司",
        "industry": "新能源·锂电材料",
        "scale": "中型",
        "geo": "华东·苏州",
        "similarity": 0.85,
        "signals": [{"type": "bidding", "title": "中标 5000 万项目"}],
    }
    score = score_candidate(cand, internal_kb_companies=_INTERNAL_KB_SAMPLE, rm_region="华东")
    assert 0 <= score["total_score"] <= 100
    assert score["candidate_name"] == "测试新能源公司"
    # 4 维度全有
    dims = {d["dimension"]: d for d in score["dimensions"]}
    assert set(dims.keys()) == {"industry", "scale", "region", "signal"}
    # industry 命中 KB 应有 ≥ 1 evidence
    assert dims["industry"]["tier"] in ("low", "medium", "high")
    assert len(dims["industry"]["evidence"]) >= 1
    # region 完全匹配 (华东·苏州 vs 华东) → high
    assert dims["region"]["tier"] in ("medium", "high")


def test_score_candidate_no_metadata_returns_zero():
    """空 candidate · 全 none tier · total_score 0."""
    score = score_candidate({}, internal_kb_companies=[], rm_region="")
    assert score["total_score"] == 0
    for d in score["dimensions"]:
        assert d["tier"] == "none"


def test_score_candidate_metadata_4_fields_preserved():
    """Q-041 4 字段 (industry/geo/scale/similarity) metadata 透传."""
    cand = {
        "industry": "金融",
        "geo": "华南",
        "scale": "大型",
        "similarity": 0.42,
    }
    score = score_candidate(cand, internal_kb_companies=[], rm_region="")
    md = score["metadata"]
    assert md["industry"] == "金融"
    assert md["geo"] == "华南"
    assert md["scale"] == "大型"
    assert md["similarity"] == 0.42


def test_score_candidates_sort_descending():
    """批量评分按 total_score 降序排."""
    cands = [
        {"name": "low", "industry": "未知行业", "scale": "微型", "geo": "西藏"},
        {
            "name": "high",
            "industry": "新能源·锂电材料",
            "scale": "中型",
            "geo": "华东·苏州",
            "signals": [{"type": "bidding"}, {"type": "growth"}, {"type": "tech"}, {"type": "award"}],
        },
    ]
    out = score_candidates(cands, internal_kb_companies=_INTERNAL_KB_SAMPLE, rm_region="华东")
    assert out[0]["candidate_name"] == "high"
    assert out[1]["candidate_name"] == "low"
    assert out[0]["total_score"] >= out[1]["total_score"]


def test_load_internal_kb_seed_file():
    """seed_companies.jsonl 真存在 · 解析后 ≥ 10 条 (实际 15 条 stub)."""
    kb = load_internal_kb()
    assert len(kb) >= 10
    # 每条至少有 row_id / name / industry
    for c in kb:
        assert c.get("row_id")
        assert c.get("name")
        assert c.get("industry")


def test_annotate_candidates_with_evidence_additive_only():
    """annotate 只加字段 · 原 4 字段 metadata 不被改写 (Q-041 守卫)."""
    candidates = [
        {
            "name": "A",
            "industry": "新能源·锂电材料",
            "geo": "华东·苏州",
            "scale": "中型",
            "similarity": 0.7,
            "signals": [],
        },
    ]
    annotated = annotate_candidates_with_evidence(candidates, rm_region="华东")
    assert len(annotated) == 1
    c = annotated[0]
    # 原 4 字段不破
    assert c["industry"] == "新能源·锂电材料"
    assert c["geo"] == "华东·苏州"
    assert c["scale"] == "中型"
    assert c["similarity"] == 0.7
    # additive 字段
    assert "evidence_score" in c
    assert "evidence_chain" in c
    assert "evidence_dimensions" in c
    assert isinstance(c["evidence_score"], int)
    assert 0 <= c["evidence_score"] <= 100
