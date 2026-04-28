# -*- coding: utf-8 -*-
"""Baidu 搜索 source · 境内 PIPL 合规备份替代 Tavily.

Stage E.3 PIPL 合规 (W-E3-A2 · 2026-04-28):
  Tavily 境外服务 · production 期不应在 banking 客户使用 (跨境数据流).
  本 source 走 Baidu Search API · 境内服务 · region="cn" · 同 BaseSource 接口.

API 选项:
  1. 百度智能云千帆 / 文心搜索 OpenAPI (推荐 · 真 search · 需 API key)
  2. 简单 HTML scrape (备用 · 不依赖 key · production 不稳)

本 impl 走第 1 路径 · 启动时检 BAIDU_SEARCH_API_KEY · 缺则 health=False · degrader 跳过.
真 API 调用 deferred 到 production 集成阶段 · 当前 stub 返 ok=False with friendly error
(BaseSource pattern with degrader 兼容 · 同 Tavily 缺 key 时行为).
"""
from __future__ import annotations

import os
from datetime import datetime

from ..base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier


class BaiduSearchSource(BaseSource):
    """百度搜索 API 适配器 (境内 · PIPL 合规备份)."""

    name = "baidu_search"
    tier = SourceTier.WEB_SEARCH
    cost = "paid"
    supported_query_types = {"news", "research", "company_info", "policy", "generic"}
    region = "cn"

    def __init__(self) -> None:
        # 千帆 OpenAPI key (production 集成时填)
        self._api_key = os.environ.get("BAIDU_SEARCH_API_KEY", "").strip()
        # search service base url (千帆 / 文心搜索)
        self._base_url = os.environ.get(
            "BAIDU_SEARCH_BASE_URL",
            "https://qianfan.baidubce.com/v2/search",
        )
        self._client = None

    def health(self) -> bool:
        return bool(self._api_key)

    def query(self, request: QueryRequest) -> QueryResult:
        if not self._api_key:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error="missing BAIDU_SEARCH_API_KEY (PIPL 合规 · 境内 search 备份未配 key)",
            )

        # 真 API 调用 deferred · 当前 stub 防止 production 误用未集成的 backend
        # production 集成时实装这部分: requests.post(self._base_url, json={...}, headers={Authorization: f"Bearer {self._api_key}"})
        # 返 results 后转 BaseSource items + evidence

        try:
            results = self._call_baidu_api(request)
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
            score = r.get("score", 0.7)
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
                confidence=float(score) if isinstance(score, (int, float)) else 0.7,
            ))

        if not items:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error="baidu search returned no results",
            )

        return QueryResult(
            ok=True,
            items=items,
            evidence=evidence,
            source_name=self.name,
        )

    def _call_baidu_api(self, request: QueryRequest) -> list[dict]:
        """真 API 调用 · production 集成时实装.

        当前 stub 直返空 list · QueryResult.ok=False · degrader 走下一 source.
        实装 sketch:
            import requests
            resp = requests.post(
                self._base_url,
                json={"query": request.query, "max_results": request.limit},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
        """
        return []
