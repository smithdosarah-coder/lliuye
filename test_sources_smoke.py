# -*- coding: utf-8 -*-
"""Smoke tests for shared.sources.* — NOT pytest; run with:

    py test_sources_smoke.py

Style matches repo convention (test_full_pipeline.py / test_g1_v14.py — top-level
functions, print results, light assertions). Tests that need network will print
SKIP / fail softly so you can eyeball which sources are live.
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.sources import bootstrap
from shared.sources.base import BaseSource, Evidence, QueryRequest, QueryResult
from shared.sources.registry import register, clear, has
from shared.sources.router import Router, register_preference, clear_preferences


# ---------------------------------------------------------------------------
# Type round-trip
# ---------------------------------------------------------------------------

def test_types_instantiation() -> None:
    print("\n== test_types_instantiation ==")
    ev = Evidence(
        source_name="foo",
        source_url="https://example.com",
        fetched_at=datetime.now().isoformat(),
        raw_excerpt="hello",
        confidence=0.9,
    )
    req = QueryRequest(query="q", query_type="generic", limit=5)
    res = QueryResult(
        ok=True, items=[{"x": 1}], evidence=[ev],
        source_name="foo",
    )
    assert res.ok is True
    assert len(res.evidence) == 1 and res.evidence[0].confidence == 0.9
    assert req.limit == 5
    print("  Evidence/QueryRequest/QueryResult round-trip ok")


# ---------------------------------------------------------------------------
# Router degradation
# ---------------------------------------------------------------------------

class _AlwaysFailSource(BaseSource):
    name = "_fail"
    supported_query_types = {"generic"}
    def query(self, request):
        return QueryResult(ok=False, error="intentional fail", source_name=self.name)


class _AlwaysOkSource(BaseSource):
    name = "_ok"
    supported_query_types = {"generic"}
    def query(self, request):
        return QueryResult(
            ok=True,
            items=[{"hit": "yes"}],
            evidence=[Evidence(source_name=self.name,
                               fetched_at=datetime.now().isoformat(),
                               raw_excerpt="mock")],
            source_name=self.name,
        )


def test_router_degrades_correctly() -> None:
    print("\n== test_router_degrades_correctly ==")
    clear(); clear_preferences()
    register(_AlwaysFailSource())
    register(_AlwaysOkSource())
    register_preference("test.chain", ["_fail", "_ok"])
    r = Router().query("test.chain", QueryRequest(query="q", query_type="generic"))
    print(f"  ok={r.ok} source={r.source_name} degraded={r.degraded}")
    assert r.ok is True
    assert r.source_name == "_ok"
    assert r.degraded is True       # should be marked degraded (was not first in chain)
    assert len(r.evidence) >= 1

    # full-fail chain: both sources fail
    clear(); clear_preferences()
    register(_AlwaysFailSource())
    register_preference("test.bad", ["_fail"])
    r2 = Router().query("test.bad", QueryRequest(query="q", query_type="generic"))
    print(f"  full-fail ok={r2.ok} error={r2.error[:60]}")
    assert r2.ok is False
    assert "_fail" in r2.error
    print("  router degradation semantics ok")


# ---------------------------------------------------------------------------
# Live: flk.npc.gov.cn (requires network)
# ---------------------------------------------------------------------------

def test_flk_npc_live() -> None:
    print("\n== test_flk_npc_live (network required) ==")
    try:
        from shared.sources.impls.flk_npc import FlkNpcSource
    except Exception as e:
        print(f"  SKIP import: {e}")
        return
    try:
        s = FlkNpcSource()
        r = s.query(QueryRequest(query="", query_type="law", limit=5))
        print(f"  ok={r.ok} items={len(r.items)} evidence={len(r.evidence)} err={r.error[:80]}")
        if r.ok:
            print(f"  sample bbbs={r.items[0].get('id','')} publish={r.items[0].get('publish','')}")
            # evidence integrity: every item has a matching evidence row
            assert len(r.items) == len(r.evidence)
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Live: gov.cn toutiao (requires network)
# ---------------------------------------------------------------------------

def test_gov_cn_live() -> None:
    print("\n== test_gov_cn_live (network required) ==")
    try:
        from shared.sources.impls.gov_cn import GovCnSource
    except Exception as e:
        print(f"  SKIP import: {e}")
        return
    try:
        s = GovCnSource()
        r = s.query(QueryRequest(query="", query_type="news", limit=5))
        print(f"  ok={r.ok} items={len(r.items)} evidence={len(r.evidence)} err={r.error[:80]}")
        if r.ok:
            first = r.items[0]
            url = first.get("url", "")
            print(f"  sample url={url[:80]}")
            assert "gov.cn" in url, "expected gov.cn domain in item url"
            assert len(r.items) == len(r.evidence)
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Live: akshare (skip if not installed)
# ---------------------------------------------------------------------------

def test_akshare_live() -> None:
    print("\n== test_akshare_live (pip install akshare required) ==")
    try:
        from shared.sources.impls.akshare import AkshareSource
    except ImportError as e:
        print(f"  SKIP no_install: {e}")
        return
    except Exception as e:
        print(f"  SKIP import: {e}")
        return
    try:
        s = AkshareSource()
        r = s.query(QueryRequest(query="CPI", query_type="macro", limit=3))
        print(f"  macro CPI ok={r.ok} items={len(r.items)} err={r.error[:80]}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# bootstrap integration test
# ---------------------------------------------------------------------------

def test_bootstrap_integration() -> None:
    print("\n== test_bootstrap_integration ==")
    clear(); clear_preferences()
    status = bootstrap()
    # At minimum we should have tavily (pure Python) registered
    registered = [k for k, v in status.items() if k.startswith("source.") and not k.endswith(".err") and v is True]
    print(f"  registered sources: {registered}")
    assert any("tavily" in s for s in registered), "tavily must always register"
    # Preferences should be wired for all 3 agents
    for agent in ("agent_compliance", "agent_credit", "agent_report"):
        key = f"prefs.{agent}"
        assert status.get(key) is True, f"preferences for {agent} not registered"
    print("  bootstrap wires sources + preferences ok")


# ---------------------------------------------------------------------------
# Evidence completeness audit
# ---------------------------------------------------------------------------

def test_evidence_completeness() -> None:
    """抽样各 live source，保证每条返回都带 Evidence。CLAUDE.md 证据支撑原则。"""
    print("\n== test_evidence_completeness ==")
    from shared.sources.impls.flk_npc import FlkNpcSource
    from shared.sources.impls.gov_cn import GovCnSource
    for src in [FlkNpcSource(), GovCnSource()]:
        try:
            qt = "law" if src.name == "flk_npc" else "news"
            r = src.query(QueryRequest(query="", query_type=qt, limit=3))
            if not r.ok:
                print(f"  {src.name}: skip (source returned ok=False: {r.error[:40]})")
                continue
            missing = [i for i, it in enumerate(r.items) if i >= len(r.evidence)]
            print(f"  {src.name}: items={len(r.items)} evidence={len(r.evidence)} all_covered={len(missing) == 0}")
            assert len(r.evidence) == len(r.items), \
                f"{src.name}: evidence count mismatch"
        except Exception as e:
            print(f"  {src.name}: FAIL {e}")


# ---------------------------------------------------------------------------
# Live: enterprise_info via Router (Agent1 升级源)
# ---------------------------------------------------------------------------

EXPECTED_ENTERPRISE_FIELDS = (
    "registered_capital",
    "legal_representative",
    "establishment_date",
    "industry",
    "business_scope",
    "registered_address",
)


def _count_filled(item: dict) -> int:
    return sum(1 for f in EXPECTED_ENTERPRISE_FIELDS if str(item.get(f, "")).strip())


def test_enterprise_info_listed() -> None:
    """上市公司路径：贵州茅台。akshare 没装时 Router 会降级到 tavily，也算 ok。"""
    print("\n== test_enterprise_info_listed ==")
    bootstrap()  # 幂等
    r = Router().query(
        "agent_channel.enterprise_info",
        QueryRequest(query="贵州茅台", query_type="company_info", limit=1),
    )
    item = r.items[0] if r.items else {}
    filled = _count_filled(item) if item else 0
    print(f"  贵州茅台: ok={r.ok} source={r.source_name} degraded={r.degraded} "
          f"filled={filled}/6 evidence={len(r.evidence)} err={r.error[:80]}")
    if r.ok and item:
        print(f"  sample fields: industry={item.get('industry','')[:30]!r} "
              f"address={item.get('registered_address','')[:30]!r}")
        # 至少应该有 evidence
        assert len(r.evidence) >= 1, "ok=True 必须带 evidence"


def test_enterprise_info_unlisted() -> None:
    """非上市公司路径（走 Tavily + LLM 抽取）：北京字节跳动科技有限公司。"""
    print("\n== test_enterprise_info_unlisted ==")
    bootstrap()
    r = Router().query(
        "agent_channel.enterprise_info",
        QueryRequest(query="北京字节跳动科技有限公司", query_type="company_info", limit=1),
    )
    item = r.items[0] if r.items else {}
    filled = _count_filled(item) if item else 0
    print(f"  字节跳动: ok={r.ok} source={r.source_name} degraded={r.degraded} "
          f"filled={filled}/6 evidence={len(r.evidence)} err={r.error[:80]}")
    if r.ok and item:
        print(f"  sample fields: legal_rep={item.get('legal_representative','')!r} "
              f"capital={item.get('registered_capital','')!r}")
        assert len(r.evidence) >= 1, "ok=True 必须带 evidence"


# ---------------------------------------------------------------------------
# Wire-through: Agent3 / Agent5 / Agent6 增强模块（接线 ≠ 业务结果）
#
# 目标：证明 enhancer 模块能跑通、能优雅降级、Evidence-First 字段完整。
# 不强求业务字段命中率（取决于 akshare/Tavily 当时是否在线）。
# ---------------------------------------------------------------------------

def test_agent_credit_profile_enhance() -> None:
    """Agent3 增强：贵州茅台 → 自动补字段 + evidence。"""
    print("\n== test_agent_credit_profile_enhance ==")
    bootstrap()
    try:
        from agent_credit.profile_enhancer import enhance_enterprise_profile
    except Exception as e:
        print(f"  FAIL import: {type(e).__name__}: {e}")
        return
    profile = {"company_name": "贵州茅台"}
    enriched, evidence = enhance_enterprise_profile(profile)
    print(f"  贵州茅台: filled={len(enriched)} evidence={len(evidence)} "
          f"sample_field={list(enriched.keys())[:3]}")
    # Evidence-First：有补字段就必须有 evidence；空补也合法（akshare/tavily 都失联）
    if enriched:
        assert evidence, "Evidence-First 违例：补了字段却没有 evidence"
        # evidence 必须有 source_url + fetched_at
        for ev in evidence:
            assert "source_url" in ev and "fetched_at" in ev, \
                f"evidence 缺字段：{ev}"

    # 空名应直接返空，不抛
    e2, ev2 = enhance_enterprise_profile({"company_name": ""})
    assert e2 == {} and ev2 == [], "空 company_name 应返回空"
    print("  agent3 enhancer 接线正常")


def test_agent_compliance_policy_scan() -> None:
    """Agent5 增强：主动扫政策，候选清单 + evidence 锚点。"""
    print("\n== test_agent_compliance_policy_scan ==")
    bootstrap()
    try:
        from agent_compliance.policy_scanner import scan_latest_policies
    except Exception as e:
        print(f"  FAIL import: {type(e).__name__}: {e}")
        return
    results = scan_latest_policies("金融监管", limit=5)
    sample_url = results[0]["source_url"] if results else ""
    print(f"  候选数={len(results)} sample_url={sample_url[:80]}")
    # 接线层面：返回必须是 list（即便全失败也是空 list）
    assert isinstance(results, list), "scan_latest_policies 必须返回 list"
    # Evidence-First：每条候选必须有 source_url + fetched_at + raw_item
    for r in results:
        for k in ("raw_item", "source_url", "fetched_at", "source_name"):
            assert k in r, f"candidate 缺字段 {k}: {r}"

    # 也验证 Agent 类入口
    try:
        from agent_compliance.agent import ComplianceRadarAgent
        agent = ComplianceRadarAgent()
        agent_results = agent.scan_external_policies("金融监管", limit=3)
        print(f"  agent5 method 入口: 候选数={len(agent_results)}")
        assert isinstance(agent_results, list)
    except Exception as e:
        print(f"  agent5 method 入口 SKIP: {type(e).__name__}: {e}")
    print("  agent5 scanner 接线正常")


def test_agent_report_enhance() -> None:
    """Agent6 增强：企业基础信息补齐 + 法规引用核验。"""
    print("\n== test_agent_report_enhance ==")
    bootstrap()
    try:
        from agent_report.material_enhancer import (
            enhance_material_with_enterprise_info,
            lookup_law_citation,
        )
    except Exception as e:
        print(f"  FAIL import: {type(e).__name__}: {e}")
        return
    extra = enhance_material_with_enterprise_info("贵州茅台")
    fields = [k for k in extra.keys() if not k.startswith("_")]
    print(f"  贵州茅台: 补齐字段={fields} url={extra.get('_evidence_url', '')[:60]}")
    # 接线：返回必须是 dict
    assert isinstance(extra, dict), "enhance_material 必须返回 dict"
    # 若有补字段，必须带 evidence_url（Evidence-First）
    if fields:
        assert "_evidence_url" in extra, "Evidence-First 违例：补了字段却没 evidence_url"
        assert "_fetched_at" in extra, "Evidence-First 违例：缺 _fetched_at"

    # 空名直接返空
    assert enhance_material_with_enterprise_info("") == {}, "空名应返空"

    # 法规引用核验
    laws = lookup_law_citation("民法典")
    print(f"  民法典 法规候选={len(laws)}")
    assert isinstance(laws, list), "lookup_law_citation 必须返回 list"
    assert lookup_law_citation("") == [], "空 query 应返空"
    print("  agent6 enhancer 接线正常")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_types_instantiation,
        test_router_degrades_correctly,
        test_bootstrap_integration,
        test_flk_npc_live,
        test_gov_cn_live,
        test_akshare_live,
        test_evidence_completeness,
        test_enterprise_info_listed,
        test_enterprise_info_unlisted,
        test_agent_credit_profile_enhance,
        test_agent_compliance_policy_scan,
        test_agent_report_enhance,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  [ASSERT FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [UNEXPECTED] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n== summary: {len(tests) - failed}/{len(tests)} passed ==")
    sys.exit(0 if failed == 0 else 1)
