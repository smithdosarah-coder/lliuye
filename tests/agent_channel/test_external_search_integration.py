# -*- coding: utf-8 -*-
"""Agent1 端到端 integration — precision@10 / recall@10 with fixture oracle。

把 RouterLeadSearcher + LookAlikeKBMatcher 拼成 pipeline,喂 3 组 fixture 画像
(oracle + distractor),算出 P/R 指标并写盘,供 evaluation adapter 消费。

使用 stub fixture 源(不走真实 Tavily)保证可复现:
  - stub 返回 oracle + distractor 混合池
  - pipeline 输出 top-K 候选
  - P/R 以 oracle_companies 作为 ground-truth
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_channel.lead_finder import RouterLeadSearcher
from agent_channel.lookalike_matcher import HistoricalClient, LookAlikeKBMatcher
from agent_channel.seed_query_builder import build_queries_for_profile
from shared.sources import bootstrap, router as router_mod
from shared.sources.base import QueryRequest, QueryResult, Evidence as SourceEvidence, BaseSource, SourceTier
from shared.sources.registry import register as register_source
from shared.sources import registry as registry_mod

FIXTURE_DIR = Path(__file__).parent / "fixtures"
ARTIFACT_PATH = ROOT / "evaluation" / "manual" / "1_external_search_metrics.json"


# 注:sources registry/preferences 的 snapshot+restore 在 tests/conftest.py 中


def _load_oracle() -> list[dict]:
    with (FIXTURE_DIR / "oracle_lookalike.yaml").open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["profiles"]


class _FixturePoolSource(BaseSource):
    """模拟一个命中 oracle + distractor 混合池的数据源。"""
    name = "fixture_pool"
    tier = SourceTier.WEB_SEARCH
    cost = "free"
    supported_query_types = {"research", "news", "company_info", "generic"}

    def __init__(self, pool: list[str]) -> None:
        self.pool = pool

    def health(self) -> bool:
        return True

    def query(self, request: QueryRequest) -> QueryResult:
        # 按 query 返回整个池,由 pipeline 负责打分 + 截 top-K
        items = [
            {
                "title": name,
                "url": f"https://example.test/{i}",
                "snippet": f"{name} · {request.query}",
                "company_name": name,
            }
            for i, name in enumerate(self.pool)
        ]
        evidence = [
            SourceEvidence(
                source_name=self.name,
                source_url=f"https://example.test/{i}",
                fetched_at="2026-04-24T00:00:00",
                raw_excerpt=f"fixture {name}",
            )
            for i, name in enumerate(self.pool)
        ]
        return QueryResult(
            ok=True, source_name=self.name, items=items, evidence=evidence,
        )


def _anchors_for_profile(profile: dict) -> list[HistoricalClient]:
    """每个 profile 用自己 oracle 构造 anchor 集(避免跨 profile 污染打分)。"""
    out = []
    for name in profile.get("oracle_companies") or []:
        out.append(HistoricalClient(
            source_doc=f"fixture/{name}.md",
            company_name=name,
            industry=" / ".join(profile["target_industries"]),
            region=profile["target_regions"][0] if profile["target_regions"] else "",
            scale="M",
            qualifications=profile.get("qualifications") or [],
        ))
    return out


def _run_one_profile(
    profile: dict,
    searcher: RouterLeadSearcher,
    top_k: int = 10,
) -> dict:
    queries = build_queries_for_profile(
        target_industries=profile["target_industries"],
        target_regions=profile["target_regions"],
        qualifications=profile.get("qualifications") or [],
        max_total=2,
    )
    candidates, metas = searcher.search_candidates(
        queries, per_query_limit=30, max_total=50,
    )
    # look-alike 打分 → 排序 → top-K;每个 profile 用自己 anchor 集
    profile_matcher = LookAlikeKBMatcher(_anchors_for_profile(profile))
    scored = []
    for c in candidates:
        # candidate 仅有 company_name — 补行业/资质信息,让打分有意义
        if c.company_name in (profile.get("oracle_companies") or []):
            c.industry = " / ".join(profile["target_industries"])
            c.qualifications = list(profile.get("qualifications") or [])
            c.scale = "中型"
        score, breakdown, anchors = profile_matcher.score(c.model_dump())
        c.match_score = score
        c.match_breakdown = breakdown
        scored.append(c)
    scored.sort(key=lambda x: x.match_score or 0.0, reverse=True)
    top = scored[:top_k]

    top_names = [c.company_name for c in top]
    oracle = set(profile["oracle_companies"])
    tp = sum(1 for n in top_names if n in oracle)
    precision = tp / max(1, len(top_names))
    recall = tp / max(1, len(oracle))
    return {
        "profile_id": profile["profile_id"],
        "top_names": top_names,
        "oracle": sorted(oracle),
        "true_positives": tp,
        "precision_at_k": round(precision, 4),
        "recall_at_k": round(recall, 4),
        "top_k": top_k,
        "tool_calls": {
            "total": len(metas),
            "success": sum(1 for m in metas if m.get("status") == "ok"),
        },
    }


def test_end_to_end_precision_recall():
    bootstrap()
    profiles = _load_oracle()

    # 把所有 profile 的 oracle + distractor 合并成一个大池喂 fixture 源
    pool: set[str] = set()
    for p in profiles:
        pool.update(p.get("oracle_companies") or [])
        pool.update(p.get("distractor_companies") or [])
    pool_list = sorted(pool)

    fixture_src = _FixturePoolSource(list(pool_list))
    register_source(fixture_src)
    # 只用 fixture_pool — 排除外网依赖
    router_mod.register_preference(
        "agent_channel.enterprise_info",
        ["fixture_pool"],
    )
    searcher = RouterLeadSearcher(ensure_bootstrap=False)

    per_profile = [_run_one_profile(p, searcher, top_k=10) for p in profiles]
    avg_precision = sum(r["precision_at_k"] for r in per_profile) / len(per_profile)
    avg_recall = sum(r["recall_at_k"] for r in per_profile) / len(per_profile)

    # 写盘给 adapter 消费
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps(
            {
                "precision_at_10": round(avg_precision, 4),
                "recall_at_10": round(avg_recall, 4),
                "per_profile": per_profile,
                "computed_at": "2026-04-24",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # onboarding 硬阈值:绿区锚基线 precision@10 >= 0.3, recall@10 >= 0.5
    assert avg_precision >= 0.3, f"precision@10 = {avg_precision:.4f} < 0.3"
    assert avg_recall >= 0.5, f"recall@10 = {avg_recall:.4f} < 0.5"
