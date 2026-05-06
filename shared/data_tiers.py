"""数据源 Tier 化分层 · 杜绝 Agent1 "10 年前新闻当推荐核心理由" 类问题

per Phase C charter Track D · D1 数据源 Tier 化分层 (PM 拍板 2026-05-06):

设计:
- Tier 1 内部权威 (银行内部系统 · 100% trust): CRM / 流水 / 征信报告 / 内部 KYC
- Tier 2 政府/监管 (高 trust + 时效 < 30d): 银保监 / 央行 / 税务 / 工商 / 法院 / 招投标
- Tier 3 行业数据 (中 trust): 行业研报 / 上市公告 / 评级机构
- Tier 4 公开 web (低 trust · 必标时间戳): Tavily / Google / Bing / 新闻聚合

硬线 (per CLAUDE.md §3.1 + Phase C charter):
- 推荐核心理由 (recommendation 主原因) 禁用 Tier 4 单一来源
- 必交叉 Tier 2-3 至少 1 条来源
- Tier 4 仅作"上下文背景" · 不作"核心 claim"
- 校验失败 = QC blocker 阻断输出

使用:
    from shared.data_tiers import DataTier, classify_source, validate_recommendation_sources

    # 分类
    tier = classify_source("https://www.cbirc.gov.cn/xxx")  # → DataTier.GOVERNMENT
    tier = classify_source("https://news.sohu.com/xxx")  # → DataTier.PUBLIC_WEB

    # 推荐校验
    sources = [
        {"url": "https://www.cbirc.gov.cn/...", "tier": "government"},
        {"url": "https://news.sohu.com/...", "tier": "public_web"},
    ]
    result = validate_recommendation_sources(sources)
    # → {"valid": True, "core_tiers": [...], "warnings": []}
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Iterable
from urllib.parse import urlparse


class DataTier(str, Enum):
    """数据源 4 Tier 分级."""

    INTERNAL_AUTHORITATIVE = "internal_authoritative"  # Tier 1 · 银行内部
    GOVERNMENT = "government"  # Tier 2 · 政府/监管
    INDUSTRY = "industry"  # Tier 3 · 行业数据
    PUBLIC_WEB = "public_web"  # Tier 4 · 公开 web
    UNKNOWN = "unknown"  # 未识别 · 默认按 Tier 4 处理


# Tier 评分 (越高越权威)
TIER_SCORE: dict[DataTier, int] = {
    DataTier.INTERNAL_AUTHORITATIVE: 100,
    DataTier.GOVERNMENT: 80,
    DataTier.INDUSTRY: 60,
    DataTier.PUBLIC_WEB: 30,
    DataTier.UNKNOWN: 10,
}


# 域名 → Tier 映射 (extensible · 客户走访后按银行实际数据源补充)
DOMAIN_TIER_MAP: dict[str, DataTier] = {
    # === Tier 2 · 政府/监管 ===
    "cbirc.gov.cn": DataTier.GOVERNMENT,  # 银保监
    "csrc.gov.cn": DataTier.GOVERNMENT,  # 证监会
    "pbc.gov.cn": DataTier.GOVERNMENT,  # 央行
    "stats.gov.cn": DataTier.GOVERNMENT,  # 国统局
    "tax.gov.cn": DataTier.GOVERNMENT,  # 税务
    "samr.gov.cn": DataTier.GOVERNMENT,  # 工商市场监管
    "court.gov.cn": DataTier.GOVERNMENT,  # 最高法
    "wenshu.court.gov.cn": DataTier.GOVERNMENT,  # 裁判文书
    "ggzy.gov.cn": DataTier.GOVERNMENT,  # 公共资源交易/招投标
    "credit.gov.cn": DataTier.GOVERNMENT,  # 信用中国
    "creditchina.gov.cn": DataTier.GOVERNMENT,
    "amac.org.cn": DataTier.GOVERNMENT,  # 中基协
    "sac.net.cn": DataTier.GOVERNMENT,  # 中证协
    # === Tier 3 · 行业数据 ===
    "sse.com.cn": DataTier.INDUSTRY,  # 上交所
    "szse.cn": DataTier.INDUSTRY,  # 深交所
    "neeq.com.cn": DataTier.INDUSTRY,  # 全国股转
    "cninfo.com.cn": DataTier.INDUSTRY,  # 巨潮资讯
    "eastmoney.com": DataTier.INDUSTRY,  # 东方财富
    "wind.com.cn": DataTier.INDUSTRY,  # Wind
    "qichacha.com": DataTier.INDUSTRY,  # 企查查
    "tianyancha.com": DataTier.INDUSTRY,  # 天眼查
    "qcc.com": DataTier.INDUSTRY,  # 企查查
    # === Tier 4 · 公开 web ===
    "sina.com.cn": DataTier.PUBLIC_WEB,
    "sohu.com": DataTier.PUBLIC_WEB,
    "163.com": DataTier.PUBLIC_WEB,
    "qq.com": DataTier.PUBLIC_WEB,
    "baidu.com": DataTier.PUBLIC_WEB,
    "google.com": DataTier.PUBLIC_WEB,
    "bing.com": DataTier.PUBLIC_WEB,
    "tavily.com": DataTier.PUBLIC_WEB,
    "weibo.com": DataTier.PUBLIC_WEB,
    "zhihu.com": DataTier.PUBLIC_WEB,
}


def classify_source(url_or_source: str) -> DataTier:
    """根据 URL 或源标识 分类 Tier.

    Args:
        url_or_source: URL 或显式 tier 标识 ('internal://' / 'government://' 等)

    Returns:
        DataTier 枚举值
    """
    if not url_or_source:
        return DataTier.UNKNOWN

    s = url_or_source.strip().lower()

    # 显式 tier 标识 (内部 source 用)
    if s.startswith("internal://"):
        return DataTier.INTERNAL_AUTHORITATIVE
    if s.startswith("government://"):
        return DataTier.GOVERNMENT
    if s.startswith("industry://"):
        return DataTier.INDUSTRY
    if s.startswith("publicweb://"):
        return DataTier.PUBLIC_WEB

    # URL 解析
    try:
        parsed = urlparse(s if s.startswith("http") else f"https://{s}")
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]  # 去 port
        # 优先精确匹配
        if host in DOMAIN_TIER_MAP:
            return DOMAIN_TIER_MAP[host]
        # 尾后缀匹配 (子域 e.g. www.cbirc.gov.cn)
        for domain, tier in DOMAIN_TIER_MAP.items():
            if host.endswith("." + domain) or host == domain:
                return tier
        # .gov.cn 默认 Tier 2
        if ".gov.cn" in host:
            return DataTier.GOVERNMENT
        return DataTier.PUBLIC_WEB
    except Exception:
        return DataTier.UNKNOWN


def validate_recommendation_sources(
    sources: Iterable[dict[str, Any]],
    *,
    require_tier_2_or_3_minimum: int = 1,
    forbid_pure_tier_4: bool = True,
) -> dict[str, Any]:
    """校验推荐核心理由的来源 · 杜绝"10 年前新闻当核心理由"类问题.

    硬线:
    - 至少 1 条来源属 Tier 1/2/3 (默认)
    - 不允许全 Tier 4 (默认)

    Args:
        sources: 推荐使用的来源列表 · 每条含 'url' 或 'tier' 或 '(url + tier)'
        require_tier_2_or_3_minimum: 最少几条 Tier 2 或更高 (默认 1)
        forbid_pure_tier_4: 是否禁全 Tier 4 单一来源 (默认 True)

    Returns:
        {
            'valid': bool,
            'tier_distribution': {tier_name: count},
            'warnings': [str],
            'block_reason': str | None,
        }
    """
    distribution: dict[str, int] = {t.value: 0 for t in DataTier}
    warnings: list[str] = []

    for source in sources:
        url = source.get("url", "")
        tier_explicit = source.get("tier")
        if tier_explicit:
            try:
                tier = DataTier(tier_explicit)
            except ValueError:
                tier = classify_source(url)
        else:
            tier = classify_source(url)
        distribution[tier.value] += 1

    total = sum(distribution.values())
    high_trust = (
        distribution[DataTier.INTERNAL_AUTHORITATIVE.value]
        + distribution[DataTier.GOVERNMENT.value]
        + distribution[DataTier.INDUSTRY.value]
    )

    block_reason: str | None = None

    if total == 0:
        block_reason = "无 source · 推荐不可信"
    elif high_trust < require_tier_2_or_3_minimum:
        block_reason = (
            f"核心理由缺 Tier 1/2/3 来源 (要求 ≥ {require_tier_2_or_3_minimum} · "
            f"实际 {high_trust} · 仅 Tier 4 公开 web 不能作核心 claim)"
        )
    elif forbid_pure_tier_4 and high_trust == 0 and distribution[DataTier.PUBLIC_WEB.value] > 0:
        block_reason = "核心理由全 Tier 4 公开 web · 不允许"

    if (
        distribution[DataTier.PUBLIC_WEB.value] > 0
        and distribution[DataTier.PUBLIC_WEB.value] >= total / 2
    ):
        warnings.append(
            f"Tier 4 公开 web 占比 {distribution[DataTier.PUBLIC_WEB.value]}/{total} "
            "·建议增加 Tier 2/3 来源"
        )

    if distribution[DataTier.UNKNOWN.value] > 0:
        warnings.append(
            f"{distribution[DataTier.UNKNOWN.value]} 条来源未识别 · 默认按 Tier 4 处理 · "
            "建议手动标注 tier"
        )

    return {
        "valid": block_reason is None,
        "tier_distribution": distribution,
        "high_trust_count": high_trust,
        "warnings": warnings,
        "block_reason": block_reason,
    }


def compute_source_trust_score(sources: Iterable[dict[str, Any]]) -> float:
    """综合来源信任分 · 加权 mean (0-100)."""
    items = list(sources)
    if not items:
        return 0.0
    total = 0.0
    for source in items:
        url = source.get("url", "")
        tier_explicit = source.get("tier")
        if tier_explicit:
            try:
                tier = DataTier(tier_explicit)
            except ValueError:
                tier = classify_source(url)
        else:
            tier = classify_source(url)
        total += TIER_SCORE[tier]
    return round(total / len(items), 2)


__all__ = [
    "DataTier",
    "TIER_SCORE",
    "DOMAIN_TIER_MAP",
    "classify_source",
    "validate_recommendation_sources",
    "compute_source_trust_score",
]
