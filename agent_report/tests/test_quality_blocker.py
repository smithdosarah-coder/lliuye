# -*- coding: utf-8 -*-
"""单测 · agent_report/quality_blocker.py(Phase 2 Task B)

DoD: L3-7(QC Blocker 零绕过)+ L2-7(证据链)
覆盖 7 用例:
  失败侧(3):
    1. test_blocker_fails_on_placeholder_residual
    2. test_blocker_fails_on_financial_inconsistency
    3. test_blocker_fails_on_compliance_overreach
  通过侧(4):
    4. test_blocker_passes_on_clean_evidence_text
    5. test_blocker_passes_when_anchor_missing
    6. test_blocker_passes_on_short_pure_text
    7. test_blocker_passes_with_evidence_marker
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.quality_blocker import (  # noqa: E402
    BlockerVerdict,
    check_compliance_terms,
    check_evidence,
    check_financial_consistency,
    check_placeholder,
    format_verdict_text,
    run_blocker,
)


# ============================================================================
# 失败侧 3 用例
# ============================================================================


def test_blocker_fails_on_placeholder_residual():
    """残留 XX 公司 / ____ / 待补充 → block"""
    text = (
        "公司主营业务为新能源材料制造,主要客户为 XX公司,"
        "近三年营收增长率约 65-70% 之间,担保情况待补充,"
        "实控人为张XX,持股比例为____。"
    )
    verdict = run_blocker(text, financial_anchor=None, expect_evidence=False)
    assert verdict.blocked is True
    assert "placeholder" in verdict.fail_dimensions
    codes = {i.code for i in verdict.issues}
    assert "company_placeholder" in codes
    assert "fake_name_placeholder" in codes
    assert "underscore_placeholder" in codes
    assert "fill_marker_residual" in codes
    rendered = format_verdict_text(verdict)
    assert "BLOCKED" in rendered


def test_blocker_fails_on_financial_inconsistency():
    """文中资产负债率与 anchor 偏差 >1pp → block"""
    text = (
        "经审计报告核对,公司 2024 年度资产负债率为 65.0%,出处:审计报告附注三。"
        "公司经营性现金流稳定,流动比率为 1.20,出处:利润表。"
    )
    anchor = {
        "ratios": {
            "asset_liability_ratio": 0.45,  # 45% vs 文中 65% 偏差 20pp → 命中
            "current_ratio": 1.32,          # 132% vs 文中 120% 偏差 12pp → 命中(单位换算后)
        }
    }
    verdict = run_blocker(text, financial_anchor=anchor)
    assert verdict.blocked is True
    assert "financial_consistency" in verdict.fail_dimensions
    codes = {i.code for i in verdict.issues}
    assert any(c.startswith("ratio_mismatch:") for c in codes), f"got codes: {codes}"


def test_blocker_fails_on_compliance_overreach():
    """copilot 越权直接核准 + 绝对化语 → block"""
    text = (
        "经综合评估,本次申请综合授信 500 万元,担保措施完美,"
        "授信资金运作绝对安全,核准授信。出处:申请书第 1 页。"
    )
    verdict = run_blocker(text, financial_anchor=None)
    assert verdict.blocked is True
    assert "compliance_terms" in verdict.fail_dimensions
    codes = {i.code for i in verdict.issues}
    assert "guarantee_loose_term" in codes
    assert "absolute_safety_claim" in codes
    assert "credit_decision_overreach" in codes


# ============================================================================
# 通过侧 4 用例
# ============================================================================


def test_blocker_passes_on_clean_evidence_text():
    """干净文本 + 出处引用 + anchor 匹配 → 通过"""
    text = (
        "经审计报告核对,公司 2024 年度营业收入 15,800 万元,"
        "净利润 1,260 万元(出处:审计报告利润表)。"
        "资产负债率约 45.0%,流动比率约 1.32(出处:审计报告附注五)。"
        "建议核准本次综合授信 500 万元,前提:补充评估报告原件。"
    )
    anchor = {
        "ratios": {
            "asset_liability_ratio": 0.45,
            "current_ratio": 1.32,
        }
    }
    verdict = run_blocker(text, financial_anchor=anchor)
    assert verdict.blocked is False, format_verdict_text(verdict)
    assert verdict.fail_dimensions == []


def test_blocker_passes_when_anchor_missing():
    """anchor 为空 → 财务维度自动跳过,不假阳"""
    text = (
        "经核对材料,公司 2024 年度营业收入 15,800 万元,"
        "净利润 1,260 万元(出处:审计报告利润表)。"
        "建议核准本次综合授信。"
    )
    verdict = run_blocker(text, financial_anchor=None)
    assert verdict.blocked is False
    fc_codes = [i.code for i in verdict.issues if i.dimension == "financial_consistency"]
    assert fc_codes == [], "anchor 缺失时不应产出 financial_consistency 类 issue"


def test_blocker_passes_on_short_pure_text():
    """短文本 + 无数字 + 无禁用词 → 通过"""
    text = "公司主营业务为软件信息服务,经营状况整体稳定。"
    verdict = run_blocker(text, financial_anchor=None, expect_evidence=False)
    assert verdict.blocked is False
    assert verdict.issues == []


def test_blocker_passes_with_evidence_marker():
    """有数字但挂了出处关键词 → evidence 维度通过"""
    text = (
        "公司 2024 年度营业收入 15,800 万元,净利润 1,260 万元,"
        "毛利率约 32%(出处:审计报告利润表 第 4 页)。"
    )
    verdict = run_blocker(text, financial_anchor=None)
    assert verdict.blocked is False
    block_issues = [i for i in verdict.issues if i.severity == "block"]
    assert block_issues == [], f"应无硬阻断: {block_issues}"


# ============================================================================
# 单维度直调(不进 verdict 总和)
# ============================================================================


def test_dimension_helpers_work_independently():
    assert "company_placeholder" in {
        i.code for i in check_placeholder("XX公司经营稳定")
    }
    assert "absolute_safety_claim" in {
        i.code for i in check_compliance_terms("绝对安全")
    }
    assert check_evidence("营收 100 万元 利润 20 万元 毛利率 30% 净利率 10%", True)
    assert check_financial_consistency(
        "资产负债率为 65%",
        {"ratios": {"asset_liability_ratio": 0.45}},
    )
