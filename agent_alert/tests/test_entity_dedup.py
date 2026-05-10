# -*- coding: utf-8 -*-
"""ALL IN Phase B step 6 · 在贷客户池 EntityKey 归一 unit test.

per CLAUDE.md §11 alert 边界 + entity-resolution-contract v1.1 §4 6 Agent 接入点表.

验证 customer_scanner._resolve_customers in贷客户池 dedup:
- 同 USCC 出现 2 次 (无论 name 怎么写) → 只保留首条
- 仅 name 同 / USCC 异 → 视作不同实体 (谨慎规则 · 不假合并)
- 仅 name 同 / USCC 都缺 → 视作同实体 (name fallback)
"""
from __future__ import annotations

from shared.kb_scan.models import CompanyProfile

from agent_alert.customer_scanner import CustomerScanner


class _StubKB:
    """KB stub · 直接给 companies list."""

    def __init__(self, companies: list[CompanyProfile]):
        self.companies = companies

    def summary(self) -> str:
        return f"stub KB · {len(self.companies)} companies"


class _StubProvider:
    """SearchProvider duck-type stub · 仅暴露 iter_loan_customers (本测试用) ·
    不依赖完整 SearchProvider ABC (避免实现 6 个不相关抽象方法).
    """

    provider_name = "stub"

    def __init__(self, loan_customers: list[CompanyProfile]):
        self._loans = loan_customers

    def iter_loan_customers(self):
        return iter(self._loans)


def _make_co(name: str, uscc: str = "") -> CompanyProfile:
    return CompanyProfile(company_name=name, unified_credit_code=uscc)


def test_kb_dedup_same_uscc_different_name():
    """同 USCC 不同 name → 只保留首条 (entity 归一 · 防多预警)."""
    kb = _StubKB([
        _make_co("腾讯科技深圳", uscc="91440300708461136T"),
        _make_co("腾讯", uscc="91440300708461136T"),  # 同实体 不同 name
    ])
    provider = _StubProvider([])
    scanner = CustomerScanner(kb=kb, search_provider=provider, matcher=None)
    customers = scanner._resolve_customers()
    assert len(customers) == 1
    assert customers[0].company_name == "腾讯科技深圳"  # 首条保留


def test_kb_no_dedup_different_uscc():
    """不同 USCC → 视作不同实体 (即使 name 一样 · 不假合并 · 谨慎规则)."""
    kb = _StubKB([
        _make_co("腾讯", uscc="91440300708461136T"),
        _make_co("腾讯", uscc="91110000100003962Y"),  # 不同 USCC
    ])
    provider = _StubProvider([])
    scanner = CustomerScanner(kb=kb, search_provider=provider, matcher=None)
    customers = scanner._resolve_customers()
    assert len(customers) == 2  # 谨慎规则 · 不合并


def test_kb_dedup_same_name_no_uscc():
    """都缺 USCC + name 同 → 视作同实体 (name fallback)."""
    kb = _StubKB([
        _make_co("某不知名小厂"),
        _make_co("某不知名小厂"),
    ])
    provider = _StubProvider([])
    scanner = CustomerScanner(kb=kb, search_provider=provider, matcher=None)
    customers = scanner._resolve_customers()
    assert len(customers) == 1


def test_provider_lookup_by_entity_key():
    """provider_loans 走 EntityKey 索引 · KB 客户合并 provider extras."""
    kb_customers = [_make_co("腾讯科技深圳", uscc="91440300708461136T")]
    provider_loan = _make_co("腾讯", uscc="91440300708461136T")
    provider_loan.tags = ["high_value"]
    provider_loan.extras = {"risk_tags": ["watch"]}

    kb = _StubKB(kb_customers)
    provider = _StubProvider([provider_loan])
    scanner = CustomerScanner(kb=kb, search_provider=provider, matcher=None)
    customers = scanner._resolve_customers()

    assert len(customers) == 1
    # provider extras 合并到 KB customer · EntityKey 命中 (USCC 一致 · name 不一致也匹)
    assert customers[0].extras.get("risk_tags") == ["watch"]
    assert customers[0].risk_tags == ["watch"]


def test_provider_fallback_dedup_when_no_kb():
    """KB 空 fallback provider · 也按 EntityKey dedup."""
    provider_loans = [
        _make_co("腾讯科技", uscc="91440300708461136T"),
        _make_co("腾讯", uscc="91440300708461136T"),  # 同实体
        _make_co("阿里巴巴", uscc="91110000100003962Y"),  # 不同实体
    ]
    kb = _StubKB([])
    provider = _StubProvider(provider_loans)
    scanner = CustomerScanner(kb=kb, search_provider=provider, matcher=None)
    customers = scanner._resolve_customers()
    assert len(customers) == 2  # 腾讯 dedup → 1 + 阿里 1 = 2
