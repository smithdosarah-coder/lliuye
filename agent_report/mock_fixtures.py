# -*- coding: utf-8 -*-
"""mock_fixtures — 预置演示场景 fixture 加载器.

策略:
  1. 优先从 D:\\刘野\\众安\\客户经理助理\\06_信贷报告助手\\ 加载真实文件
  2. 目录不存在时,使用本文件内嵌 stub(不崩)
  3. 预置 key:dingsheng_trade / zhangsan_restaurant

stub 字段尽量对齐 agent_credit/mock_data/corporate_profiles/*.json schema。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT_CANDIDATES = [
    Path(r"D:\刘野\众安\客户经理助理\06_信贷报告助手"),
]


# ---------------------------------------------------------------------------
# 内嵌 stub — 目录不存在时使用
# ---------------------------------------------------------------------------
_EMBEDDED_STUBS: dict[str, dict] = {
    "dingsheng_trade": {
        "profile_id": "corp_dingsheng_001",
        "company_name": "鼎盛商贸有限公司",
        "unified_credit_code": "91440000MAZZEXAMPLE",
        "industry": "F51-批发业",
        "establishment_date": "2018-03-15",
        "registered_capital": "1000",
        "employee_count": 42,
        "region": "广东省佛山市",
        "main_business": "建材批发与代理",
        "controller_name": "王某",
        "controller_share_pct": "80%",
        "business_line": "corporate",
        "financial_anchors": {
            "revenue_latest": 18000,
            "revenue_prev": 22000,
            "net_profit_latest": -420,
            "net_profit_prev": 350,
            "total_assets": 9600,
            "total_liabilities": 7680,
            "net_assets": 1920,
            "accounts_receivable": 4500,
            "inventory": 2200,
            "operating_cash_flow": -680,
            "short_term_borrowing": 4200,
            "ebitda": -180,
            "period": "2025年度",
        },
        "guarantee_info": {
            "type": "保证",
            "collateral": "无抵押",
            "collateral_value": 0,
            "collateral_type": "无",
            "guarantor": "法人连带保证(个人资产单一)",
        },
        "related_party_info": {
            "related_party_revenue_pct": 0.45,
            "related_party_txn_desc": "大量交易来自关联公司鼎盛地产,年度金额 8100 万,占营收 45%",
        },
        "existing_credit": {
            "total_approved": 800,
            "total_used": 800,
            "overdue_history": "2024 年曾出现 M1 逾期 1 次(已结清)",
        },
        "tax_rating": "C",
        "request": {
            "amount": 500,
            "purpose": "补充流动资金",
            "term_months": 12,
        },
        "chapters": {
            "chapter_1_background": "鼎盛商贸有限公司成立于 2018 年,注册资本 1000 万元,主营建材批发,近年受下游地产行业调整影响明显。",
            "chapter_2_operation": "公司 2025 年营收同比下滑 18%,主要客户为关联公司鼎盛地产,客户依赖度严重,回款周期拉长。",
            "chapter_3_finance": "资产负债率 80%,净利润亏损 420 万元,经营性现金流 -680 万元,速动比率仅 0.6,短期偿债压力突出。",
            "chapter_4_conclusion": "(待 Agent3 回填审批意见)",
        },
        "agent_outputs": {"agent6_report_json": None},
    },
    "zhangsan_restaurant": {
        "profile_id": "retail_zhangsan_001",
        "company_name": "张三餐饮个体工商户",
        "unified_credit_code": "92440000MBZZSTUB",
        "industry": "I6-餐饮业",
        "establishment_date": "2020-06-01",
        "registered_capital": "10",
        "employee_count": 8,
        "region": "广东省广州市",
        "main_business": "中式快餐连锁(2 家门店)",
        "controller_name": "张三",
        "controller_share_pct": "100%",
        "business_line": "inclusive",
        "financial_anchors": {
            "revenue_latest": 360,
            "revenue_prev": 320,
            "net_profit_latest": 48,
            "net_profit_prev": 40,
            "total_assets": 180,
            "total_liabilities": 60,
            "net_assets": 120,
            "accounts_receivable": 5,
            "inventory": 8,
            "operating_cash_flow": 52,
            "short_term_borrowing": 20,
            "ebitda": 62,
            "period": "2025年度",
        },
        "guarantee_info": {
            "type": "抵押",
            "collateral": "住宅一套",
            "collateral_value": 280,
            "collateral_type": "住宅",
            "guarantor": "配偶连带保证",
        },
        "related_party_info": {
            "related_party_revenue_pct": 0.0,
            "related_party_txn_desc": "无关联交易",
        },
        "existing_credit": {
            "total_approved": 50,
            "total_used": 30,
            "overdue_history": "无逾期记录",
        },
        "tax_rating": "B",
        "request": {
            "amount": 80,
            "purpose": "门店装修与设备升级",
            "term_months": 24,
        },
        "chapters": {
            "chapter_1_background": "张三于 2020 年在广州开办中式快餐个体户,现有 2 家门店,主要服务周边写字楼客群。",
            "chapter_2_operation": "2025 年营收 360 万元,同比增长 12.5%,客群稳定,翻台率健康。",
            "chapter_3_finance": "资产负债率 33%,净利率 13.3%,经营现金流 52 万元,现金流健康。",
            "chapter_4_conclusion": "(待 Agent3 回填审批意见)",
        },
        "agent_outputs": {"agent6_report_json": None},
    },
}


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def available_presets() -> list[str]:
    return sorted(_EMBEDDED_STUBS.keys())


def _try_load_from_disk(preset: str) -> Optional[dict]:
    """尝试从外部 fixture 目录加载 <preset>.json,未找到返回 None.

    Phase A worker-A4 V2 (codex audit cat 5 决议 · 2026-04-29):
      cat 5 (mock_fixtures.py:154-181 disk fixture else embedded stub fallback) 决议:
      **保留双层 fallback** (disk → embedded stub) · 理由:
        (1) `data/customer/<preset>/profile.json` 是客户脱敏样本进库路径 · 真实交付侧每个
            银行客户都会有自己的 fixture · 不可能全在代码里硬编 (反 5 原则 §3.4 脱敏再造).
        (2) 内嵌 stub (_EMBEDDED_STUBS) 是开发兜底 · 让 unit test / dev 环境无 fixture 时
            也能跑通主流程 · 与 demo/run scenarios JSON 不冲突 (后者是 演示数据 · 走
            data/mock/workspace/report/ · 命中 5 原则 §3.5 难度分层硬线).
      不删 disk fallback · 不删 embedded stub · cat 5 仅文档化 · 不需代码改动.
      详 commit message · WORKER-A4-REPORT-V2-DONE 第 4 项.
    """
    for root in FIXTURE_ROOT_CANDIDATES:
        if not root.exists():
            continue
        # 约定:根目录下有 fixtures/<preset>.json 或 <preset>/profile.json
        for candidate in (
            root / "fixtures" / f"{preset}.json",
            root / preset / "profile.json",
        ):
            if candidate.is_file():
                try:
                    return json.loads(candidate.read_text(encoding="utf-8"))
                except Exception:
                    continue
    return None


def load_preset_profile(preset: str) -> dict:
    """按 preset key 加载企业画像 dict.

    策略 (V2 codex audit cat 5 决议 · 2026-04-29):
      1) 先尝试磁盘 fixture (`data/customer/<preset>/profile.json` 等) · 命中即返
         · 这是客户脱敏样本进库路径 · 真实交付每个银行客户都会有自己的 fixture
      2) 失败或不存在 → 回退内嵌 stub (_EMBEDDED_STUBS) · 让 dev / test 不依赖文件系统
      3) 未知 preset → 默认 dingsheng_trade stub
    双层 fallback 保留 · 不删任一层 (cat 5 决议见 _try_load_from_disk docstring).
    """
    data = _try_load_from_disk(preset)
    if data is not None:
        return data
    return dict(_EMBEDDED_STUBS.get(preset) or _EMBEDDED_STUBS["dingsheng_trade"])


def sample_pending_questions(preset: str) -> list[dict]:
    """返回 1-2 个 stub 外因问题(V14-C Agent 正式接入前的占位)."""
    if preset == "zhangsan_restaurant":
        return [
            {
                "id": "q_ext_001",
                "section_id": "chapter_2_operation",
                "question": "近 3 个月周边是否有新开竞争门店?对客流有何影响?",
                "hint": "若有影响,请说明预计营收变动幅度(±%)",
                "input_type": "textarea",
            },
        ]
    # 默认场景
    return [
        {
            "id": "q_ext_001",
            "section_id": "chapter_2_operation",
            "question": "借款人下游地产行业调整的持续时间与应对措施?",
            "hint": "请说明已签订未交付订单规模、是否已与客户协商延期或替换客户",
            "input_type": "textarea",
        },
        {
            "id": "q_ext_002",
            "section_id": "chapter_3_finance",
            "question": "近 6 个月应收账款回收情况评分(1-5,1=很差,5=很好)",
            "hint": "请结合账龄结构给出判断",
            "input_type": "scale",
        },
    ]


def fallback_docx_path(outputs_dir: Path) -> Optional[Path]:
    """Mock 模式下返回一个历史生成的 docx,便于前端下载演示."""
    if not outputs_dir.exists():
        return None
    candidates = sorted(
        outputs_dir.glob("section_gen_test_*.docx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    any_docx = sorted(outputs_dir.glob("*.docx"),
                      key=lambda p: p.stat().st_mtime,
                      reverse=True)
    return any_docx[0] if any_docx else None


def downstream_handoff(preset: str) -> dict[str, str]:
    return {
        "credit": f"/credit?preset={preset}",
        "alert": f"/alert?preset={preset}",
        "compliance": f"/compliance?preset={preset}",
    }
