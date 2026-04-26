# -*- coding: utf-8 -*-
"""风控策略回测引擎 — CSV数据加载、回测执行、策略对比

功能:
    load_csv_data   — 读取CSV，自动检测编码和分隔符
    run_backtest    — 对历史数据回测
    compare_strategies — 对比新旧策略效果
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from .rule_engine import RuleSet, apply_rule, apply_ruleset


# 数据行数上限（MVP降级策略）
MAX_ROWS = 500


# ======================================================================
# Pydantic 模型
# ======================================================================

class BacktestResult(BaseModel):
    """回测结果"""
    total_records: int = Field(default=0, description="总记录数")
    approved: int = Field(default=0, description="通过数")
    rejected: int = Field(default=0, description="拒绝数")
    manual_review: int = Field(default=0, description="人工审查数")
    approval_rate: float = Field(default=0.0, description="通过率")
    metrics: dict = Field(default_factory=dict, description="补充指标")


# ======================================================================
# CSV 数据加载
# ======================================================================

def load_csv_data(file_path: str) -> pd.DataFrame:
    """读取CSV文件，自动检测编码和分隔符，限制最多500行。

    支持编码: utf-8-sig, utf-8, gbk, gb2312
    支持分隔符: 逗号, 制表符, 分号
    也支持 .xlsx / .xls 文件

    Args:
        file_path: 文件路径

    Returns:
        pd.DataFrame

    Raises:
        ValueError: 文件不存在或格式不支持
    """
    if not os.path.exists(file_path):
        raise ValueError(f"文件不存在: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    # Excel 文件
    if ext in (".xlsx", ".xls"):
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        df = pd.read_excel(file_path, engine=engine, nrows=MAX_ROWS)
        return df

    # CSV 文件
    if ext != ".csv":
        raise ValueError(f"不支持的文件格式: {ext}（仅支持 .csv / .xlsx / .xls）")

    encodings = ["utf-8-sig", "utf-8", "gbk", "gb2312"]
    separators = [",", "\t", ";"]

    for encoding in encodings:
        for sep in separators:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    sep=sep,
                    nrows=MAX_ROWS,
                )
                # 检测是否正确分割（至少应有2列或列名看起来合理）
                if len(df.columns) >= 2 or len(df) > 0:
                    return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue

    raise ValueError(f"CSV文件编码或分隔符无法识别: {file_path}")


# ======================================================================
# 数据摘要（供LLM分析）
# ======================================================================

def _summarize_data(df: pd.DataFrame) -> str:
    """生成数据摘要文本，供LLM分析使用。"""
    lines = [f"数据规模: {len(df)} 行 x {len(df.columns)} 列", ""]

    # 字段信息
    lines.append("## 字段信息")
    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = int(df[col].isnull().sum())
        null_pct = f"{null_count / len(df) * 100:.1f}%" if len(df) > 0 else "0%"
        lines.append(
            f"- {col} (类型: {dtype}, 空值: {null_count}/{len(df)} = {null_pct})"
        )
    lines.append("")

    # 数值字段统计
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        lines.append("## 数值字段统计")
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            lines.append(f"### {col}")
            lines.append(
                f"  均值: {series.mean():.2f}, 中位数: {series.median():.2f}"
            )
            lines.append(
                f"  最小: {series.min():.2f}, 最大: {series.max():.2f}"
            )
            lines.append(f"  标准差: {series.std():.2f}")
            q25, q75 = series.quantile(0.25), series.quantile(0.75)
            lines.append(f"  25%分位: {q25:.2f}, 75%分位: {q75:.2f}")
        lines.append("")

    # 类别字段分布
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        lines.append("## 类别字段分布")
        for col in cat_cols:
            nunique = df[col].nunique()
            if nunique <= 20:
                lines.append(f"### {col} (共 {nunique} 类)")
                for val, cnt in df[col].value_counts().head(10).items():
                    pct = f"{cnt / len(df) * 100:.1f}%" if len(df) > 0 else "0%"
                    lines.append(f"  {val}: {cnt} ({pct})")
            else:
                lines.append(f"### {col} (共 {nunique} 类，仅展示前5)")
                for val, cnt in df[col].value_counts().head(5).items():
                    lines.append(f"  {val}: {cnt}")
        lines.append("")

    # 前5行数据示例
    lines.append("## 数据示例（前5行）")
    lines.append(df.head(5).to_string(index=False))

    return "\n".join(lines)


# ======================================================================
# 回测执行
# ======================================================================

def run_backtest(
    df: pd.DataFrame,
    ruleset: RuleSet,
    label_column: str | None = None,
) -> BacktestResult:
    """对历史数据执行策略回测。

    Args:
        df: 历史授信数据 DataFrame
        ruleset: 策略规则集合
        label_column: 真实坏账标签列（1=坏账 / 0=正常）。未传则自动探测
            `label_default` / `label`；均不存在则跳过 per-rule FP/TN（置 0）。

    Returns:
        BacktestResult 回测结果。`metrics.rule_stats` per 条规则增
        `{FP, TN, FP_rate}`（A-019 `per_rule_fpr_spread` 依赖）。
    """
    if df.empty or not ruleset.rules:
        return BacktestResult(total_records=len(df))

    records = df.to_dict(orient="records")
    hit_results = apply_ruleset(ruleset, records)

    total = len(hit_results)
    approved = sum(1 for r in hit_results if r["action"] == "approve")
    rejected = sum(1 for r in hit_results if r["action"] == "reject")
    manual_review = sum(1 for r in hit_results if r["action"] == "manual_review")
    no_hit = sum(1 for r in hit_results if r["action"] == "none")

    approval_rate = (approved + no_hit) / total if total > 0 else 0.0

    # 各规则命中统计（priority-ordered; 命中即停）
    rule_hit_counts: dict[str, int] = {}
    for r in hit_results:
        rid = r["hit_rule_id"]
        if rid:
            rule_hit_counts[rid] = rule_hit_counts.get(rid, 0) + 1

    # Per-rule FP/TN —— 独立匹配（不走 priority-stop），语义：这条规则单独看对"正常客户"的误杀分布
    if label_column is None:
        for cand in ("label_default", "label"):
            if cand in df.columns:
                label_column = cand
                break

    labels: list[int] | None = None
    if label_column and label_column in df.columns:
        try:
            labels = [int(r.get(label_column, 0) or 0) for r in records]
        except (TypeError, ValueError):
            labels = None

    rule_stats = []
    for rule in ruleset.rules:
        count = rule_hit_counts.get(rule.rule_id, 0)
        stat: dict[str, Any] = {
            "rule_id": rule.rule_id,
            "rule_name": rule.name,
            "action": rule.action,
            "hit_count": count,
            "hit_rate": round(count / total, 4) if total > 0 else 0.0,
            "FP": 0,
            "TN": 0,
            "FP_rate": 0.0,
        }
        # 仅对 reject 规则计 FP/TN：FPR = 该规则对正常客户（label=0）的独立误拒率
        # approve / manual_review 规则保持 FP=TN=0，adapter 在 (FP+TN)=0 时跳过（A-019 N/A 语义）
        if labels is not None and rule.action == "reject":
            fp = 0
            tn = 0
            for rec, lbl in zip(records, labels):
                if lbl != 0:
                    continue
                if apply_rule(rule, rec):
                    fp += 1
                else:
                    tn += 1
            stat["FP"] = fp
            stat["TN"] = tn
            stat["FP_rate"] = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
        rule_stats.append(stat)

    return BacktestResult(
        total_records=total,
        approved=approved,
        rejected=rejected,
        manual_review=manual_review,
        approval_rate=round(approval_rate, 4),
        metrics={
            "no_hit": no_hit,
            "rule_stats": rule_stats,
            "hit_results": hit_results,
        },
    )


# ======================================================================
# 策略对比
# ======================================================================

# ======================================================================
# P3F 轨 8b Task B · baseline_ruleset 对照组 (KS comparator)
# 形态: 薄包装 · 实现在 baseline_ruleset.py · 此处仅暴露 backtesting 命名空间
# 集成入口: scripts / CLI / adapter 调 backtesting.compare_with_baseline(df, current)
# ======================================================================


def compare_with_baseline(
    df: pd.DataFrame,
    current_ruleset: RuleSet,
    label_column: str = "days_past_due",
    bad_threshold: int = 30,
) -> dict:
    """跑 baseline_ruleset + current_ruleset · 返回 ks_baseline / ks_current / ks_improvement.

    入口对应 onboarding "--compare-baseline 标志"; 调用方/CLI/adapter 通过本函数获得对照.
    具体实现 (5 条硬编规则 + KS 公式) 在 agent_riskctrl.baseline_ruleset 模块.
    """
    from .baseline_ruleset import compare_with_baseline as _impl
    return _impl(df, current_ruleset, label_column, bad_threshold)


def compare_strategies(
    result_before: BacktestResult,
    result_after: BacktestResult,
) -> dict:
    """对比新旧策略的回测效果。

    Args:
        result_before: 旧策略回测结果
        result_after: 新策略回测结果

    Returns:
        对比分析 dict
    """
    def _delta(new_val: float, old_val: float) -> str:
        diff = new_val - old_val
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.2%}"

    total = result_after.total_records
    comparison = {
        "total_records": total,
        "before": {
            "approved": result_before.approved,
            "rejected": result_before.rejected,
            "manual_review": result_before.manual_review,
            "approval_rate": result_before.approval_rate,
        },
        "after": {
            "approved": result_after.approved,
            "rejected": result_after.rejected,
            "manual_review": result_after.manual_review,
            "approval_rate": result_after.approval_rate,
        },
        "delta": {
            "approved": result_after.approved - result_before.approved,
            "rejected": result_after.rejected - result_before.rejected,
            "manual_review": result_after.manual_review - result_before.manual_review,
            "approval_rate_change": _delta(
                result_after.approval_rate, result_before.approval_rate
            ),
        },
    }
    return comparison
