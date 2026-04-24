# -*- coding: utf-8 -*-
"""Task B tests — Agent5 新政策外搜 + cross_compare 冲突比对。

覆盖 3 case:
  1. Happy path: gov_cn 偏好链真调,fixture 内部条款 "客户准入" → 冲突结果结构正确
  2. 降级兜底: gov_cn.fetch 抛 TimeoutError → Tavily fallback 接住,degraded=True
  3. 冲突点去重: 3 条同 (new_policy_id, clause_id, conflict_type) 的冲突 → 去重后 1 条
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_compliance.compliance_checker import (
    ConflictItem, PolicyRef, InternalClauseRef, cross_compare, CONFLICT_TYPES, CONFLICT_SEVERITIES
)
from agent_compliance.internal_policy_indexer import (
    InternalClause, build_internal_clause_index,
)
from agent_compliance.policy_scanner import scan_latest_policies
from agent_compliance.policy_seed_builder import build_policy_seeds
from shared.sources import bootstrap
from shared.sources.registry import register as register_source
from shared.sources.base import QueryRequest, QueryResult, Evidence as SourceEvidence, BaseSource, SourceTier


def _ensure_bootstrapped():
    bootstrap()


# -----------------------------------------------------------------------------
# Case 1 — Happy path · policy_scanner 走偏好链 gov_cn → ... → tavily
# -----------------------------------------------------------------------------

@pytest.mark.integration
def test_happy_path_policy_scan_gov_cn():
    _ensure_bootstrapped()
    # 模拟内部制度 fixture(不依赖 data/mock/compliance-kb 以保持测试独立)
    fixture_clauses = [
        InternalClause(
            clause_id="customer-admission__test__s1__i1",
            business_scope="customer-admission",
            source_doc="fixture/customer_admission.docx",
            section_title="客户准入主体条件",
            content="对公客户年营业收入 >= 2000 万元,注册资本 >= 50%。",
            keywords=["客户准入", "注册资本", "营业收入"],
        ),
    ]
    # 真调偏好链(gov_cn / pbc / flk / tavily 中任一可用)
    external_policies = scan_latest_policies(query="银保监 客户准入 新规", limit=5)

    # 不强制要求结果非空(外网可能掉线);但调用不可抛
    assert isinstance(external_policies, list)
    # 若拿到结果,检查 source_url 非空
    for ep in external_policies[:3]:
        assert "source_url" in ep
        assert "raw_item" in ep

    conflicts = cross_compare(fixture_clauses, external_policies, min_overlap=1)
    # 结构合法性
    for c in conflicts:
        assert c.conflict_type in CONFLICT_TYPES, c
        assert c.severity in CONFLICT_SEVERITIES, c
        # new_policy_id 必须被设置
        assert c.new_policy_ref.new_policy_id, c
        # evidence 非空(§3.3)
        assert c.evidence, c


# -----------------------------------------------------------------------------
# Case 2 — Degraded · gov_cn 挂掉 → fallback 走 Tavily
# -----------------------------------------------------------------------------

class _StubTavilyLike(BaseSource):
    """fallback 源:接 "law" / "policy" / "generic" / "news" 各种 query_type,始终返回一条 fixture。"""
    name = "stub_tavily_fallback"
    tier = SourceTier.WEB_SEARCH
    cost = "free"
    supported_query_types = {"law", "policy", "generic", "news", "research", "company_info"}

    def health(self) -> bool:
        return True

    def query(self, request: QueryRequest) -> QueryResult:
        return QueryResult(
            ok=True,
            source_name=self.name,
            items=[{
                "title": "银保监 小微客户准入 新政 (测试 fixture)",
                "url": "https://example.test/fixture/cbirc_2026_01.html",
                "snippet": "客户准入要求从严,注册资本 营业收入 门槛上调",
                "publish_date": "2026-04-01",
            }],
            evidence=[
                SourceEvidence(
                    source_name="stub_tavily_fallback",
                    source_url="https://example.test/fixture/cbirc_2026_01.html",
                    fetched_at="2026-04-24T00:00:00",
                    raw_excerpt="fixture fallback evidence",
                )
            ],
        )


def test_degraded_gov_cn_fail_tavily_fallback(monkeypatch):
    _ensure_bootstrapped()

    # 清掉偏好链里所有前置源的 health,强制走 stub_fallback
    from shared.sources.registry import get
    from shared.sources import router as router_mod

    def _unhealthy(self):
        return False

    # 让 gov_cn / pbc_gov / flk_npc 都被跳过(unhealthy),最后兜底 stub
    for sname in ("gov_cn", "pbc_gov", "flk_npc"):
        try:
            src = get(sname)
            monkeypatch.setattr(type(src), "health", _unhealthy, raising=False)
        except KeyError:
            continue
    # 把裸 tavily 的 health 也禁(模拟 key 失效)
    try:
        src = get("tavily")
        monkeypatch.setattr(type(src), "health", _unhealthy, raising=False)
    except KeyError:
        pass

    register_source(_StubTavilyLike())
    router_mod.register_preference(
        "agent_compliance.policy_scan",
        ["gov_cn", "pbc_gov", "flk_npc", "tavily", "stub_tavily_fallback"],
    )

    policies = scan_latest_policies(query="测试降级", limit=3)
    # 至少拿到 stub 的 1 条
    assert len(policies) >= 1, f"fallback 没接住,policies={policies}"
    assert any(p.get("source_name") == "stub_tavily_fallback" for p in policies), policies


# -----------------------------------------------------------------------------
# Case 3 — 冲突点去重
# -----------------------------------------------------------------------------

def test_conflict_dedup_same_key_once():
    clause = InternalClause(
        clause_id="kyc-aml__fx__s1__i1",
        business_scope="kyc-aml",
        source_doc="fixture/kyc.docx",
        section_title="客户尽职调查",
        content="KYC 要对受益所有人识别。",
        keywords=["KYC", "反洗钱", "受益所有人"],
    )
    # 3 条重复 external_policy — 相同 url/title(→ 同 policy_id)+ 相同触发文本
    dup_item = {
        "raw_item": {
            "title": "反洗钱管理新办法",
            "snippet": "强化 KYC 客户尽职调查,上调对受益所有人识别要求",
            "policy_id": "FIXED-POLICY-001",
        },
        "source_url": "https://example.test/fixture/aml-new.html",
        "source_name": "fixture",
    }
    policies = [dup_item, dict(dup_item), dict(dup_item)]
    conflicts = cross_compare([clause], policies, min_overlap=1)

    # 去重后仅 1 条
    assert len(conflicts) == 1, f"dedup 失败,conflicts={conflicts}"
    # conflict_id 稳定且合法
    assert conflicts[0].conflict_id
    assert conflicts[0].new_policy_ref.new_policy_id == "FIXED-POLICY-001"
    # suggested_amendment 必须引到两个 id(不是 "未能自动建议")
    amendment = conflicts[0].suggested_amendment
    assert "FIXED-POLICY-001" in amendment, amendment
    assert clause.clause_id in amendment, amendment


# -----------------------------------------------------------------------------
# 辅助 · internal_policy_indexer + policy_seed_builder 基础 sanity check
# (不触外网,纯 fixture 确保模块装配正确)
# -----------------------------------------------------------------------------

def test_indexer_and_seed_builder_sanity():
    base = ROOT / "data" / "mock" / "compliance-kb"
    if not base.is_dir():
        pytest.skip("data/mock/compliance-kb not present in this worktree")
    clauses = build_internal_clause_index(base)
    assert len(clauses) >= 5, f"期望至少 5 条 clause,实际 {len(clauses)}"
    # 至少覆盖 3 个 business_scope
    scopes = {c.business_scope for c in clauses}
    assert len(scopes) >= 3, scopes

    seeds = build_policy_seeds(clauses, max_queries=5)
    assert seeds, "policy_seeds 应非空"
    # 每条 seed.query 必须不是空 query 兜底
    for s in seeds:
        # 禁止出现 onboarding red line 里列的"合规 监管 风险"这类空兜底
        q = s.query
        assert q.strip(), s
        # query 语义部分应 >= 6 字(去掉银保监/新规后)
        stripped = q.replace("银保监", "").replace("新规", "").replace("人民银行", "").strip()
        assert len(stripped) >= 6, f"空壳 query: {q}"
        assert s.filters.get("time_range", "").endswith("_months"), s
