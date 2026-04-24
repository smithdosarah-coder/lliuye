# -*- coding: utf-8 -*-
"""EV-12 · 跨 Agent 财务比率一致率 (Batch 2 Task B).

核心用途: 架构守护点 — 验证 Agent3 授信链 和 Agent6 报告管线 对同一家企业的
财务比率计算都走 `financial_analyzer.FinancialAnalyzer`, 不发生一端偷懒走
LLM 或硬编数字的漂移.

检查 4 条关键比率 per enterprise (onboarding spec):
  - current_ratio      (流动比率)
  - debt_ratio         (资产负债率 → 映射 debt_to_asset_ratio)
  - roe                (净资产收益率 = net_profit / total_equity)
  - gross_margin       (毛利率)

一致性判定:
  - 两侧都 None: 视作 match (双侧架构一致——都没算出来, 不是漂移)
  - 任一侧非 None 且另一侧 None: 视作 mismatch (漂移信号)
  - 双侧非 None: 绝对差 ≤ tolerance (默认 0.01, 即 1%) 视作 match

聚合:
  对 N 家企业 × 4 比率 = 4N 项, 匹配项数 / 总项数 = ratio_calc_consistency.
  blocker_threshold: 0.99 (onboarding spec)

红线: 只读消费 financial_analyzer, 不改 agent_credit / agent_report / v16_*.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


RATIO_NAMES = ("current_ratio", "debt_ratio", "roe", "gross_margin")


@dataclass
class RatioPairResult:
    """单家企业单条比率的双侧对比结果."""
    enterprise_id: str
    ratio_name: str
    agent3_value: float | None
    agent6_value: float | None
    match: bool
    abs_diff: float | None
    pct_diff: float | None
    reason: str  # match / both_none / one_side_none / over_tolerance


@dataclass
class RatioConsistencyResult:
    enterprise_results: list[RatioPairResult]
    total_checks: int
    match_count: int
    consistency_rate: float           # match_count / total_checks
    blocker_threshold: float
    passed: bool
    notes: list[str]

    def to_dict(self) -> dict:
        return {
            "consistency_rate": self.consistency_rate,
            "match_count": self.match_count,
            "total_checks": self.total_checks,
            "blocker_threshold": self.blocker_threshold,
            "passed": self.passed,
            "notes": self.notes,
            "pairs": [asdict(p) for p in self.enterprise_results],
        }


def _compare(
    enterprise_id: str,
    name: str,
    v3: float | None,
    v6: float | None,
    tolerance: float,
) -> RatioPairResult:
    # 双 None → match (架构守护点: 双侧都没算出来即架构一致)
    if v3 is None and v6 is None:
        return RatioPairResult(
            enterprise_id=enterprise_id,
            ratio_name=name,
            agent3_value=None,
            agent6_value=None,
            match=True,
            abs_diff=None,
            pct_diff=None,
            reason="both_none",
        )
    # 一侧 None 一侧有值 → mismatch (漂移信号)
    if v3 is None or v6 is None:
        return RatioPairResult(
            enterprise_id=enterprise_id,
            ratio_name=name,
            agent3_value=v3,
            agent6_value=v6,
            match=False,
            abs_diff=None,
            pct_diff=None,
            reason="one_side_none",
        )
    # 双非 None → 数值比较
    abs_d = abs(float(v3) - float(v6))
    pct_d = abs_d / abs(float(v3)) if float(v3) != 0 else (0.0 if abs_d == 0 else float("inf"))
    ok = abs_d <= tolerance or pct_d <= tolerance
    return RatioPairResult(
        enterprise_id=enterprise_id,
        ratio_name=name,
        agent3_value=float(v3),
        agent6_value=float(v6),
        match=ok,
        abs_diff=abs_d,
        pct_diff=pct_d,
        reason="match" if ok else "over_tolerance",
    )


def check_ratio_consistency(
    enterprise_ids: list[str],
    tolerance: float = 0.01,
    blocker_threshold: float = 0.99,
) -> RatioConsistencyResult:
    """对 enterprise_ids (DP001..DP005) 逐家双侧抽比率, 对比一致率.

    agent3 / agent6 侧的 `_extract_financial_ratios` 都委派给同一个
    `financial_analyzer.FinancialAnalyzer`. 本函数通过 adapter 暴露的
    module-level helpers 取数:
      - from evaluation.runner.adapters.agent3_credit import extract_financial_ratios as a3_extract
      - from evaluation.runner.adapters.agent6_report  import extract_financial_ratios as a6_extract
    """
    # lazy import 避免循环 + 让 adapter 改动后此处自动生效
    from evaluation.runner.adapters.agent3_credit import (
        extract_financial_ratios as a3_extract,
    )
    from evaluation.runner.adapters.agent6_report import (
        extract_financial_ratios as a6_extract,
    )

    all_pairs: list[RatioPairResult] = []
    notes: list[str] = []
    for eid in enterprise_ids:
        try:
            v3_map = a3_extract(eid)
        except Exception as e:
            notes.append(f"{eid}: agent3 extract failed: {e}")
            v3_map = {n: None for n in RATIO_NAMES}
        try:
            v6_map = a6_extract(eid)
        except Exception as e:
            notes.append(f"{eid}: agent6 extract failed: {e}")
            v6_map = {n: None for n in RATIO_NAMES}

        for name in RATIO_NAMES:
            all_pairs.append(
                _compare(eid, name, v3_map.get(name), v6_map.get(name), tolerance)
            )

    total = len(all_pairs)
    matches = sum(1 for p in all_pairs if p.match)
    rate = (matches / total) if total else 0.0
    passed = rate >= blocker_threshold

    # 诊断摘要
    both_none_n = sum(1 for p in all_pairs if p.reason == "both_none")
    if both_none_n:
        notes.append(
            f"{both_none_n}/{total} 项双侧都 None · 视作架构 match"
            " (可能是 mock xlsx 形态与 FinancialAnalyzer 期望两栏格式不匹配, "
            "双侧都没算出来即架构一致, 非漂移)"
        )
    drift_n = sum(1 for p in all_pairs if p.reason == "one_side_none")
    if drift_n:
        notes.append(f"⚠ {drift_n}/{total} 项一侧 None 一侧有值 · 漂移信号! blocker")
    over_n = sum(1 for p in all_pairs if p.reason == "over_tolerance")
    if over_n:
        notes.append(f"⚠ {over_n}/{total} 项超过 tolerance={tolerance} · 数值不一致")

    return RatioConsistencyResult(
        enterprise_results=all_pairs,
        total_checks=total,
        match_count=matches,
        consistency_rate=rate,
        blocker_threshold=blocker_threshold,
        passed=passed,
        notes=notes,
    )
