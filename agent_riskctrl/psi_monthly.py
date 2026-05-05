# -*- coding: utf-8 -*-
"""agent_riskctrl.psi_monthly — PSI 月度跑 + 分月趋势 (BE8.6 + BE8.7).

风险经理痛 1.4.1 (per docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE8):
  "回测 KS 0.4 看着好 · 但客群分布飘了 · 实际生产期表现可能不一样"

PSI (Population Stability Index) 月度对比验证客群稳定性 ·
分月趋势 (KS/通过率/坏账率 by month) 验证策略时间稳定性 ·
两者互补 (PSI 看输入侧分布漂移 · 分月趋势看输出侧效果漂移).

设计:
  - **§3.1 确定性 Python**: PSI 公式 / 分月聚合都走 numpy/pandas · 不让 LLM 算
  - **§3.5 #5 反 5 原则**: 月份字段是 Agent2 内部数据 mock OK · 不算"替 Agent 外搜"
  - **持久化**: 跑完月度 PSI 写 jsonl `data/riskctrl/psi/<month>.jsonl` ·
    每行 1 个 record (按 feature 拆) · 易追加 · 便于历史回看
  - PSI 阈值 (银行业惯例):
      < 0.10  · 分布稳定 (绿)
      0.10-0.25 · 轻微偏移 (黄 · 关注)
      ≥ 0.25 · 显著偏移 (红 · 重新校准策略)

Public surface:
  - ``compute_psi_by_month(df, baseline_month, month_col, feature_cols, ...) -> dict``
  - ``write_psi_jsonl(records, target_month, out_dir) -> Path``
  - ``compute_monthly_trend(df, ruleset, month_col, ...) -> list[dict]`` (BE8.7)
  - ``format_trend_report(trend) -> str`` (markdown)
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from agent_riskctrl.baseline_ruleset import (
    BAD_DPD_THRESHOLD,
    LABEL_COLUMN_DEFAULT,
    compute_strategy_ks,
)
from agent_riskctrl.business_metrics import (
    BusinessMetricsConfig,
    DEFAULT_CONFIG,
    calculate_business_metrics,
)
from agent_riskctrl.metrics import calculate_psi
from agent_riskctrl.rule_engine import RuleSet, apply_ruleset


# ---------------------------------------------------------------------------
# PSI 阈值 (银行业惯例)
# ---------------------------------------------------------------------------

PSI_GREEN = 0.10
PSI_YELLOW = 0.25


def psi_severity(psi: float) -> str:
    if psi < PSI_GREEN:
        return "stable"
    if psi < PSI_YELLOW:
        return "drift"
    return "severe_drift"


# ---------------------------------------------------------------------------
# PSI by month (BE8.6)
# ---------------------------------------------------------------------------


@dataclass
class PSIRecord:
    """单 (month, feature) PSI 记录 · 1 row in jsonl."""
    target_month: str
    baseline_month: str
    feature: str
    psi: float
    severity: str         # stable / drift / severe_drift
    n_target: int
    n_baseline: int
    bins: int
    computed_at: str


def compute_psi_by_month(
    df: pd.DataFrame,
    baseline_month: str,
    month_col: str = "originated_month",
    feature_cols: list[str] | None = None,
    bins: int = 10,
) -> list[PSIRecord]:
    """对 df 按月分组 · 每月 vs baseline_month 跑 PSI · 每 feature 1 个 record.

    Args:
        df: 历史样本 (含 month_col 与 feature_cols)
        baseline_month: 基线月 (e.g. '2025-01') · 其他月 vs 此 reference
        month_col: 月份列名
        feature_cols: 要监控的字段子集 · None=自动数值列 (排除 month_col + label)
        bins: PSI 分箱

    Returns:
        list[PSIRecord] · 跨月 × 跨字段 一行一条
    """
    if df is None or len(df) == 0 or month_col not in df.columns:
        return []

    if feature_cols is None:
        # 自动选数值列 · 排除 month_col 与常见 label
        skip = {month_col, "days_past_due", "loan_id"}
        feature_cols = [
            c for c in df.columns
            if c not in skip and pd.api.types.is_numeric_dtype(df[c])
        ]

    baseline_df = df[df[month_col].astype(str) == str(baseline_month)]
    if baseline_df.empty:
        return []

    months = sorted(set(df[month_col].astype(str)))
    records: list[PSIRecord] = []
    now_iso = datetime.now().isoformat(timespec="seconds")

    for m in months:
        if m == str(baseline_month):
            continue
        target_df = df[df[month_col].astype(str) == m]
        if target_df.empty:
            continue

        for feat in feature_cols:
            if feat not in baseline_df.columns or feat not in target_df.columns:
                continue
            base_vals = baseline_df[feat].dropna().astype(float).tolist()
            tgt_vals = target_df[feat].dropna().astype(float).tolist()
            if not base_vals or not tgt_vals:
                continue
            psi = calculate_psi(base_vals, tgt_vals, bins=bins)
            records.append(PSIRecord(
                target_month=m,
                baseline_month=str(baseline_month),
                feature=feat,
                psi=psi,
                severity=psi_severity(psi),
                n_target=len(tgt_vals),
                n_baseline=len(base_vals),
                bins=bins,
                computed_at=now_iso,
            ))
    return records


def write_psi_jsonl(
    records: list[PSIRecord],
    target_month: str,
    out_dir: str | Path = "data/riskctrl/psi",
) -> Path:
    """把月度 PSI 记录写到 jsonl.

    Path: <out_dir>/<target_month>.jsonl · target_month '2025-02' 的所有 feature 一文件.
    多次跑覆盖 (同月跑两次以最后一次为准).

    Returns:
        写入路径
    """
    out_path = Path(out_dir) / f"{target_month}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    target_records = [r for r in records if r.target_month == target_month]
    with out_path.open("w", encoding="utf-8") as f:
        for r in target_records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    return out_path


# ---------------------------------------------------------------------------
# 分月趋势 (BE8.7)
# ---------------------------------------------------------------------------


@dataclass
class MonthlyTrendPoint:
    """单月聚合 metrics."""
    month: str
    n_records: int
    pass_rate: float          # 业务口径
    reject_rate: float
    review_rate: float
    bad_rate: float
    ks: float                 # 统计口径
    profit_total_wan: float
    psi_avg: float = 0.0      # 当月所有 feature PSI 均值 (vs baseline) · 0 = 基线月


def compute_monthly_trend(
    df: pd.DataFrame,
    ruleset: RuleSet,
    month_col: str = "originated_month",
    label_column: str = LABEL_COLUMN_DEFAULT,
    bad_threshold: int = BAD_DPD_THRESHOLD,
    business_config: BusinessMetricsConfig | None = None,
    psi_records: list[PSIRecord] | None = None,
) -> list[MonthlyTrendPoint]:
    """对 df 按月分组 · 每月跑 ruleset · 给 KS + 业务指标 + (可选) 当月 PSI 均值.

    Args:
        df: 含 month_col 与 ruleset 涉及字段
        ruleset: 评估的策略
        month_col: 分组列
        label_column / bad_threshold: KS / 坏账率算法
        business_config: 业务指标配置
        psi_records: 可选 · 已有 PSI by month 数据 · 注入给 trend point 的 psi_avg

    Returns:
        list[MonthlyTrendPoint] · 按月升序
    """
    if df is None or len(df) == 0 or month_col not in df.columns:
        return []

    cfg = business_config or DEFAULT_CONFIG
    months = sorted(set(df[month_col].astype(str)))

    # PSI 月平均 lookup
    psi_avg_lookup: dict[str, float] = {}
    if psi_records:
        for m in months:
            mr = [r.psi for r in psi_records if r.target_month == m]
            psi_avg_lookup[m] = round(sum(mr) / len(mr), 4) if mr else 0.0

    points: list[MonthlyTrendPoint] = []
    actual_avg_amt: float | None = None
    if "loan_amount_wan" in df.columns:
        try:
            actual_avg_amt = float(df["loan_amount_wan"].mean())
        except (ValueError, TypeError):
            actual_avg_amt = None

    for m in months:
        sub = df[df[month_col].astype(str) == m]
        if sub.empty:
            continue

        ks, _ = compute_strategy_ks(sub, ruleset, label_column, bad_threshold)

        # 算 hit / approve / reject / manual_review
        records = sub.to_dict(orient="records")
        hit_results = apply_ruleset(ruleset, records)
        approved = sum(1 for r in hit_results if r["action"] == "approve")
        rejected = sum(1 for r in hit_results if r["action"] == "reject")
        manual = sum(1 for r in hit_results if r["action"] == "manual_review")
        no_hit = sum(1 for r in hit_results if r["action"] == "none")
        total = len(hit_results)

        bad_rate = 0.0
        if label_column in sub.columns:
            try:
                bad_rate = float(
                    (sub[label_column].fillna(0).astype(float) > bad_threshold).mean()
                )
            except (TypeError, ValueError):
                bad_rate = 0.0

        bm = calculate_business_metrics(
            {
                "total_records": total,
                "approved": approved,
                "rejected": rejected,
                "manual_review": manual,
                "approval_rate": (approved + no_hit) / total if total else 0.0,
            },
            config=cfg,
            avg_loan_amount_wan_actual=actual_avg_amt,
            bad_rate=bad_rate,
        )

        points.append(MonthlyTrendPoint(
            month=m,
            n_records=total,
            pass_rate=bm["pass_rate"],
            reject_rate=bm["reject_rate"],
            review_rate=bm["review_rate"],
            bad_rate=round(bad_rate, 4),
            ks=round(ks, 4),
            profit_total_wan=bm["profit_total_wan"],
            psi_avg=psi_avg_lookup.get(m, 0.0),
        ))

    return points


# ---------------------------------------------------------------------------
# Format · markdown
# ---------------------------------------------------------------------------


def format_trend_report(trend: list[MonthlyTrendPoint]) -> str:
    """趋势点 → markdown 表."""
    if not trend:
        return "_趋势数据为空 · 检查 month_col 与样本_"
    lines = [
        "### 分月趋势 (KS / 业务指标 / PSI)",
        "",
        "| 月份 | 笔数 | 通过率 | 坏账率 | KS | 利润 (万) | PSI均值 | 状态 |",
        "|---|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for p in trend:
        sev = psi_severity(p.psi_avg) if p.psi_avg > 0 else "baseline"
        sev_label = {
            "stable": "🟢 稳定",
            "drift": "🟡 关注",
            "severe_drift": "🔴 重新校准",
            "baseline": "⚪ 基线",
        }.get(sev, sev)
        lines.append(
            f"| {p.month} | {p.n_records:,} | "
            f"{p.pass_rate * 100:.2f}% | {p.bad_rate * 100:.2f}% | "
            f"{p.ks:.4f} | {p.profit_total_wan:,.2f} | "
            f"{p.psi_avg:.4f} | {sev_label} |"
        )
    return "\n".join(lines)


def format_psi_summary(records: list[PSIRecord]) -> str:
    """PSI 记录 → markdown 表."""
    if not records:
        return "_PSI 记录为空_"
    severe = [r for r in records if r.severity == "severe_drift"]
    drift = [r for r in records if r.severity == "drift"]
    lines = [
        "### PSI 月度漂移监控",
        "",
        f"- 总记录: {len(records)} ({len(severe)} 严重 + {len(drift)} 轻微 + "
        f"{len(records) - len(severe) - len(drift)} 稳定)",
        "",
    ]
    if severe:
        lines.append("**🔴 严重漂移 (PSI ≥ 0.25 · 重新校准策略)**:")
        for r in severe[:10]:
            lines.append(
                f"- {r.target_month} · `{r.feature}` PSI={r.psi:.4f}"
            )
        lines.append("")
    if drift:
        lines.append("**🟡 轻微漂移 (0.10 ≤ PSI < 0.25 · 关注)**:")
        for r in drift[:10]:
            lines.append(
                f"- {r.target_month} · `{r.feature}` PSI={r.psi:.4f}"
            )
    return "\n".join(lines)


__all__ = [
    "MonthlyTrendPoint",
    "PSIRecord",
    "PSI_GREEN",
    "PSI_YELLOW",
    "compute_monthly_trend",
    "compute_psi_by_month",
    "format_psi_summary",
    "format_trend_report",
    "psi_severity",
    "write_psi_jsonl",
]
