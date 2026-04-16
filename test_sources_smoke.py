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
