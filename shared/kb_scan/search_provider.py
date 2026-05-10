# -*- coding: utf-8 -*-
"""SearchProvider 抽象 + Mock/Web 实现。

设计硬约束（by 用户 2026-04-13）：
  1. MockSearchProvider 与 WebSearchProvider 方法签名、返回类型完全一致
  2. 下游不得 isinstance(provider, MockSearchProvider) —— 一律吃抽象接口
  3. 一行切换：build_search_provider(demo_mode=...)
"""

from __future__ import annotations
import json
import os
import random
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timedelta

from .models import CompanyProfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MOCK_DIR = PROJECT_ROOT / "demo_data" / "mock_pool"


class SearchProvider(ABC):
    """搜索数据源抽象。Agent1/4/5 的外网/内网/mock 数据源都走这个接口。"""

    provider_name: str = "abstract"

    @abstractmethod
    def search_companies(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 50,
    ) -> list[CompanyProfile]:
        """自然语言 + 结构化过滤，搜索企业池。"""
        ...

    @abstractmethod
    def fetch_company_info(self, company_name: str) -> CompanyProfile | None:
        """按企业名精确查询（天眼查/爱企查接口）。"""
        ...

    @abstractmethod
    def search_news(
        self,
        query: str,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        """搜索新闻舆情。返回 [{title,url,snippet,published_at}]。"""
        ...

    @abstractmethod
    def search_policy_clauses(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        """搜索监管政策条款。返回 [{clause_id,title,content,source_doc}]。"""
        ...

    @abstractmethod
    def iter_loan_customers(
        self,
        filters: dict | None = None,
    ) -> list[CompanyProfile]:
        """遍历在贷客户（Agent4 扫描目标池 / 贷后管理系统）。"""
        ...

    @abstractmethod
    def iter_business_events(
        self,
        customer_id: str = "",
        event_types: list[str] | None = None,
        days: int = 90,
    ) -> list[dict]:
        """遍历业务事件（放款/还款/抵质押变动等）。"""
        ...

    @abstractmethod
    def search_court_records(
        self,
        company_name: str,
        limit: int = 5,
    ) -> list[dict]:
        """检索裁判文书/涉诉记录（Agent4 外部命中源）。"""
        ...


# ========== 实现 1：MockSearchProvider（Demo 用）==========

class MockSearchProvider(SearchProvider):
    """从本地 mock 文件读数据。签名和 Web 实现完全一致。"""

    provider_name = "mock"

    def __init__(self, mock_data_dir: str | Path = DEFAULT_MOCK_DIR):
        self._data_dir = Path(mock_data_dir)
        self._companies = self._load_jsonl("companies.jsonl", CompanyProfile)
        self._loans = self._load_jsonl("loan_customers.jsonl", CompanyProfile)
        self._news = self._load_json("news.json", default=[])
        self._policies = self._load_json("policies.json", default=[])
        self._events = self._load_json("business_events.json", default=[])
        self._court = self._load_json("court_records.json", default=[])

    # ---- IO ----
    def _load_jsonl(self, name: str, cls):
        p = self._data_dir / name
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(cls(**json.loads(line)))
            except (json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError):
                continue
        return out

    def _load_json(self, name: str, default):
        p = self._data_dir / name
        if not p.exists():
            return default
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            return default

    # ---- SearchProvider 接口实现 ----

    def search_companies(self, query, filters=None, limit=50):
        filters = filters or {}
        q = (query or "").strip()
        results = []
        for c in self._companies:
            if not self._match_filter(c, filters):
                continue
            if q and not self._match_query_text(c, q):
                continue
            results.append(c)
        return results[:limit]

    def fetch_company_info(self, company_name):
        for c in self._companies + self._loans:
            if c.company_name == company_name:
                return c
        return None

    def search_news(self, query, days=30, limit=10):
        cutoff = datetime.now() - timedelta(days=days)
        q = (query or "").lower()
        out = []
        for n in self._news:
            if q and q not in (n.get("title", "") + n.get("snippet", "")).lower():
                continue
            ts = n.get("published_at", "")
            try:
                if ts and datetime.fromisoformat(ts.replace("Z", "")) < cutoff:
                    continue
            except (ValueError, TypeError, AttributeError):
                pass
            out.append(n)
        return out[:limit]

    def search_policy_clauses(self, query, limit=20):
        q = (query or "").lower()
        out = []
        for p in self._policies:
            if not q or q in (p.get("title", "") + p.get("content", "")).lower():
                out.append(p)
        return out[:limit]

    def iter_loan_customers(self, filters=None):
        filters = filters or {}
        if not filters:
            return list(self._loans)
        return [c for c in self._loans if self._match_filter(c, filters)]

    def iter_business_events(self, customer_id="", event_types=None, days=90):
        cutoff = datetime.now() - timedelta(days=days)
        events = self._events
        if customer_id:
            events = [e for e in events if e.get("customer_id") == customer_id]
        if event_types:
            events = [e for e in events if e.get("type") in event_types]
        out = []
        for e in events:
            ts = e.get("occurred_at", "")
            try:
                if ts and datetime.fromisoformat(ts.replace("Z", "")) < cutoff:
                    continue
            except (ValueError, TypeError, AttributeError):
                pass
            out.append(e)
        return out

    def search_court_records(self, company_name, limit=5):
        out = [r for r in self._court if r.get("company_name") == company_name]
        return out[:limit]

    # ---- 内部匹配 ----

    def _match_filter(self, c: CompanyProfile, filters: dict) -> bool:
        if "industry" in filters and filters["industry"]:
            if filters["industry"] not in c.industry:
                return False
        if "region" in filters and filters["region"]:
            if filters["region"] not in c.region:
                return False
        if "scale" in filters and filters["scale"]:
            scales = filters["scale"] if isinstance(filters["scale"], list) else [filters["scale"]]
            if c.scale not in scales:
                return False
        return True

    def _match_query_text(self, c: CompanyProfile, query: str) -> bool:
        haystack = " ".join([
            c.company_name or "",
            c.industry or "",
            c.sub_industry or "",
            c.region or "",
            c.main_business or "",
            " ".join(c.keywords or []),
            " ".join(c.tags or []),
        ]).lower()
        q = query.lower()
        # 任一 token 命中即算
        tokens = [t for t in q.replace(",", " ").split() if t]
        if not tokens:
            return True
        return any(t in haystack for t in tokens)


# ========== 实现 2：WebSearchProvider（生产用，Demo 不启用）==========

class WebSearchProvider(SearchProvider):
    """真实 API：天眼查/爱企查/搜索引擎/贷后管理系统。签名与 Mock 完全一致。"""

    provider_name = "web"

    def __init__(self, api_keys: dict | None = None):
        self._api_keys = api_keys or {}
        # 生产阶段在此初始化真实客户端：
        # self._tyc = TianyanchaClient(self._api_keys.get("tianyancha"))
        # self._search = BingSearchClient(self._api_keys.get("bing"))
        # self._core_bank = BankCoreClient(self._api_keys.get("core_bank"))

    def _not_implemented(self, method: str):
        raise NotImplementedError(
            f"WebSearchProvider.{method} 需在生产环境配置真实 API 后启用。"
            "Demo 阶段请使用 build_search_provider(demo_mode=True)。"
        )

    def search_companies(self, query, filters=None, limit=50):
        """真调 Tavily + LLM 抽取 CompanyProfile。

        环境约束：
          - TAVILY_API_KEY 必须存在；否则抛 NotImplementedError，
            上层（realtime_stream）会降级到 MockSearchProvider。
        """
        filters = filters or {}
        api_key = (self._api_keys.get("tavily")
                   or os.environ.get("TAVILY_API_KEY"))
        if not api_key:
            raise NotImplementedError(
                "WebSearchProvider.search_companies 需 TAVILY_API_KEY 环境变量"
            )

        # 延迟 import：未安装 httpx / 无 LLM 时不拖累整个模块
        from .tavily_client import TavilyClient, TavilySearchError
        try:
            from llm import LLMClient
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            raise NotImplementedError(f"LLMClient not available: {e}")

        # 拼查询：原始 query + industry/region/scale
        q_parts = [query or ""]
        if filters.get("industry"):
            q_parts.append(str(filters["industry"]))
        if filters.get("region"):
            q_parts.append(str(filters["region"]))
        if filters.get("scale"):
            sc = filters["scale"]
            if isinstance(sc, list):
                q_parts.append(" ".join(sc))
            else:
                q_parts.append(str(sc))
        q = " ".join(p for p in q_parts if p).strip()
        if not q:
            return []

        # 权威信源白名单（高置信） —— 工商/政府/招投标/财经/专利
        include_domains = [
            # 工商
            "qcc.com", "tianyancha.com", "qichamao.com", "aiqicha.com",
            # 政府
            "gov.cn",  # 覆盖所有政府网（含 gsxt/cnipa/各省市）
            # 上市披露
            "cninfo.com.cn",
            # 招投标
            "chinabidding.cn", "bidcenter.com.cn",
            # 财经
            "caixin.com", "36kr.com", "yicai.com", "cs.com.cn",
            "stockstar.com", "cnstock.com",
            # 专利
            "cnipa.gov.cn",
        ]
        # 黑名单：用户编辑/低置信源 —— 严禁混入
        exclude_domains = [
            "baike.baidu.com", "baike.sogou.com", "baike.so.com",
            "zhihu.com", "douban.com", "weibo.com",
            "xiaohongshu.com", "toutiao.com",
            "soso.com", "360doc.com", "wenku.baidu.com",
            "wikipedia.org",
        ]

        client = TavilyClient(api_key=api_key)
        try:
            raw = client.search(
                q, max_results=limit, search_depth="advanced",
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            )
        except TavilySearchError:
            # 交由上层决定降级，这里原样抛（上层捕获后走 mock）
            raise

        results = raw.get("results") or []
        llm_provider = os.environ.get("CHANNEL_WEB_LLM_PROVIDER", "deepseek")
        llm_api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY") or ""
        try:
            llm = LLMClient(provider=llm_provider, api_key=llm_api_key)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
            llm = None

        # === 深度抓取：对 TOP URL 调 /extract 拿全文（远比 snippet 详细） ===
        urls_to_extract = [r.get("url") for r in results[:5] if r.get("url")]
        extracted_map: dict[str, str] = {}
        try:
            ex = client.extract(urls_to_extract, extract_depth="advanced")
            for item in (ex.get("results") or []):
                u = item.get("url")
                rc = item.get("raw_content") or ""
                if u and rc:
                    extracted_map[u] = rc[:6000]  # 上限 6000 字防爆 token
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
            extracted_map = {}  # extract 失败不阻塞，回落到 snippet

        profiles: list[CompanyProfile] = []
        for r in results:
            title = r.get("title") or ""
            url = r.get("url") or ""
            snippet = r.get("content") or ""
            # 优先用 extract 全文，否则用 snippet
            content_full = extracted_map.get(url) or snippet
            if not (title or content_full):
                continue
            profile = _extract_profile_from_web(llm, title, url, content_full, q)
            if profile is None:
                continue

            # === 置信度评分（基于来源域 + 字段完整度） ===
            domain = (url.split("/")[2] if "//" in url else url).lower()
            HIGH_CONF_DOMAINS = {
                "cninfo.com.cn", "gsxt.gov.cn",
                "qcc.com", "www.qcc.com", "m.qcc.com",
                "tianyancha.com", "www.tianyancha.com",
                "aiqicha.com",
            }
            MED_CONF_DOMAINS = {
                "stockstar.com", "cs.com.cn", "cnstock.com",
                "caixin.com", "36kr.com", "yicai.com",
                "qichamao.com",
            }
            if any(d in domain for d in HIGH_CONF_DOMAINS):
                conf_level = "high"
            elif any(d in domain for d in MED_CONF_DOMAINS):
                conf_level = "medium"
            else:
                conf_level = "low"

            # 字段完整度（非空字段比例）
            filled = sum(1 for v in [
                profile.unified_credit_code, profile.industry, profile.region,
                profile.revenue_latest, profile.registered_capital,
                profile.establishment_date, profile.main_business,
            ] if v)
            field_completeness = filled / 7.0

            # 证据链
            profile.extras = dict(profile.extras or {})
            profile.extras["data_source"] = "tavily"
            profile.extras["evidence_url"] = url
            profile.extras["evidence_snippet"] = snippet[:300]
            profile.extras["source_domain"] = domain
            profile.extras["confidence_level"] = conf_level
            profile.extras["field_completeness"] = round(field_completeness, 2)
            profile.extras["used_full_extract"] = url in extracted_map
            profiles.append(profile)

        return profiles[:limit]

    def fetch_company_info(self, company_name):
        self._not_implemented("fetch_company_info")

    def search_news(self, query, days=30, limit=10):
        self._not_implemented("search_news")

    def search_policy_clauses(self, query, limit=20):
        self._not_implemented("search_policy_clauses")

    def iter_loan_customers(self, filters=None):
        # Phase B.1.2 hotfix (PM 2026-05-10) · 在贷客户池属银行内部数据 · web 搜索器本不该返
        # 改 NotImplementedError → 返 iter([]) · alert customer_scanner.py 已 try/except 双保险
        # 演示路径: 用户上传 KB Excel/JSON → customer_scanner 优先 KB · provider 0 数据不 raise
        return iter([])

    def iter_business_events(self, customer_id="", event_types=None, days=90):
        self._not_implemented("iter_business_events")

    def search_court_records(self, company_name, limit=5):
        self._not_implemented("search_court_records")


# ========== Web 抽取辅助 ==========

def _extract_profile_from_web(
    llm, title: str, url: str, content: str, query_hint: str
) -> CompanyProfile | None:
    """从一条 Tavily result 用 LLM 结构化出 CompanyProfile。失败返回 None。"""
    # 全文给到 4500 字，足够覆盖 qcc/cninfo 详情页
    snippet = (content or "")[:4500]
    title = (title or "")[:200]
    if llm is None:
        name = _guess_company_name(title) or _guess_company_name(snippet)
        if not name:
            return None
        return CompanyProfile(company_name=name, main_business=snippet[:120])

    system = (
        "你是工商企业信息抽取助手，专为银行授信场景服务。"
        "从给定网页内容中抽取单个企业的结构化画像。"
        "**绝对不要编造**：字段在网页内容中无明确依据时，必须留空字符串/0。"
        "如果网页内容是聚合页/列表页/广告页或无明确企业实体，返回空对象 {}。"
    )
    user = f"""检索意图：{query_hint}

==== 网页标题 ====
{title}

==== 网页 URL ====
{url}

==== 网页正文（已抓取全文） ====
{snippet}

==== 抽取要求 ====
请严格从上述正文中找出对应字段，找不到则留空。返回 JSON：

{{
  "company_name": "完整工商注册全名，例：浙江富特科技股份有限公司",
  "unified_credit_code": "18 位统一社会信用代码（如正文有），无则留空",
  "industry": "一级行业：制造业/信息技术/批发零售/金融/建筑/农业 等",
  "sub_industry": "细分赛道，如：新能源汽车高压电源系统",
  "region": "省+市，例：浙江·宁波",
  "scale": "大型/中型/小型/微型，无依据留空",
  "revenue_latest": "最新营收，例：2.12 亿（2024 年）",
  "employee_count": 整数（员工总数），无则 0,
  "main_business": "主营业务 1-2 句话描述",
  "registered_capital": "注册资本，例：5000 万",
  "establishment_date": "成立日期或年份",
  "ownership_type": "国有/民营/外资/混合，无则留空",
  "qualifications": ["专精特新小巨人", "高新技术企业", "制造业单项冠军", ...],
  "keywords": ["主要产品 / 客户 / 工艺等关键词", ...]
}}

铁律：
1. 仅从【网页正文】中抽取，不要用你的训练知识补全
2. 公司名必须是正文中明确出现的，不要从行业类别推测
3. 数字（营收/员工/注册资本）必须正文有明确数据，否则留空
4. 资质 qualifications 只列正文明确提到的，不要想当然加

只输出 JSON 对象，不要 markdown 围栏。抽不到具体企业输出 {{}}。"""
    try:
        raw = llm.simple_chat(system, user, temperature=0.1)
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
        return None

    text = (raw or "").strip()
    # 去围栏
    if text.startswith("```"):
        text = text.strip("`")
        # 可能是 ```json\n{...}\n```
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        # 容错：找第一个 { 到最后一个 }
        lo = text.find("{")
        hi = text.rfind("}")
        if lo >= 0 and hi > lo:
            try:
                obj = json.loads(text[lo:hi + 1])
            except (json.JSONDecodeError, ValueError, TypeError):
                return None
        else:
            return None

    if not isinstance(obj, dict):
        return None
    name = (obj.get("company_name") or "").strip()
    if not name:
        return None
    try:
        emp = obj.get("employee_count") or 0
        emp = int(emp) if str(emp).strip() else 0
    except (ValueError, TypeError, AttributeError):
        emp = 0
    return CompanyProfile(
        company_name=name,
        unified_credit_code=obj.get("unified_credit_code") or "",
        industry=obj.get("industry") or "",
        sub_industry=obj.get("sub_industry") or "",
        region=obj.get("region") or "",
        scale=obj.get("scale") or "",
        revenue_latest=obj.get("revenue_latest") or "",
        employee_count=emp,
        ownership_type=obj.get("ownership_type") or "",
        main_business=obj.get("main_business") or "",
        registered_capital=obj.get("registered_capital") or "",
        establishment_date=obj.get("establishment_date") or "",
        qualifications=list(obj.get("qualifications") or []),
        keywords=list(obj.get("keywords") or []),
    )


def _guess_company_name(text: str) -> str:
    """无 LLM 时的朴素兜底：匹配中文公司名常见后缀。"""
    import re
    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9（）()·\- ]{2,30}(?:股份|有限|集团)?(?:公司|厂|企业|研究院))", text or "")
    return m.group(1).strip() if m else ""


# ========== 工厂：唯一入口 ==========

def build_search_provider(demo_mode: bool | None = None, **kwargs) -> SearchProvider:
    """唯一对外创建入口。

    Demo 模式（默认 True）→ MockSearchProvider
    生产模式（demo_mode=False）→ WebSearchProvider
    环境变量 KB_SCAN_DEMO_MODE=false 可全局关闭 Demo。
    """
    if demo_mode is None:
        env = os.environ.get("KB_SCAN_DEMO_MODE", "true").lower()
        demo_mode = env not in ("false", "0", "no")
    if demo_mode:
        return MockSearchProvider(**kwargs)
    return WebSearchProvider(**kwargs)
