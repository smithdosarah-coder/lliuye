"""
alert-pool 180 家在贷客户画像池（PM 内部维护 · 不进产物）。

本文件仅供 generate_*.py 消费，**绝不**导出为 csv/yaml 答案键。
难度档位（tier）只在脚本内流转，生成 clients.csv / transactions / signals 时作为
概率参数影响具体数字 / 信号组合，**不**写入任何产物字段。

分布目标（与 onboarding §2 Task A 对齐）：
  easy    ≈ 20   干净画像 / 规整流水 / 正面信号
  medium  ≈ 100  常规波动 / 中性信号为主
  hard    ≈ 40   回款降 / 余额逼顶 / 外部多条负面
  extreme ≈ 20   失信被执 + 内部流水异常 + 工商变更
  合计    = 180

脱敏再造（Q-029.D 测试阶段豁免·重名 OK），对外演示前需追溯。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


SEED = 20260424
rng = random.Random(SEED)


# 行业分布（制造业占 50% · 总 180 家）
#   制造业 ~90  贸易 ~18  物流 ~15  零售 ~13  服务 ~18  科技 ~13  建筑 ~9  农业 ~4
INDUSTRY_QUOTA = [
    ("制造业", "精密机械", 14),
    ("制造业", "电子元件", 12),
    ("制造业", "模具注塑", 8),
    ("制造业", "家电家居", 10),
    ("制造业", "汽车零部件", 10),
    ("制造业", "纺织服装", 8),
    ("制造业", "化工材料", 8),
    ("制造业", "医疗器械", 6),
    ("制造业", "金属加工", 8),
    ("制造业", "食品饮料", 6),
    ("贸易", "大宗商品贸易", 7),
    ("贸易", "消费品贸易", 6),
    ("贸易", "跨境电商", 5),
    ("物流", "公路运输", 6),
    ("物流", "冷链仓储", 4),
    ("物流", "供应链管理", 5),
    ("零售", "连锁零售", 6),
    ("零售", "生鲜零售", 4),
    ("零售", "专业零售", 3),
    ("服务", "企业服务", 6),
    ("服务", "餐饮连锁", 5),
    ("服务", "职业教育", 4),
    ("服务", "商旅酒店", 3),
    ("科技", "软件信息", 5),
    ("科技", "SaaS云服务", 4),
    ("科技", "物联网", 4),
    ("建筑", "专业工程", 5),
    ("建筑", "建材供应", 4),
    ("农业", "农产品加工", 4),
]
assert sum(x[2] for x in INDUSTRY_QUOTA) == 180, sum(x[2] for x in INDUSTRY_QUOTA)


# 区域分布（长三角 ~30% / 珠三角 ~30% / 环渤海 ~30% / 中西部 ~10%）
REGIONS = {
    "yrd": [
        ("江苏省", "苏州市", ["昆山", "吴江", "常熟", "张家港"]),
        ("江苏省", "无锡市", ["宜兴", "江阴", "锡山"]),
        ("江苏省", "常州市", ["武进", "新北", "金坛"]),
        ("江苏省", "南通市", ["海门", "如皋", "启东"]),
        ("江苏省", "南京市", ["江宁", "溧水", "栖霞"]),
        ("浙江省", "宁波市", ["鄞州", "北仑", "慈溪"]),
        ("浙江省", "杭州市", ["余杭", "萧山", "钱塘"]),
        ("浙江省", "嘉兴市", ["桐乡", "海宁", "平湖"]),
        ("浙江省", "温州市", ["瑞安", "乐清", "永嘉"]),
        ("安徽省", "合肥市", ["高新区", "包河", "肥西"]),
    ],
    "prd": [
        ("广东省", "东莞市", ["长安", "松山湖", "虎门", "塘厦"]),
        ("广东省", "佛山市", ["顺德", "南海", "三水"]),
        ("广东省", "中山市", ["古镇", "小榄", "火炬"]),
        ("广东省", "广州市", ["番禺", "白云", "黄埔"]),
        ("广东省", "深圳市", ["宝安", "龙岗", "光明"]),
        ("广东省", "珠海市", ["金湾", "斗门", "香洲"]),
        ("广东省", "惠州市", ["仲恺", "博罗", "惠阳"]),
    ],
    "bre": [
        ("山东省", "青岛市", ["即墨", "胶州", "城阳"]),
        ("山东省", "烟台市", ["福山", "莱山", "牟平"]),
        ("山东省", "潍坊市", ["寿光", "诸城", "昌邑"]),
        ("河北省", "唐山市", ["丰润", "玉田", "迁西"]),
        ("河北省", "石家庄市", ["正定", "高邑", "栾城"]),
        ("天津市", "天津市", ["滨海新区", "北辰", "武清"]),
        ("辽宁省", "大连市", ["金州", "旅顺", "瓦房店"]),
        ("辽宁省", "沈阳市", ["浑南", "铁西", "于洪"]),
        ("北京市", "北京市", ["大兴", "通州", "顺义"]),
    ],
    "mid": [
        ("湖北省", "武汉市", ["东西湖", "蔡甸", "江夏"]),
        ("湖南省", "长沙市", ["望城", "浏阳", "宁乡"]),
        ("四川省", "成都市", ["青羊", "温江", "郫都"]),
        ("重庆市", "重庆市", ["北碚", "九龙坡", "渝北"]),
        ("陕西省", "西安市", ["长安", "鄠邑", "高陵"]),
        ("河南省", "郑州市", ["金水", "中原", "荥阳"]),
    ],
}
REGION_WEIGHT = {"yrd": 0.30, "prd": 0.30, "bre": 0.30, "mid": 0.10}


# 企业名前缀 · 2-3 字 · 风格匹配 channel-kb/historical-clients/ 的"雅名 + 行业词 + 城市"拼法
PREFIX_2 = [
    "锐迅", "启星", "晟洁", "泓盈", "雅宁", "鸿新", "融创", "海通", "颂安", "禾元",
    "博瀚", "兴旺", "正合", "德赢", "炬驰", "昊瞻", "凌霄", "祥泓", "圣诺", "鼎越",
    "恒茂", "安辰", "晨曦", "森岩", "雅岚", "弘毅", "煜晟", "隽熠", "谦益", "崇德",
    "澄炎", "衡泰", "邦彦", "诚瑞", "昌朗", "广翀", "景辉", "灵犀", "沐川", "翊轩",
    "悦枫", "青柏", "梓瀚", "致远", "瑞尧", "文栋", "忆川", "楷煌", "寅申", "卓岭",
    "明岚", "康澜", "耀骏", "锡诚", "寒川", "皓月", "霁清", "启航", "寰宇", "翔晟",
    "骏迈", "舟岳", "凯飞", "晖远", "润竹", "逸舟", "启桁", "栎朗", "聆风", "千栎",
    "瑄衍", "朝煦", "弈泰", "橘社", "桢林", "沄晴", "简烁", "云渚", "璟程", "安宥",
    "延予", "瑾辉", "熹诚", "璞遥", "钰泽", "栎华", "嵩恒", "燊翊", "旻辰", "耘骧",
]


# 实体类型后缀
ENTITY_SUFFIXES = [
    "有限公司", "有限公司", "有限公司", "有限公司",  # 加权·主流
    "股份有限公司", "股份有限公司",
    "集团有限公司",
    "合作联社",  # 农业偶发
]


# 行业词库 —— 用于企业名主体 + product/服务描述
INDUSTRY_NAMEWORDS = {
    "精密机械": ["精工", "精密机械", "机电", "机械", "传动", "自动化"],
    "电子元件": ["电子", "微电子", "智能", "元器件", "电路"],
    "模具注塑": ["模具", "塑胶", "精塑", "注塑"],
    "家电家居": ["家电", "家居", "厨电", "家纺"],
    "汽车零部件": ["汽配", "汽车零部件", "传动件", "车灯", "底盘"],
    "纺织服装": ["纺织", "服饰", "针织", "印染"],
    "化工材料": ["化工", "新材料", "高分子", "涂料"],
    "医疗器械": ["医疗器械", "医械", "医学影像", "微创器械"],
    "金属加工": ["金属", "五金", "精铸", "铝材"],
    "食品饮料": ["食品", "饮料", "烘焙", "乳品"],
    "大宗商品贸易": ["钢贸", "煤炭贸易", "能源贸易", "铜铝贸易"],
    "消费品贸易": ["日用品贸易", "商贸", "百货贸易"],
    "跨境电商": ["跨境电商", "外贸", "进出口"],
    "公路运输": ["物流运输", "货运", "车队运输"],
    "冷链仓储": ["冷链", "仓储配送", "恒温仓储"],
    "供应链管理": ["供应链", "物流供应链", "分销"],
    "连锁零售": ["连锁", "零售连锁", "便利"],
    "生鲜零售": ["生鲜", "农贸"],
    "专业零售": ["专业零售", "建材零售", "办公用品"],
    "企业服务": ["企业服务", "人力资源", "财税咨询"],
    "餐饮连锁": ["餐饮", "餐饮连锁", "中央厨房"],
    "职业教育": ["教育", "职业培训", "技能培训"],
    "商旅酒店": ["商旅", "酒店管理", "文旅"],
    "软件信息": ["软件", "信息技术", "信息科技"],
    "SaaS云服务": ["云服务", "SaaS", "数字科技"],
    "物联网": ["物联网", "智联", "数智"],
    "专业工程": ["工程", "市政工程", "智能工程"],
    "建材供应": ["建材", "建材供应", "装饰材料"],
    "农产品加工": ["农产品", "食品加工", "粮油"],
}


# 产品目录（呼应 channel-kb/product-catalog）
PRODUCTS = [
    "流动资金贷款",
    "经营性物业贷款",
    "专精特新贷",
    "科技贷",
    "供应链金融",
    "融资租赁",
    "小微快贷",
    "国内信用证",
    "银行承兑汇票",
    "应收账款保理",
]


SCALE_CONFIG = {
    # (scale, 营收量级范围(万), 授信区间(万), 利率区间)
    "小型": ((800, 6000), (30, 800), (5.2, 7.5)),
    "中型": ((6000, 30000), (500, 5000), (4.3, 6.4)),
    "大型": ((30000, 200000), (3000, 20000), (3.5, 5.2)),
}


@dataclass
class Profile:
    client_id: str
    company_name: str
    industry_l1: str
    industry_l2: str
    province: str
    city: str
    district: str
    scale: str
    credit_line_wan: int
    balance_wan: int
    interest_rate: float
    term_months: int
    product: str
    first_draw_date: str
    last_review_date: str
    # PM 内部字段（绝不进 csv） --------
    tier: str = ""  # easy / medium / hard / extreme
    anomaly_hints: list[str] = field(default_factory=list)
    signal_bias: str = ""  # clean / mixed / negative / crisis
    # 额外用于 signals / transactions 的个性参数
    top_counterparties: list[str] = field(default_factory=list)
    contradiction_kind: str = ""  # "" / "ext-clean-int-bad" / "ext-bad-int-ok"


def _name_unique(rng, used: set, industry_l2: str, city: str) -> str:
    namewords = INDUSTRY_NAMEWORDS[industry_l2]
    for _ in range(30):
        prefix = rng.choice(PREFIX_2)
        word = rng.choice(namewords)
        suffix = rng.choice(ENTITY_SUFFIXES)
        # 风格：<2字前缀><行业词>（<城市>）<实体后缀>
        if suffix == "合作联社":
            name = f"{prefix}{word}合作联社（{city}）"
        else:
            name = f"{prefix}{word}（{city}）{suffix}"
        if name not in used:
            used.add(name)
            return name
    # 兜底 · 加数字避免冲突
    n = 2
    while True:
        prefix = rng.choice(PREFIX_2)
        word = rng.choice(namewords)
        name = f"{prefix}{word}{n}号（{city}）有限公司"
        if name not in used:
            used.add(name)
            return name
        n += 1


def _pick_region(rng) -> tuple[str, str, str]:
    bucket = rng.choices(
        list(REGION_WEIGHT.keys()),
        weights=list(REGION_WEIGHT.values()),
        k=1,
    )[0]
    prov, city, districts = rng.choice(REGIONS[bucket])
    return prov, city, rng.choice(districts)


def _pick_scale(rng, tier: str, industry_l2: str) -> str:
    # hard/extreme 略偏小中型（审贷压力更大），大型更少
    if tier == "extreme":
        return rng.choices(["小型", "中型", "大型"], weights=[0.4, 0.5, 0.1])[0]
    if tier == "hard":
        return rng.choices(["小型", "中型", "大型"], weights=[0.35, 0.5, 0.15])[0]
    if tier == "easy":
        return rng.choices(["小型", "中型", "大型"], weights=[0.35, 0.45, 0.2])[0]
    return rng.choices(["小型", "中型", "大型"], weights=[0.4, 0.45, 0.15])[0]


def _pick_product(rng, tier: str, industry_l2: str, scale: str) -> str:
    if industry_l2 in ("跨境电商", "大宗商品贸易", "消费品贸易"):
        base = ["应收账款保理", "国内信用证", "流动资金贷款", "供应链金融"]
    elif industry_l2 in ("公路运输", "冷链仓储", "供应链管理"):
        base = ["融资租赁", "供应链金融", "流动资金贷款"]
    elif industry_l2 in ("软件信息", "SaaS云服务", "物联网"):
        base = ["科技贷", "专精特新贷", "流动资金贷款"]
    elif industry_l2 in ("专业工程", "建材供应"):
        base = ["经营性物业贷款", "银行承兑汇票", "流动资金贷款"]
    elif scale == "小型":
        base = ["小微快贷", "流动资金贷款", "经营性物业贷款"]
    else:
        base = ["流动资金贷款", "专精特新贷", "银行承兑汇票", "供应链金融"]
    return rng.choice(base)


def _pick_credit(rng, scale: str, tier: str) -> tuple[int, int, float]:
    rev_range, credit_range, rate_range = SCALE_CONFIG[scale]
    credit = int(rng.uniform(*credit_range))
    # 授信金额对齐到 10 / 50 万
    if credit < 500:
        credit = (credit // 10) * 10
    else:
        credit = (credit // 50) * 50
    credit = max(credit, 30)
    if tier == "extreme":
        # 余额逼近授信（85-98%）
        ratio = rng.uniform(0.85, 0.98)
    elif tier == "hard":
        ratio = rng.uniform(0.65, 0.90)
    elif tier == "easy":
        ratio = rng.uniform(0.25, 0.55)
    else:
        ratio = rng.uniform(0.35, 0.75)
    balance = int(credit * ratio)
    # 对齐到 5 / 10 万
    step = 5 if credit < 500 else 10
    balance = max((balance // step) * step, 5)
    rate = round(rng.uniform(*rate_range), 2)
    return credit, balance, rate


def _pick_term(rng, product: str) -> int:
    if product in ("流动资金贷款", "小微快贷", "国内信用证", "银行承兑汇票"):
        return rng.choice([6, 12, 12, 12, 24])
    if product in ("经营性物业贷款", "融资租赁"):
        return rng.choice([36, 36, 60, 60])
    if product in ("科技贷", "专精特新贷"):
        return rng.choice([12, 24, 36])
    return rng.choice([12, 24, 36])


def _date_window(rng, end_yymm: tuple[int, int], month_range: tuple[int, int]) -> str:
    # 返回 YYYY-MM-DD，月 = end 前 month_range 个月
    months = rng.randint(*month_range)
    year, mon = end_yymm
    delta_m = months
    mon_idx = year * 12 + (mon - 1) - delta_m
    y2, m2 = divmod(mon_idx, 12)
    m2 += 1
    day = rng.randint(1, 28)
    return f"{y2:04d}-{m2:02d}-{day:02d}"


def _counterparties_for(rng, industry_l2: str, city: str) -> list[str]:
    """返回**客户侧**（inflow 来源）对手方清单 · 3-4 个。

    注意：tops 只能包含**买方**语义的主体——即收入来源。供应商、税务、社保、
    物业水电这类出向主体在 generate_transactions.py 的 supplier_pool / fee
    misc 里另行构造，不能进 tops。
    """
    tmpl = {
        "精密机械": ["{}机械采购中心", "{}重工集团", "{}装备制造客户", "{}自动化系统集成"],
        "电子元件": ["{}电子集成集团", "{}智能终端厂", "{}消费电子品牌"],
        "模具注塑": ["{}家电集团采购部", "{}汽车零部件客户", "{}日用塑胶品牌"],
        "家电家居": ["{}家电连锁", "{}家居卖场集采", "{}线上旗舰零售"],
        "汽车零部件": ["{}整车厂采购部", "{}汽车集团", "{}新能源汽车客户"],
        "纺织服装": ["{}服饰品牌客户", "{}品牌集团采购", "{}电商平台结算", "{}外贸出口客户"],
        "化工材料": ["{}下游涂料品牌", "{}工程项目客户", "{}新材料应用集团"],
        "医疗器械": ["{}三甲医院", "{}医疗集团", "{}医械经销代理"],
        "金属加工": ["{}机械制造客户", "{}工程总包", "{}汽配集团"],
        "食品饮料": ["{}连锁商超采购", "{}餐饮集团客户", "{}电商平台结算"],
        "大宗商品贸易": ["{}钢铁下游客户", "{}能源集团结算", "{}电厂大宗采购"],
        "消费品贸易": ["{}连锁零售客户", "{}电商平台结算", "{}商超集采"],
        "跨境电商": ["海外客户PayPal结算", "海外客户信用证结算", "{}跨境收款平台"],
        "公路运输": ["{}货主集团结算", "{}快递总部结算", "{}电商物流平台"],
        "冷链仓储": ["{}商超冷链结算", "{}生鲜电商平台", "{}连锁餐饮集团"],
        "供应链管理": ["{}品牌商结算", "{}电商平台结算", "{}分销总部"],
        "连锁零售": ["{}加盟店回款", "{}线上直营回款", "{}团购客户回款"],
        "生鲜零售": ["{}线上订单结算", "{}团购平台结算", "{}社区门店回款"],
        "专业零售": ["{}工程项目客户", "{}连锁分销回款", "{}B端采购客户"],
        "企业服务": ["{}政企客户回款", "{}大客户服务回款", "{}园区客户结算"],
        "餐饮连锁": ["{}加盟门店回款", "{}线上外卖平台结算", "{}团餐客户回款"],
        "职业教育": ["{}学员学费归集", "{}政府购买服务回款", "{}企业培训回款"],
        "商旅酒店": ["{}在线预订平台结算", "{}企业客户结算", "{}会议活动回款"],
        "软件信息": ["{}政企项目回款", "{}SaaS订阅回款", "{}系统集成客户"],
        "SaaS云服务": ["{}SaaS年费回款", "{}政企客户回款", "{}云服务大客户"],
        "物联网": ["{}集成商采购", "{}政企项目回款", "{}物联网品牌客户"],
        "专业工程": ["{}市政项目结算", "{}房建项目结算", "{}产业园业主结算"],
        "建材供应": ["{}工程项目回款", "{}连锁建材卖场回款", "{}经销商集采"],
        "农产品加工": ["{}连锁商超集采", "{}粮油批发客户", "{}食品加工集团"],
    }
    base = tmpl.get(industry_l2, ["{}政企客户", "{}大客户结算", "{}连锁客户回款"])
    return [t.format(city) for t in base]


def generate_profiles() -> list[Profile]:
    # 固定难度配额 · 平均打散进 industry/region
    tiers = (["easy"] * 20 + ["medium"] * 100 + ["hard"] * 40 + ["extreme"] * 20)
    rng.shuffle(tiers)

    # 按行业配额展开（industry_l1, industry_l2） × quota
    industry_pool: list[tuple[str, str]] = []
    for l1, l2, q in INDUSTRY_QUOTA:
        industry_pool.extend([(l1, l2)] * q)
    rng.shuffle(industry_pool)
    assert len(industry_pool) == 180
    assert len(tiers) == 180

    used_names: set[str] = set()
    profiles: list[Profile] = []

    # 契合 onboarding "合理矛盾" 要求：显式挑 ≥ 10 家做跨源矛盾
    contradiction_slots: list[str] = (
        ["ext-clean-int-bad"] * 6 + ["ext-bad-int-ok"] * 6
    )  # 12 家交叉混淆样本
    rng.shuffle(contradiction_slots)
    contradiction_target_tiers = ["extreme"] * 4 + ["hard"] * 6 + ["medium"] * 2

    # 预先决定哪些 client 做矛盾样本 · 按 tier 分配
    contradiction_plan: dict[str, str] = {}

    for i in range(180):
        client_id = f"AP{i + 1:03d}"
        tier = tiers[i]
        l1, l2 = industry_pool[i]
        prov, city, district = _pick_region(rng)
        scale = _pick_scale(rng, tier, l2)
        product = _pick_product(rng, tier, l2, scale)
        credit, balance, rate = _pick_credit(rng, scale, tier)
        term = _pick_term(rng, product)
        company_name = _name_unique(rng, used_names, l2, city)

        first_draw = _date_window(rng, (2026, 4), (6, 36))
        last_review = _date_window(rng, (2026, 4), (1, 12))

        counterparties = _counterparties_for(rng, l2, city)
        prof = Profile(
            client_id=client_id,
            company_name=company_name,
            industry_l1=l1,
            industry_l2=l2,
            province=prov,
            city=city,
            district=district,
            scale=scale,
            credit_line_wan=credit,
            balance_wan=balance,
            interest_rate=rate,
            term_months=term,
            product=product,
            first_draw_date=first_draw,
            last_review_date=last_review,
            tier=tier,
            top_counterparties=counterparties,
        )

        # 默认信号倾向 · 与 tier 松耦合（PM 内部）
        if tier == "easy":
            prof.signal_bias = "clean"
            prof.anomaly_hints = []
        elif tier == "medium":
            prof.signal_bias = rng.choices(["clean", "mixed"], weights=[0.35, 0.65])[0]
            prof.anomaly_hints = rng.choices(
                [[], ["seasonal"], ["seasonal"]], weights=[0.55, 0.25, 0.2]
            )[0]
        elif tier == "hard":
            prof.signal_bias = rng.choices(["mixed", "negative"], weights=[0.35, 0.65])[0]
            prof.anomaly_hints = rng.choices(
                [["inflow_drop"], ["concentration"], ["overdue"], ["inflow_drop", "balance_spike"]],
                weights=[0.35, 0.25, 0.2, 0.2],
            )[0]
        else:  # extreme
            prof.signal_bias = "crisis"
            prof.anomaly_hints = rng.choices(
                [
                    ["inflow_drop", "overdue"],
                    ["concentration", "circular"],
                    ["inflow_drop", "concentration", "overdue"],
                    ["balance_spike", "circular"],
                ],
                weights=[0.3, 0.25, 0.3, 0.15],
            )[0]

        profiles.append(prof)

    # 植入矛盾样本：挑 tier 匹配的客户覆盖签上矛盾类型
    ext_clean_int_bad_need = 6
    ext_bad_int_ok_need = 6

    # extreme & hard 内做 ext-bad-int-ok（外部爆雷但内部还健康）
    candidates_ext_bad = [p for p in profiles if p.tier in ("hard", "extreme")]
    rng.shuffle(candidates_ext_bad)
    placed = 0
    for p in candidates_ext_bad:
        if placed >= ext_bad_int_ok_need:
            break
        if p.contradiction_kind:
            continue
        p.contradiction_kind = "ext-bad-int-ok"
        # 外部偏负 · 内部流水改干净
        p.signal_bias = "negative" if p.tier == "hard" else "crisis"
        p.anomaly_hints = []  # 内部流水回到健康
        placed += 1

    # extreme 内做 ext-clean-int-bad（外部干净但内部先出问题）
    candidates_ext_clean = [p for p in profiles if p.tier in ("extreme", "hard", "medium")]
    rng.shuffle(candidates_ext_clean)
    placed = 0
    for p in candidates_ext_clean:
        if placed >= ext_clean_int_bad_need:
            break
        if p.contradiction_kind:
            continue
        p.contradiction_kind = "ext-clean-int-bad"
        # 外部干净 · 内部埋异常
        p.signal_bias = "clean" if p.tier in ("medium",) else "mixed"
        if not p.anomaly_hints:
            p.anomaly_hints = rng.choice([
                ["inflow_drop"],
                ["concentration", "overdue"],
                ["circular"],
            ])
        placed += 1

    return profiles


if __name__ == "__main__":
    ps = generate_profiles()
    by_tier: dict[str, int] = {}
    by_contra: dict[str, int] = {}
    for p in ps:
        by_tier[p.tier] = by_tier.get(p.tier, 0) + 1
        if p.contradiction_kind:
            by_contra[p.contradiction_kind] = by_contra.get(p.contradiction_kind, 0) + 1
    print("tier:", by_tier)
    print("contradiction:", by_contra)
    print("sample:", ps[0])
