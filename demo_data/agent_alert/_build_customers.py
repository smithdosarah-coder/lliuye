# -*- coding: utf-8 -*-
"""一次性构造 Agent4 Demo 用的 100 家在贷客户 Excel + JSONL + 证据材料。

产出：
- demo_data/agent_alert/loan_customers.xlsx  （演示上传用）
- demo_data/mock_pool/loan_customers.jsonl   （SearchProvider 使用）
- demo_data/mock_pool/court_records.json
- demo_data/mock_pool/news.json

结构：100 家 = 3 红 + 7 黄 + 90 绿。
红灯：华联精密制造 / 兴业通达贸易 / 德昌五金制品
黄灯：恒达汽配 / 瑞丰五金 / 金泰电子 / 永盛包装 / 华丰物流 / 大明机械 / 鑫源纺织
绿灯：其余 90 家程序化生成。
"""
from __future__ import annotations
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MOCK_POOL = ROOT / "demo_data" / "mock_pool"
MOCK_POOL.mkdir(parents=True, exist_ok=True)

random.seed(20260414)


# ---------------------------------------------------------------------------
# 红灯 3 家：交叉命中多条，必出红灯
# ---------------------------------------------------------------------------
RED_CUSTOMERS = [
    {
        "company_id": "LC10001",
        "company_name": "华联精密制造有限公司",
        "unified_credit_code": "91310115MA1K3F9001",
        "industry": "制造业",
        "sub_industry": "精密零部件",
        "region": "上海浦东",
        "scale": "小型",
        "manager": "张敏",
        "internal_rating": "BBB",
        "credit_line": 3200.0,
        "outstanding": 2850.0,
        "due_date": "2026-06-30",
        "registered_capital": "1500万",
        "establishment_date": "2012-05-18",
        "revenue_latest": "1.8亿",
        "profit_latest": -680.0,
        "debt_ratio": 78.5,
        "main_business": "精密机械零部件加工",
        "risk_tags": [
            "净利润转负",
            "涉诉1200万",
            "主要客户重整",
            "应收账款上升",
        ],
        "narrative": "2025Q4 净利润-680万；被列为被告涉诉标的1200万；核心客户（占营收35%）进入重整程序",
    },
    {
        "company_id": "LC10002",
        "company_name": "兴业通达贸易有限公司",
        "unified_credit_code": "91440300MA5L8B7002",
        "industry": "批发零售业",
        "sub_industry": "大宗商品贸易",
        "region": "广东深圳",
        "scale": "小型",
        "manager": "李强",
        "internal_rating": "BB",
        "credit_line": 2500.0,
        "outstanding": 2500.0,
        "due_date": "2026-09-15",
        "registered_capital": "2000万",
        "establishment_date": "2014-11-02",
        "revenue_latest": "3.2亿",
        "profit_latest": -450.0,
        "debt_ratio": 83.2,
        "main_business": "金属材料贸易",
        "risk_tags": ["实控人变更", "股权冻结", "资产负债率超80%"],
        "narrative": "实控人发生变更；大股东持有的60%股权被司法冻结；资产负债率攀升至83.2%",
    },
    {
        "company_id": "LC10003",
        "company_name": "德昌五金制品有限公司",
        "unified_credit_code": "91320583MA1R6E9003",
        "industry": "制造业",
        "sub_industry": "五金制品",
        "region": "江苏苏州",
        "scale": "小型",
        "manager": "王芳",
        "internal_rating": "BBB",
        "credit_line": 1800.0,
        "outstanding": 1620.0,
        "due_date": "2026-04-28",
        "registered_capital": "800万",
        "establishment_date": "2010-08-20",
        "revenue_latest": "8600万",
        "profit_latest": -120.0,
        "debt_ratio": 75.0,
        "main_business": "五金配件生产",
        "risk_tags": ["失信被执行", "停产", "贷后检查逾期"],
        "narrative": "被列入失信被执行人名单；工厂停产超过 15 天；贷后现场检查已逾期 42 天",
    },
]

