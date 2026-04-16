# -*- coding: utf-8 -*-
"""前端实时搜索流：自然语言 → 信号驱动的候选清单。

架构（v2 信号搜索）：
  一句话 → 解析标签 → 5 路并行信号搜索 → 信号抽取 → 按公司聚合
  → 信号密度排序 → 企查查补基础 → 产品推荐+话术 → 信号时间线卡片

按 6 阶段 yield 事件，每个事件是 dict：{event, stage, status, ...payload}。
消费方（api_server.py）负责 SSE 编码。
"""

from __future__ import annotations

import json
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Iterator

from llm import LLMClient
from shared.kb_scan.search_provider import MockSearchProvider
from shared.kb_scan.tavily_client import TavilyClient, TavilySearchError

# 6 阶段 key（与前端 channel-types.ts 的 CHANNEL_STAGES 对齐）
STAGES = ["parse", "signal_scan", "aggregate", "enrich", "pitch", "rank"]

# ========== 信号搜索模板 ==========
SIGNAL_QUERIES = [
    ("{industry} {region} 中标公告 2025", "bidding"),
    ("{industry} {region} 专精特新 名单 高新技术", "recognition"),
    ("{industry} {region} 专利申请 技术突破 新工艺", "tech"),
    ("{industry} {region} 扩产 新建项目 环评 投产", "growth"),
    ("{industry} {region} 获奖 评优 标杆企业 示范", "award"),
]

# ========== 产品推荐规则 ==========
PRODUCT_RULES = [
    (["扩产", "新建", "产线", "设备", "环评", "投产"], "设备贷 / 固定资产贷款"),
    (["中标", "订单", "采购", "集采"], "流动资金贷款"),
    (["应收", "供应链", "账款"], "保理 / 应收质押融资"),
    (["融资", "增资", "股权"], "过桥资金 / 股权质押"),
    (["小微", "个体", "普惠"], "普惠经营贷"),
]

# 信号搜索的域名白名单
SIGNAL_INCLUDE_DOMAINS = [
    "qcc.com", "tianyancha.com", "aiqicha.com",
    "gov.cn",
    "chinabidding.cn", "bidcenter.com.cn",
    "caixin.com", "36kr.com", "yicai.com", "cs.com.cn",
    "cnipa.gov.cn",
]

SIGNAL_EXCLUDE_DOMAINS = [
    "baike.baidu.com", "zhihu.com", "douban.com",
    "weibo.com", "xiaohongshu.com",
]


def run_channel_search_stream(
    query: str,
    provider: str = "deepseek",
    api_key: str = "",
    top_n: int = 8,
) -> Iterator[dict]:
    """主编排：yield 事件流。

    事件结构：
      {"event":"stage","stage":"parse","status":"running","message":"..."}
      {"event":"stage","stage":"parse","status":"done","tags":[...]}
      ... (6 stage x running/done)
      {"event":"done","candidates":[...], "metrics":{...}, "data_source":"tavily"|"mock_fallback"}
      错误：{"event":"error","message":"...","traceback":"..."}
    """
    try:
        try:
            llm = LLMClient(provider=provider or "deepseek", api_key=api_key or "")
        except Exception:
            llm = None

        # ===== Stage 1: parse =====
        yield {"event": "stage", "stage": "parse", "status": "running",
               "message": "解析用户意图..."}
        tags = _parse_intent(llm, query)
        yield {"event": "stage", "stage": "parse", "status": "done", "tags": tags}

        # 从 tags 中提取 industry / region
        industry = ""
        region = ""
        for t in tags:
            if t.get("category") == "行业":
                industry = t.get("value", "")
            elif t.get("category") == "区域":
                region = t.get("value", "")

        # ===== Stage 2: signal_scan — 5 路并行信号搜索 =====
        yield {"event": "stage", "stage": "signal_scan", "status": "running",
               "message": "5 路信号并行搜索（中标/认可/技术/增长/获奖）..."}
        raw_signals, data_source = _parallel_signal_search(
            llm, industry, region, query, tags
        )
        yield {"event": "stage", "stage": "signal_scan", "status": "done",
               "count": len(raw_signals), "data_source": data_source}

        # ===== Stage 3: aggregate — 按公司聚合 =====
        yield {"event": "stage", "stage": "aggregate", "status": "running",
               "message": "实体聚合去重..."}
        company_map = _aggregate_by_company(raw_signals)
        yield {"event": "stage", "stage": "aggregate", "status": "done",
               "total": len(company_map)}

        # 信号密度打分 + 排序
        scored = _score_and_rank(company_map)
        top_companies = scored[:top_n]

        # ===== Stage 4: enrich — 企查查补基础 + 产品匹配 =====
        yield {"event": "stage", "stage": "enrich", "status": "running",
               "message": "企查查补全工商信息 + 产品匹配..."}
        enriched = _enrich_top_companies(top_companies, tags)
        yield {"event": "stage", "stage": "enrich", "status": "done",
               "count": len(enriched)}

        # ===== Stage 5: pitch — 话术生成 =====
        yield {"event": "stage", "stage": "pitch", "status": "running",
               "message": "生成个性化切入话术..."}
        for item in enriched:
            item["pitch"] = _generate_pitch(llm, item)
        yield {"event": "stage", "stage": "pitch", "status": "done"}

        # ===== Stage 6: rank — 最终排序输出 =====
        yield {"event": "stage", "stage": "rank", "status": "running",
               "message": "信号密度排序..."}
        # 构建最终输出
        candidates = _build_final_output(enriched, tags)
        yield {"event": "stage", "stage": "rank", "status": "done"}

        yield {
            "event": "done",
            "candidates": candidates,
            "metrics": {
                "signalTotal": len(raw_signals),
                "companiesFound": len(company_map),
                "final": len(candidates),
            },
            "data_source": data_source,
        }
    except Exception as e:
        yield {
            "event": "error",
            "message": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }


