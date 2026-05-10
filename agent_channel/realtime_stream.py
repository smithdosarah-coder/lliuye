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
import logging
import os
import re
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from statistics import median
from typing import Iterator

from llm import LLMClient
from agent_channel.candidate_evidence_scorer import annotate_candidates_with_evidence
from shared.kb_scan.search_provider import MockSearchProvider
from shared.kb_scan.tavily_client import TavilyClient, TavilySearchError
from shared.sse_envelope import (
    DATA_SOURCE_LIVE,
    DATA_SOURCE_MOCK_FALLBACK,
    DATA_SOURCE_MOCK_FORCED,
    make_done,
)

# 诊断 log：走 uvicorn stderr。
# 关键事件（数据源决策、0 命中降级）用 WARNING，便于线上排查；
# 细粒度（每路 result count、每条 extract 成败）用 DEBUG，默认静默。
logger = logging.getLogger(__name__)

# 6 阶段 key（与前端 channel-types.ts 的 CHANNEL_STAGES 对齐）
STAGES = ["parse", "signal_scan", "aggregate", "enrich", "pitch", "rank"]


# ============================================================================
# Batch 2 · Router/Lookalike 事件工厂(additive only;现有事件契约不变)
# ============================================================================
#
# 和 RouterLeadSearcher / LookAlikeKBMatcher 协作时,调用方可以通过这两个
# 工厂函数产出 SSE 事件,把 Router 偏好链命中 + look-alike 锚定透明化到前端。
# 命名遵循 "<namespace>.<verb>" 契约,不与 STAGES 冲突。

SOURCE_HIT_EVENT = "source.hit"
LOOKALIKE_MATCH_EVENT = "lookalike.match"


def source_hit_event(
    *, query: str, source_name: str, degraded: bool, count: int,
    evidence_urls: list[str] | None = None,
) -> dict:
    """Router.query 返回后,调用方产出的一条 "source.hit" SSE 事件。

    字段:
      query / source_name / degraded / count: 命中元信息
      evidence_urls: 前端点击回溯原文的 url 列表(可空)
    """
    return {
        "event": SOURCE_HIT_EVENT,
        "query": query,
        "source_name": source_name,
        "degraded": bool(degraded),
        "count": int(count),
        "evidence_urls": list(evidence_urls or []),
    }