# ---------------------------------------------------------------------------
# 黄灯 7 家：仅外部或仅内部命中一路
# ---------------------------------------------------------------------------
YELLOW_CUSTOMERS = [
    {
        "company_id": "LC10101",
        "company_name": "恒达汽配有限公司",
        "unified_credit_code": "91330108MA2H5K9101",
        "industry": "制造业",
        "sub_industry": "汽车零部件",
        "region": "浙江杭州",
        "scale": "小型",
        "manager": "陈晓",
        "internal_rating": "BBB",
        "credit_line": 800.0,
        "outstanding": 720.0,
        "due_date": "2026-08-20",
        "registered_capital": "500万",
        "establishment_date": "2013-03-10",
        "revenue_latest": "9800万",
        "profit_latest": 320.0,
        "debt_ratio": 65.2,
        "main_business": "汽车配件生产",
        "risk_tags": ["应收账款周转恶化"],
        "narrative": "应收账款周转天数从 45 天升至 78 天；行业景气下行",
    },
    {
        "company_id": "LC10102",
        "company_name": "瑞丰五金有限公司",
        "unified_credit_code": "91330108MA2H5K9102",
        "industry": "制造业",
        "sub_industry": "五金",
        "region": "浙江宁波",
        "scale": "小型",
        "manager": "周伟",
        "internal_rating": "BBB",
        "credit_line": 600.0,
        "outstanding": 580.0,
        "due_date": "2026-07-15",
        "registered_capital": "400万",
        "establishment_date": "2015-06-08",
        "revenue_latest": "6200万",
        "profit_latest": 180.0,
        "debt_ratio": 72.1,
        "main_business": "五金机电",
        "risk_tags": ["资产负债率偏高", "工商变更"],
        "narrative": "资产负债率 72.1% 触及黄线；近期发生经营范围变更",
    },
    {
        "company_id": "LC10103",
        "company_name": "金泰电子有限公司",
        "unified_credit_code": "91440300MA5L8B7103",
        "industry": "制造业",
        "sub_industry": "电子元器件",
        "region": "广东东莞",
        "scale": "小型",
        "manager": "黄磊",
        "internal_rating": "BBB",
        "credit_line": 1200.0,
        "outstanding": 1050.0,
        "due_date": "2026-10-30",
        "registered_capital": "1000万",
        "establishment_date": "2011-12-15",
        "revenue_latest": "1.4亿",
        "profit_latest": 260.0,
        "debt_ratio": 68.0,
        "main_business": "电子元器件生产",
        "risk_tags": ["行业下行", "毛利率下滑"],
        "narrative": "消费电子行业景气下行；毛利率同比下降 6 个百分点",
    },
    {
        "company_id": "LC10104",
        "company_name": "永盛包装材料有限公司",
        "unified_credit_code": "91320100MA1R6E9104",
        "industry": "制造业",
        "sub_industry": "包装材料",
        "region": "江苏南京",
        "scale": "小型",
        "manager": "孙莉",
        "internal_rating": "BBB",
        "credit_line": 700.0,
        "outstanding": 700.0,
        "due_date": "2026-05-22",
        "registered_capital": "500万",
        "establishment_date": "2012-09-28",
        "revenue_latest": "7200万",
        "profit_latest": 110.0,
        "debt_ratio": 64.0,
        "main_business": "包装材料生产",
        "risk_tags": ["一般涉诉"],
        "narrative": "作为被告涉诉标的 180 万元（一般合同纠纷）",
    },
    {
        "company_id": "LC10105",
        "company_name": "华丰物流有限公司",
        "unified_credit_code": "91110000MA01A8P105",
        "industry": "交通运输业",
        "sub_industry": "道路货运",
        "region": "北京朝阳",
        "scale": "小型",
        "manager": "赵亮",
        "internal_rating": "BBB",
        "credit_line": 900.0,
        "outstanding": 810.0,
        "due_date": "2026-11-08",
        "registered_capital": "800万",
        "establishment_date": "2014-07-10",
        "revenue_latest": "1.1亿",
        "profit_latest": 95.0,
        "debt_ratio": 66.0,
        "main_business": "公路货运",
        "risk_tags": ["贷后检查逾期"],
        "narrative": "贷后现场检查已逾期 35 天（触发本行贷后检查缺位制度）",
    },
    {
        "company_id": "LC10106",
        "company_name": "大明机械有限公司",
        "unified_credit_code": "91370200MA3E7T2106",
        "industry": "制造业",
        "sub_industry": "通用机械",
        "region": "山东青岛",
        "scale": "小型",
        "manager": "钱进",
        "internal_rating": "BBB",
        "credit_line": 1500.0,
        "outstanding": 1350.0,
        "due_date": "2026-07-30",
        "registered_capital": "1200万",
        "establishment_date": "2010-04-05",
        "revenue_latest": "1.6亿",
        "profit_latest": 290.0,
        "debt_ratio": 69.5,
        "main_business": "通用机械制造",
        "risk_tags": ["核心客户流失"],
        "narrative": "主要客户 A 占营收 34% 终止合作；2025Q4 营收环比下降 8%",
    },
    {
        "company_id": "LC10107",
        "company_name": "鑫源纺织有限公司",
        "unified_credit_code": "91330200MA2J8K9107",
        "industry": "制造业",
        "sub_industry": "纺织服装",
        "region": "浙江绍兴",
        "scale": "小型",
        "manager": "冯雪",
        "internal_rating": "BBB",
        "credit_line": 500.0,
        "outstanding": 450.0,
        "due_date": "2026-06-12",
        "registered_capital": "300万",
        "establishment_date": "2013-11-20",
        "revenue_latest": "4800万",
        "profit_latest": 75.0,
        "debt_ratio": 71.5,
        "main_business": "纺织面料",
        "risk_tags": ["关联企业涉诉", "行业下行"],
        "narrative": "关联企业因应收账款纠纷涉诉；纺织行业景气度持续下行",
    },
]