# ========== Stage 1: 意图解析 ==========

def _parse_intent(llm, query: str) -> list[dict]:
    """LLM 结构化抽取 tags。失败降级到正则。"""
    if llm is None:
        return _regex_parse(query)
    system = "你是企业画像解析助手。把用户的一句话描述，拆成结构化标签 JSON。"
    user = f"""用户描述：{query}

请返回 JSON 数组，每条是 {{"category": "...", "value": "..."}}，category 从以下取：
区域、行业、规模、资质、融资阶段、经营特征、关键词

只输出 JSON 数组，不要其他文字。"""
    try:
        raw = llm.simple_chat(system, user, temperature=0.2)
        raw = (raw or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        tags = json.loads(raw)
        if not isinstance(tags, list):
            raise ValueError("not a list")
        out = [
            {"category": t["category"], "value": t["value"]}
            for t in tags
            if isinstance(t, dict) and "category" in t and "value" in t
        ]
        return out[:10] if out else _regex_parse(query)
    except Exception:
        return _regex_parse(query)


def _regex_parse(text: str) -> list[dict]:
    tags: list[dict] = []

    def push(c: str, v: str):
        tags.append({"category": c, "value": v})

    m = re.search(r"(浙江|江苏|广东|上海|北京|深圳|杭州|苏州|宁波|长三角|珠三角)", text)
    if m:
        push("区域", m.group(1))
    m = re.search(
        r"(新能源汽车|精密零部件|零部件|SaaS|工业软件|建材批发|批发|互联网|科技|AI|装备制造|机械)",
        text,
    )
    if m:
        push("行业", m.group(1))
    m = re.search(r"年营收\s*([\d\.]+\s*[-到至–]\s*[\d\.]+\s*[亿万]|[\d\.]+\s*[亿万])", text)
    if m:
        push("规模", "营收 " + m.group(1))
    if "专精特新" in text:
        push("资质", "专精特新")
    if not tags:
        push("关键词", (text or "")[:20])
    return tags


# ========== Stage 2: 5 路并行信号搜索 ==========

def _parallel_signal_search(
    llm, industry: str, region: str, query: str, tags: list[dict]
) -> tuple[list[dict], str]:
    """5 路并行 Tavily 搜索 + LLM 信号抽取。降级到 mock 时返回合成信号。"""
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return _mock_signal_fallback(query, tags), "mock_fallback"

    # 构建 5 路查询
    ind = industry or "企业"
    reg = region or ""
    queries = [
        (tpl.format(industry=ind, region=reg).strip(), stype)
        for tpl, stype in SIGNAL_QUERIES
    ]

    client = TavilyClient(api_key=tavily_key)
    all_signals: list[dict] = []

    def _search_one(q: str, signal_type: str) -> list[dict]:
        """单路搜索 + LLM 信号抽取。"""
        try:
            raw = client.search(
                q, max_results=8, search_depth="advanced",
                include_domains=SIGNAL_INCLUDE_DOMAINS,
                exclude_domains=SIGNAL_EXCLUDE_DOMAINS,
            )
        except TavilySearchError:
            return []
        results = raw.get("results") or []
        signals = []
        for r in results:
            title = r.get("title") or ""
            content = r.get("content") or ""
            url = r.get("url") or ""
            if not (title or content):
                continue
            extracted = _extract_signal(llm, title, content, url, signal_type)
            if extracted:
                signals.extend(extracted)
        return signals

    # 并行执行 5 路搜索
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_search_one, q, stype): stype
            for q, stype in queries
        }
        for future in as_completed(futures):
            try:
                signals = future.result()
                all_signals.extend(signals)
            except Exception:
                continue

    if all_signals:
        return all_signals, "tavily"

    # Tavily 搜到 0 条信号 → 降级 mock
    return _mock_signal_fallback(query, tags), "mock_fallback"


