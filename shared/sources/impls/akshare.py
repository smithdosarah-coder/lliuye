# -*- coding: utf-8 -*-
"""akshare 聚合源 — 研报 / 财务指标 / 宏观数据。

install: `pip install akshare`
如果用户 env 没装，本模块 import 时抛 ImportError，bootstrap() 会捕获并跳过
AkshareSource 的注册——不影响其他源。

禁止让 LLM 「重算」 akshare 返回的数字（违反 CLAUDE.md 数据层优先原则）。
原始数字直接填进 items，上层 agent 也只是透传，不重算。
"""
from __future__ import annotations

from datetime import datetime

import akshare as ak  # noqa: F401 — import 即激活，失败时整模块不可用

from ..base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier


class AkshareSource(BaseSource):
    name = "akshare"
    tier = SourceTier.AGGREGATOR
    cost = "free"
    supported_query_types = {"research", "financial", "macro", "industry"}

    def health(self) -> bool:
        # akshare 没有 API key，import 成功即视为可用；真实可用性由 query 探测
        return True

    def query(self, request: QueryRequest) -> QueryResult:
        qt = request.query_type
        try:
            if qt == "financial":
                return self._query_financial(request)
            if qt == "research":
                return self._query_research(request)
            if qt == "macro":
                return self._query_macro(request)
            if qt == "industry":
                return self._query_industry(request)
        except Exception as e:
            return QueryResult(
                ok=False,
                source_name=self.name,
                error=f"{type(e).__name__}: {e}",
            )

        return QueryResult(
            ok=False,
            source_name=self.name,
            error=f"unsupported query_type: {qt}",
        )

    # ------------------------------------------------------------------
    # financial — 个股财务分析指标
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_stock_code(code: str) -> str:
        s = str(code).strip().upper().replace("SH", "").replace("SZ", "").replace("BJ", "").replace(".", "")
        if not s.isdigit() or len(s) != 6:
            return str(code)
        head = s[0]
        if head == "6":
            return f"{s}.SH"
        if head in ("0", "3"):
            return f"{s}.SZ"
        if head in ("4", "8"):
            return f"{s}.BJ"
        return s

    def _query_financial(self, request: QueryRequest) -> QueryResult:
        stock_code = request.filters.get("stock_code") or request.query
        if not stock_code:
            return QueryResult(
                ok=False, source_name=self.name,
                error="financial query requires stock_code in filters or query",
            )
        stock_code = self._normalize_stock_code(stock_code)
        df = ak.stock_financial_analysis_indicator_em(symbol=str(stock_code))
        if df is None or df.empty:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"no financial data for stock_code={stock_code}",
            )
        # 限制返回条数（最近 N 期）
        df = df.head(max(1, request.limit))
        items = df.to_dict(orient="records")
        now = datetime.now().isoformat()
        evidence = [Evidence(
            source_name=self.name,
            source_url=f"akshare://stock_financial_analysis_indicator_em/{stock_code}",
            fetched_at=now,
            raw_excerpt=f"{len(items)} periods for {stock_code}",
            confidence=1.0,
        )]
        return QueryResult(ok=True, items=items, evidence=evidence, source_name=self.name)

    # ------------------------------------------------------------------
    # research — 研报列表（可按行业过滤）
    # ------------------------------------------------------------------
    def _query_research(self, request: QueryRequest) -> QueryResult:
        symbol = request.filters.get("symbol", "")   # 个股代码（可空 = 全市场）
        industry = request.filters.get("industry", "")
        df = ak.stock_research_report_em(symbol=symbol) if symbol else ak.stock_research_report_em(symbol="")
        if df is None or df.empty:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"no research reports for symbol={symbol!r}",
            )
        if industry:
            # 行业列名 akshare 侧多次改版；做兼容匹配
            industry_col = None
            for col in df.columns:
                if "行业" in str(col):
                    industry_col = col
                    break
            if industry_col is not None:
                df = df[df[industry_col].astype(str).str.contains(industry, na=False)]
        df = df.head(max(1, request.limit))
        if df.empty:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"no research reports matching industry={industry!r}",
            )
        items = df.to_dict(orient="records")
        now = datetime.now().isoformat()
        evidence: list[Evidence] = []
        for it in items:
            # 尝试多种常见列名
            title = it.get("报告名称") or it.get("报告标题") or ""
            url = it.get("报告链接") or it.get("PDF链接") or ""
            evidence.append(Evidence(
                source_name=self.name,
                source_url=str(url),
                fetched_at=now,
                raw_excerpt=str(title)[:500],
                confidence=1.0,
            ))
        return QueryResult(ok=True, items=items, evidence=evidence, source_name=self.name)

    # ------------------------------------------------------------------
    # macro — 宏观指标（CPI / GDP / PMI ...）
    # ------------------------------------------------------------------
    def _query_macro(self, request: QueryRequest) -> QueryResult:
        indicator = (request.filters.get("indicator") or request.query or "").strip().upper()
        mapping = {
            "CPI": ak.macro_china_cpi,
            "PPI": ak.macro_china_ppi,
            "GDP": ak.macro_china_gdp,
            "PMI": ak.macro_china_pmi_yearly,
        }
        fn = mapping.get(indicator)
        if fn is None:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"unsupported macro indicator: {indicator!r}. supported: {sorted(mapping)}",
            )
        df = fn()
        if df is None or df.empty:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"akshare returned empty for {indicator}",
            )
        df = df.head(max(1, request.limit))
        items = df.to_dict(orient="records")
        now = datetime.now().isoformat()
        evidence = [Evidence(
            source_name=self.name,
            source_url=f"akshare://{indicator}",
            fetched_at=now,
            raw_excerpt=f"{indicator} {len(items)} rows",
            confidence=1.0,
        )]
        return QueryResult(ok=True, items=items, evidence=evidence, source_name=self.name)

    # ------------------------------------------------------------------
    # industry — 行业板块快照
    # ------------------------------------------------------------------
    def _query_industry(self, request: QueryRequest) -> QueryResult:
        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return QueryResult(
                ok=False, source_name=self.name,
                error="akshare stock_board_industry_name_em empty",
            )
        keyword = (request.filters.get("industry") or request.query or "").strip()
        if keyword:
            name_col = None
            for col in df.columns:
                if "板块名称" in str(col) or "行业" in str(col):
                    name_col = col
                    break
            if name_col is not None:
                df = df[df[name_col].astype(str).str.contains(keyword, na=False)]
        df = df.head(max(1, request.limit))
        if df.empty:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"no industry match: {keyword!r}",
            )
        items = df.to_dict(orient="records")
        now = datetime.now().isoformat()
        evidence = [Evidence(
            source_name=self.name,
            source_url="akshare://stock_board_industry_name_em",
            fetched_at=now,
            raw_excerpt=f"{len(items)} industry rows",
            confidence=1.0,
        )]
        return QueryResult(ok=True, items=items, evidence=evidence, source_name=self.name)
