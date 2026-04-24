"""
Task C · 外部信号流 external-signals/<client_id>.md 生成器。

每家客户一份 md · 近 12 月（2025-05 ~ 2026-04）· 3-10 条事件。

信号类型：舆情 / 工商变更 / 司法 / 行业事件（四源混合）
分布（对照 onboarding §2 Task C）：
  clean     3-4 条 干净（奖项 / 新签合同 / 白名单 / 展会）
  mixed     3-6 条 中性为主 + 1-2 条 中性偏负面
  negative  5-8 条 偏负面（工商变更 + 中小额诉讼 + 行业负面 · 尚未失信）
  crisis    6-10 条 密集高风险（失信被执/限消/股权冻结 ≥ 1 + 股东变更 +
            多方起诉）

"合理矛盾" 硬线：profiles.contradiction_kind 驱动部分客户矛盾注入 ≥ 10 家
  ext-clean-int-bad：外部干净（clean/mixed）· 内部流水异常（Task B 已埋）
  ext-bad-int-ok   ：外部 negative/crisis · 内部流水健康（Task B 已跳异常）

零答案硬线：见 onboarding §2 Task C "零答案字段红线" —— md 不出现任何
反 5 原则 §1 盲测法禁止的标注字段；不写 "这是高风险客户，Agent4 应判红"
这类元注释；读者只能看到"时间线事件描述"，交叉判断全留给 Agent4。
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

from profiles import Profile, generate_profiles


WINDOW_START = date(2025, 5, 1)
WINDOW_END = date(2026, 4, 30)


MEDIA_SOURCES = [
    "财新网",
    "每经网",
    "21 世纪经济报道",
    "中国基金报",
    "证券时报",
    "经济观察报",
    "第一财经",
    "新华财经",
    "界面新闻",
    "证券日报",
]


COURT_SUFFIXES = [
    "人民法院",
    "中级人民法院",
    "基层人民法院",
]


REGULATOR_TEMPLATES = [
    "国家金融监督管理总局{prov}监管分局",
    "{city}市场监督管理局",
    "{city}税务局",
    "{prov}海关",
    "{city}生态环境局",
    "{prov}发改委",
    "{city}工业和信息化局",
    "{city}应急管理局",
]


POSITIVE_EVENTS = [
    ("行业奖项", "入选{prov}省制造业高质量发展典型案例", "舆情"),
    ("白名单入选", "通过{prov}省专精特新「小巨人」企业复核评审", "舆情"),
    ("新签合同", "与头部客户完成年度框架采购签约，合同金额较去年同比增长", "舆情"),
    ("政府扶持", "获{city}市「揭榜挂帅」重点项目专项资金支持", "舆情"),
    ("行业展会", "参展{prov}省国际{industry}产业博览会并达成意向订单", "舆情"),
    ("绿色制造", "通过 ISO 14001 环境管理体系再认证", "舆情"),
    ("技术突破", "自主研发项目通过省级科技成果评价", "舆情"),
    ("资质更新", "质量管理体系认证证书顺利续期", "舆情"),
    ("合规表彰", "列入{city}市纳税信用 A 级企业公示名单", "舆情"),
    ("合作升级", "与科研院所签订产学研战略合作协议", "舆情"),
]


NEUTRAL_GSHANG_EVENTS = [
    ("股东增资", "股东完成注册资本增资变更，注册资本由 {cap_from} 增至 {cap_to}", "工商变更"),
    ("法人变更", "法定代表人由 {legal_from} 变更为 {legal_to}", "工商变更"),
    ("经营范围", "经营范围新增 {new_biz} 等相关条目", "工商变更"),
    ("地址变更", "住所由 {addr_from} 变更至 {addr_to}", "工商变更"),
    ("董事调整", "董事会成员变更备案，新增 {new_director} 任董事", "工商变更"),
    ("章程修订", "公司章程经股东会决议修订并办理备案", "工商变更"),
]


MINOR_NEGATIVE_EVENTS = [
    ("小额诉讼", "因一笔{amount}万元购销合同纠纷作为{role}被{court}受理立案", "司法"),
    ("经营异常提示", "因{reason}被列入经营异常名录提示（{days}日内完成整改移出）", "工商变更"),
    ("投诉舆情", "在{platform}出现涉及售后服务的客户投诉帖", "舆情"),
    ("监管提醒", "在{reg} {year}年行业自查中被列入关注名单（已整改）", "行业事件"),
    ("税务提醒", "因{tax_item}被{city}税务局发出税务风险提示函", "行业事件"),
]


NEGATIVE_EVENTS = [
    ("股东减资", "股东决议减少注册资本 {down_pct}%，经债权人公告程序办理", "工商变更"),
    ("法人变更", "短期内法定代表人先后变更两次，决策层稳定性受到关注", "工商变更"),
    ("多起诉讼", "近期有 {n} 起买卖合同纠纷被{court}立案，涉及金额 {amount} 万元", "司法"),
    ("被列异常", "因未按期公示年度报告被{city}市场监督管理局列入经营异常名录", "工商变更"),
    ("行业下行", "所在{industry}行业在 {year} 年 {quarter} 季度出现产能过剩和价格明显回落", "行业事件"),
    ("关联方风险", "疑似关联企业「{related}」被行业媒体报道发生欠薪和停产", "舆情"),
    ("监管处罚", "因{violation}被{reg}作出警告并处罚款 {fine} 万元", "行业事件"),
    ("原材料波动", "上游核心原材料{material}价格季度内波动超过 {vol}%，经营成本承压", "行业事件"),
    ("供应商纠纷", "与主要供应商因结算周期争议多次协商未果，涉诉预期升高", "司法"),
]


CRISIS_EVENTS = [
    ("失信被执", "被{court}纳入失信被执行人名单，未履行义务金额 {amount} 万元", "司法"),
    ("限制消费", "法定代表人 {legal} 被{court}采取限制消费措施", "司法"),
    ("股权冻结", "实际控制人持有的 {pct}% 股权被{court}裁定冻结", "司法"),
    ("刑事立案", "因{crime}相关线索，{prov}公安机关已立案侦查（经侦介入）", "司法"),
    ("重大诉讼", "涉及 {n} 起金融借款合同纠纷集中爆发，累计金额 {amount} 万元以上", "司法"),
    ("工商警示", "因{severe_reason}被{city}市场监督管理局列入严重违法失信企业名单", "工商变更"),
    ("股东大变动", "实际控制人变更，原控股股东将 {pct}% 股权对外质押", "工商变更"),
    ("行业雷区", "所在细分行业多家龙头公司近期集中出现债务违约和停产传闻", "舆情"),
    ("媒体调查", "多家主流财经媒体发表调查报道，关注其关联交易和现金流匹配度", "舆情"),
    ("产品召回", "因产品质量被{reg}责令批次性召回，召回规模覆盖多省经销渠道", "行业事件"),
    ("吊销预警", "被提示可能被吊销营业执照的风险事件在{prov}工商系统公示", "工商变更"),
    ("贷款违约", "在多家同业被列入风险分类下调观察名单", "舆情"),
]


LEGAL_NAMES = [
    "王建国", "李海涛", "张云鹏", "陈子昂", "刘彦成", "周明达", "吴天翊",
    "赵景辉", "许文渊", "孙博远", "胡昌盛", "郑雨昊", "谢鸿飞", "何承宇",
    "杨岚山", "林清泓", "黄炎午", "徐承泽",
]


def _fmt_date(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _spread_dates(rng: random.Random, n: int) -> list[date]:
    """在 12 月窗口里分散抽 n 个不同日期 · 均匀+扰动，避免集中在某周"""
    total_days = (WINDOW_END - WINDOW_START).days
    # 分段均分 · 每段内抽 1 个 offset
    dates: list[date] = []
    for i in range(n):
        seg_start = int(total_days * i / n)
        seg_end = int(total_days * (i + 1) / n)
        offset = rng.randint(seg_start, max(seg_start, seg_end - 1))
        dates.append(WINDOW_START + timedelta(days=offset))
    rng.shuffle(dates)
    return dates


def _format_body(template: str, rng: random.Random, p: Profile) -> str:
    # 填充 {slot}
    city = p.city
    city_bare = city[:-1] if city.endswith("市") else city  # "惠州市" → "惠州"，避免"惠州市市人民法院"
    prov = p.province.replace("省", "").replace("市", "").replace("自治区", "")
    industry = p.industry_l2
    subs = {
        "city": city,
        "prov": prov,
        "industry": industry,
        "cap_from": f"{rng.choice([500, 1000, 1500, 2000, 3000, 5000])} 万元",
        "cap_to": f"{rng.choice([1500, 3000, 5000, 8000, 10000])} 万元",
        "legal_from": rng.choice(LEGAL_NAMES),
        "legal_to": rng.choice(LEGAL_NAMES),
        "legal": rng.choice(LEGAL_NAMES),
        "new_biz": rng.choice([
            "机电设备销售", "新材料销售", "进出口业务", "技术服务与技术咨询",
            "数据处理和存储服务", "国内贸易代理",
        ]),
        "addr_from": f"{city}市原厂区",
        "addr_to": f"{city}市{rng.choice(['新园区', '开发区二期', '高新区北片', '工业邻里中心'])}",
        "new_director": rng.choice(LEGAL_NAMES),
        "amount": str(rng.choice([35, 80, 120, 240, 480, 860, 1200, 1800, 2400, 3600, 5000, 8000])),
        "role": rng.choice(["被告", "原告", "第三人"]),
        "court": f"{city_bare}市{rng.choice(COURT_SUFFIXES)}",
        "reason": rng.choice([
            "未按期报送年度报告", "登记住所无法联系", "未按规定公示即时信息",
            "超出经营范围业务未备案",
        ]),
        "days": str(rng.choice([30, 45, 60, 90])),
        "platform": rng.choice(["黑猫投诉", "行业论坛", "短视频平台"]),
        "reg": rng.choice([
            f"{prov}银行业协会自律巡查",
            f"{city}市场监督管理局",
            f"{prov}发改委行业办公室",
        ]),
        "year": str(rng.choice([2025, 2026])),
        "quarter": rng.choice(["一", "二", "三", "四"]),
        "tax_item": rng.choice(["增值税申报口径差异", "出口退税环节抽查", "企业所得税汇算清缴差异"]),
        "down_pct": str(rng.choice([20, 25, 30, 40])),
        "n": str(rng.choice([2, 3, 4, 5, 6, 8])),
        "related": f"{city}{rng.choice(['关联贸易', '关联实业', '关联供应链'])}有限公司",
        "violation": rng.choice([
            "生产安全隐患整改不及时", "广告宣传不规范", "环保排放超标",
            "计量器具未按规定校准",
        ]),
        "fine": str(rng.choice([5, 12, 20, 35, 60, 80])),
        "material": rng.choice(["铜", "铝", "钢材", "塑料粒子", "电子元件", "原油"]),
        "vol": str(rng.choice([18, 22, 30, 40, 55])),
        "pct": str(rng.choice([15, 20, 25, 30, 40, 50])),
        "crime": rng.choice(["合同欺诈", "非法吸收公众存款", "虚开增值税专用发票"]),
        "severe_reason": rng.choice([
            "连续 3 年未报送年报", "提交虚假材料取得登记",
        ]),
    }
    try:
        return template.format(**subs)
    except KeyError:
        return template


def _choose_source(rng: random.Random, kind: str, p: Profile) -> str:
    prov = p.province.replace("省", "").replace("市", "").replace("自治区", "")
    city = p.city
    city_bare = city[:-1] if city.endswith("市") else city
    if kind == "舆情":
        return rng.choice(MEDIA_SOURCES)
    if kind == "司法":
        return f"{city_bare}市{rng.choice(COURT_SUFFIXES)}"
    if kind == "工商变更":
        return rng.choice([
            f"{city}市场监督管理局",
            f"{prov}企业信用信息公示系统",
        ])
    if kind == "行业事件":
        return rng.choice([t.format(prov=prov, city=city) for t in REGULATOR_TEMPLATES])
    return "行业公开信息"


def _pick_events(rng: random.Random, p: Profile) -> list[tuple[str, str, str]]:
    """返回 [(title, kind, body_template), ...] 清单"""
    bias = p.signal_bias
    contra = p.contradiction_kind
    out: list[tuple[str, str, str]] = []

    if bias == "clean":
        n = rng.randint(3, 4)
        picks = rng.sample(POSITIVE_EVENTS, min(n, len(POSITIVE_EVENTS)))
        # clean 下可能点缀 1 条中性工商（如增资/董事调整 · 非敏感）
        if contra == "ext-clean-int-bad" and rng.random() < 0.4:
            picks.append(rng.choice([e for e in NEUTRAL_GSHANG_EVENTS if e[0] in ("股东增资", "董事调整")]))
        out.extend(picks)

    elif bias == "mixed":
        n = rng.randint(3, 6)
        positives = rng.sample(POSITIVE_EVENTS, min(rng.randint(1, 3), len(POSITIVE_EVENTS)))
        neutrals = rng.sample(NEUTRAL_GSHANG_EVENTS, rng.randint(1, 2))
        minors = rng.sample(MINOR_NEGATIVE_EVENTS, rng.randint(0, 2))
        all_opts = positives + neutrals + minors
        rng.shuffle(all_opts)
        out.extend(all_opts[:n])

    elif bias == "negative":
        n = rng.randint(5, 8)
        negs = rng.sample(NEGATIVE_EVENTS, min(rng.randint(3, 5), len(NEGATIVE_EVENTS)))
        neutrals = rng.sample(NEUTRAL_GSHANG_EVENTS, rng.randint(1, 2))
        minors = rng.sample(MINOR_NEGATIVE_EVENTS, rng.randint(1, 2))
        # 小概率夹 1 条正面（体现真实信息噪声）
        extras = [rng.choice(POSITIVE_EVENTS)] if rng.random() < 0.4 else []
        all_opts = negs + neutrals + minors + extras
        rng.shuffle(all_opts)
        out.extend(all_opts[:n])

    elif bias == "crisis":
        n = rng.randint(6, 10)
        # 至少 1 条 crisis（失信被执/限消/股权冻结 之一）
        crisis_core = [e for e in CRISIS_EVENTS if e[0] in ("失信被执", "限制消费", "股权冻结")]
        mandatory = [rng.choice(crisis_core)]
        other_crises = rng.sample(
            [e for e in CRISIS_EVENTS if e not in mandatory],
            rng.randint(2, 4),
        )
        negs = rng.sample(NEGATIVE_EVENTS, rng.randint(1, 3))
        neutrals = rng.sample(NEUTRAL_GSHANG_EVENTS, rng.randint(1, 2))
        # 危机场景仍夹 1 条正面记录（真实语境常见，如"虽曾获奖但已爆雷"）
        extras = [rng.choice(POSITIVE_EVENTS)] if rng.random() < 0.35 else []
        all_opts = mandatory + other_crises + negs + neutrals + extras
        rng.shuffle(all_opts)
        out.extend(all_opts[:n])

    else:
        # 兜底 · 按 mixed 走
        out.extend(rng.sample(POSITIVE_EVENTS, 3))

    # 限制 3-10 条
    if len(out) < 3:
        out.extend(rng.sample(POSITIVE_EVENTS, 3 - len(out)))
    if len(out) > 10:
        out = out[:10]
    return out


def _render_md(p: Profile, events: list[tuple[date, tuple[str, str, str]]]) -> str:
    header = (
        f"# {p.company_name}（{p.client_id}）· 外部信号时间线\n\n"
        f"> 舆情 / 司法 / 工商 / 行业监管四源拼接 · 近 12 月（{WINDOW_START} ~ {WINDOW_END}）· 每条出处注明。\n\n"
    )
    parts: list[str] = [header]
    # 事件按日期降序展示（近 → 远）
    events_sorted = sorted(events, key=lambda x: x[0], reverse=True)
    rng_local = random.Random(20260424_100 + int(p.client_id[2:]))
    for d, (title, body_tpl, kind) in events_sorted:
        body = _format_body(body_tpl, rng_local, p)
        source = _choose_source(rng_local, kind, p)
        parts.append(f"## {_fmt_date(d)} · {kind} · {title}\n\n{body}。\n\n出处：{source}\n\n---\n\n")
    return "".join(parts).rstrip() + "\n"


def _write_for_profile(p: Profile, out_path: Path) -> None:
    rng = random.Random(20260424_200 + int(p.client_id[2:]))
    evs = _pick_events(rng, p)
    dates = _spread_dates(rng, len(evs))
    events = list(zip(dates, evs))
    text = _render_md(p, events)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "external-signals"
    out_dir.mkdir(parents=True, exist_ok=True)
    profiles = generate_profiles()
    total_events = 0
    for p in profiles:
        _write_for_profile(p, out_dir / f"{p.client_id}.md")
        text = (out_dir / f"{p.client_id}.md").read_text(encoding="utf-8")
        total_events += text.count("\n## ")
    print(f"wrote {len(profiles)} md files · total_events={total_events}")


if __name__ == "__main__":
    main()