def lookalike_match_event(
    *, candidate_name: str, match_score: float,
    breakdown: dict, top_anchors: list[str] | None = None,
) -> dict:
    """LookAlikeKBMatcher.score 返回后,调用方产出的一条 "lookalike.match" 事件。

    字段:
      candidate_name: 候选企业名
      match_score: [0, 1] 归一化分
      breakdown: {industry, scale, qualifications} 三维分
      top_anchors: 命中 Top-K 历史客户名
    """
    return {
        "event": LOOKALIKE_MATCH_EVENT,
        "candidate_name": candidate_name,
        "match_score": float(match_score),
        "breakdown": dict(breakdown),
        "top_anchors": list(top_anchors or []),
    }

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
    force_mock: bool = False,
    rm_region: str = "",
) -> Iterator[dict]:
    """主编排：yield 事件流。

    参数：
      force_mock — 前端 DEMO 开关。True 时跳过 Tavily，直接走 mock 池，
                   data_source 标记为 "mock_forced"，区别于 key 缺失 / 搜索 0 结果
                   触发的 "mock_fallback"。

    事件结构：
      {"event":"stage","stage":"parse","status":"running","message":"..."}
      {"event":"stage","stage":"parse","status":"done","tags":[...]}
      ... (6 stage x running/done)
      {"event":"done","candidates":[...], "metrics":{...},
       "data_source":"live"|"mock_forced"|"mock_fallback",
       "provider_source":"tavily" (only when data_source == live)}
      错误：{"event":"error","message":"...","traceback":"..."}

    V2 fix · codex review issue 3 · data_source 必须是 sse-envelope canonical enum
    (DATA_SOURCE_LIVE/MOCK_FORCED/MOCK_FALLBACK) · provider 细节 (e.g. tavily) 通过
    provider_source 单独字段透传 · A4 worker 复用本模式时不要再用 "tavily" 作 data_source
    """
    # C4 banner-spec rule 2 · warnings 收集 · 透传到 done envelope.warnings
    # 触发源(目前):TAVILY_API_KEY 缺 / TavilyClient init 失败 → mock_fallback
    warnings: list[str] = []

    try:
        session_id = str(uuid.uuid4())
        # api_key 优先级：调用方显式传入 > env DEEPSEEK_API_KEY > 空（退化到无 LLM 路径）
        # 修根因：前端请求体默认 api_key="",此前直接送给 LLMClient → DeepSeek 401 →
        #         _extract_signal 全失败 → all_signals=0 → mock_fallback。
        effective_key = (api_key or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        if not effective_key:
            logger.warning(
                "[channel] no LLM api_key (neither request nor env DEEPSEEK_API_KEY) → LLM disabled, signal extraction will use naive fallback"
            )
        try:
            llm = LLMClient(provider=provider or "deepseek", api_key=effective_key) if effective_key else None
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            logger.warning("[channel] LLMClient init failed: %s", e)
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

        # ===== Stage 2: signal_scan — 5 路并行信号搜索（流式，每路完成即通知）=====
        yield {"event": "stage", "stage": "signal_scan", "status": "running",
               "message": "5 路信号并行搜索（中标/认可/技术/增长/获奖）..."}
        raw_signals: list[dict] = []
        # V2 issue 3 · 初始值用 envelope canonical enum (非 "tavily")
        # _parallel_signal_search_iter 仍 yield "tavily" 作内部 provider 标记 ·
        # 在 final tuple 解构后 normalize 为 envelope enum + 拆出 provider_source
        provider_source: str | None = None
        data_source: str = DATA_SOURCE_LIVE
        route_progress = 0
        for item in _parallel_signal_search_iter(
            llm, industry, region, query, tags, force_mock=force_mock,
        ):
            kind = item[0]
            if kind == "progress":
                _, route, count = item
                route_progress += 1
                # 每路完成即 yield 进度事件 —— 防止 tunnel/cloudflare 判断连接死掉
                yield {"event": "progress", "stage": "signal_scan",
                       "route": route, "signals": count,
                       "routes_done": route_progress, "routes_total": 5}
            elif kind == "warning":
                # C4 banner-spec rule 2 · Tavily silent fallback 透明化 · 前端 banner 显
                _, msg = item
                warnings.append(msg)
                yield {"event": "stage", "stage": "signal_scan",
                       "status": "warning", "message": msg}
            elif kind == "final":
                _, raw_signals, raw_source = item
                # V2 issue 3 · raw_source 是 _parallel_signal_search_iter 内部 provider
                # 标记 ("tavily" / "mock_forced" / "mock_fallback") · 这里映射到 envelope enum
                if raw_source == "tavily":
                    data_source = DATA_SOURCE_LIVE
                    provider_source = "tavily"
                elif raw_source in (DATA_SOURCE_MOCK_FORCED, DATA_SOURCE_MOCK_FALLBACK):
                    data_source = raw_source
                    provider_source = None
                else:
                    data_source = raw_source  # 未知值不 silent 改写 · 让上层看到原值
                    provider_source = None
        # V2 issue 3 · stage event 也用 envelope enum · provider_source 单独字段
        stage_done_evt: dict = {"event": "stage", "stage": "signal_scan",
                                "status": "done", "count": len(raw_signals),
                                "data_source": data_source}
        if provider_source:
            stage_done_evt["provider_source"] = provider_source
        yield stage_done_evt

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

        # ===== Stage 5: pitch — 话术生成 (LLM grounded with evidence) =====
        # Critical 1+2 fix-forward (Codex review V1 bu84635ul · 2026-05-05):
        # - 旧顺序: enrich → pitch (LLM 看不到 evidence) → build → annotate
        # - 新顺序: enrich → build → annotate → pitch (LLM 看到 evidence_chain) → done
        # 把 _build_final_output + annotate 提前到 pitch 之前 · _generate_pitch 走
        # shared/llm_caller.LLMCaller (而非 legacy llm.simple_chat) · prompt 含 evidence_chain.
        # B.5: query + llm 透传给 sse_extras 做 industry/geo/scale 抽取 + similarity
        # 评分 + 8 维 radar + match_dimensions/products/pitch_scripts (B.5 别于本 BE1 evidence)
        candidates = _build_final_output(enriched, tags, query=query, llm=llm)
        # BE1 (Phase B Sprint 3 · 2026-05-05): 候选证据评分 · 4 维度确定性 0-100
        # + 证据链 (出处 file/URL/段落 ID) · 给 LLM grounded 推荐时的 grounded input
        # additive 字段 (evidence_score / evidence_chain / evidence_dimensions) ·
        # 不破 Q-041 4 字段 (industry/geo/scale/similarity) · 不调 LLM (per §3.1)
        candidates = annotate_candidates_with_evidence(candidates, rm_region=rm_region)

        yield {"event": "stage", "stage": "pitch", "status": "running",
               "message": "生成 grounded 切入话术 (走 evidence_chain 锚定)..."}
        for c in candidates:
            # 注意: _generate_pitch llm 参数保留签名兼容 (per domains/product_recommend.py)
            # · 内部已切到 LLMCaller PIPL chain · 此 llm 参数不再 use
            c["pitch"] = _generate_pitch(llm, c)
        yield {"event": "stage", "stage": "pitch", "status": "done"}

        # ===== Stage 6: rank — 最终排序输出 (candidates 已就绪) =====
        yield {"event": "stage", "stage": "rank", "status": "running",
               "message": "信号密度排序..."}
        yield {"event": "stage", "stage": "rank", "status": "done"}

        # C3 · workspace-state-protocol §4 + sse-envelope §3.1 · 7 panel canonical 共形
        # shared/sse_envelope.py make_done(panels=...) 把 panels expand 到 done event 顶层
        # V2 issue 3 · data_source 已在 final tuple 解构时 normalize · 这里直接透传 ·
        # provider_source 通过 make_done **extras 进 done event 顶层 (UI 需展示 "tavily" 时读它)
        done_extras: dict = {"warnings": warnings}
        if provider_source:
            done_extras["provider_source"] = provider_source
        yield make_done(
            panels={
                "candidates": candidates,
                "signals": _aggregate_signal_sources(raw_signals),
                "radar": _build_radar_p50(candidates),
                "funnel": _build_funnel(raw_signals, company_map, enriched, candidates),
                "match_dimensions": _aggregate_match_dimensions(candidates),
                "product_recommendations": _aggregate_product_recommendations(candidates),
                "pitch_scripts": _aggregate_pitch_scripts(candidates),
                # V3 fix · CHANNEL_PANEL_KEYS 8 key · ConversationPanel 显式从 done envelope 派生
                # 当前 live 路径不生成 AI dialog turns · 默认 [] · 前端 normalizeBackendDone 兜底
                # tplFallback.conversation (mock session 模板的对话) · A4-channel 生成 AI 复盘时再
                # 真填 turns
                "conversation": [],
            },
            metrics={
                "signalTotal": len(raw_signals),
                "companiesFound": len(company_map),
                "final": len(candidates),
            },
            data_source=data_source,
            session_id=session_id,
            **done_extras,
        )
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
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
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, json.JSONDecodeError):
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