def _extract_signal(
    llm, title: str, content: str, url: str, signal_type: str
) -> list[dict] | None:
    """从一条搜索结果中用 LLM 提取信号结构体。"""
    if llm is None:
        # 无 LLM 时用朴素抽取
        name = _guess_company_name(title + " " + content)
        if not name:
            return None
        return [{
            "company_name": name,
            "signal_type": signal_type,
            "signal_title": title[:80],
            "signal_detail": content[:150],
            "signal_date": "",
            "signal_source": _domain_from_url(url),
            "source_url": url,
        }]

    system = (
        "你是企业信号抽取助手。从网页内容中提取企业相关的商业信号。"
        "每个信号必须关联到一个具体的公司名。"
        "严禁编造：正文没有的信息不要填。"
    )
    user_prompt = f"""信号类型提示：{signal_type}

==== 网页标题 ====
{title[:200]}

==== 网页正文 ====
{(content or '')[:3000]}

==== 网页 URL ====
{url}

请从上述内容中提取企业信号，返回 JSON 数组。每条信号：
{{
  "company_name": "完整公司名",
  "signal_type": "{signal_type}",
  "signal_title": "信号标题（20字内）",
  "signal_detail": "信号详情（50字内，含金额/规模等关键数字）",
  "signal_date": "YYYY-MM-DD 格式，无则留空",
  "signal_source": "来源名称（如：中国招投标平台）",
  "source_url": "{url}"
}}

规则：
1. 一条网页可能提到多家公司，每家一条信号
2. 公司名必须是正文中明确出现的完整工商注册名
3. 找不到具体公司则返回空数组 []
4. 只输出 JSON 数组"""

    try:
        raw = llm.simple_chat(system, user_prompt, temperature=0.1)
    except Exception:
        return None

    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        arr = json.loads(text)
    except Exception:
        lo = text.find("[")
        hi = text.rfind("]")
        if lo >= 0 and hi > lo:
            try:
                arr = json.loads(text[lo:hi + 1])
            except Exception:
                return None
        else:
            return None

    if not isinstance(arr, list):
        return None

    cleaned = []
    for item in arr:
        if not isinstance(item, dict):
            continue
        name = (item.get("company_name") or "").strip()
        if not name:
            continue
        cleaned.append({
            "company_name": name,
            "signal_type": item.get("signal_type") or signal_type,
            "signal_title": (item.get("signal_title") or "")[:80],
            "signal_detail": (item.get("signal_detail") or "")[:200],
            "signal_date": (item.get("signal_date") or "")[:10],
            "signal_source": item.get("signal_source") or _domain_from_url(url),
            "source_url": item.get("source_url") or url,
        })
    return cleaned or None


