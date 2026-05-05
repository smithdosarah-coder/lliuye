# -*- coding: utf-8 -*-
"""agent_riskctrl.business_metrics — 业务指标双轨 (BE6.4).

CLAUDE.md §1 风险经理给行长汇报场景 · 数据科学家与业务方语言不通:

- **统计口径** (数据科学家): KS / AUC / FPR / TPR / PSI · 在 metrics.py
- **业务口径** (业务方): 通过率 / 坏账率 / 利润影响 / 拒绝量 · **本模块**

两轨同 commit ship · API /api/riskctrl/backtest done event 同时输出双轨 ·
前端业务面板可消费业务口径 · 数据面板可消费统计口径 · 行长拿"业务可读结论"
就行 (e.g. "新策略 vs 老策略: 通过率↓5pp · 坏账率↓2pp · 月利润影响 +120 万元").

设计:
  - **§3.1 确定性 Python**: 利润影响估算公式 verify-able · 不让 LLM 现场算
  - **§3.5 反 5 原则 #5**: 利率/净息差/坏账损失率参数当前 mock default ·
    后续接银行真口径 (per Sprint 4 配置文件 risk_economics.yaml)

利润影响公式 (per 行业惯例 简化版):
    profit ≈ 通过笔数 × 平均贷款金额 × (净息差 - 坏账率)
            - 拒绝笔数 × 平均贷款金额 × 机会成本率(可省)

  其中:
    净息差 (NIM): 默认 3.5% (国有大行口径) · `nim_default`
    坏账损失率 (LGD): 默认 60% (LGD * 实际坏账率 = 损失)
    机会成本率: 默认 0 (保守 · 拒绝即不发生)

Public surface:
  - ``BusinessMetricsConfig``: 配置 (NIM / LGD / 机会成本)
  - ``calculate_business_metrics(backtest_result, config=None) -> dict``
  - ``compare_business_metrics(before, after, config=None) -> dict``
  - ``format_business_summary(metrics) -> str`` (行长可读 markdown)
"""
from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Config (defaults from 国有大行口径 · 后续走 yaml 配置)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusinessMetricsConfig:
    """业务指标计算配置 · 默认值取行业中位数."""
    nim_default: float = 0.035            # 净息差 3.5%
    lgd_default: float = 0.60             # 坏账损失率 60%
    avg_loan_amount_wan: float = 100.0    # 默认平均贷款 100 万元 (中小企业口径)
    opportunity_cost_rate: float = 0.0    # 机会成本率 (保守 · 默认 0)
    currency_unit: str = "万元"


DEFAULT_CONFIG = BusinessMetricsConfig()


# ---------------------------------------------------------------------------
# 单 ruleset 业务指标
# ---------------------------------------------------------------------------


def calculate_business_metrics(
    backtest_result_dict: dict,
    config: BusinessMetricsConfig | None = None,
    avg_loan_amount_wan_actual: float | None = None,
    bad_rate: float | None = None,
) -> dict:
    """从 backtest 结果算业务指标.

    Args:
        backtest_result_dict: BacktestResult.model_dump() ·
            必含 total_records / approved / rejected / manual_review / approval_rate
        config: 配置 (默认 DEFAULT_CONFIG)
        avg_loan_amount_wan_actual: 实际平均贷款金额 (CSV 算出 · 优于默认)
        bad_rate: 实测坏账率 (label=days_past_due>30 那部分) ·
            None 时按 config.lgd_default × 总体均值估

    Returns:
        dict {
            通过率, 拒绝率, 复核率, 坏账率,
            利润影响_总, 利润影响_per_loan,
            通过笔数, 拒绝笔数, 复核笔数,
            avg_loan_amount_wan, nim, lgd_assumption
        }
    """
    cfg = config or DEFAULT_CONFIG

    total = int(backtest_result_dict.get("total_records", 0))
    approved = int(backtest_result_dict.get("approved", 0))
    rejected = int(backtest_result_dict.get("rejected", 0))
    manual = int(backtest_result_dict.get("manual_review", 0))
    no_hit = total - approved - rejected - manual
    if no_hit < 0:
        no_hit = 0
    # 通过 = approved + no_hit (rule 命中即停 + 未命中默认放行)
    pass_count = approved + no_hit

    pass_rate = pass_count / total if total else 0.0
    reject_rate = rejected / total if total else 0.0
    review_rate = manual / total if total else 0.0

    avg_amt = avg_loan_amount_wan_actual or cfg.avg_loan_amount_wan
    actual_bad_rate = bad_rate if bad_rate is not None else 0.0  # 无 label 时 0

    # 利润影响 (万元)
    # 通过笔数 × 平均金额 × (NIM - LGD × bad_rate) - 拒绝笔数 × 平均金额 × 机会成本率
    revenue_per_pass = avg_amt * (cfg.nim_default - cfg.lgd_default * actual_bad_rate)
    profit_pass_total = pass_count * revenue_per_pass
    profit_reject_loss = rejected * avg_amt * cfg.opportunity_cost_rate
    profit_total = profit_pass_total - profit_reject_loss
    profit_per_loan = profit_total / total if total else 0.0

    return {
        "pass_count": pass_count,
        "reject_count": rejected,
        "review_count": manual,
        "pass_rate": round(pass_rate, 4),
        "reject_rate": round(reject_rate, 4),
        "review_rate": round(review_rate, 4),
        "bad_rate": round(actual_bad_rate, 4),
        "profit_total_wan": round(profit_total, 2),
        "profit_per_loan_wan": round(profit_per_loan, 4),
        "avg_loan_amount_wan": round(avg_amt, 2),
        "nim": cfg.nim_default,
        "lgd_assumption": cfg.lgd_default,
        "currency_unit": cfg.currency_unit,
    }