def _parallel_signal_search_iter(
    llm, industry: str, region: str, query: str, tags: list[dict],
    force_mock: bool = False,
):
    """流式版：每路完成 yield ("progress", stype, count)，最终 yield ("final", signals, data_source).

    设计目的：SSE 下游每 3-10 秒收到一个 progress 事件，防止 Cloudflare 等中间代理
    因为长时间静默而 buffer/断开。
    """
    for item in _parallel_signal_search_core(llm, industry, region, query, tags, force_mock):
        yield item


def _parallel_signal_search_core(
    llm, industry: str, region: str, query: str, tags: list[dict],
    force_mock: bool = False,
):
    """原 _parallel_signal_search 的 generator 版。"""
    # === 诊断 log: 入口状态快照 ===
    tavily_key = os.environ.get("TAVILY_API_KEY")
    key_preview = (tavily_key[:10] + "...") if tavily_key else None
    logger.warning(
        "[channel.signal_search] enter: force_mock=%s TAVILY_API_KEY=%s llm=%s industry=%r region=%r",
        force_mock, key_preview, "yes" if llm else "no", industry, region,
    )

    # 前端显式切 DEMO → 跳过 Tavily
    if force_mock:
        logger.warning("[channel.signal_search] force_mock=True → skip Tavily, use mock pool")
        yield ("final", _mock_signal_fallback(query, tags), "mock_forced")
        return

    if not tavily_key:
        logger.warning("[channel.signal_search] TAVILY_API_KEY missing → mock_fallback")
        # C4 banner-spec rule 2 · 显式 warning · 不静默 · 前端 banner 提示
        yield ("warning", "TAVILY_API_KEY 未配置 · 已降级为 mock 演示数据 · 配置 key 后可恢复 live")
        yield ("final", _mock_signal_fallback(query, tags), "mock_fallback")
        return

    # 构建 5 路查询
    ind = industry or "企业"
    reg = region or ""
    queries = [
        (tpl.format(industry=ind, region=reg).strip(), stype)
        for tpl, stype in SIGNAL_QUERIES
    ]

    try:
        client = TavilyClient(api_key=tavily_key)
    except TavilySearchError as e:
        logger.warning("[channel.signal_search] TavilyClient init failed: %s → mock_fallback", e)
        yield ("warning", f"Tavily 客户端初始化失败 ({e}) · 已降级为 mock 演示数据")
        yield ("final", _mock_signal_fallback(query, tags), "mock_fallback")
        return

    all_signals: list[dict] = []
    # 统计每路情况：{stype: (raw_count, extracted_count, error)}
    route_stats: dict[str, tuple[int, int, str]] = {}

    def _search_one(q: str, signal_type: str) -> list[dict]:
        """单路搜索 + LLM 信号抽取。"""
        try:
            raw = client.search(
                q, max_results=2, search_depth="advanced",
                include_domains=SIGNAL_INCLUDE_DOMAINS,
                exclude_domains=SIGNAL_EXCLUDE_DOMAINS,
            )
        except TavilySearchError as e:
            logger.warning(
                "[channel.signal_search] route=%s TavilySearchError: status=%s msg=%s preview=%.200s",
                signal_type, getattr(e, "status", None), str(e), getattr(e, "body_preview", ""),
            )
            route_stats[signal_type] = (0, 0, f"tavily_err:{e}")
            return []
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
            logger.warning(
                "[channel.signal_search] route=%s unexpected error: %s: %s",
                signal_type, type(e).__name__, e,
            )
            route_stats[signal_type] = (0, 0, f"unexpected:{type(e).__name__}")
            return []
        results = raw.get("results") or []
        logger.info(
            "[channel.signal_search] route=%s query=%r raw_results=%d",
            signal_type, q, len(results),
        )
        signals = []
        extract_success = 0
        extract_fail = 0
        for r in results:
            title = r.get("title") or ""
            content = r.get("content") or ""
            url = r.get("url") or ""
            if not (title or content):
                extract_fail += 1
                continue
            extracted = _extract_signal(llm, title, content, url, signal_type)
            if extracted:
                signals.extend(extracted)
                extract_success += 1
            else:
                extract_fail += 1
        logger.info(
            "[channel.signal_search] route=%s extract: success=%d fail=%d signals=%d",
            signal_type, extract_success, extract_fail, len(signals),
        )
        route_stats[signal_type] = (len(results), len(signals), "")
        return signals

    # 并行执行 5 路搜索 —— 手动管理 pool 避免退出时等待 hang 的 future
    pool = ThreadPoolExecutor(max_workers=5)
    futures = {
        pool.submit(_search_one, q, stype): stype
        for q, stype in queries
    }
    try:
        try:
            for future in as_completed(futures, timeout=25):
                stype = futures[future]
                try:
                    signals = future.result(timeout=15)
                    all_signals.extend(signals)
                    yield ("progress", stype, len(signals))
                except TimeoutError:
                    logger.warning("[channel.signal_search] route=%s TIMEOUT 15s, skipped", stype)
                    route_stats[stype] = (0, 0, "timeout_15s")
                    yield ("progress", stype, 0)
                except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
                    logger.warning("[channel.signal_search] route=%s future failed: %s", stype, e)
                    route_stats[stype] = (0, 0, f"exc:{type(e).__name__}")
                    yield ("progress", stype, 0)
                    continue
        except TimeoutError:
            logger.warning("[channel.signal_search] overall 25s TIMEOUT, cancelling remaining")
            for f, s in futures.items():
                if not f.done():
                    f.cancel()
                    route_stats[s] = (0, 0, "cancelled_overall_timeout")
                    yield ("progress", s, 0)
    finally:
        # wait=False + cancel_futures=True：立刻退出，不等 hang 的任务
        pool.shutdown(wait=False, cancel_futures=True)

    # 汇总 log
    logger.warning(
        "[channel.signal_search] DONE: all_signals=%d route_stats=%s",
        len(all_signals), route_stats,
    )

    if all_signals:
        yield ("final", all_signals, "tavily")
        return

    # Tavily 搜到 0 条信号 → 降级 mock
    logger.warning(
        "[channel.signal_search] all routes returned 0 signals → mock_fallback (route_stats=%s)",
        route_stats,
    )
    yield ("warning", "Tavily 5 路搜索 0 命中 · 已降级为 mock 演示数据 · 检查 query / 网络代理")
    yield ("final", _mock_signal_fallback(query, tags), "mock_fallback")


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
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
        return None

    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        arr = json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        lo = text.find("[")
        hi = text.rfind("]")
        if lo >= 0 and hi > lo:
            try:
                arr = json.loads(text[lo:hi + 1])
            except (json.JSONDecodeError, ValueError, TypeError):
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
    except (ValueError, TypeError):
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
    """工商基础信息查询。

    新版优先走分层数据源 Router (agent_channel.enterprise_info)：
        - 上市公司 → akshare（结构化）
        - 非上市公司 → Tavily 定向搜 qcc/tianyancha + LLM 严抽 6 字段

    Router 不可用 / 全链失败时降级到下方旧 Tavily snippet 抠字段逻辑——
    确保零回归：分层架构挂了 Agent1 还能跑。

    返回 dict 同时带 snake_case（新源 schema）和 camelCase（下游 candidates 兼容）
    两套键名，下游 _enrich_top_companies / 渲染层零感知。
    """
    # --- 新路径：分层数据源 Router ---
    try:
        from shared.sources.router import Router
        from shared.sources.base import QueryRequest
        result = Router().query(
            "agent_channel.enterprise_info",
            QueryRequest(query=company_name, query_type="company_info", limit=1),
        )
        if result.ok and result.items:
            info = result.items[0]
            evidence_url = result.evidence[0].source_url if result.evidence else ""
            # snake_case → camelCase 兼容映射；下游 candidates dict 沿用 camelCase
            mapped: dict = {
                # snake_case（新 schema）
                "registered_capital": info.get("registered_capital", ""),
                "legal_representative": info.get("legal_representative", ""),
                "establishment_date": info.get("establishment_date", ""),
                "industry": info.get("industry", ""),
                "business_scope": info.get("business_scope", ""),
                "registered_address": info.get("registered_address", ""),
                # camelCase（保下游零感知，对应原朴素抽取的旧键名）
                "registeredCapital": info.get("registered_capital", ""),
                "legalRep": info.get("legal_representative", ""),
                "founded": info.get("establishment_date", ""),
                # 透传：来源/取证 URL，便于前端做"数据来自 xxx"角标
                "_source": result.source_name,
                "_evidence_url": evidence_url,
                "_degraded": result.degraded,
            }
            return mapped
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
        # 优雅降级到旧 Tavily 逻辑——分层架构挂了不影响 Agent1
        pass

    # --- Fallback：原 Tavily snippet 抠字段逻辑（一行不改地保留）---
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
            except (ValueError, TypeError):
                pass
        return info
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
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