def _mock_signal_fallback(query: str, tags: list[dict]) -> list[dict]:
    """Tavily 不可用时，从 mock 池生成合成信号。"""
    mock = MockSearchProvider()
    filters = _tags_to_filters(tags)
    query_hint = " ".join(t.get("value", "") for t in tags) or (query or "")
    profiles = mock.search_companies(query_hint, filters=filters, limit=10)
    if not profiles and filters:
        loose = {k: v for k, v in filters.items() if k == "region"}
        profiles = mock.search_companies(query_hint, filters=loose, limit=10)
    if not profiles:
        profiles = mock.search_companies("", filters={}, limit=10)

    # 将 mock profiles 转成合成信号
    signal_types = ["bidding", "recognition", "tech", "growth", "award"]
    signals = []
    for i, p in enumerate(profiles):
        stype = signal_types[i % len(signal_types)]
        signals.append({
            "company_name": p.company_name,
            "signal_type": stype,
            "signal_title": f"{p.company_name} - {_signal_type_label(stype)}信号",
            "signal_detail": p.main_business or "模拟数据",
            "signal_date": "",
            "signal_source": "内部 Mock 客户库",
            "source_url": "",
        })
        # 给部分公司加第二条信号，模拟多信号聚合
        if i < 5:
            stype2 = signal_types[(i + 2) % len(signal_types)]
            signals.append({
                "company_name": p.company_name,
                "signal_type": stype2,
                "signal_title": f"{p.company_name} - {_signal_type_label(stype2)}信号",
                "signal_detail": " / ".join(p.qualifications) if p.qualifications else "模拟信号",
                "signal_date": "",
                "signal_source": "内部 Mock 客户库",
                "source_url": "",
            })
    return signals


# ========== Stage 3: 按公司聚合 ==========

def _aggregate_by_company(signals: list[dict]) -> dict[str, dict]:
    """将信号按公司名聚合，返回 {company_name: {signals: [...], ...}}。"""
    company_map: dict[str, dict] = {}
    for s in signals:
        name = s.get("company_name", "")
        if not name:
            continue
        if name not in company_map:
            company_map[name] = {"company_name": name, "signals": []}
        company_map[name]["signals"].append(s)
    return company_map


# ========== 信号密度打分 ==========

def _score_and_rank(company_map: dict[str, dict]) -> list[dict]:
    """信号密度打分 + 排序。"""
    scored = []
    for name, data in company_map.items():
        signals = data["signals"]
        # 不同类型的信号数
        unique_types = set(s.get("signal_type") for s in signals)
        signal_count = len(unique_types)

        score = signal_count * 15
        # 增长类（bidding/growth）加权
        score += sum(
            5 for s in signals if s.get("signal_type") in ("bidding", "growth")
        )
        # 近期信号加权
        score += sum(
            3 for s in signals if _is_recent(s.get("signal_date", ""), days=60)
        )

        scored.append({
            "company_name": name,
            "signals": signals,
            "signalScore": score,
            "signalCount": len(signals),
        })
    scored.sort(key=lambda x: x["signalScore"], reverse=True)
    return scored


def _is_recent(date_str: str, days: int = 60) -> bool:
    """判断日期是否在最近 N 天内。"""
    if not date_str:
        return False
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return (datetime.now() - dt) < timedelta(days=days)
    except Exception:
        return False


# ========== Stage 4: 企查查补基础 + 产品匹配 ==========

def _enrich_top_companies(top_companies: list[dict], tags: list[dict]) -> list[dict]:
    """对 Top N 公司查企查查补工商信息 + 产品推荐。"""
    tavily_key = os.environ.get("TAVILY_API_KEY")

    for item in top_companies:
        name = item["company_name"]
        # 企查查二次查询
        qcc_info = _fetch_qcc_info(name, tavily_key) if tavily_key else {}
        item["qcc"] = qcc_info

        # 匹配标签
        item["matchTags"] = _build_match_tags(item, tags)

        # 产品推荐
        item["recommendedProducts"] = _recommend_products(item["signals"])

    return top_companies


