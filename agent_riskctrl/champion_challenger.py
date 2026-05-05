# -*- coding: utf-8 -*-
"""agent_riskctrl.champion_challenger — 双 model 对比 (BE8.5).

风险经理痛 1.4.1 (per docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE8):
  "新策略 vs 老策略 数据 vs 业务双轨都看到 才敢上线 · 不敢只看 KS"

Champion = 当前生产策略 · Challenger = 待评估候选策略 ·
跑同样 CSV · 对比 KS / 通过率 / 坏账率 / 利润 · 给 winner 推荐 + 理由.

设计:
  - **§3.1 确定性 Python**: winner 推荐基于阈值规则 · 不让 LLM 现场判
  - **复用** baseline_ruleset.compute_strategy_ks (KS 计算) +
    backtesting.run_backtest (统计) + business_metrics.calculate_business_metrics (业务)
    + business_metrics.compare_business_metrics (双轨 delta)
  - 输出**三层报告**:
    1. 统计层 (KS / KS curve / per-rule FP)
    2. 业务层 (通过率 / 坏账率 / 利润)
    3. **推荐层** (winner + reasons + risk_flags)

Public surface:
  - ``ChampionChallengerResult`` dataclass
  - ``compare_champion_challenger(df, champion, challenger, ...) -> ChampionChallengerResult``
  - ``format_cc_report(result) -> str`` (markdown · 行长可读 + 数据科学家可读双区)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from agent_riskctrl.backtesting import run_backtest
from agent_riskctrl.baseline_ruleset import (
    BAD_DPD_THRESHOLD,
    LABEL_COLUMN_DEFAULT,
    compute_strategy_ks,
)
from agent_riskctrl.business_metrics import (
    BusinessMetricsConfig,
    DEFAULT_CONFIG,
    calculate_business_metrics,
    compare_business_metrics,
    format_business_summary,
    format_compare_summary,
)
from agent_riskctrl.rule_engine import RuleSet


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class ChampionChallengerResult:
    """双 model 对比报告."""

    # 统计层
    champion_ks: float
    challenger_ks: float
    ks_delta: float
    champion_ks_meta: dict
    challenger_ks_meta: dict

    # 业务层 (BE6.4 双轨)
    champion_business: dict
    challenger_business: dict
    business_compare: dict   # compare_business_metrics 输出

    # backtest 原结果
    champion_backtest: dict
    challenger_backtest: dict

    # 推荐层
    winner: str              # "champion" | "challenger" | "tie"
    winner_reasons: list[str]
    risk_flags: list[str]    # 不阻断但提示业务方
    label_column_used: str
    bad_threshold: int

    # 元数据
    n_records: int = 0
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 决策 logic (winner + flags)
# ---------------------------------------------------------------------------

# 阈值 · 业务方拍板时的判据
KS_DELTA_SIGNIFICANT = 0.02      # KS 提升 ≥ 2pp 视显著
PROFIT_DELTA_SIGNIFICANT = 1.0   # 利润 delta ≥ 1 万元视显著
BAD_RATE_DELTA_FLAG = 0.5        # 坏账率 ↑ ≥ 0.5 pp 触 risk flag
PASS_RATE_DELTA_FLAG = 5.0       # 通过率 跌 ≥ 5 pp 触 risk flag (拒绝面过度)


def _decide_winner(
    ks_delta: float,
    business_compare_dict: dict,
) -> tuple[str, list[str], list[str]]:
    """三合一推荐 logic.

    Returns:
        (winner, reasons, risk_flags)
    """
    reasons: list[str] = []
    flags: list[str] = []

    profit_delta = business_compare_dict.get("profit_delta_wan", 0)
    bad_delta_pp = business_compare_dict.get("bad_rate_delta_pp", 0)
    pass_delta_pp = business_compare_dict.get("pass_rate_delta_pp", 0)

    # 风险 flag (无论 winner) · 业务方拍板必看
    if bad_delta_pp > BAD_RATE_DELTA_FLAG:
        flags.append(
            f"⚠ challenger 坏账率上升 {bad_delta_pp:+.2f}pp · 风险偏好提升"
        )
    if pass_delta_pp < -PASS_RATE_DELTA_FLAG:
        flags.append(
            f"⚠ challenger 通过率下降 {pass_delta_pp:+.2f}pp · "
            f"客户拒绝面扩大 · 业务收入受影响"
        )

    # winner 决策 - 三方面都看 ks/profit/bad_rate
    ks_better = ks_delta > KS_DELTA_SIGNIFICANT
    ks_worse = ks_delta < -KS_DELTA_SIGNIFICANT
    profit_better = profit_delta > PROFIT_DELTA_SIGNIFICANT
    profit_worse = profit_delta < -PROFIT_DELTA_SIGNIFICANT
    bad_better = bad_delta_pp < -0.1
    bad_worse = bad_delta_pp > 0.1

    win_score_challenger = (
        int(ks_better) + int(profit_better) + int(bad_better)
    )
    win_score_champion = (
        int(ks_worse) + int(profit_worse) + int(bad_worse)
    )

    if win_score_challenger > win_score_champion:
        winner = "challenger"
        if ks_better:
            reasons.append(f"KS 提升 {ks_delta:+.4f} (>= {KS_DELTA_SIGNIFICANT})")
        if profit_better:
            reasons.append(f"利润提升 {profit_delta:+,.2f} 万元")
        if bad_better:
            reasons.append(f"坏账率下降 {bad_delta_pp:+.2f}pp")
    elif win_score_champion > win_score_challenger:
        winner = "champion"
        if ks_worse:
            reasons.append(f"challenger KS 下降 {ks_delta:+.4f}")
        if profit_worse:
            reasons.append(f"challenger 利润下降 {profit_delta:+,.2f} 万元")
        if bad_worse:
            reasons.append(f"challenger 坏账率上升 {bad_delta_pp:+.2f}pp")
    else:
        winner = "tie"
        reasons.append(
            f"KS {ks_delta:+.4f} / 利润 {profit_delta:+,.2f}万 / "
            f"坏账率 {bad_delta_pp:+.2f}pp · 三项无一显著差异 · "
            f"业务方拍板决定是否换 (建议观察期 1 个月再判)"
        )

    return winner, reasons, flags


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def compare_champion_challenger(
    df: pd.DataFrame,
    champion: RuleSet,
    challenger: RuleSet,
    label_column: str = LABEL_COLUMN_DEFAULT,
    bad_threshold: int = BAD_DPD_THRESHOLD,
    business_config: BusinessMetricsConfig | None = None,
) -> ChampionChallengerResult:
    """跑 champion + challenger · 给三层报告 + winner 推荐.

    Args:
        df: 历史样本 (Q-040 MAX_ROWS=50000 由 backtesting.load_csv_data 控)
        champion: 当前生产 RuleSet
        challenger: 候选 RuleSet
        label_column: bad 标签列 (默认 days_past_due)
        bad_threshold: 标签阈值 (默认 30 DPD)
        business_config: 业务指标配置 (默认 DEFAULT_CONFIG NIM=3.5%/LGD=60%)

    Returns:
        ChampionChallengerResult
    """
    cfg = business_config or DEFAULT_CONFIG

    # ===== 统计层 KS =====
    ks_champ, meta_champ = compute_strategy_ks(
        df, champion, label_column, bad_threshold,
    )
    ks_chall, meta_chall = compute_strategy_ks(
        df, challenger, label_column, bad_threshold,
    )

    # ===== backtest (含 per-rule FP) =====
    bt_champ = run_backtest(df, champion, label_column=label_column)
    bt_chall = run_backtest(df, challenger, label_column=label_column)

    # ===== 业务层 =====
    actual_avg_amt: float | None = None
    if "loan_amount_wan" in df.columns:
        try:
            actual_avg_amt = float(df["loan_amount_wan"].mean())
        except (ValueError, TypeError):
            actual_avg_amt = None

    actual_bad_rate: float | None = None
    if label_column in df.columns:
        try:
            actual_bad_rate = float(
                (df[label_column].fillna(0).astype(float) > bad_threshold).mean()
            )
        except (TypeError, ValueError):
            actual_bad_rate = None

    bm_champ = calculate_business_metrics(
        {
            "total_records": bt_champ.total_records,
            "approved": bt_champ.approved,
            "rejected": bt_champ.rejected,
            "manual_review": bt_champ.manual_review,
            "approval_rate": bt_champ.approval_rate,
        },
        config=cfg,
        avg_loan_amount_wan_actual=actual_avg_amt,
        bad_rate=actual_bad_rate,
    )
    bm_chall = calculate_business_metrics(
        {
            "total_records": bt_chall.total_records,
            "approved": bt_chall.approved,
            "rejected": bt_chall.rejected,
            "manual_review": bt_chall.manual_review,
            "approval_rate": bt_chall.approval_rate,
        },
        config=cfg,
        avg_loan_amount_wan_actual=actual_avg_amt,
        bad_rate=actual_bad_rate,
    )

    biz_compare = compare_business_metrics(bm_champ, bm_chall)

    # ===== 推荐层 =====
    ks_delta = ks_chall - ks_champ
    winner, reasons, flags = _decide_winner(ks_delta, biz_compare)

    # config snapshot
    config_dict: dict[str, Any] = {
        "nim": cfg.nim_default,
        "lgd": cfg.lgd_default,
        "ks_delta_significant": KS_DELTA_SIGNIFICANT,
        "profit_delta_significant_wan": PROFIT_DELTA_SIGNIFICANT,
    }

    return ChampionChallengerResult(
        champion_ks=round(ks_champ, 4),
        challenger_ks=round(ks_chall, 4),
        ks_delta=round(ks_delta, 4),
        champion_ks_meta=meta_champ,
        challenger_ks_meta=meta_chall,
        champion_business=bm_champ,
        challenger_business=bm_chall,
        business_compare=biz_compare,
        champion_backtest={
            "total_records": bt_champ.total_records,
            "approved": bt_champ.approved,
            "rejected": bt_champ.rejected,
            "manual_review": bt_champ.manual_review,
            "approval_rate": bt_champ.approval_rate,
            "rule_stats": (bt_champ.metrics or {}).get("rule_stats", []),
        },
        challenger_backtest={
            "total_records": bt_chall.total_records,
            "approved": bt_chall.approved,
            "rejected": bt_chall.rejected,
            "manual_review": bt_chall.manual_review,
            "approval_rate": bt_chall.approval_rate,
            "rule_stats": (bt_chall.metrics or {}).get("rule_stats", []),
        },
        winner=winner,
        winner_reasons=reasons,
        risk_flags=flags,
        label_column_used=label_column,
        bad_threshold=bad_threshold,
        n_records=int(len(df)),
        config=config_dict,
    )


# ---------------------------------------------------------------------------
# Format · 行长汇报 markdown
# ---------------------------------------------------------------------------


def format_cc_report(result: ChampionChallengerResult) -> str:
    """生成 markdown 报告 · 双区 (业务方 + 数据科学家)."""
    lines = [
        "# Champion / Challenger 对比报告",
        "",
        f"- 样本量: {result.n_records:,} 行 · "
        f"标签列: `{result.label_column_used}` (>{result.bad_threshold} 视坏账)",
        "",
    ]

    # === 推荐层 (top · 行长一眼看) ===
    winner_label = {
        "champion": "🏆 留 Champion (现策略)",
        "challenger": "🚀 换 Challenger (新策略)",
        "tie": "⚖️ 持平 · 业务方拍板",
    }.get(result.winner, result.winner)
    lines.append(f"## 结论: {winner_label}")
    lines.append("")
    if result.winner_reasons:
        lines.append("**推荐理由**:")
        lines.extend(f"- {r}" for r in result.winner_reasons)
        lines.append("")
    if result.risk_flags:
        lines.append("**风险提示**:")
        lines.extend(f"- {f}" for f in result.risk_flags)
        lines.append("")

    # === 业务层 ===
    lines.append("## 业务口径对比")
    lines.append("")
    lines.append(format_compare_summary(result.business_compare))
    lines.append("")
    lines.append("### Champion 业务指标")
    lines.append(format_business_summary(result.champion_business))
    lines.append("")
    lines.append("### Challenger 业务指标")
    lines.append(format_business_summary(result.challenger_business))
    lines.append("")

    # === 统计层 ===
    lines.append("## 统计口径对比 (数据科学家)")
    lines.append("")
    lines.append(f"- **Champion KS**: {result.champion_ks:.4f}")
    lines.append(f"- **Challenger KS**: {result.challenger_ks:.4f}")
    lines.append(f"- **KS Delta**: {result.ks_delta:+.4f}")

    return "\n".join(lines)


__all__ = [
    "BAD_RATE_DELTA_FLAG",
    "ChampionChallengerResult",
    "KS_DELTA_SIGNIFICANT",
    "PASS_RATE_DELTA_FLAG",
    "PROFIT_DELTA_SIGNIFICANT",
    "compare_champion_challenger",
    "format_cc_report",
]