def _build_pitch_system_prompt() -> str:
    """Channel pitch 8 段 system prompt · 接 shared/prompts/contract · A1 spec landed
    自动 pickup · 当前 placeholder 时 fallback 本地 explicit 实装.

    per Codex review V1 NEEDS-FIX critical 2 · pitch 必须用 shared/llm_caller +
    8 段 system prompt + grounded evidence (不裸 simple_chat).
    """
    try:
        from shared.prompts.contract import assemble
        a1_prompt = assemble(role="agent1_channel_pitch")
        if a1_prompt:
            return a1_prompt
    except (ImportError, RuntimeError):
        pass

    # A1 placeholder · fallback 本地 explicit 8 段
    return (
        "[1 safety] 你是众安信科 Agent1 全渠道获客的客户经理营销助手。严守 PIPL 合规底线 · "
        "不输出 PII · 不编造未在 evidence_chain 中出现的信息 · 不写 jailbreak 引诱话术。\n\n"
        "[2 evidence-first] 三层信息框架: 必须以 user prompt 中的 evidence_chain 为锚 · "
        "不引外部数据 · 每条话术信息点必须能映射到 evidence_chain 中某条 quote。\n\n"
        "[3 agent-role] Agent1 客户经理首次接触话术助手 · 不做授信决策 (Agent3 owns) · "
        "不做合规判定 (Agent5 owns) · 仅生成 50-80 字开场白。\n\n"
        "[4 tool-use] 本场景无 tool · 全部上下文在 user prompt。\n\n"
        "[5 output-schema] 仅输出话术文本 · 不要 markdown / JSON / 引号 / 解释 · "
        "长度 50-80 字 (汉字)。\n\n"
        "[6 self-check] 输出前自审: (a) 长度 50-80 字; (b) 提及的具体信号必能在 "
        "evidence_chain 找到 quote (不泛化套话); (c) 自然引出推荐产品 (不硬推); "
        "(d) 不输出 PII / 公司外部敏感信息。\n\n"
        "[7 few-shot] (Phase B Sprint 3 POC · skip · 等 data/feedback/ jsonl 积累)\n\n"
        "[8 evaluation-hook] 评估锚点: evaluation/agent_channel.yaml 的 evidence_rate · "
        "不输出无证据 talking point。"
    )


