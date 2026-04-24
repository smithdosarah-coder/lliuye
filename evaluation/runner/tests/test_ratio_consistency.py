# -*- coding: utf-8 -*-
"""EV-12 · ratio_consistency.check_ratio_consistency 单元测试.

覆盖 4 个 case (onboarding Task B 验收):
  1. 完全一致 (4 比率 × 1 企业, a3==a6)
  2. 1% 边界 (tolerance=0.01, 差值 = 0.01 视作 match)
  3. 超出 tolerance (差值 > 0.01 视作 mismatch, 拉低 rate)
  4. 单边缺字段 (a3=None, a6=0.5 → mismatch with reason=one_side_none)

测试通过 monkeypatch 替换 adapter 的 extract_financial_ratios 函数 (不
触发实际 xlsx 解析, 测试纯在 check_ratio_consistency 逻辑层).

跑法:
  py -m unittest evaluation.runner.tests.test_ratio_consistency -v
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from evaluation.runner.cross_agent.ratio_consistency import (
    check_ratio_consistency,
    RATIO_NAMES,
)


def _agent3_fn(values: dict[str, dict[str, float | None]]):
    def _inner(eid: str) -> dict[str, float | None]:
        return values.get(eid, {n: None for n in RATIO_NAMES})
    return _inner


def _agent6_fn(values: dict[str, dict[str, float | None]]):
    def _inner(eid: str) -> dict[str, float | None]:
        return values.get(eid, {n: None for n in RATIO_NAMES})
    return _inner


def _run_with(a3_data, a6_data, enterprises=None, tolerance=0.01, thresh=0.99):
    enterprises = enterprises or list(set(a3_data.keys()) | set(a6_data.keys()))
    with patch(
        "evaluation.runner.adapters.agent3_credit.extract_financial_ratios",
        side_effect=_agent3_fn(a3_data),
    ), patch(
        "evaluation.runner.adapters.agent6_report.extract_financial_ratios",
        side_effect=_agent6_fn(a6_data),
    ):
        return check_ratio_consistency(enterprises, tolerance=tolerance, blocker_threshold=thresh)


class TestRatioConsistency(unittest.TestCase):
    def test_case1_exact_match(self):
        """1 家企业 × 4 比率 完全一致 → rate=1.0 passed=True."""
        a = {"DP_T1": {"current_ratio": 1.5, "debt_ratio": 45.0, "roe": 12.0, "gross_margin": 28.5}}
        r = _run_with(a, a, enterprises=["DP_T1"])
        self.assertEqual(r.match_count, 4)
        self.assertEqual(r.total_checks, 4)
        self.assertAlmostEqual(r.consistency_rate, 1.0, places=6)
        self.assertTrue(r.passed)
        # 每条 reason 都是 match
        self.assertTrue(all(p.reason == "match" for p in r.enterprise_results))

    def test_case2_boundary_within_tolerance(self):
        """差值 == tolerance → match (≤ 含等号)."""
        a3 = {"DP_T2": {"current_ratio": 1.50, "debt_ratio": 45.0, "roe": 12.0, "gross_margin": 28.5}}
        a6 = {"DP_T2": {"current_ratio": 1.51, "debt_ratio": 45.0, "roe": 12.0, "gross_margin": 28.5}}
        # abs_diff = 0.01, tolerance = 0.01 (abs_diff <= tolerance → match)
        r = _run_with(a3, a6, enterprises=["DP_T2"], tolerance=0.01)
        self.assertEqual(r.match_count, 4)
        self.assertAlmostEqual(r.consistency_rate, 1.0, places=6)

    def test_case3_over_tolerance(self):
        """差值 > tolerance 且 pct 差 > tolerance → mismatch."""
        a3 = {"DP_T3": {"current_ratio": 1.50, "debt_ratio": 45.0, "roe": 12.0, "gross_margin": 28.5}}
        # current_ratio 差 0.15 (绝对差 0.15 > tolerance 0.01 且 pct_diff 0.10 > 0.01 → mismatch)
        a6 = {"DP_T3": {"current_ratio": 1.65, "debt_ratio": 45.0, "roe": 12.0, "gross_margin": 28.5}}
        r = _run_with(a3, a6, enterprises=["DP_T3"], tolerance=0.01, thresh=0.99)
        self.assertEqual(r.match_count, 3)
        self.assertEqual(r.total_checks, 4)
        self.assertAlmostEqual(r.consistency_rate, 0.75, places=6)
        self.assertFalse(r.passed)  # 0.75 < 0.99 blocker
        over = [p for p in r.enterprise_results if p.reason == "over_tolerance"]
        self.assertEqual(len(over), 1)
        self.assertEqual(over[0].ratio_name, "current_ratio")

    def test_case4_one_side_none_drift(self):
        """一侧 None 另一侧有值 → mismatch (漂移信号)."""
        # Agent3 算出来了, Agent6 没算 → 架构漂移
        a3 = {"DP_T4": {"current_ratio": 1.5, "debt_ratio": 45.0, "roe": 12.0, "gross_margin": 28.5}}
        a6 = {"DP_T4": {"current_ratio": 1.5, "debt_ratio": 45.0, "roe": None, "gross_margin": None}}
        r = _run_with(a3, a6, enterprises=["DP_T4"], tolerance=0.01)
        # current_ratio + debt_ratio match; roe + gross_margin drift
        self.assertEqual(r.match_count, 2)
        self.assertEqual(r.total_checks, 4)
        self.assertAlmostEqual(r.consistency_rate, 0.5, places=6)
        drift = [p for p in r.enterprise_results if p.reason == "one_side_none"]
        self.assertEqual(len(drift), 2)
        self.assertFalse(r.passed)
        # notes 中应包含漂移警告
        self.assertTrue(any("漂移信号" in n for n in r.notes))


if __name__ == "__main__":
    unittest.main()
