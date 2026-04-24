"""
Task B · 内部交易流水 transactions/AP<id>.csv 生成器。

每家客户一份 CSV · 窗口 2024-05 → 2026-04（24 月）· 日级（YYYY-MM-DD）。

五列：date, amount(元), type, counterparty, note

规模锚定：
  - 小型（营收 800-6000 万） → 月均 inflow 70-500 万，outflow 约 70-85%
  - 中型（6000-30000 万）    → 月均 inflow 500-2500 万
  - 大型（30000-200000 万）  → 月均 inflow 2500-17000 万

异常模式（profiles.anomaly_hints 触发 · 数字化植入 · **绝不**落 type 外标注）：
  - inflow_drop   近 3 月 inflow 均值 < 12 月基线 60%
  - concentration 近 3 月单一对手方占比 > 80%
  - overdue       1-3 条 type=overdue
  - balance_spike 对敲：大额 outflow 后 1-3 日内大额 inflow（counterparty 不同）
  - circular      balance_spike 多次重复
  - seasonal      Jan/Feb 春节低谷 -40%，Nov/Dec 年末冲量 +25%（正常波动）

命名：主 CSV 即 `transactions/AP001.csv` ... 列顺序一致。

零答案硬线：见 onboarding §2 Task B "零答案字段" —— 异常只通过金额/时间/对手
方关系体现，不添加任何元数据标注列。
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from profiles import Profile, generate_profiles


# 窗口起止（近 24 月）
WINDOW_START_Y, WINDOW_START_M = 2024, 5
WINDOW_END_Y, WINDOW_END_M = 2026, 4


# 月度基线（单位：元）· 按 (scale, 倍率) 映射营收量级下的月度 inflow 中位
SCALE_MONTHLY_INFLOW = {
    "小型": (700_000, 4_800_000),    # 70-480 万
    "中型": (5_000_000, 24_000_000),  # 500-2400 万
    "大型": (25_000_000, 160_000_000), # 2500-16000 万
}


def _month_iter() -> list[tuple[int, int]]:
    out = []
    y, m = WINDOW_START_Y, WINDOW_START_M
    while (y, m) <= (WINDOW_END_Y, WINDOW_END_M):
        out.append((y, m))
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


MONTHS = _month_iter()  # 24 个


def _season_factor(mon: int) -> float:
    # 季节性：春节低谷 / 年末冲量 / 其余正常
    if mon in (1, 2):
        return 0.72
    if mon in (11, 12):
        return 1.22
    if mon in (7, 8):
        return 0.95
    return 1.0


def _round_amount(x: float) -> int:
    # 金额舍入到合理颗粒：小额百元、中额千元、大额万元
    if x < 50_000:
        step = 100
    elif x < 500_000:
        step = 1_000
    elif x < 5_000_000:
        step = 10_000
    else:
        step = 100_000
    return max(int(round(x / step) * step), step)


def _iter_dates_for_month(y: int, m: int, rng: random.Random, count: int) -> list[date]:
    if m == 12:
        ndays = 31
    else:
        ndays = (date(y, m + 1, 1) - date(y, m, 1)).days
    days = rng.sample(range(1, ndays + 1), min(count, ndays))
    days.sort()
    return [date(y, m, d) for d in days]


def _extended_counterparties(rng: random.Random, p: Profile) -> tuple[list[str], list[str]]:
    """主对手 3-5 + 残留 3-6"""
    tops = list(p.top_counterparties)
    # 最多 5 个主对手
    if len(tops) > 5:
        tops = tops[:5]
    # 补齐到 3
    while len(tops) < 3:
        tops.append(f"{p.city}杂项客户{len(tops) + 1}")
    # 残留池（低频小额）
    city = p.city
    misc_pool = [
        f"{city}税务局",
        f"{city}社保中心",
        f"{city}工商银行",
        f"{city}物业服务",
        f"{city}电力公司",
        f"{city}燃气服务",
        f"{city}自来水公司",
        f"{city}劳务派遣",
        f"{city}办公耗材",
        f"{city}广告设计",
        f"{city}差旅报销",
        f"{p.industry_l2}协会会费",
        f"{city}快递服务",
    ]
    rng.shuffle(misc_pool)
    misc = misc_pool[: rng.randint(4, 7)]
    return tops, misc


def _write_for_profile(p: Profile, out_path: Path) -> None:
    # 用 client_id 数字部分做确定性 seed · 避免 Python hash randomization 影响复现
    seed = 20260424_000 + int(p.client_id[2:])
    rng = random.Random(seed)
    tops, misc = _extended_counterparties(rng, p)
    min_m, max_m = SCALE_MONTHLY_INFLOW[p.scale]
    baseline = rng.uniform(min_m, max_m)

    # 收支比
    outflow_ratio = rng.uniform(0.68, 0.85)

    # 异常植入参数
    has_inflow_drop = "inflow_drop" in p.anomaly_hints
    has_concentration = "concentration" in p.anomaly_hints
    has_overdue = "overdue" in p.anomaly_hints
    has_spike = "balance_spike" in p.anomaly_hints
    has_circular = "circular" in p.anomaly_hints
    has_seasonal_only = ("seasonal" in p.anomaly_hints) and len(p.anomaly_hints) == 1

    rows: list[tuple[str, int, str, str, str]] = []
    n_months = len(MONTHS)

    # 预计算近 3 月 index · 用于触发异常
    last3_idx = {n_months - 3, n_months - 2, n_months - 1}

    # concentration 目标对手（近 3 月 > 80% 聚拢到一家）
    concentration_target = tops[0] if has_concentration else None

    # overdue slots
    overdue_slots = set()
    if has_overdue:
        overdue_count = rng.randint(1, 3)
        candidates = list(range(n_months - 8, n_months))  # 近 8 月挑 1-3 条
        for i in rng.sample(candidates, overdue_count):
            overdue_slots.add(i)

    # spike / circular 数量
    spike_count = 0
    if has_spike:
        spike_count = rng.randint(2, 4)
    if has_circular:
        spike_count += rng.randint(3, 6)

    spike_event_months: list[int] = []
    if spike_count:
        pool = list(range(6, n_months))  # 避开头 6 月，异常集中在最近 18 月
        for idx in rng.sample(pool, min(spike_count, len(pool))):
            spike_event_months.append(idx)
    spike_event_months.sort()

    for m_idx, (y, m) in enumerate(MONTHS):
        season = _season_factor(m)
        recent = m_idx in last3_idx

        # 月度 inflow base
        month_infl = baseline * season * rng.uniform(0.88, 1.12)

        # inflow_drop：近 3 月打 40-55 折
        if has_inflow_drop and recent:
            month_infl *= rng.uniform(0.45, 0.60)

        # 汇总行 inflow 行数 · 中/大型多些
        if p.scale == "小型":
            n_inflow_rows = rng.randint(3, 6)
        elif p.scale == "中型":
            n_inflow_rows = rng.randint(5, 9)
        else:
            n_inflow_rows = rng.randint(7, 12)

        # 月度 outflow 预算
        month_outfl = month_infl * rng.uniform(outflow_ratio - 0.05, outflow_ratio + 0.05)
        if p.scale == "小型":
            n_outflow_rows = rng.randint(2, 5)
        elif p.scale == "中型":
            n_outflow_rows = rng.randint(4, 7)
        else:
            n_outflow_rows = rng.randint(5, 9)

        # 费用/其他
        n_fee_rows = rng.choice([0, 1, 1, 2])

        total_rows = n_inflow_rows + n_outflow_rows + n_fee_rows
        dates = _iter_dates_for_month(y, m, rng, total_rows)
        # dates 不一定够，兜底补
        while len(dates) < total_rows:
            dates.append(date(y, m, rng.randint(1, 28)))
        rng.shuffle(dates)

        # 分配 inflow 金额
        if concentration_target and recent:
            # 80%+ 聚到 concentration_target
            share = rng.uniform(0.82, 0.92)
            main_share = month_infl * share
            other_share = month_infl - main_share
        else:
            main_share = 0
            other_share = month_infl

        inflow_notes_templates = [
            "月末结款", "货款回款", "工程款回款", "项目回款", "结算款",
            "销售回款", "合同结款", "订单回款"
        ]

        # 主对手回款
        inflow_entries: list[tuple[int, str, str]] = []
        if concentration_target and recent and main_share > 0:
            # 近 3 月 · 单一对手 > 80% 月度占比
            chunks = rng.randint(1, 2)
            for _ in range(chunks):
                amt = _round_amount(main_share / chunks)
                note = rng.choice(inflow_notes_templates)
                inflow_entries.append((amt, concentration_target, note))
            # 剩余 1-2 条小额（仅 1-2 条，避免拉低浓度）
            n_rest = min(max(n_inflow_rows - chunks, 0), 2)
            if n_rest > 0 and other_share > 0:
                non_target_tops = [t for t in tops if t != concentration_target]
                if not non_target_tops:
                    non_target_tops = [f"{p.city}零星结算客户"]
                for _ in range(n_rest):
                    amt = _round_amount(other_share / n_rest)
                    cp = rng.choice(non_target_tops)
                    note = rng.choice(inflow_notes_templates)
                    inflow_entries.append((amt, cp, note))
        else:
            # 主对手 65-85% · 零散 15-35%
            main_pool = other_share * rng.uniform(0.65, 0.85)
            misc_pool_amt = other_share - main_pool
            n_main = max(n_inflow_rows - rng.randint(1, 2), 2)
            for i in range(n_main):
                amt = _round_amount(main_pool / n_main * rng.uniform(0.7, 1.3))
                cp = rng.choice(tops)
                note = rng.choice(inflow_notes_templates)
                inflow_entries.append((amt, cp, note))
            n_misc = n_inflow_rows - n_main
            # 零散 inflow 仍应来自客户侧（tops + 客户型零散）· 不混 misc（税务/社保/水电）
            small_client_pool = tops + [
                f"{p.city}小额客户回款", f"{p.city}零售客户结算", f"{p.city}线上订单结算"
            ]
            for _ in range(max(n_misc, 0)):
                amt = _round_amount(max(misc_pool_amt / max(n_misc, 1), 2000) * rng.uniform(0.5, 1.5))
                cp = rng.choice(small_client_pool)
                inflow_entries.append((amt, cp, rng.choice(inflow_notes_templates)))

        # 分配 outflow 金额
        outflow_notes = [
            "原料采购付款", "设备采购付款", "工资发放", "房租水电", "税费缴纳",
            "物流运费", "外协加工", "运营费用", "供应商货款", "出口押汇偿还"
        ]
        outflow_entries: list[tuple[int, str, str]] = []
        supplier_pool = [f"{p.city}{p.industry_l2}原料供应", f"{p.city}物流运输有限公司",
                         f"{p.city}设备维保", f"{p.city}包装制品", f"{p.city}外协加工"]
        supplier_pool.extend(misc[:2])
        for _ in range(n_outflow_rows):
            amt = _round_amount(month_outfl / n_outflow_rows * rng.uniform(0.5, 1.5))
            cp = rng.choice(supplier_pool)
            outflow_entries.append((amt, cp, rng.choice(outflow_notes)))

        # 费用/其他
        fee_entries: list[tuple[int, str, str]] = []
        for _ in range(n_fee_rows):
            amt = _round_amount(rng.uniform(800, 15_000))
            cp = rng.choice([
                f"{p.city}税务局", f"{p.city}社保中心", "银行手续费", "工商登记费",
                f"{p.city}物业服务", f"{p.city}电力公司", f"{p.city}自来水公司"
            ])
            fee_entries.append((amt, cp, rng.choice(["手续费", "税费", "工本费", "公共事业"])))

        # 逾期
        overdue_entries: list[tuple[int, str, str]] = []
        if m_idx in overdue_slots:
            amt = _round_amount(baseline * rng.uniform(0.02, 0.08))
            overdue_entries.append((amt, f"{p.city}工商银行", rng.choice(["贷款利息逾期", "本金逾期", "承兑汇票逾期"])))

        # spike/circular：在 spike_event_months 里 · 一对前后 1-3 天
        spike_entries: list[tuple[date, int, str, str, str]] = []  # 带 date 以便贴近
        if m_idx in spike_event_months:
            cp_a = rng.choice(misc + [f"{p.city}关联方往来{i}" for i in range(1, 4)])
            cp_b = rng.choice(misc + [f"{p.city}关联方往来{i}" for i in range(4, 8)])
            amt = _round_amount(month_infl * rng.uniform(0.6, 1.2))
            pivot_day = rng.randint(5, 22)
            d_out = date(y, m, pivot_day)
            d_in = d_out + timedelta(days=rng.randint(1, 3))
            if d_in.month != m:
                d_in = date(y, m, min(pivot_day + 1, 28))
            spike_entries.append((d_out, amt, "outflow", cp_a, "往来资金付款"))
            spike_entries.append((d_in, amt + rng.randint(-50_000, 50_000), "inflow", cp_b, "往来资金回款"))

        # 合并输出 · 分配 date
        pools: list[tuple[int, str, str, str]] = []
        pools.extend((a, "inflow", cp, n) for (a, cp, n) in inflow_entries)
        pools.extend((a, "outflow", cp, n) for (a, cp, n) in outflow_entries)
        pools.extend((a, "fee", cp, n) for (a, cp, n) in fee_entries)
        pools.extend((a, "overdue", cp, n) for (a, cp, n) in overdue_entries)
        need = len(pools)
        date_list = dates[:need]
        while len(date_list) < need:
            date_list.append(date(y, m, rng.randint(1, 28)))
        rng.shuffle(date_list)
        # 记录基线行
        for (a, t, cp, n), d in zip(pools, date_list):
            rows.append((d.strftime("%Y-%m-%d"), a, t, cp, n))
        # spike 行（带独立日期）
        for d, amt, t, cp, note in spike_entries:
            rows.append((d.strftime("%Y-%m-%d"), amt, t, cp, note))

    # 按日期排序
    rows.sort(key=lambda r: r[0])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["date", "amount", "type", "counterparty", "note"])
        for r in rows:
            w.writerow(r)


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "transactions"
    out_dir.mkdir(parents=True, exist_ok=True)
    profiles = generate_profiles()
    total_rows = 0
    for p in profiles:
        target = out_dir / f"{p.client_id}.csv"
        _write_for_profile(p, target)
        with target.open("r", encoding="utf-8") as f:
            total_rows += sum(1 for _ in f) - 1
    print(f"wrote {len(profiles)} files · total_rows={total_rows}")


if __name__ == "__main__":
    main()