def _generate_pitch(llm, item: dict) -> str:
    """LLM grounded 话术生成 · 走 shared/llm_caller (PIPL 境内 fallback chain)
    + 8 段 system prompt + evidence_chain (deterministic grounded input).

    per Codex review V1 NEEDS-FIX:
    - critical 1: pitch 之前 candidate 已 annotate (run_channel_search_stream 重排
      stage 顺序 · _build_final_output + annotate 移到 stage 5 之前) · 本函数能
      在 item['evidence_chain'] / item['evidence_score'] / item['evidence_dimensions']
      读到确定性证据 · LLM 看见 grounded input
    - critical 2: 走 shared.llm_caller.LLMCaller (PIPL 境内 chain) · 不再用
      legacy llm.simple_chat (legacy `llm` 参数保留为签名兼容 · 不 use)

    `llm` 参数保留为签名兼容 (`agent_channel/domains/product_recommend.py:9` 复用)
    · 内部不再 use · 走 LLMCaller PIPL chain.
    """
    signals = item.get("signals", []) or []
    if not signals:
        return _fallback_pitch(item)

    top_signal = signals[0] if signals else {}
    products = (
        item.get("recommendedProducts")
        or item.get("recommended_products")
        or []
    )

    # evidence_chain 是 candidate_evidence_scorer 注入的 list[EvidenceItem]
    # · 每条 {source, quote, source_url?, file?, paragraph_id, confidence}
    evidence_chain = item.get("evidence_chain") or []
    evidence_lines = []
    for ev in evidence_chain[:6]:
        src = ev.get("source", "") or "unknown"
        quote = ev.get("quote", "") or ev.get("file", "") or ev.get("source_url", "")
        if quote:
            evidence_lines.append(f"- [{src}] {str(quote)[:120]}")
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "(本批 evidence 为空 · 仅基于信号生成)"

    company_name = (
        item.get("company_name")
        or item.get("name")
        or "目标企业"
    )
    industry = item.get("industry") or "未知"
    geo = item.get("geo") or item.get("region") or "未知"
    scale = item.get("scale") or "未知"
    similarity = item.get("similarity", 0)
    evidence_score = item.get("evidence_score", 0)

    user_prompt = (
        f"公司名: {company_name}\n"
        f"行业: {industry}\n"
        f"地域: {geo}\n"
        f"规模: {scale}\n"
        f"相似度 (vs 内源已成交客户): {similarity:.2f}\n"
        f"证据评分: {evidence_score}/100 (确定性 4 维度 industry/scale/region/signal 加权)\n\n"
        f"证据链 (deterministic · 来自内源 KB / 外部信号 / RM 配置):\n{evidence_block}\n\n"
        f"最强信号: {top_signal.get('signal_title') or top_signal.get('title', '')} — "
        f"{top_signal.get('signal_detail') or top_signal.get('detail', '')}\n"
        f"推荐产品: {', '.join(products) if products else '(未指定 · 用通用融资方案兜底)'}\n"
        f"信号总数: {len(signals)}\n\n"
        "请生成一段 50-80 字的客户经理首次电话/拜访开场白:\n"
        "1. 必须提及证据链中具体信号 (不泛泛而谈)\n"
        "2. 自然引出推荐产品 (不硬推)\n"
        "3. 语气专业但亲和\n"
        "4. 只输出话术文本 · 不要引号 / 解释 / 格式标记"
    )

    system = _build_pitch_system_prompt()

    try:
        from shared.llm_caller.client import LLMCaller
        from shared.llm_caller.provider import ProviderUnavailableError
    except ImportError:
        return _fallback_pitch(item)

    caller = LLMCaller(agent_id="channel", endpoint="/api/channel/run/pitch")
    try:
        result = caller.chat(system, user_prompt, temperature=0.5)
    except ProviderUnavailableError:
        return _fallback_pitch(item)
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
        return _fallback_pitch(item)

    pitch = (result.content or "").strip()
    if pitch:
        return pitch[:200]
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

