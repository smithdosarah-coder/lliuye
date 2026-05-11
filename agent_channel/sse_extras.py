# -*- coding: utf-8 -*-
"""SSE done event 候选额外字段构建器 · master plan §B.5 + Q-041 fix-forward。

为 ``run_channel_search_stream`` 的 done 事件每个 candidate 补齐:
  - ``industry`` / ``geo`` / ``scale`` (Q-041 修 · 原硬编 "未获取")
  - ``similarity``                       (0~1 float · P0 keyword overlap)
  - ``radar_8axis``                      (8 维 0-100)
  - ``match_dimensions``                 (PRD v2 "为什么像")
  - ``product_recommendations``          (Top3 structured)
  - ``pitch_scripts``                    (含 ``{客户名}`` 占位符)

设计:
  - 抽取优先级 qcc → signal 关键词 → (可选) LLM → fallback "未获取"
  - 全部 *additive* · 现有 candidate 键名(camelCase)保持不变 · 前端 b.5b
    步消费这批新键 (snake_case) 时双源都在 · 零回归
  - similarity 用 P0 简单 token Jaccard · P3 改 ``LookAlikeKBMatcher`` /
    ``SimilarityScorer`` (channel-spec.md §C5 § 4a/4b)

Author: Worker A1 (Stage B 第 1 批) · 2026-04-28
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

NA = "未获取"
CUSTOMER_NAME_PLACEHOLDER = "{客户名}"


# ============================================================================
# 词典与启发式规则 (regex / keyword 走通 · LLM 仅做兜底)
# ============================================================================

_REGION_PATTERNS = [
    # 直辖市
    "北京", "上海", "天津", "重庆",
    # 省份
    "浙江", "江苏", "广东", "山东", "河北", "河南", "湖北", "湖南",
    "四川", "福建", "安徽", "江西", "陕西", "辽宁", "吉林", "黑龙江",
    "内蒙古", "广西", "云南", "贵州", "山西", "甘肃", "海南", "新疆",
    "西藏", "青海", "宁夏",
    # 经济区
    "长三角", "珠三角", "京津冀", "成渝",
    # 重点城市
    "杭州", "苏州", "宁波", "无锡", "南京", "深圳", "广州", "厦门",
    "福州", "成都", "武汉", "合肥", "西安", "青岛", "济南", "温州",
    "绍兴", "嘉兴", "金华", "台州",
]

_SCALE_HINTS = {
    "微型": "微型", "小微": "小型", "小型": "小型",
    "中型": "中型",
    "大型": "大型", "巨型": "大型",
}

_INDUSTRY_HINTS = [
    # PRD 高频
    "新能源汽车", "新能源", "半导体", "光伏", "储能",
    "精密零部件", "精密机械", "智能制造", "装备制造",
    "SaaS", "工业软件", "信息技术", "互联网",
    "建材", "批发零售", "批发", "纺织", "服装",
    "医疗器械", "生物医药", "医药",
    "汽车零部件", "汽车", "机械",
    "人工智能", "AI", "大数据", "云计算",
    "食品", "农食", "生鲜",
    "教育", "培训",
    "物流", "运输",
    "金融", "保险",
]

_QUALIFICATION_KEYWORDS = [
    "专精特新", "高新技术", "国家级", "省级", "AAA",
    "ISO", "科技型中小", "瞪羚", "独角兽",
]

_RADAR_AXES = (
    "信号密度",
    "行业匹配",
    "区域匹配",
    "规模匹配",
    "近期活跃度",
    "资质含金量",
    "技术强度",
    "相似度",
)

# 结构化产品库 (复用 v1 PRODUCT_RULES 名称 · 加 fit_score 元信息)
_PRODUCT_DB: dict[str, dict[str, str]] = {
    "设备贷 / 固定资产贷款": {
        "category": "对公贷款",
        "intro": "针对企业新购置生产设备 / 厂房改扩建的中长期贷款 · 期限 3-5 年 · "
                 "利率 LPR+50~150 bp",
    },
    "流动资金贷款": {
        "category": "对公贷款",
        "intro": "用于日常经营周转 · 一年期 · 满足中标 / 订单交付前的备货资金需求",
    },
    "保理 / 应收质押融资": {
        "category": "供应链金融",
        "intro": "应收账款质押 / 转让 · 解决 B2B 账期占款 · 期限 3-12 月",
    },
    "过桥资金 / 股权质押": {
        "category": "投行融资",
        "intro": "股权融资过渡期资金 · 3-6 月短期 · 配合股权融资节点",
    },
    "普惠经营贷": {
        "category": "对公小微",
        "intro": "无抵押 / 信用 · 50-300 万 · 3 年内 · 小微企业 / 个体工商户",
    },
}


# ============================================================================
# Industry / Geo / Scale 抽取
# ============================================================================

def extract_metadata(
    item: dict,
    tags: list[dict] | None = None,
    llm: Any = None,
) -> dict:
    """从 qcc + signal text 抽 ``industry`` / ``geo`` / ``scale``.

    优先级链:
      1. ``item['qcc']`` 已结构化字段 (Router / 朴素 Tavily 抠字段)
      2. signal 文本关键词命中 (regex)
      3. (可选) LLM 单字段抽取 (llm 参数非空时)
      4. ``tags`` 推断 (用户 query 标签 "行业 / 区域" 兜底 · 标记为推断态)
      5. 兜底 ``NA`` ("未获取")

    返回 ``{"industry": str, "geo": str, "scale": str}`` · 三字段必非空 (NA 兜底)。
    """
    tags = tags or []
    qcc = item.get("qcc") or {}
    signals = item.get("signals") or []
    all_text = " ".join(
        (s.get("signal_title", "") + " " + s.get("signal_detail", ""))
        for s in signals
    )

    # ---------- industry ----------
    industry = (qcc.get("industry") or "").strip()
    if not industry:
        for kw in _INDUSTRY_HINTS:
            if kw in all_text:
                industry = kw
                break
    if not industry and llm is not None:
        industry = _llm_extract_field(llm, item, "industry") or ""
    if not industry:
        # tag 推断兜底 (用户 query 表明的行业 · 标记为推断)
        for t in tags:
            if t.get("category") == "行业" and (t.get("value") or "").strip():
                industry = f"{t['value']} (推断)"
                break
    industry = industry or NA

    # ---------- geo ----------
    geo = ""
    addr = (
        qcc.get("registered_address")
        or qcc.get("registeredAddress")
        or ""
    ).strip()
    if addr:
        for region in _REGION_PATTERNS:
            if region in addr:
                geo = region
                break
        if not geo:
            geo = addr[:8]
    if not geo:
        for region in _REGION_PATTERNS:
            if region in all_text:
                geo = region
                break
    if not geo:
        # 兜底:从 signal_source / source_url 域名找区域线索
        for s in signals:
            src = s.get("signal_source", "")
            for region in _REGION_PATTERNS:
                if region in src:
                    geo = region
                    break
            if geo:
                break
    if not geo and llm is not None:
        geo = _llm_extract_field(llm, item, "geo") or ""
    if not geo:
        for t in tags:
            if t.get("category") == "区域" and (t.get("value") or "").strip():
                geo = f"{t['value']} (推断)"
                break
    geo = geo or NA

    # ---------- scale ----------
    scale = ""
    cap_text = (
        qcc.get("registered_capital")
        or qcc.get("registeredCapital")
        or ""
    ).strip()
    if cap_text:
        m = re.search(r"([\d\.]+)\s*(万|亿)", cap_text)
        if m:
            try:
                val = float(m.group(1))
                unit = m.group(2)
                yuan = val * (1e8 if unit == "亿" else 1e4)
                scale = _scale_from_capital_yuan(yuan)
            except (ValueError, TypeError):
                pass
    if not scale:
        for hint, label in _SCALE_HINTS.items():
            if hint in all_text:
                scale = label
                break
    if not scale:
        m = re.search(r"营收\s*([\d\.]+)\s*(亿|万)", all_text)
        if m:
            try:
                val = float(m.group(1))
                unit = m.group(2)
                yuan = val * (1e8 if unit == "亿" else 1e4)
                scale = _scale_from_revenue_yuan(yuan)
            except (ValueError, TypeError):
                pass
    if not scale:
        # 员工数兜底 (国家统计局粗分)
        emp = item.get("qcc", {}).get("employees") or 0
        if emp:
            try:
                emp_n = int(emp)
                if emp_n < 20:
                    scale = "微型"
                elif emp_n < 300:
                    scale = "小型"
                elif emp_n < 1000:
                    scale = "中型"
                else:
                    scale = "大型"
            except (ValueError, TypeError):
                pass
    if not scale and llm is not None:
        scale = _llm_extract_field(llm, item, "scale") or ""
    if not scale:
        for t in tags:
            if t.get("category") == "规模" and (t.get("value") or "").strip():
                scale = f"{t['value']} (推断)"
                break
    scale = scale or NA

    return {"industry": industry, "geo": geo, "scale": scale}


def _scale_from_capital_yuan(yuan: float) -> str:
    """注册资本 → 规模 (粗估 · 中小企业主流分布)."""
    if yuan < 1e6:           # < 100 万
        return "微型"
    if yuan < 5e7:           # < 5000 万
        return "小型"
    if yuan < 5e8:           # < 5 亿
        return "中型"
    return "大型"


def _scale_from_revenue_yuan(yuan: float) -> str:
    """营收 → 规模 (国家统计局工业小微分类粗化)."""
    if yuan < 3e6:           # < 300 万
        return "微型"
    if yuan < 2e7:           # < 2000 万
        return "小型"
    if yuan < 4e8:           # < 4 亿
        return "中型"
    return "大型"


_LLM_EXTRACT_SYSTEM = (
    "你是企业信息抽取助手。从给定信号文本中抽取 1 个字段值（不超过 12 字），"
    "无法判断时返回空串。只返回值，不要其他文字。"
)


def _llm_extract_field(llm: Any, item: dict, field: str) -> str:
    """LLM 兜底单字段抽取。失败返回空串。"""
    field_label = {
        "industry": "行业",
        "geo": "区域 (省或市)",
        "scale": "规模 (微型/小型/中型/大型 之一)",
    }[field]
    signals = item.get("signals") or []
    sample = "\n".join(
        f"- {s.get('signal_title', '')}: {(s.get('signal_detail', '') or '')[:80]}"
        for s in signals[:5]
    )
    user = (
        f"公司：{item.get('company_name', '')}\n"
        f"信号片段：\n{sample}\n\n"
        f"请抽取 {field_label}，只返回值，无则返回空。"
    )
    try:
        raw = llm.simple_chat(_LLM_EXTRACT_SYSTEM, user, temperature=0.1)
        v = (raw or "").strip().strip('"').strip("'").strip("。").strip("`")
        if 0 < len(v) <= 12:
            return v
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
        return ""
    return ""


# ============================================================================
# Similarity (P0 keyword Jaccard · P3 留 TODO)
# ============================================================================

def compute_similarity(item: dict, query: str, tags: list[dict]) -> float:
    """P0 simple keyword overlap between query/tags and candidate text.

    返回 0~1 float (4 位小数 · ``round`` clamp)。

    P3 TODO (channel-spec.md §C5):
      - 4a 画像相似度 (industry 0.30 / sub_industry 0.15 / region 0.20 /
            scale 0.15 / tags 0.20)
      - 4b 样本锚相似度 (LookAlikeKBMatcher Jaccard 三维 · 已实装于
            ``agent_channel.lookalike_matcher.LookAlikeKBMatcher``)
      - 综合 = 0.6 × profile_score + 0.4 × anchor_score
    """
    query_tokens: set[str] = _tokenize(query)
    for t in tags:
        v = (t.get("value") or "").strip()
        if v:
            query_tokens.add(v)
            query_tokens.update(_tokenize(v))
    query_tokens = {t for t in query_tokens if t and len(t) >= 2}
    if not query_tokens:
        return 0.0

    candidate_text = item.get("company_name", "")
    for s in item.get("signals") or []:
        candidate_text += " " + s.get("signal_title", "")
        candidate_text += " " + s.get("signal_detail", "")
    for tag in item.get("matchTags") or []:
        candidate_text += " " + tag.get("label", "") + " " + tag.get("detail", "")
    candidate_tokens = _tokenize(candidate_text)
    if not candidate_tokens:
        return 0.0

    # substring-Jaccard:候选 token 命中 query token 即 hit (允许子串包含)
    hit = 0
    for q in query_tokens:
        if q in candidate_text:
            hit += 1
            continue
        # 反向:某个 candidate token 包含 query token (短中文词)
        if any(q in c for c in candidate_tokens):
            hit += 1
    sim = hit / max(len(query_tokens), 1)
    return round(min(max(sim, 0.0), 1.0), 4)


def _tokenize(text: str) -> set[str]:
    """简化分词:英文 word + 中文 2/3-gram。"""
    if not text:
        return set()
    tokens: set[str] = set()
    for w in re.findall(r"[A-Za-z]{2,}", text):
        tokens.add(w.lower())
    cn = re.sub(r"[^一-龥]", "", text)
    for n in (2, 3, 4):
        for i in range(len(cn) - n + 1):
            tokens.add(cn[i:i + n])
    return tokens


# ============================================================================
# 8 维 Radar
# ============================================================================

def build_radar_8axis(
    item: dict,
    similarity: float,
    metadata: dict,
    tags: list[dict],
) -> dict:
    """8 维 0-100 评分 · key 即 axis 名 (中文)。"""
    signals = item.get("signals") or []
    types = {s.get("signal_type") for s in signals if s.get("signal_type")}

    # 信号密度: 5 type 满分
    density = min(100, len(types) * 20)

    # 行业 / 区域 / 规模 匹配:tags 命中 → 高分
    target_industry = next(
        (t.get("value", "") for t in tags if t.get("category") == "行业"), "",
    )
    target_region = next(
        (t.get("value", "") for t in tags if t.get("category") == "区域"), "",
    )

    industry_match = (
        80 if target_industry and target_industry in metadata.get("industry", "")
        else (50 if metadata.get("industry") and metadata.get("industry") != NA else 30)
    )
    region_match = (
        80 if target_region and target_region in metadata.get("geo", "")
        else (50 if metadata.get("geo") and metadata.get("geo") != NA else 30)
    )
    scale_label = metadata.get("scale", "")
    scale_match = 70 if scale_label and scale_label != NA else 40

    # 近期活跃度 (60 天内信号数)
    cutoff = datetime.now() - timedelta(days=60)
    recent_count = 0
    for s in signals:
        d = (s.get("signal_date") or "")[:10]
        if not d or len(d) < 10:
            continue
        try:
            if datetime.strptime(d, "%Y-%m-%d") >= cutoff:
                recent_count += 1
        except (ValueError, TypeError):
            pass
    activity = min(100, recent_count * 25)

    # 资质含金量
    all_text = " ".join(
        (s.get("signal_title", "") + " " + s.get("signal_detail", ""))
        for s in signals
    )
    qual_hits = sum(1 for k in _QUALIFICATION_KEYWORDS if k in all_text)
    quality = min(100, qual_hits * 30)

    # 技术强度
    tech_score = 75 if "tech" in types else (50 if "growth" in types else 30)

    # 相似度 0-1 → 0-100
    sim_score = int(round(similarity * 100))

    return {
        "信号密度": density,
        "行业匹配": industry_match,
        "区域匹配": region_match,
        "规模匹配": scale_match,
        "近期活跃度": activity,
        "资质含金量": quality,
        "技术强度": tech_score,
        "相似度": sim_score,
    }


# ============================================================================
# Match Dimensions (PRD v2 "为什么像")
# ============================================================================

def build_match_dimensions(
    item: dict,
    tags: list[dict],
    metadata: dict,
) -> list[dict]:
    """转换 matchTags + tags + metadata → PRD 标准 ``[{dim_name, hit_evidence, score}]``."""
    out: list[dict] = []

    # 行业
    target_ind = next(
        (t.get("value", "") for t in tags if t.get("category") == "行业"), "",
    )
    if target_ind:
        cand_ind = metadata.get("industry", "") or ""
        all_text = " ".join(
            s.get("signal_title", "") for s in item.get("signals") or []
        )
        hit = (target_ind in cand_ind) or (target_ind in all_text)
        out.append({
            "dim_name": "行业匹配",
            "hit_evidence": (
                f"目标「{target_ind}」· 候选「{cand_ind or NA}」"
                + (" · 信号文本命中" if not (target_ind in cand_ind) and hit else "")
            ),
            "score": 90 if hit else 40,
        })

    # 区域
    target_reg = next(
        (t.get("value", "") for t in tags if t.get("category") == "区域"), "",
    )
    if target_reg:
        cand_geo = metadata.get("geo", "") or ""
        hit = target_reg in cand_geo
        out.append({
            "dim_name": "区域匹配",
            "hit_evidence": f"目标「{target_reg}」· 候选地域「{cand_geo or NA}」",
            "score": 90 if hit else 40,
        })

    # 规模
    scale = metadata.get("scale", "")
    if scale and scale != NA:
        out.append({
            "dim_name": "规模匹配",
            "hit_evidence": f"候选规模「{scale}」",
            "score": 75,
        })

    # 信号丰富度
    signals = item.get("signals") or []
    types = sorted({s.get("signal_type") for s in signals if s.get("signal_type")})
    if signals:
        out.append({
            "dim_name": "信号丰富度",
            "hit_evidence": (
                f"{len(types)} 类信号 · 共 {len(signals)} 条 ({', '.join(types)})"
            ),
            "score": min(100, len(types) * 20 + len(signals) * 3),
        })

    # 现有 matchTags 转换 (近期扩产 / 专精特新 / 中标 / 技术突破 等)
    existing = {m["dim_name"] for m in out}
    for tag in item.get("matchTags") or []:
        label = (tag.get("label") or "").strip()
        detail = (tag.get("detail") or "").strip()
        if not label or label in existing:
            continue
        out.append({
            "dim_name": label,
            "hit_evidence": detail or label,
            "score": 80 if tag.get("matched") else 50,
        })
        existing.add(label)

    return out


# ============================================================================
# Product Recommendations Top3 (structured)
# ============================================================================

def build_product_recommendations(
    item: dict,
    similarity: float = 0.5,
) -> list[dict]:
    """Top3 product · structured ``[{product_name, fit_score, intro, category}]``.

    fit_score 由 (基础名次档 90/75/60) × (0.7 + 0.3 × similarity) 调整。
    现有 ``recommendedProducts`` (str list) 不足 3 个时按 PRODUCT_DB 默认补齐。
    """
    raw_products: list[str] = list(item.get("recommendedProducts") or [])
    out: list[dict] = []
    seen: set[str] = set()

    for i, name in enumerate(raw_products[:3]):
        meta = _PRODUCT_DB.get(name) or {
            "category": "对公融资",
            "intro": f"『{name}』产品详情待补全 · RM 可联系产品经理确认额度 / 期限 / 利率",
        }
        base = [90, 75, 60][i]
        adjusted = int(round(base * (0.7 + 0.3 * similarity)))
        out.append({
            "product_name": name,
            "fit_score": min(100, max(40, adjusted)),
            "intro": meta["intro"],
            "category": meta["category"],
        })
        seen.add(name)

    # 不足 3 个 fallback 补到 3
    fallback_chain = [
        "流动资金贷款", "普惠经营贷", "保理 / 应收质押融资",
        "设备贷 / 固定资产贷款",
    ]
    idx = 0
    while len(out) < 3 and idx < len(fallback_chain):
        cand = fallback_chain[idx]
        idx += 1
        if cand in seen:
            continue
        meta = _PRODUCT_DB[cand]
        out.append({
            "product_name": cand,
            "fit_score": 50,
            "intro": meta["intro"],
            "category": meta["category"],
        })
        seen.add(cand)

    return out


# ============================================================================
# Pitch Scripts (placeholder)
# ============================================================================

def build_pitch_scripts(item: dict) -> list[dict]:
    """转换 pitch (str) → ``[{customer_name_placeholder, script_text, source}]``.

    候选名替换为占位符 ``{客户名}`` · 客户经理可批量复用为不同企业 (同行业话术)。
    pitch 为空时返回空列表 (前端按 ``len === 0`` 渲染骨架/未生成态)。
    """
    pitch = (item.get("pitch") or "").strip()
    if not pitch:
        return []

    company = item.get("company_name", "") or ""
    templated = pitch
    if company and company in pitch:
        templated = pitch.replace(company, CUSTOMER_NAME_PLACEHOLDER)

    return [{
        "customer_name_placeholder": CUSTOMER_NAME_PLACEHOLDER,
        "script_text": templated,
        "source": "agent6",
    }]


# ============================================================================
# Entry: 一次性 enrich 单个 candidate item
# ============================================================================

def enrich_candidate(
    item: dict,
    query: str,
    tags: list[dict],
    llm: Any = None,
) -> dict:
    """主入口 · 在 ``_build_final_output`` 内每候选调一次。

    返回 dict 含 B.5 全部新字段 + Q-054 第 5 维度 signal_density:
      ``industry / geo / scale / similarity`` (Q-041 4 字段)
      ``signal_density / signal_density_reason``  (Q-054 第 5 维度 · 0-1 + 降级原因)
      ``radar_8axis / match_dimensions / product_recommendations / pitch_scripts``

    上层 merge 进 candidate 即可 (新字段全为 snake_case · 不与现有 camelCase 撞键)。
    """
    from agent_channel.signal_density import compute_signal_density

    metadata = extract_metadata(item, tags=tags, llm=llm)
    similarity = compute_similarity(item, query, tags)
    radar_8axis = build_radar_8axis(item, similarity, metadata, tags)
    match_dimensions = build_match_dimensions(item, tags, metadata)
    product_recommendations = build_product_recommendations(item, similarity=similarity)
    pitch_scripts = build_pitch_scripts(item)

    # Q-054 B1 · 第 5 维度 signal_density · LLM 走 shared.llm_caller (PIPL fallback chain)
    # 仅 legacy llm 参数非空时启 LLM salience · 否则静态 prior fallback
    sd_caller: Any = None
    if llm is not None:
        try:
            from shared.llm_caller import LLMCaller
            sd_caller = LLMCaller(
                agent_id="channel",
                endpoint="signal_salience",
            )
        except ImportError:
            sd_caller = None
    sd_result = compute_signal_density(item, llm=sd_caller)

    return {
        "industry": metadata["industry"],
        "geo": metadata["geo"],
        "scale": metadata["scale"],
        "similarity": similarity,
        # Q-054 5 字段共生 (per Q-041 banner-spec · 5 字段第 5 字段 signal_density)
        "signal_density": sd_result["signal_density"],
        "signal_density_reason": sd_result["signal_density_reason"],
        "radar_8axis": radar_8axis,
        "match_dimensions": match_dimensions,
        "product_recommendations": product_recommendations,
        "pitch_scripts": pitch_scripts,
    }


__all__ = [
    "NA",
    "CUSTOMER_NAME_PLACEHOLDER",
    "extract_metadata",
    "compute_similarity",
    "build_radar_8axis",
    "build_match_dimensions",
    "build_product_recommendations",
    "build_pitch_scripts",
    "enrich_candidate",
]
