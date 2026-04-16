# -*- coding: utf-8 -*-
"""Agent1 全渠道流量匹配 — 渠道规则库与匹配引擎"""

from __future__ import annotations

# 5大渠道类别，每类包含子渠道和适用条件
CHANNEL_CATALOG = {
    "普惠金融": {
        "description": "面向小微企业和个体工商户的融资服务",
        "sub_channels": [
            {
                "name": "小微企业信用贷",
                "conditions": {
                    "scale": ["小型", "微型"],
                    "industries": [],  # 不限行业
                    "keywords": ["小微", "个体", "创业", "经营周转"],
                    "max_amount": "1000万",
                },
            },
            {
                "name": "个体工商户经营贷",
                "conditions": {
                    "scale": ["微型"],
                    "industries": ["零售", "餐饮", "服务业", "批发"],
                    "keywords": ["个体户", "门店", "经营"],
                    "max_amount": "300万",
                },
            },
            {
                "name": "乡村振兴贷",
                "conditions": {
                    "scale": ["小型", "微型"],
                    "industries": ["农业", "畜牧业", "林业", "渔业", "农产品加工"],
                    "keywords": ["乡村", "农业", "种植", "养殖", "农产品"],
                    "max_amount": "500万",
                },
            },
        ],
    },
    "科技金融": {
        "description": "支持科技创新和高新技术企业的融资服务",
        "sub_channels": [
            {
                "name": "高新技术企业贷",
                "conditions": {
                    "scale": ["小型", "中型", "大型"],
                    "industries": ["信息技术", "电子", "生物医药", "新材料", "人工智能", "半导体", "软件"],
                    "keywords": ["高新", "科技", "研发", "专利", "技术创新"],
                    "max_amount": "3000万",
                },
            },
            {
                "name": "专精特新企业贷",
                "conditions": {
                    "scale": ["小型", "中型"],
                    "industries": [],
                    "keywords": ["专精特新", "小巨人", "隐形冠军", "细分领域"],
                    "max_amount": "2000万",
                },
            },
            {
                "name": "知识产权质押贷",
                "conditions": {
                    "scale": ["小型", "中型"],
                    "industries": ["信息技术", "生物医药", "新材料", "软件"],
                    "keywords": ["专利", "知识产权", "商标", "著作权"],
                    "max_amount": "1000万",
                },
            },
        ],
    },
    "绿色金融": {
        "description": "支持绿色低碳发展和环保产业的融资服务",
        "sub_channels": [
            {
                "name": "绿色信贷",
                "conditions": {
                    "scale": ["小型", "中型", "大型"],
                    "industries": ["环保", "新能源", "节能", "清洁能源", "水处理", "固废处理"],
                    "keywords": ["绿色", "环保", "低碳", "节能减排", "碳中和"],
                    "max_amount": "5000万",
                },
            },
            {
                "name": "碳减排贷款",
                "conditions": {
                    "scale": ["中型", "大型"],
                    "industries": ["新能源", "电力", "钢铁", "化工", "建材"],
                    "keywords": ["碳减排", "碳交易", "碳中和", "清洁能源", "光伏", "风电"],
                    "max_amount": "1亿",
                },
            },
        ],
    },
    "供应链金融": {
        "description": "基于供应链上下游关系的融资服务",
        "sub_channels": [
            {
                "name": "应收账款融资",
                "conditions": {
                    "scale": ["小型", "中型"],
                    "industries": ["制造业", "批发", "贸易", "建筑"],
                    "keywords": ["应收账款", "供应商", "赊销", "账期"],
                    "max_amount": "3000万",
                },
            },
            {
                "name": "订单融资",
                "conditions": {
                    "scale": ["小型", "中型"],
                    "industries": ["制造业", "外贸", "电子", "服装"],
                    "keywords": ["订单", "合同", "采购", "出口"],
                    "max_amount": "2000万",
                },
            },
            {
                "name": "仓单质押贷",
                "conditions": {
                    "scale": ["小型", "中型", "大型"],
                    "industries": ["大宗商品", "粮食", "钢铁", "有色金属", "化工"],
                    "keywords": ["仓单", "存货", "库存", "大宗商品"],
                    "max_amount": "5000万",
                },
            },
        ],
    },
    "产业园区": {
        "description": "针对产业园区入驻企业的批量获客渠道",
        "sub_channels": [
            {
                "name": "园区批量授信",
                "conditions": {
                    "scale": ["小型", "中型"],
                    "industries": [],
                    "keywords": ["园区", "产业园", "孵化器", "加速器", "科技园"],
                    "max_amount": "1000万",
                },
            },
            {
                "name": "开发区重点企业贷",
                "conditions": {
                    "scale": ["中型", "大型"],
                    "industries": ["制造业", "信息技术", "新材料", "生物医药"],
                    "keywords": ["开发区", "经济技术开发区", "高新区", "自贸区"],
                    "max_amount": "5000万",
                },
            },
        ],
    },
}


def match_channels(company_info: dict) -> list[dict]:
    """
    遍历渠道规则，匹配适合企业的渠道列表。

    参数:
        company_info: 企业信息字典，包含 industry, region, scale, keywords 等

    返回:
        匹配的渠道列表，每项包含 category, channel, match_reasons
    """
    industry = company_info.get("industry", "").strip()
    scale = company_info.get("scale", "").strip()
    keywords_str = company_info.get("keywords", "")
    company_name = company_info.get("company_name", "")

    # 合并所有文本用于关键词匹配
    all_text = f"{industry} {keywords_str} {company_name} {company_info.get('region', '')}"
    all_text = all_text.lower()

    matched = []

    for category_name, category_data in CHANNEL_CATALOG.items():
        for sub in category_data["sub_channels"]:
            reasons = []
            cond = sub["conditions"]

            # 规模匹配
            scale_match = False
            if not cond["scale"]:
                scale_match = True
            elif scale and scale in cond["scale"]:
                scale_match = True
                reasons.append(f"企业规模({scale})符合要求")

            # 行业匹配
            industry_match = False
            if not cond["industries"]:
                industry_match = True
            else:
                for ind in cond["industries"]:
                    if ind in industry or ind.lower() in all_text:
                        industry_match = True
                        reasons.append(f"行业({industry})匹配")
                        break

            # 关键词匹配
            keyword_match = False
            matched_kws = []
            for kw in cond["keywords"]:
                if kw.lower() in all_text:
                    keyword_match = True
                    matched_kws.append(kw)
            if matched_kws:
                reasons.append(f"关键词命中: {', '.join(matched_kws)}")

            # 综合判断：至少满足2个维度 或 关键词强匹配
            dimensions_met = sum([scale_match, industry_match, keyword_match])
            if dimensions_met >= 2 or (keyword_match and len(matched_kws) >= 2):
                matched.append({
                    "category": category_name,
                    "channel_name": sub["name"],
                    "max_amount": cond["max_amount"],
                    "match_reasons": reasons,
                    "dimensions_met": dimensions_met,
                })

    # 按匹配维度数量降序排列
    matched.sort(key=lambda x: x["dimensions_met"], reverse=True)
    return matched
