# -*- coding: utf-8 -*-
"""中国人民银行（pbc.gov.cn）货币政策 / 公告扫描器。

目标栏目:
- 货币政策: http://www.pbc.gov.cn/rmyh/105145/index.html
- 公告通知: http://www.pbc.gov.cn/goutongjiaoliu/113456/index.html

PBC 页面结构较稳定，typical pattern:
  <a href="/rmyh/....html" title="XXX"> TITLE </a>  <span>2024-05-20</span>

bs4 可用则优先；否则降级到正则。
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

PBC_POLICY_URL = "http://www.pbc.gov.cn/rmyh/105145/index.html"
PBC_NOTICE_URL = "http://www.pbc.gov.cn/goutongjiaoliu/113456/index.html"
_UA = "Mozilla/5.0 (compatible; CreditReportAgent/1.0; +https://claude.com/code)"


class PbcGovSource(BaseSource):
    name = "pbc_gov"
    tier = SourceTier.OFFICIAL
    cost = "free"
    supported_query_types = {"policy", "macro", "monetary"}

    def __init__(self) -> None:
        self._client = httpx.Client(
            timeout=15.0,
            headers={"User-Agent": _UA},
            follow_redirects=True,
        )

    def query(self, request: QueryRequest) -> QueryResult:
        # 货币政策 / 宏观 → 货币政策栏；其他 → 公告通知
        if request.query_type in ("monetary", "macro", "policy"):
            url = PBC_POLICY_URL
        else:
            url = PBC_NOTICE_URL

        try:
            resp = self._client.get(url)
        except httpx.HTTPError as e:
            return QueryResult(ok=False, source_name=self.name, error=f"network: {e}")
        if resp.status_code >= 400:
            return QueryResult(ok=False, source_name=self.name, error=f"HTTP {resp.status_code}")

        # PBC 默认编码 GBK/UTF-8 混用，交给 httpx 自动探测即可
        html = resp.text or ""
        items = _parse_pbc_listing(html)

        kw = (request.query or "").strip()
        if kw:
            items = [it for it in items if kw in it.get("title", "")]

        items = items[: max(1, request.limit)]
        if not items:
            return QueryResult(ok=False, source_name=self.name, error="no items parsed")

        now = datetime.now().isoformat()
        evidence = [
            Evidence(
                source_name=self.name,
                source_url=it.get("url", ""),
                fetched_at=now,
                raw_excerpt=it.get("title", "")[:500],
                confidence=1.0,
            )
            for it in items
        ]
        return QueryResult(ok=True, items=items, evidence=evidence, source_name=self.name)


def _parse_pbc_listing(html: str) -> list[dict]:
    if _HAS_BS4:
        return _parse_pbc_bs4(html)
    return _parse_pbc_regex(html)


def _parse_pbc_bs4(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []

    # pbc 用 table + tr + td 结构最常见
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href or href.startswith("javascript"):
            continue
        # pbc 文章特征：数字目录 + .html
        if "/rmyh/" not in href and "/goutongjiaoliu/" not in href and "/zhengcehuobisi/" not in href:
            continue
        if not href.endswith(".html"):
            continue
        title = a.get("title") or a.get_text(strip=True)
        if not title or len(title) < 6:
            continue
        if href.startswith("/"):
            href = "http://www.pbc.gov.cn" + href
        items.append({
            "title": title,
            "url": href,
            "publish_date": "",
            "snippet": title,
        })

    seen = set()
    deduped = []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)
    return deduped


def _parse_pbc_regex(html: str) -> list[dict]:
    items: list[dict] = []
    pattern = re.compile(
        r'<a[^>]+href="([^"]+\.html)"[^>]*>([^<]{6,120})</a>',
        re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        href, title = match.group(1), match.group(2).strip()
        if "/rmyh/" not in href and "/goutongjiaoliu/" not in href and "/zhengcehuobisi/" not in href:
            continue
        if href.startswith("/"):
            href = "http://www.pbc.gov.cn" + href
        items.append({
            "title": title,
            "url": href,
            "publish_date": "",
            "snippet": title,
        })
    seen = set()
    out = []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        out.append(it)
    return out