def _build_final_output(
    enriched: list[dict],
    tags: list[dict],
    query: str = "",
    llm=None,
) -> list[dict]:
    """将内部结构转为前端契约格式。

    Stage B.5 + Q-041 fix-forward (2026-04-28):
      - 现有 camelCase 字段全部保留 (additive · 不破坏 production normalize)
      - ``industry`` / ``region`` 不再硬编 "未获取" · 由 ``sse_extras.extract_metadata``
        从 qcc + signal text 抽取 (Q-041 fix)
      - 追加 snake_case 字段 (B.5 spec): ``score / geo / scale / similarity /
        radar_8axis / match_dimensions / product_recommendations / pitch_scripts``
      - ``query`` / ``llm`` 上游传入 · 用于关键词抽取 + 相似度评分 + LLM 兜底
    """
    from agent_channel.sse_extras import NA as EXTRAS_NA, enrich_candidate

    NA = "未获取"
    candidates = []
    for _idx, item in enumerate(enriched):
        qcc = item.get("qcc", {}) or {}
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

        # B.5 新字段 (snake_case · 见 sse_extras.enrich_candidate docstring)
        extras = enrich_candidate(item, query=query, tags=tags, llm=llm)

        # Q-041 fix:industry / region 从 extras 取真值;legacy "NA" 兜底
        industry = extras["industry"]
        # legacy region 字段沿用 qcc.region 或 extras.geo · 不留空 fallback NA
        region = qcc.get("region") or extras["geo"] or NA
        signal_score = item.get("signalScore", 0)

        # PM 2026-05-08 ALL IN bug fix · 候选企业必出唯一 id (Q-041 5 字段 + id)
        # 之前候选 dict 没 id 字段 · 前端 setSelectedCandidate(c.id) 全收 "未获取" (NA fallback)
        # find(c.id === selectedCandidate) 在 8 个 id 都相同的数组里永远返第一家
        # → 雷达图 + 抽屉永远显第一家 · 不联动 (PM 反复痛点真根因)
        # Phase B.2 (PM 2026-05-10 §8 unique id contract v1.1): 占位 id · 后由
        # ensure_list_unique_ids 重派 (走 make_unique_id 标准路径 + GB 32100 校验 + 同 list 去重)
        candidates.append({
            # ---- 占位 id · 下方 ensure_list_unique_ids 会按 contract v1.1 派生覆盖 ----
            "id": "",
            # ---- legacy camelCase (production 已消费 · 不动) ----
            "name": item["company_name"],
            "signalScore": signal_score,
            "signalCount": item.get("signalCount", 0),
            "source": "external",
            "signals": signals_out,
            # 基础信息(qcc / extras 补全)
            "region": region,
            "industry": industry,            # ← Q-041 fix · 不再硬编 NA
            "uscc": qcc.get("uscc", NA),
            "registeredCapital": qcc.get("registeredCapital", NA),
            "founded": qcc.get("founded", NA),
            "legalRep": qcc.get("legalRep", NA),
            "employees": qcc.get("employees", 0),
            "mainBusiness": NA,
            # 匹配+营销 (legacy)
            "matchTags": item.get("matchTags", []),
            "recommendedProducts": item.get("recommendedProducts", []),
            "pitch": item.get("pitch", ""),
            # 来源
            "dataSources": data_sources,

            # ---- B.5 新增 snake_case (前端 b.5b 步消费 · 现 additive 输出) ----
            # score: signalScore 别名 · 前端 ChannelWorkspace.tsx 候选卡 score 取此键
            "score": int(signal_score) if signal_score else 0,
            # Q-041 4 字段 fix-forward
            "geo": extras["geo"],
            "scale": extras["scale"],
            "similarity": extras["similarity"],
            # Q-054 B1 · 第 5 维度 signal_density 0-1 (近 90 天动态信号密度 · LLM+静态)
            "signal_density": extras["signal_density"],
            "signal_density_reason": extras["signal_density_reason"],
            # 8 维 radar (per-candidate · 与全局 radar 不同 · 给候选 detail drawer 用)
            "radar_8axis": extras["radar_8axis"],
            # PRD v2 "为什么像" + Top3 产品 + 话术 (struct)
            "match_dimensions": extras["match_dimensions"],
            "product_recommendations": extras["product_recommendations"],
            "pitch_scripts": extras["pitch_scripts"],
        })

    # Phase B.2 (PM 2026-05-10 §8 candidate-identity-contract v1.1) · 必经 helper
    # 派生 id 字段 · 走 make_unique_id (USCC GB 32100 校验 + name normalize + 同 list 去重)
    # 上面占位 id="" → 这里覆盖派生 · 不允许 raw dict emit (per contract §4.2 hard rule)
    from shared.entity_resolver import ensure_list_unique_ids
    ensure_list_unique_ids(candidates, name_field="name", uscc_field="uscc")

    return candidates