# ---------------------------------------------------------------------------
# 双 ruleset 对比 (champion/challenger 业务侧)
# ---------------------------------------------------------------------------


def compare_business_metrics(
    before_metrics: dict, after_metrics: dict,
) -> dict:
    """对比新旧策略业务指标 · 给出 delta + 业务方向.

    Returns:
        dict {
            pass_rate_delta_pp,
            reject_rate_delta_pp,
            bad_rate_delta_pp,
            profit_delta_wan,
            profit_delta_pct,
            recommendation: "adopt"|"reject"|"review"
        }

    pp = percentage point (百分点)
    """
    def _delta(a: float, b: float) -> float:
        return round(a - b, 4)

    pass_delta_pp = round((after_metrics.get("pass_rate", 0) -
                           before_metrics.get("pass_rate", 0)) * 100, 2)
    reject_delta_pp = round((after_metrics.get("reject_rate", 0) -
                             before_metrics.get("reject_rate", 0)) * 100, 2)
    bad_delta_pp = round((after_metrics.get("bad_rate", 0) -
                          before_metrics.get("bad_rate", 0)) * 100, 2)
    profit_delta = _delta(
        after_metrics.get("profit_total_wan", 0),
        before_metrics.get("profit_total_wan", 0),
    )
    before_profit = before_metrics.get("profit_total_wan", 0) or 1e-9
    profit_delta_pct = round(profit_delta / abs(before_profit) * 100, 2)

    # 推荐: 业务方简单 heuristic
    recommendation = "review"
    reasons: list[str] = []
    if profit_delta > 0 and bad_delta_pp <= 0:
        recommendation = "adopt"
        reasons.append("利润↑ + 坏账率不增 · 双优")
    elif profit_delta < 0 and bad_delta_pp >= 0:
        recommendation = "reject"
        reasons.append("利润↓ + 坏账率不降 · 双输")
    elif profit_delta > 0 and bad_delta_pp > 0:
        reasons.append("利润↑ 但坏账率↑ · 风险偏好提升 · 业务方拍板")
    elif profit_delta < 0 and bad_delta_pp < 0:
        reasons.append("坏账率↓ 但利润↓ · 风控收紧 · 业务方拍板")

    return {
        "pass_rate_delta_pp": pass_delta_pp,
        "reject_rate_delta_pp": reject_delta_pp,
        "bad_rate_delta_pp": bad_delta_pp,
        "profit_delta_wan": profit_delta,
        "profit_delta_pct": profit_delta_pct,
        "recommendation": recommendation,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# 业务方可读 summary (行长汇报场景)
# ---------------------------------------------------------------------------


def format_business_summary(metrics: dict) -> str:
    """单 ruleset 业务指标 → 行长可读 markdown."""
    lines = [
        "### 业务指标 (业务口径)",
        "",
        f"- **通过率**: {metrics.get('pass_rate', 0) * 100:.2f}% "
        f"({metrics.get('pass_count', 0):,} 笔)",
        f"- **拒绝率**: {metrics.get('reject_rate', 0) * 100:.2f}% "
        f"({metrics.get('reject_count', 0):,} 笔)",
        f"- **复核率**: {metrics.get('review_rate', 0) * 100:.2f}% "
        f"({metrics.get('review_count', 0):,} 笔)",
        f"- **实测坏账率**: {metrics.get('bad_rate', 0) * 100:.2f}%",
        f"- **预估利润**: {metrics.get('profit_total_wan', 0):,.2f} "
        f"{metrics.get('currency_unit', '万元')} "
        f"(单笔均利 {metrics.get('profit_per_loan_wan', 0):.4f} "
        f"{metrics.get('currency_unit', '万元')})",
        "",
        f"> 假设条件: 净息差 {metrics.get('nim', 0) * 100:.2f}% · "
        f"坏账损失率 {metrics.get('lgd_assumption', 0) * 100:.0f}% · "
        f"平均贷款金额 {metrics.get('avg_loan_amount_wan', 0):,.2f} 万元",
    ]
    return "\n".join(lines)


def format_compare_summary(compare_result: dict) -> str:
    """双策略对比 → 行长可读 markdown."""
    rec = compare_result.get("recommendation", "review")
    rec_label = {"adopt": "✅ 建议采纳", "reject": "❌ 建议否决",
                 "review": "⚠️ 业务方拍板"}.get(rec, rec)
    lines = [
        "### 新旧策略对比 (业务口径)",
        "",
        f"- **通过率**: {compare_result.get('pass_rate_delta_pp', 0):+.2f} pp",
        f"- **拒绝率**: {compare_result.get('reject_rate_delta_pp', 0):+.2f} pp",
        f"- **坏账率**: {compare_result.get('bad_rate_delta_pp', 0):+.2f} pp",
        f"- **利润影响**: {compare_result.get('profit_delta_wan', 0):+,.2f} 万元"
        f" ({compare_result.get('profit_delta_pct', 0):+.2f}%)",
        "",
        f"**结论**: {rec_label}",
    ]
    reasons = compare_result.get("reasons", [])
    if reasons:
        lines.append("")
        lines.extend(f"- {r}" for r in reasons)
    return "\n".join(lines)


__all__ = [
    "BusinessMetricsConfig",
    "DEFAULT_CONFIG",
    "calculate_business_metrics",
    "compare_business_metrics",
    "format_business_summary",
    "format_compare_summary",
]