# ---------------------------------------------------------------------------
# 绿灯 90 家：程序化生成
# ---------------------------------------------------------------------------
INDUSTRIES = [
    ("制造业", "精密零部件", "机械加工"),
    ("制造业", "食品加工", "食品饮料生产"),
    ("批发零售业", "建材贸易", "建筑材料销售"),
    ("批发零售业", "农副产品", "农产品批发"),
    ("服务业", "企业服务", "管理咨询"),
    ("建筑业", "市政工程", "市政建设"),
    ("信息技术业", "软件开发", "企业软件"),
    ("交通运输业", "仓储物流", "仓储服务"),
    ("住宿餐饮业", "餐饮连锁", "餐饮管理"),
]
REGIONS = ["上海浦东", "上海徐汇", "北京海淀", "北京朝阳", "浙江杭州", "浙江宁波",
           "江苏苏州", "江苏无锡", "广东深圳", "广东广州", "山东济南", "山东青岛",
           "福建厦门", "四川成都", "湖北武汉"]
NAME_PREFIX = ["裕达", "瑞祥", "博远", "新盛", "安邦", "锦泰", "诚信", "翔宇", "长兴",
               "万邦", "广利", "恒联", "兴弘", "泰和", "恒通", "正大", "宏图", "盛泽",
               "广源", "永利", "同安", "聚鑫", "昊辉", "明德", "嘉利", "鼎新", "中润",
               "博通", "龙昌", "华瑞", "万隆", "精诚", "华鼎"]
NAME_SUFFIX = ["科技", "实业", "工贸", "机电", "材料", "商贸", "供应链", "智能", "环保",
               "新材料", "精密", "食品", "建材", "五金"]

MANAGERS = ["王磊", "李娜", "张晓明", "陈华", "刘佳", "林涛", "赵敏", "孙强", "周雯"]


