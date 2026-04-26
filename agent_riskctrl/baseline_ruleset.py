# -*- coding: utf-8 -*-
"""Agent2 风控 · baseline_ruleset 对照组 (P3F 轨 8b Task B)

固定 5 条业界常见的简单阈值规则 · **不随样本变化** · 作为 KS 改进 (ks_improvement) 对照基线。

字段集对齐 data/mock/agent2-samples/loans.csv (data-foundation 轨 8a 落):
  credit_score / debt_ratio / past_overdue_count_1y / current_overdue_count / monthly_income_cny

KS 计算约定:
  - label binarization: days_past_due >= BAD_DPD_THRESHOLD (默认 30) → bad=1, else good=0
  - 每条记录 risk score: rule action 映射 reject=2 / manual_review=1 / approve|none=0
  - KS = max |F_bad(s) - F_good(s)| over score CDF (调 metrics.calculate_ks)

为何用 30 DPD 而非 90 DPD:
  零售 retail 行业惯例 30+ DPD 视作 problem loan; loans.csv 难度档 60/20/15/5 → 30+ 占 20%
  → 双类各有足够样本 KS 数值有意义; 90+ 仅 5% bad rate 在 KS 上数值偏弱.
  阈值由 BAD_DPD_THRESHOLD 控制 · 调用方可覆盖.

历史溯源: Phase-3-Final 轨 8b · 解决 Agent2 评估 ks_improvement / rule_interpretability 5/10 PARTIAL pending.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .metrics import calculate_ks
from .rule_engine import (
    RuleCondition,
    RuleSet,
    StrategyRule,
    apply_ruleset,
)


BASELINE_VERSION = "v1.0"
BASELINE_DESCRIPTION = (
    "Agent2 baseline_ruleset · 5 业界常见简单阈值规则 · 不随样本变化 · "
    "ks_improvement 对照基线 (P3F 轨 8b)"
)

# 默认 bad 标签阈值 — 30+ DPD 零售 problem loan 惯例
BAD_DPD_THRESHOLD = 30
LABEL_COLUMN_DEFAULT = "days_past_due"

# Action → 风险分数 (KS y_pred)
_ACTION_RISK_SCORE = {
    "reject": 2,
    "manual_review": 1,
    "approve": 0,
    "none": 0,
}


# ---------------------------------------------------------------------------
# 5 条硬编 baseline 规则 (固定 · 不随样本变 · CA-B3-6)
#   priority 1 最高 · 命中即停 (apply_ruleset 实现)
# ---------------------------------------------------------------------------

BASELINE_RULE_SPECS: list[dict[str, Any]] = [
    {
        "rule_id": "BL_R001",
        "name": "当前已逾期直接拒绝",
        "description": "当前 overdue 笔数 > 0 视为高危 · 业界一票否决",
        "conditions": [
            {"field": "current_overdue_count", "operator": ">", "value": 0},
        ],
        "action": "reject",
        "priority": 1,
    },
    {
        "rule_id": "BL_R002",
        "name": "近 1 年多次逾期拒绝",
        "description": "过去 12 个月逾期 ≥ 3 次 · 还款意愿/能力存疑",
        "conditions": [
            {"field": "past_overdue_count_1y", "operator": ">=", "value": 3},
        ],
        "action": "reject",
        "priority": 2,
    },
    {
        "rule_id": "BL_R003",
        "name": "低征信分拒绝",
        "description": "央行征信分 < 600 · 普惠 retail 通用准入下限",
        "conditions": [
            {"field": "credit_score", "operator": "<", "value": 600},
        ],
        "action": "reject",
        "priority": 3,
    },
    {
        "rule_id": "BL_R004",
        "name": "高负债率人工复核",
        "description": "负债率 > 0.7 偿付能力承压 · 转人工 (对私样本无该字段则不命中)",
        "conditions": [
            {"field": "debt_ratio", "operator": ">", "value": 0.7},
        ],
        "action": "manual_review",
        "priority": 4,
    },
    {
        "rule_id": "BL_R005",
        "name": "低月收入拒绝",
        "description": "月收入 < 3000 元 · 还款来源不稳",
        "conditions": [
            {"field": "monthly_income_cny", "operator": "<", "value": 3000},
        ],
        "action": "reject",
        "priority": 5,
    },
]


def get_baseline_ruleset() -> RuleSet:
    """返回 5 条 baseline DSL 规则 (RuleSet) · 每次调用结构一致."""
    rules = [
        StrategyRule(
            rule_id=spec["rule_id"],
            name=spec["name"],
            description=spec["description"],
            conditions=[
                RuleCondition(field=c["field"], operator=c["operator"], value=c["value"])
                for c in spec["conditions"]
            ],
            action=spec["action"],
            priority=spec["priority"],
        )
        for spec in BASELINE_RULE_SPECS
    ]
    return RuleSet(rules=rules, description=BASELINE_DESCRIPTION)


# ---------------------------------------------------------------------------
# KS 计算 · 单 ruleset
# ---------------------------------------------------------------------------


def _binarize_dpd(value: Any, threshold: int) -> int:
    try:
        return 1 if float(value) >= threshold else 0
    except (TypeError, ValueError):
        return 0


def _action_score(action: str) -> int:
    return _ACTION_RISK_SCORE.get(action, 0)


def compute_strategy_ks(
    df: pd.DataFrame,
    ruleset: RuleSet,
    label_column: str = LABEL_COLUMN_DEFAULT,
    bad_threshold: int = BAD_DPD_THRESHOLD,
) -> tuple[float, dict[str, Any]]:
    """对 df 跑 ruleset · 返回 (ks_value, meta).

    Args:
        df: pandas DataFrame · 必须含 label_column
        ruleset: 风控 RuleSet
        label_column: 监督信号列名 · 默认 'days_past_due'
        bad_threshold: bad 标签阈值 · DPD ≥ threshold 视 bad=1

    Returns:
        (ks, meta) ·
            ks ∈ [0,1] · df 为空或 label 缺失返回 (0.0, {...reason})
            meta = {n_records, n_pos, n_neg, action_dist, label_column, bad_threshold}
    """
    if df is None or len(df) == 0:
        return 0.0, {"reason": "empty_df"}
    if label_column not in df.columns:
        return 0.0, {
            "reason": f"label_column_missing:{label_column}",
            "available_columns": list(df.columns),
        }
    if not ruleset.rules:
        return 0.0, {"reason": "empty_ruleset"}

    records = df.to_dict(orient="records")
    hit_results = apply_ruleset(ruleset, records)

    actions = [r.get("action", "none") for r in hit_results]
    y_pred = [_action_score(a) for a in actions]
    y_true = [_binarize_dpd(rec.get(label_column), bad_threshold) for rec in records]

    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos

    if n_pos == 0 or n_neg == 0:
        return 0.0, {
            "reason": "single_class_label",
            "n_records": len(y_true),
            "n_pos": n_pos,
            "n_neg": n_neg,
            "bad_threshold": bad_threshold,
        }

    ks = calculate_ks(y_true, y_pred)

    action_dist: dict[str, int] = {}
    for a in actions:
        action_dist[a] = action_dist.get(a, 0) + 1

    return ks, {
        "n_records": len(y_true),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "action_dist": action_dist,
        "label_column": label_column,
        "bad_threshold": bad_threshold,
    }


# ---------------------------------------------------------------------------
# 对照组 · ks_baseline / ks_current / ks_improvement
# ---------------------------------------------------------------------------


def compare_with_baseline(
    df: pd.DataFrame,
    current_ruleset: RuleSet,
    label_column: str = LABEL_COLUMN_DEFAULT,
    bad_threshold: int = BAD_DPD_THRESHOLD,
) -> dict[str, Any]:
    """跑 baseline_ruleset + current_ruleset · 返回三项 KS + breakdown.

    Returns:
        {
            "ks_baseline": float,
            "ks_current": float,
            "ks_improvement": float,         # current - baseline
            "baseline_meta": {...},
            "current_meta": {...},
            "label_column": str,
            "bad_threshold": int,
            "baseline_version": "v1.0",
        }
    """
    baseline = get_baseline_ruleset()
    ks_baseline, bm = compute_strategy_ks(df, baseline, label_column, bad_threshold)
    ks_current, cm = compute_strategy_ks(df, current_ruleset, label_column, bad_threshold)

    return {
        "ks_baseline": round(ks_baseline, 4),
        "ks_current": round(ks_current, 4),
        "ks_improvement": round(ks_current - ks_baseline, 4),
        "baseline_meta": bm,
        "current_meta": cm,
        "label_column": label_column,
        "bad_threshold": bad_threshold,
        "baseline_version": BASELINE_VERSION,
    }
