# -*- coding: utf-8 -*-
"""Tavily 搜索 API 轻量客户端（同步 + 磁盘缓存）。

- 项目目前的 LLM 调用都是同步（OpenAI SDK），这里保持风格一致，用 httpx.Client。
- 24 小时文件缓存：key = sha1(query + max_results + search_depth + include_domains)
- 默认缓存目录 ./.cache/tavily/，可通过构造函数覆盖。
- 错误（网络/HTTP 4xx 5xx）统一抛 TavilySearchError(status, body_preview)。
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx


TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
TAVILY_EXTRACT_ENDPOINT = "https://api.tavily.com/extract"
TAVILY_ENDPOINT = TAVILY_SEARCH_ENDPOINT  # 兼容老引用
DEFAULT_CACHE_DIR = Path(".cache") / "tavily"
CACHE_TTL = timedelta(hours=24)


class TavilySearchError(Exception):
    """Tavily 调用失败的统一异常。"""

    def __init__(self, message: str, status: int | None = None, body_preview: str = ""):
        self.status = status
        self.body_preview = body_preview
        super().__init__(message)


class TavilyClient:
    """Tavily Search API 同步客户端。"""

    def __init__(self, api_key: str, cache_dir: Path | None = None):
        if not api_key:
            raise TavilySearchError("TavilyClient requires api_key")
        self._api_key = api_key
        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # httpx proxies 从环境变量读（兼容 HTTP_PROXY/HTTPS_PROXY）
        proxies: str | None = (
            os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
            or os.environ.get("https_proxy")
            or os.environ.get("http_proxy")
        )
        # httpx 0.28+ 移除了 proxies kwarg；为了兼容，只在显式设置时传
        client_kwargs: dict[str, Any] = {"timeout": 20.0}
        if proxies:
            # 尝试新 API (proxy=) 回退到老 API (proxies=)
            try:
                self._client = httpx.Client(proxy=proxies, **client_kwargs)
            except TypeError:
                self._client = httpx.Client(proxies=proxies, **client_kwargs)
        else:
            self._client = httpx.Client(**client_kwargs)

    # ---------- cache ----------

    def _cache_key(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        include_domains: list[str] | None,
    ) -> str:
        blob = json.dumps(
            {
                "q": query,
                "m": max_results,
                "d": search_depth,
                "dom": include_domains or [],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str) -> dict | None:
        p = self._cache_dir / f"{key}.json"
        if not p.exists():
            return None
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            cached_at = raw.get("cached_at")
            if cached_at:
                ts = datetime.fromisoformat(cached_at)
                if datetime.now() - ts > CACHE_TTL:
                    return None
            return raw.get("data")
        except (OSError, json.JSONDecodeError, ValueError, TypeError, AttributeError):
            return None

    def _cache_put(self, key: str, data: dict) -> None:
        p = self._cache_dir / f"{key}.json"
        try:
            p.write_text(
                json.dumps(
                    {"cached_at": datetime.now().isoformat(), "data": data},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except (OSError, ValueError, TypeError):
            # 缓存写失败不影响主路径
            pass

    # ---------- public ----------

    def search(
        self,
        query: str,
        max_results: int = 15,
        search_depth: str = "advanced",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> dict:
        """调用 Tavily /search。返回原始 JSON（含 results:[{title,url,content,score}]）。

        缓存命中直接返回。未命中/过期会真调 + 写缓存。
        """
        key = self._cache_key(query, max_results, search_depth, include_domains)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        body: dict[str, Any] = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": False,
        }
        if include_domains:
            body["include_domains"] = include_domains
        if exclude_domains:
            body["exclude_domains"] = exclude_domains

        try:
            resp = self._client.post(TAVILY_SEARCH_ENDPOINT, json=body)
        except httpx.HTTPError as e:
            raise TavilySearchError(f"network error: {e}", status=None, body_preview=str(e)[:500])

        if resp.status_code >= 400:
            preview = (resp.text or "")[:500]
            raise TavilySearchError(
                f"tavily HTTP {resp.status_code}", status=resp.status_code, body_preview=preview
            )

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise TavilySearchError(f"invalid json: {e}", status=resp.status_code, body_preview=resp.text[:500])

        self._cache_put(key, data)
        return data

    def extract(self, urls: list[str], extract_depth: str = "advanced") -> dict:
        """调用 Tavily /extract，返回 {results:[{url, raw_content, ...}]}.

        - 全文抓取（~3000 字 vs search snippet 300 字），用于深度字段提取。
        - 用 sha1 缓存复用，TTL 同 search。
        """
        if not urls:
            return {"results": []}
        # 限制最多 5 个 URL（Tavily 单请求上限通常 20，但太多会慢）
        urls = urls[:5]
        key = hashlib.sha1(
            json.dumps({"extract": urls, "depth": extract_depth},
                       ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        body = {
            "api_key": self._api_key,
            "urls": urls,
            "extract_depth": extract_depth,
        }
        try:
            resp = self._client.post(TAVILY_EXTRACT_ENDPOINT, json=body, timeout=45.0)
        except httpx.HTTPError as e:
            raise TavilySearchError(
                f"extract network error: {e}", status=None, body_preview=str(e)[:500]
            )
        if resp.status_code >= 400:
            preview = (resp.text or "")[:500]
            raise TavilySearchError(
                f"tavily extract HTTP {resp.status_code}",
                status=resp.status_code, body_preview=preview,
            )
        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise TavilySearchError(
                f"extract invalid json: {e}",
                status=resp.status_code, body_preview=resp.text[:500],
            )
        self._cache_put(key, data)
        return data

    def close(self) -> None:
        try:
            self._client.close()
        except (OSError, AttributeError, RuntimeError):
            pass

    def __del__(self):
        self.close()