def _fetch_qcc_info(company_name: str, tavily_key: str) -> dict:
    """用 Tavily 搜 "公司全名 site:qcc.com" 抽取基础工商信息。"""
    try:
        client = TavilyClient(api_key=tavily_key)
        raw = client.search(
            f"{company_name} site:qcc.com",
            max_results=1,
            search_depth="basic",
            include_domains=["qcc.com"],
        )
        results = raw.get("results") or []
        if not results:
            return {}
        content = results[0].get("content") or ""
        title = results[0].get("title") or ""
        text = title + " " + content

        # 朴素抽取（不再调 LLM，省 token）
        info: dict = {}
        # 法人
        m = re.search(r"法[定人]*代表人[：:]\s*([\u4e00-\u9fa5]{2,4})", text)
        if m:
            info["legalRep"] = m.group(1)
        # 注册资本
        m = re.search(r"注册资本[：:]\s*([\d\.]+\s*[万亿])", text)
        if m:
            info["registeredCapital"] = m.group(1)
        # 成立日期
        m = re.search(r"成立日期[：:]\s*(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})", text)
        if m:
            info["founded"] = m.group(1)
        elif re.search(r"成立日期[：:]\s*(\d{4})", text):
            info["founded"] = re.search(r"成立日期[：:]\s*(\d{4})", text).group(1)
        # 统一社会信用代码
        m = re.search(r"([0-9A-Z]{18})", text)
        if m:
            info["uscc"] = m.group(1)
        # 员工
        m = re.search(r"(\d+)\s*人", text)
        if m:
            try:
                info["employees"] = int(m.group(1))
            except Exception:
                pass
        return info
    except Exception:
        return {}


def _build_match_tags(item: dict, tags: list[dict]) -> list[dict]:
    """构建匹配标签（行业/区域/信号类型维度）。"""
    match_tags = []
    signals = item.get("signals", [])
    signal_types = set(s.get("signal_type") for s in signals)

    # 行业匹配
    industry_tag = next((t for t in tags if t.get("category") == "行业"), None)
    if industry_tag:
        # 简单判断：如果信号中出现了行业相关词
        match_tags.append({
            "label": "行业精确匹配",
            "matched": True,
            "detail": f"信号涉及目标行业 '{industry_tag['value']}'",
        })

    # 区域匹配
    region_tag = next((t for t in tags if t.get("category") == "区域"), None)
    qcc = item.get("qcc", {})
    if region_tag:
        match_tags.append({
            "label": "区域命中",
            "matched": True,
            "detail": f"目标区域 '{region_tag['value']}'",
        })

    # 近期扩产
    if "growth" in signal_types:
        growth_signals = [s for s in signals if s.get("signal_type") == "growth"]
        detail = growth_signals[0].get("signal_title", "") if growth_signals else ""
        match_tags.append({
            "label": "近期扩产",
            "matched": True,
            "detail": detail,
        })

    # 专精特新
    if "recognition" in signal_types:
        rec_signals = [s for s in signals if s.get("signal_type") == "recognition"]
        detail = rec_signals[0].get("signal_title", "") if rec_signals else ""
        match_tags.append({
            "label": "专精特新",
            "matched": True,
            "detail": detail,
        })

    # 中标信号
    if "bidding" in signal_types:
        bid_signals = [s for s in signals if s.get("signal_type") == "bidding"]
        detail = bid_signals[0].get("signal_title", "") if bid_signals else ""
        match_tags.append({
            "label": "近期中标",
            "matched": True,
            "detail": detail,
        })

    # 技术突破
    if "tech" in signal_types:
        tech_signals = [s for s in signals if s.get("signal_type") == "tech"]
        detail = tech_signals[0].get("signal_title", "") if tech_signals else ""
        match_tags.append({
            "label": "技术突破",
            "matched": True,
            "detail": detail,
        })

    return match_tags


def _recommend_products(signals: list[dict]) -> list[str]:
    """根据信号内容匹配推荐产品。"""
    all_text = " ".join(
        (s.get("signal_title", "") + " " + s.get("signal_detail", ""))
        for s in signals
    )
    products = []
    for keywords, product in PRODUCT_RULES:
        if any(kw in all_text for kw in keywords):
            products.append(product)
    if not products:
        products.append("流动资金贷款")
    return products


# ========== Stage 5: 话术生成 ==========