def _gen_green(i: int) -> dict:
    industry, sub, main_biz = random.choice(INDUSTRIES)
    region = random.choice(REGIONS)
    prefix = random.choice(NAME_PREFIX)
    suffix = random.choice(NAME_SUFFIX)
    name = f"{prefix}{suffix}有限公司"
    cid = f"LC2{i:04d}"
    credit = random.choice([300, 400, 500, 600, 800, 1000, 1200, 1500, 1800, 2000, 2500])
    outstanding = round(credit * random.uniform(0.6, 0.95), 0)
    year = random.randint(2026, 2027)
    month = random.randint(1, 12)
    day = random.randint(5, 28)
    due = f"{year}-{month:02d}-{day:02d}"
    reg_cap = random.choice([300, 500, 800, 1000, 1500, 2000])
    est_year = random.randint(2008, 2020)
    est_month = random.randint(1, 12)
    est_day = random.randint(1, 28)
    revenue_num = random.randint(3000, 25000)  # 万元
    if revenue_num >= 10000:
        rev = f"{revenue_num/10000:.1f}亿"
    else:
        rev = f"{revenue_num}万"
    profit = round(revenue_num * random.uniform(0.03, 0.10), 0)  # 正向利润
    debt = round(random.uniform(40, 62), 1)  # 健康范围
    return {
        "company_id": cid,
        "company_name": name,
        "unified_credit_code": f"9131{i:04d}MA1{i:06d}",
        "industry": industry,
        "sub_industry": sub,
        "region": region,
        "scale": random.choice(["小型", "微型"]),
        "manager": random.choice(MANAGERS),
        "internal_rating": random.choice(["A", "BBB", "A-"]),
        "credit_line": float(credit),
        "outstanding": float(outstanding),
        "due_date": due,
        "registered_capital": f"{reg_cap}万",
        "establishment_date": f"{est_year}-{est_month:02d}-{est_day:02d}",
        "revenue_latest": rev,
        "profit_latest": float(profit),
        "debt_ratio": debt,
        "main_business": main_biz,
        "risk_tags": [],
        "narrative": "",
    }


def build_all_customers() -> list[dict]:
    green = [_gen_green(i) for i in range(1, 91)]
    # 名称去重，避免偶然重名
    seen = set()
    uniq = []
    for c in green:
        if c["company_name"] in seen:
            c["company_name"] = c["company_name"][:-4] + str(len(uniq)) + "有限公司"
        seen.add(c["company_name"])
        uniq.append(c)
    return RED_CUSTOMERS + YELLOW_CUSTOMERS + uniq


# ---------------------------------------------------------------------------
# 写 Excel
# ---------------------------------------------------------------------------
def write_excel(customers: list[dict], xlsx_path: Path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "在贷客户名录"
    headers = [
        "客户号", "企业名称", "统一社会信用代码", "行业", "细分行业", "地区",
        "规模", "客户经理", "内评", "授信额度(万元)", "贷款余额(万元)",
        "贷款到期日", "注册资本", "成立日期", "最近营收", "最近净利润(万元)",
        "资产负债率(%)", "主营业务", "风险标签",
    ]
    ws.append(headers)
    for c in customers:
        ws.append([
            c["company_id"], c["company_name"], c["unified_credit_code"],
            c["industry"], c["sub_industry"], c["region"], c["scale"],
            c["manager"], c["internal_rating"],
            c["credit_line"], c["outstanding"], c["due_date"],
            c["registered_capital"], c["establishment_date"],
            c["revenue_latest"], c["profit_latest"], c["debt_ratio"],
            c["main_business"], "，".join(c.get("risk_tags", [])),
        ])
    widths = [10, 30, 22, 10, 14, 10, 8, 10, 6, 14, 14, 12, 10, 12, 10, 14, 12, 24, 30]
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(ord("A") + i)].width = w
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(xlsx_path))


