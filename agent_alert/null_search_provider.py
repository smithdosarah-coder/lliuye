# -*- coding: utf-8 -*-
"""ALL IN Phase B.2 (PM 2026-05-10 真意 reframe) · NullSearchProvider.

派活红线 #4: silent fallback fake 数据 · 派活 reframe: "mock 只能 mock 输入 ·
不能 mock 结果" · MockSearchProvider 在 Tavily 不可用时返合成 mock 结果 · 违此红线.

NullSearchProvider 替代 MockSearchProvider 在 fallback 路径 · 全方法返 [] ·
不出合成数据 · 让 CrossMatcher 仅跑内部规则 (POL- 前缀) · 真实降级语义:
"外部源不可用 · 仅内部规则命中" · banner 明示用户.

Scope:
- agent_alert 写域 · 不动 shared/kb_scan/search_provider.py (禁改域)
- 仅 build_alert_provider 切换 · CrossMatcher / customer_scanner 不知情
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from shared.kb_scan.search_provider import SearchProvider

if TYPE_CHECKING:
    from shared.kb_scan.models import CompanyProfile


class NullSearchProvider(SearchProvider):
    """空 provider · 全方法返 [] · 不合成 mock 结果.

    用途: Tavily key 缺 / Tavily disabled / web_fallback_X 路径 · 替代旧 MockSearchProvider
    silent fallback. CrossMatcher 外部路径返 0 hit · 内部规则仍真跑 · banner 透明告知降级.

    PM 真意 (2026-05-10): 结果不能 mock · 仅输入 mock · NullSearchProvider 满足此约束.
    """

    provider_name = "null"

    def search_companies(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 50,
    ) -> list["CompanyProfile"]:
        return []

    def fetch_company_info(self, company_name: str) -> "CompanyProfile | None":
        return None

    def search_news(
        self,
        query: str,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        return []

    def search_policy_clauses(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        return []

    def iter_loan_customers(
        self,
        filters: dict | None = None,
    ) -> list["CompanyProfile"]:
        return []

    def iter_business_events(
        self,
        customer_id: str = "",
        event_types: list[str] | None = None,
        days: int = 90,
    ) -> list[dict]:
        return []

    def search_court_records(
        self,
        company_name: str,
        limit: int = 5,
    ) -> list[dict]:
        return []
