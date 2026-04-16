# -*- coding: utf-8 -*-
"""生成互联网贷款合规专项巡检场景的业务 Excel 数据。

运行：
    py demo_data/agent_compliance/scenarios/internet_loan/_build_data.py

输出：
    loans_q4.xlsx          100 条放款
    cooperations.xlsx      30 条合作
    models.xlsx            15 条模型上线
    scenario.json          场景配置 + 预埋违规清单
"""
from __future__ import annotations
import json
import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

HERE = Path(__file__).parent
random.seed(20260414)


# ============================================================
# 1. 放款台账（loans_q4.xlsx）— 100 条
# ============================================================

LOAN_HEADERS = [
    "放款单号", "客户ID", "放款日期", "放款金额(元)",
    "期限(月)", "贷款用途", "合作方", "还款状态",
]

# 预埋违规
PLANTED_LOANS: list[dict] = [
    # 严重 #1 期限超限
    {"放款单号": "LN20251108", "客户ID": "C5012", "放款日期": "2025-11-08",
     "放款金额(元)": 80000, "期限(月)": 18, "贷款用途": "个人消费",
     "合作方": "", "还款状态": "正常"},
    {"放款单号": "LN20251211", "客户ID": "C5089", "放款日期": "2025-12-11",
     "放款金额(元)": 120000, "期限(月)": 24, "贷款用途": "个人消费",
     "合作方": "", "还款状态": "正常"},
    # 严重 #4 额度超限
    {"放款单号": "LN20251021", "客户ID": "C5033", "放款日期": "2025-10-21",
     "放款金额(元)": 350000, "期限(月)": 12, "贷款用途": "个人消费",
     "合作方": "", "还款状态": "正常"},
    # 观察 #: 贷款用途可疑（按摸到"股票"算观察项）
    {"放款单号": "LN20251203", "客户ID": "C5066", "放款日期": "2025-12-03",
     "放款金额(元)": 50000, "期限(月)": 6, "贷款用途": "个人消费-股票投资",
     "合作方": "", "还款状态": "正常"},
]


def gen_loans(n=100):
    rows: list[dict] = list(PLANTED_LOANS)
    # 正常放款
    used_ids = {r["放款单号"] for r in rows}
    d0 = date(2025, 10, 1)
    i = 1
    while len(rows) < n:
        d = d0 + timedelta(days=random.randint(0, 90))
        lid = f"LN{d.strftime('%Y%m%d')}{i:02d}"
        if lid in used_ids:
            i += 1
            continue
        used_ids.add(lid)
        rows.append({
            "放款单号": lid,
            "客户ID": f"C{random.randint(4000, 5999)}",
            "放款日期": d.isoformat(),
            "放款金额(元)": random.choice([30000, 50000, 80000, 100000, 150000, 180000]),
            "期限(月)": random.choice([3, 6, 9, 12]),
            "贷款用途": random.choice(["个人消费", "日常生活", "家庭装修", "教育支出"]),
            "合作方": "",
            "还款状态": random.choice(["正常"] * 9 + ["逾期"]),
        })
        i += 1
    return rows


# ============================================================
# 2. 联合贷款（cooperations.xlsx）— 30 条
# ============================================================

COOP_HEADERS = [
    "合作单号", "合作方名称", "放款总额(元)", "本行出资(元)",
    "出资比例(%)", "合作日期", "合同状态",
]

# 严重 #3 出资比例不足
PLANTED_COOPS: list[dict] = [
    {"合作单号": "COOP202510007", "合作方名称": "XX小贷", "放款总额(元)": 5000000,
     "本行出资(元)": 750000, "出资比例(%)": 15.0, "合作日期": "2025-10-15",
     "合同状态": "生效中"},
    {"合作单号": "COOP202511003", "合作方名称": "YY消金", "放款总额(元)": 2000000,
     "本行出资(元)": 440000, "出资比例(%)": 22.0, "合作日期": "2025-11-05",
     "合同状态": "生效中"},
    # 一般缺陷 #: 合作清单超期未更新、文档不齐
    {"合作单号": "COOP202512015", "合作方名称": "ZZ金融", "放款总额(元)": 1500000,
     "本行出资(元)": 750000, "出资比例(%)": 50.0, "合作日期": "2025-12-20",
     "合同状态": "文档缺失"},
    # 观察 #: 出资比例刚好超过阈值
    {"合作单号": "COOP202510018", "合作方名称": "AA担保", "放款总额(元)": 1000000,
     "本行出资(元)": 310000, "出资比例(%)": 31.0, "合作日期": "2025-10-28",
     "合同状态": "生效中"},
]


def gen_coops(n=30):
    rows: list[dict] = list(PLANTED_COOPS)
    used = {r["合作单号"] for r in rows}
    d0 = date(2025, 10, 1)
    i = 20
    while len(rows) < n:
        d = d0 + timedelta(days=random.randint(0, 90))
        cid = f"COOP{d.strftime('%Y%m')}{i:05d}"
        if cid in used:
            i += 1
            continue
        used.add(cid)
        total = random.choice([500000, 1000000, 2000000, 3000000])
        ratio = round(random.uniform(35, 65), 1)
        rows.append({
            "合作单号": cid,
            "合作方名称": random.choice(["甲小贷", "乙消金", "丙担保", "丁金融"]),
            "放款总额(元)": total,
            "本行出资(元)": int(total * ratio / 100),
            "出资比例(%)": ratio,
            "合作日期": d.isoformat(),
            "合同状态": "生效中",
        })
        i += 1
    return rows


# ============================================================
# 3. 风控模型上线（models.xlsx）— 15 条
# ============================================================