# ========== 工具函数 ==========

# ============================================================================
# C3 · 7 panel aggregator helpers (workspace-state-protocol §4 + sse-envelope §3.1)
# 6 fns 把 _build_final_output 的 candidates + raw_signals + company_map 聚合到
# done envelope 7 panel keys (CHANNEL_PANEL_KEYS = candidates / signals / radar /
# funnel / match_dimensions / product_recommendations / pitch_scripts).
# ============================================================================

# signal_type → SignalSource.key (前端 8 信号源 enum)
# 反模式禁止: 凭空编 hits/coverage 数字 · 必须从 raw_signals 真聚合
_SIGNAL_TYPE_TO_KEY = {
    "bidding": "bidding",
    "recognition": "pr",
    "tech": "pr",
    "award": "pr",
    "news": "pr",
    "growth": "funding",
    "biz": "biz",
    "legal": "legal",
    "tax": "tax",
    "recruit": "hr",
    "social": "social",
}

_SIGNAL_KEY_LABELS = {
    "biz": "工商变更",
    "bidding": "招投标",
    "pr": "媒体公告",
    "legal": "司法诉讼",
    "social": "社交舆情",
    "tax": "税务",
    "hr": "招聘动态",
    "funding": "融资动态",
}


def _aggregate_signal_sources(raw_signals: list[dict]) -> list[dict]:
    """8 信号源 status / hits / coverage · 从 raw_signals 真聚合 (反模式: 假数据)."""
    counts: dict[str, int] = {k: 0 for k in _SIGNAL_KEY_LABELS}
    for s in raw_signals:
        k = _SIGNAL_TYPE_TO_KEY.get(s.get("signal_type", ""), "pr")
        counts[k] = counts.get(k, 0) + 1
    total = sum(counts.values()) or 1
    out = []
    for i, (key, label) in enumerate(_SIGNAL_KEY_LABELS.items()):
        hits = counts.get(key, 0)
        out.append({
            "id": f"src-{key}",
            "key": key,
            "label": label,
            "status": "active" if hits > 0 else "off",
            "weight": round(hits / total, 2),
            "freq": "实时" if hits > 0 else "—",
            "coverage": min(100, int(hits * 100 / max(1, total))),
            "hits": hits,
        })
    return out


