# -*- coding: utf-8 -*-
"""gov.cn 政策/新闻扫描器。

爬取目标:
- 头条: https://www.gov.cn/toutiao/
- 新闻: https://www.gov.cn/xinwen/

已知 DOM 结构: `<ul class="tj3_ul"><li>...<a href title>...<span>date</span></li></ul>`
但 gov.cn 页面改版频繁，解析用 bs4 优先、stdlib html.parser 回退；两者都拿不到则返 ok=False。

依赖:
- httpx（项目已有）
- beautifulsoup4（可选；没装则回退 stdlib 解析）
"""
from __future__ import annotations

import re
from datetime import datetime

import httpx

from ..base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier

try:
    from bs4 import BeautifulSoup  # type: ignore
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

GOV_TOUTIAO_URL = "https://www.gov.cn/toutiao/"
GOV_XINWEN_URL = "https://www.gov.cn/xinwen/"
_UA = "Mozilla/5.0 (compatible; CreditReportAgent/1.0; +https://claude.com/code)"


class GovCnSource(BaseSource):
    name = "gov_cn"
    tier = SourceTier.OFFICIAL
    cost = "free"
    supported_query_types = {"policy", "news"}

    def __init__(self) -> None:
        self._client = httpx.Client(
            timeout=15.0,
            headers={"User-Agent": _UA},
            follow_redirects=True,
        )

    def query(self, request: QueryRequest) -> QueryResult:
        # 目前 /xinwen/ 是 JS 跳转页（raw HTML 只有 500B meta-refresh），
        # 可抓取的静态列表实际都在 /toutiao/。待页面改版后再细分。
        target_url = GOV_TOUTIAO_URL

        try:
            resp = self._client.get(target_url)
        except httpx.HTTPError as e:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"network: {e}",
            )
        if resp.status_code >= 400:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"HTTP {resp.status_code}",
            )

        html = resp.text or ""
        items = _parse_gov_listing(html, base_url=target_url)

        # 关键词过滤（query 非空时）
        kw = (request.query or "").strip()
        if kw:
            items = [it for it in items if kw in it.get("title", "") or kw in it.get("snippet", "")]

        items = items[: max(1, request.limit)]
        if not items:
            return QueryResult(
                ok=False, source_name=self.name,
                error="no articles parsed",
            )

        now = datetime.now().isoformat()
        evidence = [
            Evidence(
                source_name=self.name,
                source_url=it.get("url", ""),
                fetched_at=now,
                raw_excerpt=(it.get("title", "") + "  " + it.get("snippet", ""))[:500],
                confidence=1.0,
            )
            for it in items
        ]
        return QueryResult(
            ok=True,
            items=items,
            evidence=evidence,
            source_name=self.name,
        )


def _parse_gov_listing(html: str, base_url: str) -> list[dict]:
    """解析 gov.cn 列表页 HTML → [{title, url, publish_date, snippet}]。

    bs4 优先，不可用时退化到基于正则的简单抽取。"""
    if _HAS_BS4:
        return _parse_with_bs4(html, base_url)
    return _parse_with_regex(html, base_url)


def _parse_with_bs4(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []

    # 已知主列表: ul.tj3_ul li a
    for ul in soup.select("ul.tj3_ul, ul.news_box, div.news_box ul"):
        for li in ul.find_all("li"):
            a = li.find("a")
            if not a:
                continue
            title = a.get_text(strip=True)
            url = a.get("href", "")
            if url and url.startswith("/"):
                url = "https://www.gov.cn" + url
            date_span = li.find("span")
            date_str = date_span.get_text(strip=True) if date_span else ""
            if title and url:
                items.append({
                    "title": title,
                    "url": url,
                    "publish_date": date_str,
                    "snippet": title,
                })

    # 回退：全页抓所有 a[href*="content"]（gov.cn 内容页路径特征）
    # 现观察到真实路径是 /yaowen/liebiao/YYYYMM/content_NNNN.htm 或 /zhengce/...
    if not items:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not _is_gov_article(href):
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 6:
                continue
            if href.startswith("/"):
                href = "https://www.gov.cn" + href
            items.append({
                "title": title,
                "url": href,
                "publish_date": "",
                "snippet": title,
            })
    # 去重
    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)
    return deduped


def _is_gov_article(href: str) -> bool:
    if not href or href.startswith("javascript"):
        return False
    if "content_" in href:
        return True
    if "/zhengce/" in href:
        return True
    if "/yaowen/" in href and href.endswith(".htm"):
        return True
    if "/xinwen/" in href and href.endswith(".htm"):
        return True
    return False


def _parse_with_regex(html: str, base_url: str) -> list[dict]:
    """stdlib-only 回退解析器。不像 bs4 精确，但够 smoke test 跑通。"""
    items: list[dict] = []
    # 匹配 <a href="..." >TITLE</a>  非贪婪 — 允许 title 跨空白/换行
    pattern = re.compile(
        r'<a[^>]+href="([^"]+)"[^>]*>([^<]{6,200})</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(html):
        href = match.group(1)
        title = match.group(2).strip()
        if not _is_gov_article(href):
            continue
        if href.startswith("/"):
            href = "https://www.gov.cn" + href
        items.append({
            "title": title,
            "url": href,
            "publish_date": "",
            "snippet": title,
        })
    # 去重
    seen = set()
    deduped = []
    for it in items:
        key = it["url"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    return deduped
