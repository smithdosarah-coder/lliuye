# -*- coding: utf-8 -*-
"""EnterpriseInfoSource — 企业工商基础信息源。

设计动机：
    Agent1 全渠道流量匹配 (_fetch_qcc_info) 之前直接用 Tavily snippet 抓
    "site:qcc.com" 然后正则抠几个字段，命中率低、字段稀疏。把它升级成分层
    数据源：
        1. 上市公司 → akshare（结构化、权威、零成本）
        2. 非上市公司 → Tavily 定向搜 (qcc/tianyancha) + LLM 严抽 6 字段

CLAUDE.md 约束：
    - 字段抽不到 → 空字符串，禁止 LLM 编（"幻觉零容忍"）
    - 每条返回带 Evidence（"证据支撑"）
    - 复用项目已有 LLMClient，不引入新厂商
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from ..base import BaseSource, Evidence, QueryRequest, QueryResult, SourceTier


# 6 个必抽字段——和 shared/kb_scan/models.py:CompanyProfile 部分对齐
REQUIRED_FIELDS = (
    "registered_capital",      # 注册资本
    "legal_representative",    # 法人代表
    "establishment_date",      # 成立日期
    "industry",                # 行业分类
    "business_scope",          # 经营范围
    "registered_address",      # 注册地址
)


_LLM_EXTRACT_PROMPT = """你是工商信息抽取专家。请从下面若干段网页内容里精确抽取「{company_name}」的 6 个字段。

要求：
1. 只输出 JSON 对象，无任何其他文字、markdown 或注释
2. 字段缺失或不确定 → 空字符串，绝对禁止猜测或编造
3. 字段值必须能在原文中找到对应（保留原文表述，不要二次加工）
4. 对多个候选取最权威、最完整的一条

字段定义：
- registered_capital: 注册资本（含金额单位，如「1000万人民币」）
- legal_representative: 法人代表（中文姓名 2-4 字）
- establishment_date: 成立日期（YYYY-MM-DD 或原文格式）
- industry: 行业分类（国民经济行业分类的具体描述）
- business_scope: 经营范围（完整原文，可截断到 300 字内）
- registered_address: 注册地址（省/市/区/详址）

公司名: {company_name}

网页内容:
{evidence_blocks}

