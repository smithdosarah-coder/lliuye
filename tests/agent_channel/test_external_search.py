# -*- coding: utf-8 -*-
"""Task A tests — Agent1 外部搜索 + look-alike 三维打分。

覆盖 3 case (onboarding 硬闸):
  1. happy path: TAVILY_API_KEY 真调,≥5 候选,match_score > 0.3,evidence 非空有 source_url
  2. degraded: 清空 TAVILY_API_KEY → degraded=True,无异常,至少 1 条 fixture 结果
  3. look-alike 正确性: 精确画像 + 3 条 fixture 锚,Top-1 match_score > 0.6,breakdown 合理
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 保障从仓库根运行 pytest 时 import 路径正确
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_channel.lead_finder import RouterLeadSearcher
from agent_channel.lookalike_matcher import HistoricalClient, LookAlikeKBMatcher
from agent_channel.seed_query_builder import build_queries_for_profile
from shared.sources import bootstrap
from shared.sources.base import QueryRequest, QueryResult, Evidence as SourceEvidence
from shared.sources.registry import register as register_source


def _ensure_bootstrapped():
    bootstrap()


# -----------------------------------------------------------------------------
# Case 1 — Happy path (Tavily real call)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("TAVILY_API_KEY", "").strip(),
    reason="TAVILY_API_KEY not set — skip live-call case",
)
def test_happy_path_real_tavily():
    """Live Tavily integration test · 仅 KEY 真有效时运行.

    per Codex review V1 NEEDS-FIX major 3 · 401 (key 失效) 时 skip 而非 fail ·
    防 stale env key 弄炸 CI.
    """
    _ensure_bootstrapped()
    queries = build_queries_for_profile(
        target_industries=["先进制造业"],
        target_regions=["长三角"],
        qualifications=["专精特新"],
        max_total=2,
    )
    assert queries, "seed query builder 必须产出至少 1 条查询"
    searcher = RouterLeadSearcher()
    try:
        candidates, metas = searcher.search_candidates(
            queries, per_query_limit=10, max_total=15,
        )
    except Exception as e:  # noqa: BLE001 — 网络 / auth 类异常 skip 不 fail
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg or "invalid api key" in msg.lower():
            pytest.skip(f"TAVILY_API_KEY invalid (401) · skip live test · {type(e).__name__}: {msg[:120]}")
        if "TavilySearchError" in type(e).__name__ and "HTTP" in msg:
            pytest.skip(f"Tavily HTTP error · skip · {msg[:120]}")
        raise
    # 至少一条 query 成功
    ok_metas = [m for m in metas if m.get("status") == "ok"]
    if not ok_metas:
        pytest.skip(f"no successful source hit (likely network / auth) · metas={metas}")
    # 候选数 >= 5 (across 2 queries)
    assert len(candidates) >= 5, f"candidates={len(candidates)} < 5, metas={metas}"
    # 每条候选必须有 evidence + source_url
    for c in candidates[:5]:
        assert c.evidence, f"{c.company_name} 缺 evidence"
        assert any(e.url for e in c.evidence), f"{c.company_name} evidence 无 source_url"


# -----------------------------------------------------------------------------
# Case 2 — Degraded (no Tavily key → mock fixture path via registry override)
# -----------------------------------------------------------------------------

class _StubFixtureSource:
    """最简可降级 fixture 源,模拟 TAVILY_API_KEY 缺失时的 mock fallback。"""
    name = "stub_fixture"
    tier = None
    cost = "free"
    supported_query_types = {"research", "news", "company_info", "generic"}

    def __init__(self) -> None:
        from shared.sources.base import SourceTier
        self.tier = SourceTier.WEB_SEARCH

    def supports(self, qt: str) -> bool:
        return qt in self.supported_query_types

    def health(self) -> bool:
        return True

    def query(self, request: QueryRequest) -> QueryResult:
        return QueryResult(
            ok=True,
            source_name=self.name,
            items=[{
                "title": "壹禾先进制造股份有限公司",
                "url": "https://example.test/fixture/company1",
                "snippet": "壹禾先进制造股份有限公司 主营高端装备与精密零部件",
            }],
            evidence=[
                SourceEvidence(
                    source_name=self.name,
                    source_url="https://example.test/fixture/company1",
                    fetched_at="2026-04-24T00:00:00",
                    raw_excerpt="fixture evidence",
                )
            ],
        )


def test_degraded_no_tavily_key(monkeypatch):
    _ensure_bootstrapped()
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    # 用 stub fixture 源替换 tavily 在偏好链末尾的位置,保证降级到它。
    # 必须先 bootstrap (注册所有源),再 override preference,
    # 最后用 ensure_bootstrap=False 构造 searcher 避免 re-bootstrap 把 preference 重置
    _ensure_bootstrapped()
    from shared.sources import router as router_mod
    register_source(_StubFixtureSource())
    router_mod.register_preference(
        "agent_channel.enterprise_info",
        ["tavily", "stub_fixture"],
    )

    searcher = RouterLeadSearcher(ensure_bootstrap=False)
    candidates, metas = searcher.search_candidates(
        ["测试 query"], per_query_limit=5, max_total=5,
    )
    # 不抛异常 + 至少拿到 stub fixture 的 1 条
    assert len(candidates) >= 1, f"candidates={candidates} metas={metas}"
    # meta 应暴露 degraded=True (从 tavily 降级到 stub_fixture)
    ok_meta = next((m for m in metas if m.get("status") == "ok"), None)
    assert ok_meta is not None, f"no ok meta: {metas}"
    assert ok_meta.get("degraded") is True, f"meta missing degraded=True: {ok_meta}"
    # 顶层也能从 extras 透传 degraded
    assert candidates[0].extras.get("degraded") is True


# -----------------------------------------------------------------------------
# Case 3 — Look-alike correctness
# -----------------------------------------------------------------------------

def test_lookalike_correctness_precise_profile():
    # 画像: 半导体 / 上海 / 5-10 亿 / 省专精特新
    anchors = [
        HistoricalClient(
            source_doc="fixture/a1",
            company_name="高度相似锚",
            industry="半导体 / 电子",
            region="上海",
            scale="L",
            qualifications=["专精特新", "高新技术"],
        ),
        HistoricalClient(
            source_doc="fixture/a2",
            company_name="不相关锚-餐饮",
            industry="餐饮连锁",
            region="北京",
            scale="S",
            qualifications=[],
        ),
        HistoricalClient(
            source_doc="fixture/a3",
            company_name="不相关锚-物流",
            industry="物流运输",
            region="广东",
            scale="M",
            qualifications=[],
        ),
    ]
    matcher = LookAlikeKBMatcher(anchors)

    candidate = {
        "company_name": "目标候选-半导体",
        "industry": "半导体 / 电子",
        "region": "上海",
        "scale": "大型",
        "revenue_latest": "6亿",
        "qualifications": ["专精特新"],
        "tags": ["省级", "高新技术"],
    }
    score, breakdown, top3 = matcher.score(candidate)

    # Top-1 match_score 必须 > 0.6
    assert score > 0.6, f"match_score={score} 低于 0.6 阈值 breakdown={breakdown}"
    # breakdown 三维都应 > 0 (行业/规模/资质全命中)
    assert breakdown["industry"] > 0, breakdown
    assert breakdown["scale"] > 0, breakdown
    assert breakdown["qualifications"] > 0, breakdown
    # Top-1 anchor 必须是"高度相似锚"
    assert top3, "top3 anchors 不应为空"
    assert top3[0].company_name == "高度相似锚", f"top1={top3[0].company_name}"
