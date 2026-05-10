# -*- coding: utf-8 -*-
"""ALL IN Phase B.2.3 (PM 2026-05-10 主 CLI 自验) · AlertPoolSyntheticProvider.

PM 真意 reframe (2026-05-10): "mock 只能 mock 输入 · 不能 mock 结果"
- 输入: data/mock/alert-pool/{clients.csv, external-signals/AP*.md}  (audit-grade fixture · 反 §3.5 5 原则)
- backend 真跑: cross_matcher / alert_engine / disposition (LLM) / persist_hitlist / decision_ledger
- 不假装 Tavily live · 不 silent 合成 mock 结果 (违 PM 真意)

修真问题 (主 CLI 2026-05-10 自验):
  /demo/run 真跑 backend pipeline 但 production 没 TAVILY_API_KEY → fallback NullSearchProvider
  → external scan 0 hit · cross_matcher 全 green · 0 户红/黄

修法:
  把 alert-pool/external-signals/AP*.md (audit-grade fixture · 真存在的负面信号)
  用 SearchProvider 接口暴露给 cross_matcher · 公司名 match alert-pool/clients.csv ·
  cross_matcher 真匹配 LAW-/FIN-/BIZ-/IND-/REL- 关键词 → 真生成红/黄 hit list.

  这不是"假装 Tavily" — banner mode_label = "alert_pool_fixture" · 客户走访演示透明告知:
  "演示路径 · 内置审计级合成信号 · 真后端 pipeline 跑红/黄判级"

Scope:
- agent_alert 写域 · 不动 shared/kb_scan/search_provider.py
- 仅 _alert_demo_event_stream 切换 provider · CrossMatcher / customer_scanner 不知情
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from shared.kb_scan.search_provider import SearchProvider

if TYPE_CHECKING:
    from shared.kb_scan.models import CompanyProfile

# alert-pool fixture 路径
_ROOT = Path(__file__).resolve().parent.parent
_FIXTURE_DIR = _ROOT / "data" / "mock" / "alert-pool"
_CLIENTS_CSV = _FIXTURE_DIR / "clients.csv"
_SIGNALS_DIR = _FIXTURE_DIR / "external-signals"


def _build_company_to_client_id_map() -> dict[str, str]:
    """从 clients.csv 建 company_name → client_id (AP00X) 索引."""
    import csv

    out: dict[str, str] = {}
    if not _CLIENTS_CSV.is_file():
        return out
    with _CLIENTS_CSV.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = (row.get("client_id") or "").strip()
            name = (row.get("company_name") or "").strip()
            if cid and name:
                out[name] = cid
    return out


def _parse_signals_md(md_path: Path) -> list[dict]:
    """解析单个 AP*.md · 返事件列表 [{date, kind, title, snippet, source}]."""
    if not md_path.is_file():
        return []
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    events: list[dict] = []
    # 段落格式: "## YYYY-MM-DD · <kind> · <title>\n\n<snippet>\n\n出处:<source>"
    section_re = re.compile(
        r"##\s*(\d{4}-\d{2}-\d{2})\s*·\s*([^·\n]+?)\s*·\s*([^\n]+?)\s*\n+([\s\S]*?)(?=\n##|\Z)",
        re.MULTILINE,
    )
    for m in section_re.finditer(text):
        date, kind, title, body = m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
        # 切 snippet + source
        source_m = re.search(r"出处[:：]\s*([^\n]+)", body)
        source = source_m.group(1).strip() if source_m else ""
        # snippet 是 body 去掉 "出处" 行 / "---" 分隔符
        snippet_lines = [
            ln.strip() for ln in body.split("\n")
            if ln.strip() and not ln.strip().startswith("---") and not ln.strip().startswith("出处")
        ]
        snippet = " ".join(snippet_lines)[:300]
        events.append({
            "date": date,
            "kind": kind,
            "title": title,
            "snippet": snippet,
            "source": source,
        })
    return events


class AlertPoolSyntheticProvider(SearchProvider):
    """alert-pool fixture 驱动的 SearchProvider · 演示路径专用.

    与 NullSearchProvider 区别: 返真实负面信号 (从 fixture 读) ·
    与 MockSearchProvider 区别: 不合成 mock 结果 (是真存在的 audit-grade 数据).

    实现接口:
    - search_news(company_name, days, limit): 从 AP*.md 选 days 内的舆情 + 司法 + 工商 · 返 news 格式
    - search_court_records(company_name, limit): 从 AP*.md 选司法事件 · 返 court 格式
    - 其余方法返 [] (不消费)
    """

    provider_name = "alert_pool_fixture"

    def __init__(self) -> None:
        self._name_to_cid = _build_company_to_client_id_map()
        # lazy load: company_name → events (按需 parse · 减启动开销)
        self._cache: dict[str, list[dict]] = {}

    def _events_for(self, company_name: str) -> list[dict]:
        """惰性加载 company_name 对应 AP*.md 事件."""
        if company_name in self._cache:
            return self._cache[company_name]
        cid = self._name_to_cid.get(company_name, "")
        if not cid:
            self._cache[company_name] = []
            return []
        md_path = _SIGNALS_DIR / f"{cid}.md"
        events = _parse_signals_md(md_path)
        self._cache[company_name] = events
        return events

    def search_companies(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 50,
    ) -> list["CompanyProfile"]:
        return []

    def fetch_company_info(self, company_name: str) -> "CompanyProfile | None":
        return None

    def search_news(
        self,
        query: str,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        """返 news 格式 [{title, snippet, published_at, url}].

        消费方 cross_matcher.py:216 调 search_news(profile.company_name, days=365)
        把 title + snippet 拼 signal_source_blob · 关键词 match FIN-/BIZ-/IND-/REL-.
        """
        events = self._events_for(query)
        if not events:
            return []
        # 不限 days · 全返 (cross_matcher 用 days=365 · alert-pool 数据近 12 月)
        out: list[dict] = []
        for e in events:
            # 排除司法类 (走 search_court_records) · 留舆情/工商/行业
            kind = e.get("kind", "")
            if "司法" in kind:
                continue
            out.append({
                "title": e.get("title", ""),
                "snippet": e.get("snippet", ""),
                "published_at": e.get("date", ""),
                "url": "",
            })
            if len(out) >= limit:
                break
        return out

    def search_policy_clauses(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        return []

    def iter_loan_customers(
        self,
        filters: dict | None = None,
    ) -> list["CompanyProfile"]:
        return []

    def iter_business_events(
        self,
        customer_id: str = "",
        event_types: list[str] | None = None,
        days: int = 90,
    ) -> list[dict]:
        return []

    def search_court_records(
        self,
        company_name: str,
        limit: int = 5,
    ) -> list[dict]:
        """返裁判文书格式 [{role, amount, status, case_no, snippet, url}].

        消费方 cross_matcher.py:182 调 search_court_records(profile.company_name)
        关键词 "失信" → LAW-002 · role=被告 → LAW-001.
        """
        events = self._events_for(company_name)
        if not events:
            return []
        out: list[dict] = []
        for e in events:
            kind = e.get("kind", "")
            title = e.get("title", "")
            snippet = e.get("snippet", "")
            blob = f"{title} {snippet}"
            if "司法" not in kind and not any(k in blob for k in ["失信", "被执行", "涉诉", "查封", "拍卖"]):
                continue
            # 推断 role / status
            if "失信" in blob or "被执行" in blob:
                role = "被执行人"
                status = "失信被执行"
            elif "涉诉" in blob or "起诉" in blob:
                role = "被告"
                status = "诉讼中"
            else:
                role = "被告"
                status = ""
            # 推断 amount (从 snippet 抽 "X 万" / "X 万元")
            amount = 0
            amt_m = re.search(r"(\d+(?:\.\d+)?)\s*万", blob)
            if amt_m:
                try:
                    amount = int(float(amt_m.group(1)) * 10000)
                except (ValueError, TypeError):
                    amount = 0
            out.append({
                "role": role,
                "amount": amount,
                "status": status,
                "case_no": f"{company_name[:6]}-{e.get('date', '')}",
                "snippet": snippet,
                "url": "",
            })
            if len(out) >= limit:
                break
        return out
