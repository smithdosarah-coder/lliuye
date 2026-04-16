# -*- coding: utf-8 -*-
"""国家法律法规数据库（flk.npc.gov.cn）源。

调研结论（2026-04，live probe）:
- 站点是 Vite SPA，所有 /api/*、/api/search、/api/list 走 404 路由回 SPA shell。
- 真实后端挂在 `/law-search/*` 下（从前端打包 JS 里挖出）。
- `/law-search/search/list` 要求的 SearchDto schema 有多处内部 int 枚举，
  未登记不开文档，黑盒拼参数只返 `{"msg":null,"code":500}`。稳定复现。
- **可用**接口:
    - GET `/law-search/index/aggregateData` → 新发生效 / 热搜法规 / 热门下载，JSON 齐整。
    - GET `/law-search/search/recommend?bbbs=<id>` → 关联推荐（需已知 bbbs）。

策略:
- MVP 只用 aggregateData（稳定、真实、官方授权）。items 字段齐全（title/gbrq/flxz/bbbs）。
- 关键词过滤在客户端做——聚合接口一次返回 recent/hot 各类法规，够覆盖「引用最近立法」场景。
- 当用户有精准搜索诉求时，Router 走 tavily 降级即可。
- 以后若反编译出 SearchDto 的完整 schema，新增 _query_search 方法即可，接口不变。

返回 items schema:
[{bbbs, title, publish: gbrq, office: '' , status: '', type: flxz,
  url: 'https://flk.npc.gov.cn/detail.html?MmM5MDlmZGQ2N2U...' }]
"""
from __future__ import annotations

import base64
from datetime import datetime

import httpx

from ..base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier

AGGREGATE_URL = "https://flk.npc.gov.cn/law-search/index/aggregateData"
DETAIL_URL_PREFIX = "https://flk.npc.gov.cn/detail2.html?"

_UA = "Mozilla/5.0 (compatible; CreditReportAgent/1.0; +https://claude.com/code)"


class FlkNpcSource(BaseSource):
    name = "flk_npc"
    tier = SourceTier.OFFICIAL
    cost = "free"
    supported_query_types = {"law", "regulation"}

    def __init__(self) -> None:
        self._client = httpx.Client(
            timeout=20.0,
            headers={
                "User-Agent": _UA,
                "Referer": "https://flk.npc.gov.cn/",
                "Accept": "application/json, text/plain, */*",
            },
            follow_redirects=True,
        )

    def query(self, request: QueryRequest) -> QueryResult:
        try:
            resp = self._client.get(AGGREGATE_URL)
        except httpx.HTTPError as e:
            return QueryResult(ok=False, source_name=self.name, error=f"network: {e}")
        if resp.status_code != 200:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"HTTP {resp.status_code}",
            )
        try:
            body = resp.json()
        except Exception as e:
            return QueryResult(ok=False, source_name=self.name, error=f"invalid json: {e}")

        if body.get("code") != 200:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"api code={body.get('code')} msg={body.get('msg')}",
            )
        data = body.get("data") or {}

        # 合并 xfsd（新发生效）+ popularSearch（热搜法规）+ popularDownload（热门下载）
        # 注：xf 是 dict（按时间分组）不是 list，暂不消费
        merged: list[dict] = []
        for key in ("xfsd", "popularSearch", "popularDownload"):
            arr = data.get(key) or []
            if not isinstance(arr, list):
                continue
            for it in arr:
                if isinstance(it, dict):
                    merged.append(it)

        # 去重：以 bbbs 为 key
        seen: set[str] = set()
        deduped: list[dict] = []
        for it in merged:
            bbbs = it.get("bbbs")
            if not bbbs or bbbs in seen:
                continue
            seen.add(bbbs)
            deduped.append(it)

        # 关键词过滤
        kw = (request.query or "").strip()
        if kw:
            deduped = [it for it in deduped if kw in (it.get("title") or "")]

        deduped = deduped[: max(1, request.limit)]
        if not deduped:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"no laws matching query={kw!r} (flk aggregateData only exposes recent/popular; use tavily for deep search)",
            )

        items: list[dict] = []
        evidence: list[Evidence] = []
        now = datetime.now().isoformat()
        for it in deduped:
            bbbs = it.get("bbbs", "")
            title = it.get("title", "")
            publish = it.get("gbrq", "")
            flxz = it.get("flxz", "")
            # detail.html 需要 bbbs base64 — 前端是这么拼的
            try:
                encoded = base64.b64encode(bbbs.encode("utf-8")).decode("ascii")
                url = DETAIL_URL_PREFIX + encoded
            except Exception:
                url = "https://flk.npc.gov.cn/"

            items.append({
                "id": bbbs,
                "title": title,
                "office": it.get("fbjg", ""),   # 发布机构（通常空）
                "publish": publish,
                "status": it.get("tyzt", ""),   # 通用状态
                "type": flxz,
                "url": url,
            })
            evidence.append(Evidence(
                source_name=self.name,
                source_url=url,
                fetched_at=now,
                raw_excerpt=f"{title}｜{flxz}｜{publish}",
                confidence=1.0,
            ))

        return QueryResult(ok=True, items=items, evidence=evidence, source_name=self.name)
