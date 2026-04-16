# -*- coding: utf-8 -*-
"""Agent1 全渠道流量匹配 — 评分模型"""

from __future__ import annotations
from pydantic import BaseModel, Field


class ChannelRecommendation(BaseModel):
    """单个渠道推荐结果"""
    channel_name: str = Field(description="渠道名称")
    category: str = Field(description="渠道类别")
    score: int = Field(description="匹配得分(0-100)")
    max_amount: str = Field(default="", description="最高额度")
    reason: str = Field(default="", description="推荐理由")
    match_reasons: list[str] = Field(default_factory=list, description="规则匹配原因")


# 权重配置
WEIGHTS = {
    "industry": 0.30,   # 行业匹配 30%
    "scale": 0.25,      # 规模匹配 25%
    "region": 0.20,     # 地域匹配 20%
    "policy": 0.15,     # 政策匹配 15%
    "history": 0.10,    # 历史匹配 10%
}

# 重点扶持行业（政策加分）
POLICY_BOOST_INDUSTRIES = [
    "新能源", "半导体", "人工智能", "生物医药", "新材料",
    "高端装备", "信息技术", "节能环保", "数字经济", "现代农业",
]

# 重点扶持地区（地域加分）
POLICY_BOOST_REGIONS = [
    "长三角", "珠三角", "成渝", "京津冀",
    "上海", "深圳", "北京", "杭州", "苏州", "合肥", "成都", "武汉",
    "自贸区", "高新区", "经开区", "新区",
]


def calculate_match_score(company_info: dict, channel: dict) -> int:
    """
    计算企业与渠道的匹配得分（0-100）。

    加权维度：
    - 行业匹配 30%
    - 规模匹配 25%
    - 地域匹配 20%
    - 政策匹配 15%
    - 历史匹配 10%

    参数:
        company_info: 企业信息字典
        channel: 匹配渠道信息（来自 match_channels 的结果）

    返回:
        0-100 的整数分数
    """
    scores = {}

    # 1. 行业得分：基于匹配维度数
    dimensions = channel.get("dimensions_met", 0)
    scores["industry"] = min(100, dimensions * 40)

    # 2. 规模得分：有规模信息且匹配
    scale = company_info.get("scale", "")
    if scale:
        match_reasons = " ".join(channel.get("match_reasons", []))
        if "规模" in match_reasons:
            scores["scale"] = 90
        else:
            scores["scale"] = 50  # 有规模信息但非强匹配
    else:
        scores["scale"] = 30  # 无规模信息，给基础分

    # 3. 地域得分
    region = company_info.get("region", "")
    scores["region"] = 40  # 基础分
    if region:
        for boost_region in POLICY_BOOST_REGIONS:
            if boost_region in region:
                scores["region"] = 85
                break
        else:
            scores["region"] = 60  # 有地域信息但非重点区域

    # 4. 政策得分
    industry = company_info.get("industry", "")
    keywords = company_info.get("keywords", "")
    all_text = f"{industry} {keywords}"
    scores["policy"] = 30  # 基础分
    for boost_ind in POLICY_BOOST_INDUSTRIES:
        if boost_ind in all_text:
            scores["policy"] = 90
            break

    # 5. 历史得分（目前无历史数据，给中等基础分）
    scores["history"] = 50

    # 加权计算总分
    total = 0.0
    for key, weight in WEIGHTS.items():
        total += scores.get(key, 0) * weight

    return min(100, max(0, int(round(total))))


def rank_recommendations(company_info: dict,
                         matched_channels: list[dict]) -> list[ChannelRecommendation]:
    """
    对匹配到的渠道进行评分排序，返回推荐列表。

    参数:
        company_info: 企业信息
        matched_channels: match_channels() 的返回结果

    返回:
        按得分降序排列的 ChannelRecommendation 列表
    """
    recommendations = []
    for ch in matched_channels:
        score = calculate_match_score(company_info, ch)
        rec = ChannelRecommendation(
            channel_name=ch["channel_name"],
            category=ch["category"],
            score=score,
            max_amount=ch.get("max_amount", ""),
            match_reasons=ch.get("match_reasons", []),
        )
        recommendations.append(rec)

    # 按得分降序排序
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations
