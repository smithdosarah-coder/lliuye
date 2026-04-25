# -*- coding: utf-8 -*-
"""单测 · agent_report/template_adapter.py(Phase 2 Task C)

DoD: L3-12(模板覆盖度,≥2 银行模板)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.template_adapter import (  # noqa: E402
    TemplateProfile,
    coverage_summary,
    detect_template,
    scan_directory,
)


SAMPLES = PROJECT_ROOT / "samples"


def test_scan_directory_covers_all_5_templates():
    profiles = scan_directory(SAMPLES)
    names = {p.template_name for p in profiles}
    assert "科创贷申报书_模板.docx" in names
    assert "小微对私授信申报书_模板.docx" in names
    assert "普惠申报书_骨架型.docx" in names
    # 至少 5 份
    assert len(profiles) >= 5


def test_tech_credit_template_detected_with_correct_flags():
    p = SAMPLES / "科创贷申报书_模板.docx"
    prof = detect_template(p)
    assert prof.scenario == "tech_credit"
    assert prof.business_line == "corporate"
    assert prof.feature_flags["needs_rd_intensity_check"] is True
    assert prof.feature_flags["needs_financial_anchor"] is True


def test_micro_personal_template_detected_with_personal_flags():
    p = SAMPLES / "小微对私授信申报书_模板.docx"
    prof = detect_template(p)
    assert prof.scenario == "micro_personal"
    assert prof.business_line == "personal"
    assert prof.feature_flags["needs_credit_query_breakdown"] is True
    assert prof.feature_flags["personal_data_grade_core"] is True


def test_corporate_long_form_priority_over_tech_credit():
    """文件名含'对公成稿'必须优先于内容关键词'研发'命中 corporate_long_form。"""
    p = SAMPLES / "经纬测绘_对公成稿A.docx"
    prof = detect_template(p)
    assert prof.scenario == "corporate_long_form"
    assert prof.business_line == "corporate"


def test_coverage_summary_structure():
    profiles = scan_directory(SAMPLES)
    summary = coverage_summary(profiles)
    assert summary["total_templates"] >= 5
    # 4 个场景全覆盖(Phase 2 验收点:tech_credit + micro_personal 已上)
    by = summary["by_scenario"]
    assert "tech_credit" in by
    assert "micro_personal" in by
    assert "corporate_long_form" in by
    assert "inclusive_skeleton" in by


def test_unknown_template_falls_back_safely(tmp_path):
    """未识别模板 → unknown,不抛异常,有兜底 qc_floor。"""
    fake = tmp_path / "未知_xxx.docx"
    from docx import Document
    d = Document()
    d.add_paragraph("纯随机文本,不带任何识别关键词。")
    d.save(str(fake))
    prof = detect_template(fake)
    assert prof.scenario == "unknown"
    assert prof.business_line == "reserved"
    assert prof.expected_qc_floor > 0
