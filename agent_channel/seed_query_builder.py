# -*- coding: utf-8 -*-
"""Seed query builder — 从 data/mock/channel-kb/marketing-preferences/*.docx
确定性地抽取「拓展方向 + 行业 + 区域 + 营收区间 + 资质偏好」并组装 Tavily 查询串。

设计约束 (Batch 2 · §3.5 环境边界):
    - 不走 LLM;走 python-docx + 轻量正则/关键词识别
    - 不硬编"贷款 审贷 企业"这类空 query 兜底(onboarding red line)
    - 每条 SeedBundle 携带 source_doc 便于证据链回指

调用方式:
    bundles = parse_marketing_preferences("data/mock/channel-kb/marketing-preferences")
    queries = build_queries(bundles, max_total=6)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


# 匹配 "2.1 先进制造业" / "2.2 专精特新业" 等小节标题中的行业关键词
# 长度约束 2-8 字避免 greedy 抓到整句 "哪些公司是温度标准重点客户"
_SECTION_INDUSTRY_RE = re.compile(
    r"^\s*\d+(?:\.\d+)?\s*[、.．]?\s*([一-鿿]{2,8}(?:业|型企业|领域))(?=[\s　、,，。:：])",
    re.M,
)

# 匹配 "营收范围：5000 万 – 3 亿元" / "营业额 300 万以上" 等
_REVENUE_RE = re.compile(
    r"(?:营收|营业(?:额|收入)|年收入)[^0-9]{0,6}"
    r"(\d+(?:\.\d+)?)\s*(万|亿)?"
    r"\s*[~\-–至到]\s*"
    r"(\d+(?:\.\d+)?)\s*(万|亿)?"
)

# 匹配资质关键短语
_QUAL_PATTERNS = [
    r"专精特新",
    r"高新技术(?:企业)?",
    r"科技型中小企业",
    r"专利[0-9 ]*项",
    r"省级[一-鿿]*资[质格]",
    r"国家级[一-鿿]*资[质格]",
    r"ISO\s*\d{4,5}",
    r"AAA\s*信用",
]

# 区域提取:常见省/直辖市/经济区
_REGION_TOKENS = [
    "长三角", "珠三角", "京津冀", "成渝", "粤港澳",
    "北京", "上海", "广州", "深圳", "杭州", "苏州", "南京", "宁波", "无锡",
    "成都", "重庆", "武汉", "合肥", "西安", "青岛", "天津",
    "江苏", "浙江", "广东", "山东", "四川", "安徽", "福建", "湖北", "湖南", "河南",
]


@dataclass
class SeedBundle:
    """一份 marketing-preferences 文档解析出的检索种子。"""
    source_doc: str
    industries: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    revenue_range_wan: tuple[float, float] | None = None   # 单位:万元
    qualifications: list[str] = field(default_factory=list)
    raw_excerpts: list[str] = field(default_factory=list)


def _wan(value: float, unit: str | None) -> float:
    if unit == "亿":
        return value * 10000.0
    return value


def _read_docx_paragraphs(path: str | Path) -> list[str]:
    try:
        import docx
    except ImportError:
        return []
    try:
        doc = docx.Document(str(path))
    except (OSError, ValueError, KeyError):
        return []
    return [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]


def _extract_industries(text: str) -> list[str]:
    found: list[str] = []
    for m in _SECTION_INDUSTRY_RE.finditer(text):
        token = m.group(1).strip()
        if token and token not in found:
            found.append(token)
    # 额外从散落关键词补
    extras = re.findall(r"[一-鿿]{2,4}(?:制造|行业|业)", text)
    for e in extras[:6]:
        if e not in found and len(e) <= 8:
            found.append(e)
    return found[:8]


def _extract_revenue_range(text: str) -> tuple[float, float] | None:
    m = _REVENUE_RE.search(text)
    if not m:
        return None
    lo = _wan(float(m.group(1)), m.group(2))
    hi = _wan(float(m.group(3)), m.group(4))
    if lo > hi:
        lo, hi = hi, lo
    return (lo, hi)


def _extract_qualifications(text: str) -> list[str]:
    found: list[str] = []
    for pat in _QUAL_PATTERNS:
        for m in re.finditer(pat, text):
            token = m.group(0).strip()
            if token and token not in found:
                found.append(token)
    return found[:8]


def _extract_regions(text: str) -> list[str]:
    found: list[str] = []
    for tok in _REGION_TOKENS:
        if tok in text and tok not in found:
            found.append(tok)
        if len(found) >= 6:
            break
    return found


def parse_marketing_preferences(kb_dir: str | Path) -> list[SeedBundle]:
    """遍历目录下所有 .docx 并抽取 SeedBundle(不走 LLM)。

    空目录 / 零 docx 时返回空 list,调用方应自行决定降级路径。
    """
    base = Path(kb_dir)
    if not base.is_dir():
        return []
    bundles: list[SeedBundle] = []
    for fname in sorted(os.listdir(base)):
        if not fname.lower().endswith(".docx"):
            continue
        # 避开 "避开清单" 类反向文档(onboarding 没要求作为 seed 源)
        if "避开" in fname or "exclude" in fname.lower():
            continue
        fpath = base / fname
        paragraphs = _read_docx_paragraphs(fpath)
        if not paragraphs:
            continue
        full = "\n".join(paragraphs)
        bundle = SeedBundle(
            source_doc=str(fpath),
            industries=_extract_industries(full),
            regions=_extract_regions(full),
            revenue_range_wan=_extract_revenue_range(full),
            qualifications=_extract_qualifications(full),
            raw_excerpts=paragraphs[:12],
        )
        # 空壳 bundle 不入队(避免生成 "贷款 审贷 企业" 类空 query)
        if bundle.industries or bundle.regions or bundle.qualifications:
            bundles.append(bundle)
    return bundles


def build_queries(
    bundles: list[SeedBundle],
    max_total: int = 6,
    max_per_bundle: int = 3,
) -> list[str]:
    """把若干 SeedBundle 组合成 region × industry × qualification 查询串。

    只在 bundle 真含内容时拼;全空 bundle 一律跳过(red line:禁止空 query 兜底)。
    """
    queries: list[str] = []
    for bundle in bundles:
        if not (bundle.industries or bundle.regions or bundle.qualifications):
            continue
        bundle_q = 0
        regions = bundle.regions or [""]
        industries = bundle.industries or [""]
        quals = bundle.qualifications or [""]
        for region in regions[:3]:
            for industry in industries[:3]:
                qual = quals[0] if quals else ""
                parts = [p for p in (region, industry, qual, "企业") if p]
                q = " ".join(parts).strip()
                q = re.sub(r"\s+", " ", q)
                if q and q not in queries:
                    queries.append(q)
                    bundle_q += 1
                if bundle_q >= max_per_bundle or len(queries) >= max_total:
                    break
            if bundle_q >= max_per_bundle or len(queries) >= max_total:
                break
        if len(queries) >= max_total:
            break
    return queries


def build_queries_for_profile(
    target_industries: list[str],
    target_regions: list[str],
    qualifications: list[str] | None = None,
    max_total: int = 5,
) -> list[str]:
    """显式画像 → 查询串(供 lookalike correctness 测试等不经 docx 的路径使用)。"""
    quals = qualifications or []
    queries: list[str] = []
    for region in (target_regions or [""])[:3]:
        for industry in (target_industries or [""])[:3]:
            qual = quals[0] if quals else ""
            parts = [p for p in (region, industry, qual, "企业") if p]
            q = " ".join(parts).strip()
            q = re.sub(r"\s+", " ", q)
            if q and q not in queries:
                queries.append(q)
            if len(queries) >= max_total:
                break
        if len(queries) >= max_total:
            break
    return queries
