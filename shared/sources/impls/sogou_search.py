# -*- coding: utf-8 -*-
"""Sogou 搜索 source · 境内 PIPL 合规备份 (与 Baidu 双源).

Stage E.3 PIPL 合规 (W-E3-A2 · 2026-04-28):
  双源备份 (Baidu + Sogou) · 防 Baidu 单点 · 都境内 · region="cn".

API: 搜狗开放平台 / Tencent 新闻搜索 OpenAPI (key 通过 SOGOU_SEARCH_API_KEY env).
真 API 调用 deferred · 启动时检 key · 缺则 degrader 跳过.
"""
from __future__ import annotations

import os
from datetime import datetime

from ..base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier


class SogouSearchSource(BaseSource):
    """搜狗搜索 API 适配器 (境内 · 双源备份)."""

    name = "sogou_search"
    tier = SourceTier.WEB_SEARCH
    cost = "paid"
    supported_query_types = {"news", "research", "company_info", "generic"}
    region = "cn"

    def __init__(self) -> None:
        self._api_key = os.environ.get("SOGOU_SEARCH_API_KEY", "").strip()
        self._base_url = os.environ.get(
            "SOGOU_SEARCH_BASE_URL",
            "https://api.sogou.com/v1/search",
        )

    def health(self) -> bool:
        return bool(self._api_key)

    def query(self, request: QueryRequest) -> QueryResult:
        if not self._api_key:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error="missing SOGOU_SEARCH_API_KEY (PIPL 合规 · 境内 search 双源备份未配)",
            )

        try:
            results = self._call_sogou_api(request)
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error=f"{type(e).__name__}: {e}",
            )

        items: list[dict] = []
        evidence: list[Evidence] = []
        now = datetime.now().isoformat()
        for r in results:
            title = r.get("title", "")
            url = r.get("url", "")
            snippet = r.get("snippet", "")
            score = r.get("score", 0.65)
            items.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "score": score,
            })
            evidence.append(Evidence(
                source_name=self.name,
                source_url=url,
                fetched_at=now,
                raw_excerpt=(snippet or "")[:500],
                confidence=float(score) if isinstance(score, (int, float)) else 0.65,
            ))

        if not items:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error="sogou search returned no results",
            )

        return QueryResult(
            ok=True,
            items=items,
            evidence=evidence,
            source_name=self.name,
        )

    def _call_sogou_api(self, request: QueryRequest) -> list[dict]:
        """真 API 调用 · production 集成时实装 (同 BaiduSearchSource pattern)."""
        return []