# ---------------------------------------------------------------------------
# 写 mock_pool JSONL
# ---------------------------------------------------------------------------
def write_mock_pool(customers: list[dict]):
    jsonl_path = MOCK_POOL / "loan_customers.jsonl"
    lines = []
    for c in customers:
        profile = {
            "company_id": c["company_id"],
            "company_name": c["company_name"],
            "unified_credit_code": c["unified_credit_code"],
            "industry": c["industry"],
            "sub_industry": c["sub_industry"],
            "region": c["region"],
            "scale": c["scale"],
            "revenue_latest": c["revenue_latest"],
            "registered_capital": c["registered_capital"],
            "establishment_date": c["establishment_date"],
            "main_business": c["main_business"],
            "tags": c.get("risk_tags", []),
            "credit_balance": f"{c['outstanding']:.0f}万",
            "extras": {
                "manager": c["manager"],
                "internal_rating": c["internal_rating"],
                "credit_line": c["credit_line"],
                "outstanding": c["outstanding"],
                "due_date": c["due_date"],
                "profit_latest": c["profit_latest"],
                "debt_ratio": c["debt_ratio"],
                "narrative": c.get("narrative", ""),
                "risk_tags": c.get("risk_tags", []),
            },
        }
        lines.append(json.dumps(profile, ensure_ascii=False))
    jsonl_path.write_text("\n".join(lines), encoding="utf-8")

    # court_records
    court = [
        {
            "case_no": "(2025)沪0115民初12345号",
            "company_name": "华联精密制造有限公司",
            "role": "被告",
            "case_type": "买卖合同纠纷",
            "amount": 12000000,
            "filed_at": "2025-11-18",
            "status": "一审审理中",
            "url": "https://wenshu.court.gov.cn/mock/2025_0115_12345",
            "snippet": "原告诉请被告华联精密制造有限公司支付货款 1200 万元及违约金。",
        },
        {
            "case_no": "(2025)苏0583执恢1289号",
            "company_name": "德昌五金制品有限公司",
            "role": "被执行人",
            "case_type": "强制执行",
            "amount": 3500000,
            "filed_at": "2025-12-02",
            "status": "已列入失信被执行人名单",
            "url": "https://wenshu.court.gov.cn/mock/2025_0583_1289",
            "snippet": "德昌五金制品有限公司因未履行生效判决被列入失信被执行人名单。",
        },
        {
            "case_no": "(2025)苏01民初8891号",
            "company_name": "永盛包装材料有限公司",
            "role": "被告",
            "case_type": "一般合同纠纷",
            "amount": 1800000,
            "filed_at": "2025-10-09",
            "status": "一审审理中",
            "url": "https://wenshu.court.gov.cn/mock/2025_0100_8891",
            "snippet": "涉及货款纠纷 180 万元，已开庭审理。",
        },
    ]
    (MOCK_POOL / "court_records.json").write_text(
        json.dumps(court, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # news
    news = [
        {
            "title": "华联精密核心客户流失，财务承压",
            "url": "https://news.mock/cj/20251115/hualian-lose-customer",
            "snippet": "据财经媒体报道，华联精密核心客户占营收 35%进入重整程序，公司 2025Q4 亏损 680 万元。",
            "published_at": "2025-11-15",
            "company_name": "华联精密制造有限公司",
            "sentiment": "负面",
        },
        {
            "title": "兴业通达贸易实控人变更，大股东股权被司法冻结",
            "url": "https://news.mock/cj/20260108/xingye-controller-change",
            "snippet": "近日企查查显示，兴业通达贸易有限公司完成实控人变更，大股东 60% 股权被司法冻结。",
            "published_at": "2026-01-08",
            "company_name": "兴业通达贸易有限公司",
            "sentiment": "负面",
        },
        {
            "title": "德昌五金遭法院列入失信名单，工厂停产",
            "url": "https://news.mock/cj/20260220/dechang-default",
            "snippet": "德昌五金制品被列入失信被执行人名单，苏州厂区已停产超两周。",
            "published_at": "2026-02-20",
            "company_name": "德昌五金制品有限公司",
            "sentiment": "负面",
        },
        {
            "title": "汽车零部件行业景气下行，恒达汽配回款周期拉长",
            "url": "https://news.mock/cj/20260115/hengda-accounts",
            "snippet": "受主机厂销量下滑影响，恒达汽配 2025Q4 应收账款周转天数从 45 天升至 78 天。",
            "published_at": "2026-01-15",
            "company_name": "恒达汽配有限公司",
            "sentiment": "负面",
        },
        {
            "title": "消费电子景气度下行，金泰电子毛利率承压",
            "url": "https://news.mock/cj/20260110/jintai-margin",
            "snippet": "电子行业需求低迷，金泰电子毛利率同比下降 6 个百分点。",
            "published_at": "2026-01-10",
            "company_name": "金泰电子有限公司",
            "sentiment": "中性",
        },
        {
            "title": "永盛包装涉一般合同纠纷",
            "url": "https://news.mock/cj/20251120/yongsheng-dispute",
            "snippet": "永盛包装作为被告涉诉标的 180 万元的一般合同纠纷案件已开庭。",
            "published_at": "2025-11-20",
            "company_name": "永盛包装材料有限公司",
            "sentiment": "负面",
        },
        {
            "title": "鑫源纺织关联企业涉诉，行业整体承压",
            "url": "https://news.mock/cj/20260205/xinyuan-related",
            "snippet": "鑫源纺织关联企业因应收账款纠纷涉诉，纺织业景气度持续下行。",
            "published_at": "2026-02-05",
            "company_name": "鑫源纺织有限公司",
            "sentiment": "中性",
        },
        {
            "title": "大明机械主要客户终止合作",
            "url": "https://news.mock/cj/20260128/daming-customer",
            "snippet": "据业内消息，大明机械主要客户 A（占营收 34%）已终止采购合作。",
            "published_at": "2026-01-28",
            "company_name": "大明机械有限公司",
            "sentiment": "负面",
        },
    ]
    (MOCK_POOL / "news.json").write_text(
        json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 场景元数据
# ---------------------------------------------------------------------------
SCENARIO = {
    "scenario_id": "micro_credit_100",
    "title": "小微信贷 100 家扫描",
    "description": "某城商行小微信贷事业部 100 家在贷客户池全量体检（预期 3 红 / 7 黄 / 90 绿）。",
    "expected": {"red": 3, "yellow": 7, "green": 90},
    "kb_files": {
        "customers": "demo_data/agent_alert/loan_customers.xlsx",
        "rules": "demo_data/agent_alert/warning_rules.json",
        "policy": "demo_data/agent_alert/internal_policy.md",
    },
    "highlighted_cases": [
        {
            "company_name": "华联精密制造有限公司",
            "level": "red",
            "rule_ids": ["FIN-002", "LAW-001", "POL-003"],
        },
        {
            "company_name": "兴业通达贸易有限公司",
            "level": "red",
            "rule_ids": ["BIZ-002", "REL-002", "FIN-003"],
        },
        {
            "company_name": "德昌五金制品有限公司",
            "level": "red",
            "rule_ids": ["LAW-002", "BIZ-004", "POL-006"],
        },
    ],
}


def main():
    customers = build_all_customers()
    assert len(customers) == 100, f"期望 100 家，实得 {len(customers)}"
    xlsx_path = HERE / "loan_customers.xlsx"
    write_excel(customers, xlsx_path)
    write_mock_pool(customers)
    (HERE / "scenario.json").write_text(
        json.dumps(SCENARIO, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ok] 生成 {len(customers)} 家客户 → {xlsx_path}")
    print(f"[ok] mock_pool → {MOCK_POOL}")
    print(f"[ok] scenario → {HERE/'scenario.json'}")


if __name__ == "__main__":
    main()