MODEL_HEADERS = [
    "模型单号", "模型名称", "上线日期",
    "独立验证状态", "上线报送日期",
    "审批人", "模型类型",
]

PLANTED_MODELS: list[dict] = [
    # 严重 #2 模型未独立验证
    {"模型单号": "ML20251015", "模型名称": "反欺诈评分卡 v3", "上线日期": "2025-10-15",
     "独立验证状态": "未验证", "上线报送日期": "2025-10-18",
     "审批人": "王某", "模型类型": "反欺诈"},
    # 严重 #5 未 5 日内上报
    {"模型单号": "ML20251122", "模型名称": "行为评分模型 v2", "上线日期": "2025-11-22",
     "独立验证状态": "已验证", "上线报送日期": "2025-12-10",
     "审批人": "李某", "模型类型": "行为评分"},
    # 一般缺陷 #: 监测缺失
    {"模型单号": "ML20251009", "模型名称": "准入评分 v4", "上线日期": "2025-10-09",
     "独立验证状态": "已验证", "上线报送日期": "2025-10-11",
     "审批人": "张某", "模型类型": "准入", "监测频率": "年度"},
]


def gen_models(n=15):
    rows: list[dict] = list(PLANTED_MODELS)
    used = {r["模型单号"] for r in rows}
    d0 = date(2025, 10, 1)
    i = 40
    while len(rows) < n:
        d = d0 + timedelta(days=random.randint(0, 90))
        mid = f"ML{d.strftime('%Y%m%d')}"
        if mid in used:
            mid = f"ML{d.strftime('%Y%m%d')}{i:02d}"
        if mid in used:
            i += 1
            continue
        used.add(mid)
        report_d = d + timedelta(days=random.randint(1, 4))  # 正常 5 日内
        rows.append({
            "模型单号": mid,
            "模型名称": random.choice(["准入评分 v{}", "额度评分 v{}", "反欺诈 v{}",
                                   "定价模型 v{}", "贷后预警 v{}"]).format(random.randint(1, 5)),
            "上线日期": d.isoformat(),
            "独立验证状态": "已验证",
            "上线报送日期": report_d.isoformat(),
            "审批人": random.choice(["张某", "王某", "李某", "赵某"]),
            "模型类型": random.choice(["准入", "额度", "定价", "反欺诈", "行为评分"]),
        })
        i += 1
    return rows


# ============================================================
# 写 Excel
# ============================================================

def write_xlsx(filename: str, headers: list[str], rows: list[dict]):
    wb = Workbook()
    ws = wb.active
    ws.title = filename.split(".")[0]
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h, "") for h in headers])
    # 列宽
    for i, h in enumerate(headers):
        ws.column_dimensions[chr(ord("A") + i)].width = max(14, len(h) + 4)
    out = HERE / filename
    wb.save(str(out))
    print(f"[ok] {out.relative_to(HERE.parent.parent.parent)}  rows={len(rows)}")


def main():
    loans = gen_loans(100)
    coops = gen_coops(30)
    models = gen_models(15)

    write_xlsx("loans_q4.xlsx", LOAN_HEADERS, loans)
    write_xlsx("cooperations.xlsx", COOP_HEADERS, coops)
    write_xlsx("models.xlsx", MODEL_HEADERS, models)

    # 写场景清单
    scenario = {
        "scenario_id": "internet_loan",
        "title": "互联网贷款合规专项巡检",
        "description": "3 份政策 + 100 条放款 + 30 条合作 + 15 条模型，预埋 5 严重 8 一般 12 观察",
        "policies": [
            "policy_online_loan.md",
            "policy_supplement.md",
        ],
        "internal_rules": [
            "internal_policy.md",
        ],
        "business_data": [
            "loans_q4.xlsx",
            "cooperations.xlsx",
            "models.xlsx",
        ],
        "expected_counts": {
            "rules": 68,     # 50 政策 + 18 内部
            "events": 145,   # 100 + 30 + 15
            "matrix_cells": 68 * 145,  # 9860
            "severe": 5,
            "normal": 8,
            "observation": 12,
        },
        "planted_violations": {
            "severe": [
                {
                    "id": "V-S-1", "type": "个人消费贷款期限超限",
                    "rule_hint": "个人消费贷款期限不得超过一年",
                    "article_hint": "政策1·第6条 / 本行制度·第9条",
                    "events": ["LN20251108", "LN20251211"],
                },
                {
                    "id": "V-S-2", "type": "风控模型未独立验证",
                    "rule_hint": "风控模型上线前必须独立验证",
                    "article_hint": "政策1·第18条",
                    "events": ["ML20251015"],
                },
                {
                    "id": "V-S-3", "type": "联合贷款出资比例不足",
                    "rule_hint": "单笔出资比例不得低于 30%",
                    "article_hint": "政策2·第3条 / 本行制度·第11条",
                    "events": ["COOP202510007", "COOP202511003"],
                },
                {
                    "id": "V-S-4", "type": "个人消费贷款额度超限",
                    "rule_hint": "单户授信额度不得超过 20 万元",
                    "article_hint": "政策1·第8条 / 本行制度·第8条",
                    "events": ["LN20251021"],
                },
                {
                    "id": "V-S-5", "type": "模型上线超时未报送",
                    "rule_hint": "模型上线 5 个工作日内书面报送",
                    "article_hint": "本行制度·第12条",
                    "events": ["ML20251122"],
                },
            ],
            "normal": 8,
            "observation": 12,
        },
    }

    scenario_json = HERE / "scenario.json"
    scenario_json.write_text(
        json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ok] {scenario_json.name}")


if __name__ == "__main__":
    main()
