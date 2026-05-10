# -*- coding: utf-8 -*-
"""agent_riskctrl.demo — Phase B.2 ALL IN reframe (2026-05-10).

PM 真意: 演示 ≠ 预先烤好的 KS / 样本数答案 · 演示 = 用优质内部 mock 输入 (loans.csv)
跑 **真后端 pipeline** (LLM dsl_gen + 确定性 backtest) · 真返结果.

旧实现 (Phase A worker-A4 · 2026-04-29 fixture loader · scenarios/*.json) 已废弃 ·
违反反 5 原则 §3.5 (答案给嘴边) + dispatch B.2 红线 (禁用 workspace/<x>/scenarios/easy.json 等).

新形态:
  · DEMO_SEEDS 仅含输入 (strategy_intent + csv_path + label) · 不含 KS / 通过率 / 坏账率 等结果
  · /api/riskctrl/demo/run 收 seed_id → 真跑 dsl_gen + backtest → 真返结果
  · 不再有 fixture-driven 输出
"""
from __future__ import annotations

from typing import TypedDict


class RiskctrlDemoSeed(TypedDict):
    """Demo input seed · 仅输入 · 严格不含答案字段 (per dispatch B.2 §3.5)."""

    seed_id: str
    label: str
    strategy_intent: str  # 自然语言策略意图 · 喂给 LLM dsl_gen
    csv_path: str  # 历史样本 CSV 相对路径 · 喂给 backtest engine
    difficulty: str  # 难度档 (反 5 原则 §3.5 难度分层 · 仅供前端展示 · 不影响计算)


# Phase B.2 三档优质 input seed (反 5 原则 §3.5 难度分层 · 内部 mock 输入)
# csv_path 全指向同一份真实 mock loans.csv (7500 行 · MAX_ROWS=50000 上限内)
# 不同 seed 的差异在 strategy_intent · 不在结果数据 · 结果由 LLM + 真 backtest 算
DEMO_SEEDS: tuple[RiskctrlDemoSeed, ...] = (
    {
        "seed_id": "credit_v15",
        "label": "新客首贷 v1.5 · 高负债 + 新成立企业",
        "strategy_intent": (
            "对新客户首贷场景: 负债率 > 80% 直接拒绝 · "
            "成立年限 < 1 年转人工复核 · 当前逾期 ≥ 1 笔直接拒绝"
        ),
        "csv_path": "data/mock/agent2-samples/loans.csv",
        "difficulty": "简单",
    },
    {
        "seed_id": "aml_kyc",
        "label": "AML/KYC v2.3 · 大额异常 + 跨省高频",
        "strategy_intent": (
            "针对反洗钱场景: 月内大额借记 ≥ 5 笔转人工 · "
            "近一月跨省交易 ≥ 3 次转人工 · 月余额波动率 > 0.5 转人工"
        ),
        "csv_path": "data/mock/agent2-samples/loans.csv",
        "difficulty": "中等",
    },
    {
        "seed_id": "fraud_high",
        "label": "欺诈拦截 v0.7 · 多担保 + 高频查询",
        "strategy_intent": (
            "欺诈高风险拦截: 近一年担保 ≥ 3 次直接拒绝 · "
            "近三个月征信查询 ≥ 5 次转人工 · 近一年逾期 ≥ 2 次直接拒绝"
        ),
        "csv_path": "data/mock/agent2-samples/loans.csv",
        "difficulty": "极端",
    },
)


def list_seeds() -> list[dict[str, str]]:
    """枚举可用 demo seed · 给前端 dropdown 用 (含 difficulty 标签)."""
    return [
        {
            "seed_id": s["seed_id"],
            "label": s["label"],
            "difficulty": s["difficulty"],
            "strategy_intent": s["strategy_intent"],
            "csv_path": s["csv_path"],
        }
        for s in DEMO_SEEDS
    ]


def get_seed(seed_id: str) -> RiskctrlDemoSeed | None:
    """按 seed_id 查找 · 找不到返 None (caller 自行 404)."""
    for s in DEMO_SEEDS:
        if s["seed_id"] == seed_id:
            return s
    return None


VALID_SEED_IDS: tuple[str, ...] = tuple(s["seed_id"] for s in DEMO_SEEDS)


# ============================================================================
# 向下兼容 shim · 旧 import 路径 (Phase A) · 不破其他 caller
# ============================================================================

VALID_SCENARIOS = VALID_SEED_IDS  # legacy alias · 仅留为防止 grep miss


def list_scenarios() -> list[dict[str, str]]:
    """Legacy alias · 等价于 list_seeds() 但只返 (key, label) 双字段 (旧前端 dropdown 形态)."""
    return [{"key": s["seed_id"], "label": s["label"]} for s in DEMO_SEEDS]