def _generate_pitch(llm, item: dict) -> str:
    """基于最强信号 + 推荐产品，生成个性化切入话术。"""
    if llm is None:
        return _fallback_pitch(item)

    signals = item.get("signals", [])
    top_signal = signals[0] if signals else {}
    products = item.get("recommendedProducts", [])

    system = "你是银行客户经理的营销助手。根据企业信号生成简短的首次接触话术。"
    user_prompt = f"""公司名：{item['company_name']}
最强信号：{top_signal.get('signal_title', '')} — {top_signal.get('signal_detail', '')}
推荐产品：{', '.join(products)}
信号数量：{len(signals)} 条

请生成一段个性化的客户经理首次电话/拜访开场白，要求：
1. 50-80 字
2. 提及具体信号（不要泛泛而谈）
3. 自然引出产品
4. 语气专业但亲和

只输出话术文本，不要引号或其他格式。"""

    try:
        raw = llm.simple_chat(system, user_prompt, temperature=0.5)
        pitch = (raw or "").strip()
        if pitch:
            return pitch[:200]
    except Exception:
        pass

    return _fallback_pitch(item)


def _fallback_pitch(item: dict) -> str:
    """无 LLM 时的兜底话术。"""
    signals = item.get("signals", [])
    products = item.get("recommendedProducts", [])
    top_signal = signals[0] if signals else {}
    title = top_signal.get("signal_title", "近期业务动态")
    prod = products[0] if products else "融资方案"
    return f"您好，注意到贵司{title}，我行可提供{prod}支持，方便约个时间详细沟通吗？"


# ========== Stage 6: 构建最终输出 ==========

def _build_final_output(enriched: list[dict], tags: list[dict]) -> list[dict]:
    """将内部结构转为前端契约格式。"""
    NA = "未获取"
    candidates = []
    for item in enriched:
        qcc = item.get("qcc", {})
        signals_out = []
        data_sources = []
        seen_sources = set()

        for s in item.get("signals", []):
            signals_out.append({
                "type": s.get("signal_type", ""),
                "title": s.get("signal_title", ""),
                "detail": s.get("signal_detail", ""),
                "date": s.get("signal_date", ""),
                "source": s.get("signal_source", ""),
                "url": s.get("source_url", ""),
            })
            src = s.get("signal_source", "")
            url = s.get("source_url", "")
            if src and src not in seen_sources:
                seen_sources.add(src)
                data_sources.append({"label": src, "hint": url[:80] if url else ""})

        candidates.append({
            "name": item["company_name"],
            "signalScore": item.get("signalScore", 0),
            "signalCount": item.get("signalCount", 0),
            "source": "external",
            "signals": signals_out,
            # 基础信息（企查查补全）
            "region": qcc.get("region", NA),
            "industry": NA,
            "uscc": qcc.get("uscc", NA),
            "registeredCapital": qcc.get("registeredCapital", NA),
            "founded": qcc.get("founded", NA),
            "legalRep": qcc.get("legalRep", NA),
            "employees": qcc.get("employees", 0),
            "mainBusiness": NA,
            # 匹配+营销
            "matchTags": item.get("matchTags", []),
            "recommendedProducts": item.get("recommendedProducts", []),
            "pitch": item.get("pitch", ""),
            # 来源
            "dataSources": data_sources,
        })

    return candidates


# ========== 工具函数 ==========

def _tags_to_filters(tags: list[dict]) -> dict:
    f: dict = {}
    for t in tags:
        c = t.get("category")
        v = t.get("value") or ""
        if c == "区域":
            f["region"] = v
        elif c == "行业":
            f["industry"] = v
        elif c == "规模":
            if "小" in v or "微" in v:
                f["scale"] = ["小型", "微型"]
            elif "大" in v:
                f["scale"] = ["大型"]
            else:
                f["scale"] = ["中型"]
    return f


def _signal_type_label(stype: str) -> str:
    return {
        "bidding": "中标",
        "recognition": "认可",
        "tech": "技术",
        "growth": "扩产",
        "award": "获奖",
    }.get(stype, stype)


def _guess_company_name(text: str) -> str:
    """无 LLM 时的朴素兜底：匹配中文公司名常见后缀。"""
    m = re.search(
        r"([\u4e00-\u9fa5A-Za-z0-9（）()·\- ]{2,30}(?:股份|有限|集团)?(?:公司|厂|企业|研究院))",
        text or "",
    )
    return m.group(1).strip() if m else ""


def _domain_from_url(url: str) -> str:
    """从 URL 提取域名作为来源名。"""
    try:
        parts = url.split("/")
        if len(parts) >= 3:
            return parts[2]
    except Exception:
        pass
    return ""
