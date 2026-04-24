# -*- coding: utf-8 -*-
"""5 家深柱企业 profile · PM 内部追踪的档级信息绝不入此文件。

本模块仅暴露**构建材料包需要的客观业务字段**：企业名、行业、地区、法人、
银行、主业、主要客户/供应商、多年营收量级、资质、租赁年份等。

- 不含 difficulty / tags / benchmark_ref / expected_decision 等答案字段
- 企业名全部脱敏（不与真实存续企业重名）
- 身份证 / 银行卡号 / 手机号全部 mock 用占位串
- 营收/利润量级保留但数值浮动，供 generator 进一步叠加月度/季度噪声
"""

PROFILES = [
    # -------- DP001 --------
    {
        "dp_id": "DP001",
        "name_short": "龙峰精工",
        "name_full": "龙峰精工机械（福建）有限公司",
        "industry": "精密机械加工",
        "region_full": "福建省-泉州市-晋江市",
        "address_detail": "晋江市经济开发区信息产业园 5 号楼 3 层",
        "legal_person": "黄祖桐",
        "legal_person_id_mask": "3505**19821014****",
        "uscc": "91350582MA2XXXX011",
        "open_bank": "中国工商银行晋江经济开发区支行",
        "open_bank_acct": "1607********0001102",
        "establish_year": 2012,
        "registered_capital_wan": 1200,
        "revenue_2022_wan": 4900,
        "revenue_2023_wan": 5800,
        "revenue_2024_wan": 6500,
        "revenue_2025q1_wan": 1680,
        "net_profit_2024_wan": 620,
        "total_asset_2024_wan": 8800,
        "total_liab_2024_wan": 3900,
        "employee_count": 58,
        "patents_count": 15,
        "main_business": "航空航天与汽车用精密零部件 CNC 加工及表面处理",
        "main_customers": [
            ("华晟汽车配件（泉州）有限公司", 1500),
            ("顺辉机械制造有限公司", 800),
            ("飞讯精密工业股份有限公司", 620),
        ],
        "main_suppliers": [
            ("宝钢华东销售中心", 820),
            ("川崎机床服务（上海）", 300),
            ("大众优质金属原料贸易有限公司", 260),
        ],
        "banks": [
            ("中国工商银行晋江经济开发区支行", "主结算账户"),
            ("交通银行晋江分行", "流动资金贷款 500 万"),
            ("兴业银行晋江分行", "综合授信 1000 万"),
        ],
        "bank_flow_months": ["202501", "202502", "202503", "202504", "202505", "202506"],
        "qualifications": [
            ("高新技术企业", 2023),
            ("专精特新小巨人企业（省级）", 2024),
        ],
        "lease_periods": [(2021, 2023), (2023, 2026)],
        "audit_firm_alias": "德昇",
        "renew_purpose": "流动资金续贷 500 万元 · 12 个月期",
    },

    # -------- DP002 --------
    {
        "dp_id": "DP002",
        "name_short": "蓝汀家电",
        "name_full": "蓝汀家电连锁（浙江）有限公司",
        "industry": "家电零售连锁",
        "region_full": "浙江省-金华市-义乌市",
        "address_detail": "义乌市江东街道青年路 126 号 1-3 层",
        "legal_person": "陈立嘉",
        "legal_person_id_mask": "3307**19780322****",
        "uscc": "91330782MA2XXXX022",
        "open_bank": "招商银行义乌支行",
        "open_bank_acct": "5716********0022035",
        "establish_year": 2009,
        "registered_capital_wan": 2000,
        "revenue_2022_wan": 6800,   # 2022 材料有缺失，产出时随机裁剪
        "revenue_2023_wan": 7500,
        "revenue_2024_wan": 8200,
        "revenue_2025q1_wan": 1980,
        "net_profit_2024_wan": 420,
        "total_asset_2024_wan": 7600,
        "total_liab_2024_wan": 4400,
        "employee_count": 46,
        "patents_count": 0,
        "main_business": "大家电+小家电线下零售与售后（直营 18 家 + 加盟 11 家门店）",
        "main_customers": [
            ("（义乌）个人消费客户", None),  # 零售 C 端
            ("义乌某酒店集团采购部", 680),
            ("商务代采购客户合集", 320),
        ],
        "main_suppliers": [
            ("海尔浙江销售中心", 2200),
            ("美的华东运营中心", 1850),
            ("奥克斯空调浙中分公司", 1100),
        ],
        "banks": [
            ("招商银行义乌支行", "主结算账户"),
            ("宁波银行义乌小微金融", "经营性贷款 800 万"),
            ("中国农业银行义乌支行", "电票结算 + 少量授信"),
        ],
        "bank_flow_months": ["202411", "202412", "202501", "202502", "202503", "202504", "202505", "202506"],
        "qualifications": [
            ("义乌市商务诚信示范企业", 2023),
        ],
        "lease_periods": [(2022, 2025), (2025, 2028)],
        "audit_firm_alias": "正衡",
        "renew_purpose": "经营性流贷续作 800 万元 · 12 个月期",
        "quirks": {
            "revenue_declare_vs_audit_gap_pct": 7,  # 申报 vs 审计差 7%（合理口径差）
            "missing_2022_audit": True,              # 2022 审计报告缺失
        },
    },

    # -------- DP003 --------
    {
        "dp_id": "DP003",
        "name_short": "宸星家装",
        "name_full": "宸星家装工程（四川）有限公司",
        "industry": "家装工程连锁",
        "region_full": "四川省-成都市-武侯区",
        "address_detail": "武侯区聚龙路 88 号 A 栋 6 层",
        "legal_person": "周承泽",
        "legal_person_id_mask": "5101**19750118****",
        "uscc": "91510107MA2XXXX033",
        "open_bank": "中国建设银行成都武侯支行",
        "open_bank_acct": "5101********0033078",
        "establish_year": 2013,
        "registered_capital_wan": 2800,
        "revenue_2022_wan": 9200,
        "revenue_2023_wan": 10800,
        "revenue_2024_wan": 12000,
        "revenue_2025q1_wan": 2480,
        "net_profit_2024_wan": 540,
        "total_asset_2024_wan": 11600,
        "total_liab_2024_wan": 7800,
        "employee_count": 128,
        "patents_count": 3,
        "main_business": "住宅整装与工装家装项目承接（12 家直营门店+在建项目 8 个）",
        "main_customers": [
            ("双流某精装房项目（地产方）", 2200),
            ("成都某品牌酒店装修", 1800),
            ("成都某商业综合体软装", 1100),
        ],
        "main_suppliers": [
            ("大自然地板四川销售", 1400),
            ("立邦涂料成都分公司", 860),
            ("欧派橱柜成都运营中心", 1200),
        ],
        "banks": [
            ("中国建设银行成都武侯支行", "主结算账户"),
            ("中国银行成都科华南路支行", "工程保函 1200 万"),
            ("中国农业银行成都武侯支行", "票据结算"),
            ("招商银行成都分行", "流贷 1000 万"),
        ],
        "bank_flow_months": ["202410", "202411", "202412", "202501", "202502", "202503", "202504", "202505", "202506"],
        "qualifications": [
            ("建筑装饰工程施工专业承包二级", 2019),
            ("成都市装饰协会理事单位", 2022),
        ],
        "lease_periods": [(2020, 2023), (2023, 2026)],
        "audit_firm_alias": "融聚",
        "renew_purpose": "流动资金续贷 1000 万元 · 12 个月期",
        "quirks": {
            "accounts_receivable_high": True,  # 应收账款较高（合理行业特征）
            "scan_files_disorganized_naming": True,
        },
    },

    # -------- DP004 --------
    {
        "dp_id": "DP004",
        "name_short": "汇德建材",
        "name_full": "汇德建材贸易（河北）有限公司",
        "industry": "建材贸易",
        "region_full": "河北省-廊坊市-广阳区",
        "address_detail": "广阳区新源道 128 号建材物流园 A 区 12 号库",
        "legal_person": "孙宏昊",
        "legal_person_id_mask": "1310**19700805****",
        "uscc": "91131003MA2XXXX044",
        "open_bank": "中国工商银行廊坊分行",
        "open_bank_acct": "1713********0044091",
        "establish_year": 2008,
        "registered_capital_wan": 5600,
        "revenue_2022_wan": 28000,
        "revenue_2023_wan": 26400,
        "revenue_2024_wan": 28800,
        "revenue_2025q1_wan": 6100,
        "net_profit_2024_wan": 1080,
        "total_asset_2024_wan": 22000,
        "total_liab_2024_wan": 16800,
        "employee_count": 62,
        "patents_count": 0,
        "main_business": "水泥/钢材/建材批发贸易 + 地产链条工程项目供货",
        "main_customers": [
            ("某 TOP30 地产廊坊项目群", 9200),
            ("汇德顺达建设工程有限公司", 6800),  # 关联方线索（后缀同"汇德"、法人旗下另一家）
            ("环京某市政工程项目部", 2400),
        ],
        "main_suppliers": [
            ("冀钢股份廊坊办事处", 7200),
            ("金隅水泥华北区", 4200),
            ("汇德顺达建设工程有限公司", 1800),  # 同一家既是客户又是供应商
        ],
        "banks": [
            ("中国工商银行廊坊分行", "主结算账户"),
            ("中信银行廊坊分行", "流贷 1500 万"),
            ("中国农业银行廊坊分行", "承兑+敞口"),
            ("张家口银行廊坊支行", "小额流贷"),
        ],
        "bank_flow_months": ["202410", "202411", "202412", "202501", "202502", "202503", "202504", "202505", "202506"],
        "qualifications": [
            ("钢材贸易资质（市级备案）", 2010),
        ],
        "lease_periods": [(2018, 2021), (2021, 2024), (2024, 2027)],
        "audit_firm_alias": "华衡",
        "renew_purpose": "经营性流贷续作 1500 万元 · 12 个月期",
        "quirks": {
            "financial_vs_flow_large_gap_pct": 22,  # 财报 vs 流水 22% 大偏差
            "related_party_hidden_in_contracts": True,  # 关联方线索埋合同里
            "messy_naming_severe": True,
        },
    },

    # -------- DP005 --------
    {
        "dp_id": "DP005",
        "name_short": "星胤实业",
        "name_full": "星胤实业集团（某省）有限公司",
        "industry": "实业集团（多元化）",
        "region_full": "某省-某地级市-主城区",
        "address_detail": "经济技术开发区长宁大道 1688 号星胤大厦 18-22 层",
        "legal_person": "柳慎之",
        "legal_person_id_mask": "3411**19660219****",
        "uscc": "91340100MA2XXXX055",
        "open_bank": "交通银行某分行营业部",
        "open_bank_acct": "4220********0055112",
        "establish_year": 2006,
        "registered_capital_wan": 36000,
        "revenue_2022_wan": 42000,
        "revenue_2023_wan": 45000,
        "revenue_2024_wan": 45500,
        "revenue_2025q1_wan": 9800,
        "net_profit_2024_wan": 1250,
        "total_asset_2024_wan": 58000,
        "total_liab_2024_wan": 43600,
        "employee_count": 286,
        "patents_count": 5,
        "main_business": "实业+商业双主业集团（旗下 6 家子公司 · 含 1 家与地产相关联的商管公司）",
        "main_customers": [
            ("星胤商管运营（某省）", 12000),    # 关联方（同姓星胤）
            ("某省某商业地产项目群", 8400),
            ("某省国资某采购联盟", 6200),
        ],
        "main_suppliers": [
            ("星悦产业投资有限公司", 5800),      # 关联方
            ("某省某钢贸综合体", 4400),
            ("慎之工贸（某省）有限公司", 2800),  # 法人名字同"慎之"—— 关联方
        ],
        "banks": [
            ("交通银行某分行营业部", "主结算+综合授信 8000 万"),
            ("中国工商银行某分行", "项目贷 3000 万"),
            ("浦发银行某分行", "承兑 4000 万"),
            ("某省农商银行", "小额流贷 + 互保"),
        ],
        "bank_flow_months": ["202410", "202411", "202412", "202501", "202502", "202503", "202504", "202505", "202506"],
        "qualifications": [
            ("省级工业龙头企业", 2020),
            ("某专项行业许可（2018 批号）", 2018),
        ],
        "qualification_expired": [("某专项行业许可", 2023)],  # 2023 到期未续
        "lease_periods": [(2006, 2016), (2016, 2026)],
        "audit_firm_alias": "立信致远",
        "renew_purpose": "综合授信续作 8000 万元 + 项目贷展期 3000 万元",
        "quirks": {
            "qualification_expired": True,
            "related_party_flow_pct": 35,      # 流水中关联方占比 35%
            "cross_guarantee_chain": True,      # 子公司互保链
            "2024_project_materials_missing": True,  # 某项目 2024 年材料"遗漏"
        },
    },
]


def get_profile(dp_id: str) -> dict:
    for p in PROFILES:
        if p["dp_id"] == dp_id:
            return p
    raise KeyError(dp_id)


def all_profiles():
    return list(PROFILES)