直接输出 JSON：
"""


class EnterpriseInfoSource(BaseSource):
    """企业工商基础信息源。

    路由偏好链建议：["enterprise_info", "tavily"]——本源失败时
    Router/Degrader 会回退到原始 tavily 通用搜。
    """

    name = "enterprise_info"
    tier = SourceTier.AGGREGATOR
    cost = "free"
    supported_query_types = {"company_info", "enterprise_basic"}

    def __init__(self) -> None:
        self._llm = None  # 延迟初始化，避免无 LLM 配置时 import 即崩

    # ------------------------------------------------------------------
    # health：本源永远报 healthy；具体能力由 query() 内部分支判断
    # ------------------------------------------------------------------
    def health(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # query 入口
    # ------------------------------------------------------------------
    def query(self, request: QueryRequest) -> QueryResult:
        company_name = (request.query or "").strip()
        if not company_name:
            return QueryResult(
                ok=False, source_name=self.name,
                error="company name is empty",
            )

        # --- 路径 1：上市公司（akshare 结构化） ---
        listed_result = self._try_listed_path(company_name)
        if listed_result is not None and listed_result.ok:
            return listed_result

        # --- 路径 2：非上市公司（Tavily + LLM 抽取） ---
        return self._try_unlisted_path(company_name)

    # ------------------------------------------------------------------
    # 路径 1：上市公司
    # ------------------------------------------------------------------
    def _try_listed_path(self, company_name: str) -> QueryResult | None:
        """尝试 akshare 上市公司路径。akshare 未装 / 未匹配 → 返回 None。"""
        try:
            import akshare as ak  # 局部 import — 没装就跳过整条路径
        except Exception:
            return None

        try:
            stock_code = self._match_listed_code(ak, company_name)
        except Exception:
            return None
        if not stock_code:
            return None

        try:
            info = self._fetch_listed_info(ak, stock_code, company_name)
        except Exception as e:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"akshare fetch failed: {type(e).__name__}: {e}",
            )

        now = datetime.now().isoformat()
        evidence = [Evidence(
            source_name=self.name,
            source_url=(
                f"https://emweb.securities.eastmoney.com/PC_HSF10/"
                f"CompanyProfile/?code={stock_code}"
            ),
            fetched_at=now,
            raw_excerpt=f"akshare stock_individual_info_em(symbol={stock_code})",
            confidence=1.0,
        )]
        return QueryResult(
            ok=True, items=[info], evidence=evidence, source_name=self.name,
        )

    def _match_listed_code(self, ak, company_name: str) -> str:
        """模糊匹配 A 股代码。返回首个 name contains company_name 的 code。"""
        df = ak.stock_info_a_code_name()
        if df is None or df.empty:
            return ""
        # 兼容列名（akshare 多次改版：早期 'code'/'name'，新版可能本地化）
        code_col = next((c for c in df.columns if str(c).lower() in ("code", "代码")), None)
        name_col = next((c for c in df.columns if str(c).lower() in ("name", "名称")), None)
        if code_col is None or name_col is None:
            return ""
        # 精确优先，子串次之
        exact = df[df[name_col].astype(str) == company_name]
        if not exact.empty:
            return str(exact.iloc[0][code_col])
        sub = df[df[name_col].astype(str).str.contains(re.escape(company_name), na=False)]
        if sub.empty:
            return ""
        return str(sub.iloc[0][code_col])

    def _fetch_listed_info(self, ak, stock_code: str, company_name: str) -> dict[str, Any]:
        """拿上市公司基础信息。返回符合 REQUIRED_FIELDS schema 的 dict。

        akshare 的 stock_individual_info_em 返回 [item, value] 长表；不同版本字段
        中文名略有差异，这里做容错映射。
        """
        df = ak.stock_individual_info_em(symbol=str(stock_code))
        kv: dict[str, str] = {}
        if df is not None and not df.empty:
            # 容错：某些版本是 [item, value]，某些版本是 [项目, 值]
            cols = list(df.columns)
            if len(cols) >= 2:
                key_col, val_col = cols[0], cols[1]
                for _, row in df.iterrows():
                    k = str(row[key_col]).strip()
                    v = "" if row[val_col] is None else str(row[val_col]).strip()
                    if k and v and v.lower() != "nan":
                        kv[k] = v

        # akshare 上市公司不直接给「注册资本/法人」，但行业/上市时间确切
        info: dict[str, Any] = {
            "registered_capital": kv.get("总股本") or "",   # 占位：股本而非工商注册资本
            "legal_representative": "",                     # akshare 不返回，留空——禁编
            "establishment_date": kv.get("上市时间") or "",
            "industry": kv.get("行业") or kv.get("所处行业") or "",
            "business_scope": kv.get("主营业务") or "",
            "registered_address": kv.get("公司地址") or kv.get("办公地址") or "",
            # 透传：调用方可拿到 stock_code 做更深查询
            "_listed": True,
            "_stock_code": stock_code,
            "_company_name": company_name,
        }
        return info

    # ------------------------------------------------------------------
    # 路径 2：非上市公司（Tavily + LLM）
    # ------------------------------------------------------------------
    def _try_unlisted_path(self, company_name: str) -> QueryResult:
        raw = self._tavily_search(company_name)
        if not raw:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"no web evidence found for {company_name!r}",
            )

        try:
            extracted = self._llm_extract_fields(company_name, raw)
        except Exception as e:
            return QueryResult(
                ok=False, source_name=self.name,
                error=f"llm extraction failed: {type(e).__name__}: {e}",
            )

        # 即便 LLM 抽出全空，也算 ok=True（让调用方拿到 evidence；空字段优于编造）
        now = datetime.now().isoformat()
        evidence = [
            Evidence(
                source_name=self.name,
                source_url=r.get("url", ""),
                fetched_at=now,
                raw_excerpt=(r.get("content") or "")[:500],
                confidence=float(r.get("score", 0.5)) if isinstance(r.get("score"), (int, float)) else 0.5,
            )
            for r in raw
        ]
        return QueryResult(
            ok=True, items=[extracted], evidence=evidence, source_name=self.name,
        )

    def _tavily_search(self, company_name: str) -> list[dict]:
        """定向搜 qcc/tianyancha。Tavily 不可用 → 返回空 list（让上层判 ok=False）。"""
        try:
            import os
            from shared.kb_scan.tavily_client import TavilyClient
            api_key = os.environ.get("TAVILY_API_KEY", "").strip()
            if not api_key:
                return []
            client = TavilyClient(api_key=api_key)
            raw = client.search(
                query=f"{company_name} 注册资本 法人代表 经营范围",
                max_results=3,
                search_depth="advanced",
                include_domains=["qcc.com", "tianyancha.com", "qichacha.com"],
            )
            return raw.get("results") or []
        except Exception:
            return []

    def _llm_extract_fields(self, company_name: str, raw: list[dict]) -> dict[str, Any]:
        """LLM 严抽 6 字段。任一字段抽不到 → 空字符串，绝不编造。"""
        # 拼证据块——保留 url 作锚点，方便 LLM 区分多源
        blocks: list[str] = []
        for i, r in enumerate(raw, 1):
            url = r.get("url", "")
            content = (r.get("content") or "").strip()
            blocks.append(f"--- 段落 {i}（来源 {url}）---\n{content[:1500]}")
        evidence_blocks = "\n\n".join(blocks)

        prompt = _LLM_EXTRACT_PROMPT.format(
            company_name=company_name,
            evidence_blocks=evidence_blocks,
        )

        llm = self._get_llm()
        resp = llm.simple_chat(
            "你是企业工商信息抽取助手，只输出 JSON 对象，禁止编造。",
            prompt,
        )

        parsed = self._safe_parse_json(resp)
        # 强制对齐 schema：缺失键统一补空
        return {f: str(parsed.get(f, "") or "") for f in REQUIRED_FIELDS}

    def _safe_parse_json(self, resp: str) -> dict[str, Any]:
        """从 LLM 回复中宽容解析 JSON 对象。失败 → 空 dict（让上层补空字段）。"""
        if not resp:
            return {}
        # 去 markdown fence
        cleaned = re.sub(r"```(?:json)?\s*", "", resp)
        cleaned = re.sub(r"```\s*$", "", cleaned)
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if not m:
            return {}
        try:
            data = json.loads(m.group())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        # 延迟 import，匹配 rule_extractor.py 的约定
        from llm import LLMClient
        self._llm = LLMClient()
        return self._llm