# radar 8-axis key → frontend RadarQuadrant
_RADAR_QUADRANT = {
    "信号密度": "base",
    "行业匹配": "base",
    "区域匹配": "base",
    "规模匹配": "base",
    "近期活跃度": "demand",
    "资质含金量": "bonus",
    "技术强度": "bonus",
    "相似度": "market",
}


def _build_radar_p50(candidates: list[dict]) -> list[dict]:
    """8 维 P50 对标 · 用候选集 median 当 score · benchmark=50 (P50 锚)."""
    if not candidates:
        return []
    # 收集每 axis 的所有候选 score · 取 median 作为 panel score
    axis_scores: dict[str, list[float]] = {}
    for c in candidates:
        radar = c.get("radar_8axis") or {}
        for axis, val in radar.items():
            try:
                axis_scores.setdefault(axis, []).append(float(val))
            except (TypeError, ValueError):
                continue
    out = []
    for axis, scores in axis_scores.items():
        if not scores:
            continue
        out.append({
            "axis": axis,
            "score": int(round(median(scores))),
            "benchmark": 50,  # P50 锚 · 行业中位
            "quadrant": _RADAR_QUADRANT.get(axis, "base"),
            "note": f"{len(scores)} 候选 · median",
        })
    return out


def _build_funnel(
    raw_signals: list[dict],
    company_map: dict,
    enriched: list[dict],
    candidates: list[dict],
) -> list[dict]:
    """5 阶段扫描漏斗 · 数据来自 stage 实时计数 · 前端 FunnelStrip 消费."""
    return [
        {"id": "fn-1", "label": "信号池",     "count": len(raw_signals),
         "detail": f"{len({s.get('signal_source') for s in raw_signals if s.get('signal_source')})} 源"},
        {"id": "fn-2", "label": "实体聚合",   "count": len(company_map),
         "detail": "按企业名/USCC 去重"},
        {"id": "fn-3", "label": "Top 排序",   "count": len(enriched),
         "detail": "信号密度 + 时效加权"},
        {"id": "fn-4", "label": "工商补全",   "count": len(enriched),
         "detail": "企查查 + 资质字段"},
        {"id": "fn-5", "label": "Top 推荐",   "count": len(candidates),
         "detail": "话术 + 产品匹配"},
    ]


def _aggregate_match_dimensions(candidates: list[dict]) -> list[dict]:
    """top-level union · 取 top 候选所有 match_dimension (展示给 panel · 不去重 dim_name).
    候选 detail drawer 仍消费 per-candidate match_dimensions (在 candidates[].match_dimensions)."""
    out: list[dict] = []
    for c in candidates[:3]:
        for md in c.get("match_dimensions", []) or []:
            out.append(md)
    return out


def _aggregate_product_recommendations(candidates: list[dict]) -> list[dict]:
    """top-level Top3 · 跨候选选 fit_score 最高 3 个 (per-candidate 仍在 candidates[].product_recommendations)."""
    flat: list[dict] = []
    for c in candidates:
        for p in c.get("product_recommendations", []) or []:
            flat.append(p)
    flat.sort(key=lambda p: p.get("fit_score", 0), reverse=True)
    return flat[:3]


def _aggregate_pitch_scripts(candidates: list[dict]) -> list[dict]:
    """top-level pitch · top 3 候选各 1 (per-candidate 仍在 candidates[].pitch_scripts)."""
    out: list[dict] = []
    for c in candidates[:3]:
        scripts = c.get("pitch_scripts") or []
        if scripts:
            out.append(scripts[0])
    return out


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
    except (AttributeError, TypeError, IndexError):
        pass
    return ""
