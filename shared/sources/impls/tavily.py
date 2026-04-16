# -*- coding: utf-8 -*-
"""Tavily 网页搜索 source — 包装 shared.kb_scan.tavily_client.TavilyClient。

零改动原则：不修改 shared/kb_scan/ 下任何文件，只做上层封装。
"""
from __future__ import annotations

import os
from datetime import datetime

from ..base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier


class TavilySource(BaseSource):
    """Tavily search API 适配器。"""

    name = "tavily"
    tier = SourceTier.WEB_SEARCH
    cost = "paid"   # Tavily 按次计费
    supported_query_types = {"news", "research", "company_info", "generic"}

    def __init__(self) -> None:
        self._api_key = os.environ.get("TAVILY_API_KEY", "").strip()
        self._client = None  # 延迟初始化，避免无 key 时导入报错

    def health(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        """按需构造底层 client，失败也不抛——由 query() 负责返回 ok=False。"""
        if self._client is not None:
            return self._client
        if not self._api_key:
            return None
        try:
            from shared.kb_scan.tavily_client import TavilyClient
            self._client = TavilyClient(api_key=self._api_key)
        except Exception:
            self._client = None
        return self._client

    def query(self, request: QueryRequest) -> QueryResult:
        if not self._api_key:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error="missing TAVILY_API_KEY",
            )

        client = self._get_client()
        if client is None:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error="tavily client init failed",
            )

        include_domains = request.filters.get("include_domains")
        exclude_domains = request.filters.get("exclude_domains")
        search_depth = request.filters.get("search_depth", "advanced")

        try:
            raw = client.search(
                query=request.query,
                max_results=max(1, request.limit),
                search_depth=search_depth,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            )
        except Exception as e:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error=f"{type(e).__name__}: {e}",
            )

        results = raw.get("results") or []
        items: list[dict] = []
        evidence: list[Evidence] = []
        now = datetime.now().isoformat()
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            score = r.get("score", 0.0)
            items.append({
                "title": title,
                "url": url,
                "snippet": content,
                "score": score,
            })
            evidence.append(Evidence(
                source_name=self.name,
                source_url=url,
                fetched_at=now,
                raw_excerpt=(content or "")[:500],
                confidence=float(score) if isinstance(score, (int, float)) else 0.5,
            ))

        if not items:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error="tavily returned no results",
            )

        return QueryResult(
            ok=True,
            items=items,
            evidence=evidence,
            source_name=self.name,
        )
