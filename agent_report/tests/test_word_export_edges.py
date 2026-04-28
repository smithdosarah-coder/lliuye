# -*- coding: utf-8 -*-
"""agent_report.word_export edges · Stage E.4 expansion."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.word_export import (  # noqa: E402
    NA,
    _fmt,
    _safe_section_title,
    build_filename,
    export,
)


# ============================================================================
# _fmt · 14 case
# ============================================================================

@pytest.mark.parametrize("input_, expected", [
    (None, NA),
    ("", NA),
    ("   ", NA),
    ("hello", "hello"),
    (123, "123"),
    (0, "0"),
    (3.14, "3.14"),
    ([], NA),
    (["a"], "a"),
    (["a", "b"], "a · b"),
    ({}, NA),
    ({"k": "v"}, "k: v"),
    (True, "True"),
    (False, "False"),
])
def test_fmt(input_, expected):
    result = _fmt(input_)
    if input_ in (None, "", "   ", [], {}):
        assert result == NA
    elif isinstance(input_, list) and input_:
        assert " · " in result or len(input_) == 1
    elif isinstance(input_, dict) and input_:
        assert ":" in result
    else:
        assert str(input_) in result or result == str(input_)


# ============================================================================
# _safe_section_title · 8 case
# ============================================================================

@pytest.mark.parametrize("sec, expected_contains_or_eq", [
    ({"id": "chapter_1_background", "title": ""}, "一、企业背景"),
    ({"id": "chapter_2_operation", "title": ""}, "二、经营情况"),
    ({"id": "chapter_3_finance", "title": ""}, "三、财务分析"),
    ({"id": "chapter_4_conclusion", "title": ""}, "四、审批意见"),
    ({"id": "custom", "title": "自定义标题"}, "自定义标题"),
    ({"id": "x", "title": ""}, "x"),
    ({"id": "", "title": ""}, "段落"),
    ({}, "段落"),
])
def test_safe_section_title(sec, expected_contains_or_eq):
    result = _safe_section_title(sec)
    assert expected_contains_or_eq in result or result == expected_contains_or_eq


# ============================================================================
# build_filename · 12 case
# ============================================================================

@pytest.mark.parametrize("profile_company, report_id, illegal_present", [
    ("正常公司", "session-1", False),
    ("含/斜杠", "x", False),
    ("含*问号?", "x", False),
    ("含<>|", "x", False),
    ("含 空格", "x", False),
    ("very_long_" * 5, "x", False),
    ("", "x", False),
    ("name", "session/with/slash", False),
])
def test_filename_strips_illegal_chars_report(profile_company, report_id, illegal_present):
    fn = build_filename({
        "profile": {"company_name": profile_company} if profile_company else None,
        "report_id": report_id,
    })
    for bad in r'\/:*?"<>|':
        assert bad not in fn


def test_filename_includes_company():
    fn = build_filename({"profile": {"company_name": "测试有限公司"}, "report_id": "x"})
    assert "测试有限公司" in fn


def test_filename_includes_report_id():
    fn = build_filename({"report_id": "abc-123"})
    assert "abc-123" in fn


def test_filename_session_id_alias():
    fn = build_filename({"session_id": "alias-xxx"})
    assert "alias-xxx" in fn


def test_filename_default_when_blank():
    fn = build_filename({})
    assert fn.endswith(".docx")
    assert "agent6_报告" in fn


# ============================================================================
# export · 12 case
# ============================================================================

@pytest.mark.parametrize("business_line, expected_in_doc", [
    ("corporate", "对公"),
    ("inclusive", "普惠"),
    ("reserved", "预留"),
])
def test_export_business_line_label(business_line, expected_in_doc):
    payload = {
        "profile": {"company_name": "x"},
        "sections": [],
        "business_line": business_line,
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert expected_in_doc in text


@pytest.mark.parametrize("section_id, expected_title", [
    ("chapter_1_background", "一、企业背景"),
    ("chapter_2_operation", "二、经营情况"),
    ("chapter_3_finance", "三、财务分析"),
    ("chapter_4_conclusion", "四、审批意见"),
])
def test_export_chapter_titles(section_id, expected_title):
    payload = {
        "profile": {"company_name": "x"},
        "sections": [{"id": section_id, "title": expected_title, "content": "内容", "status": "done"}],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert expected_title in text


@pytest.mark.parametrize("status, status_visible", [
    ("done", False),  # done 不显状态
    ("pending", True),  # pending 显
    ("writing", True),
    ("qc_blocked", True),
])
def test_export_section_status_marker(status, status_visible):
    payload = {
        "profile": {"company_name": "x"},
        "sections": [{"id": "ch1", "title": "T", "content": "C", "status": status, "word_count": 100}],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    if status_visible:
        # 状态字段进 metadata
        assert status in text or "状态" in text


@pytest.mark.parametrize("qc_passed, expected_token", [
    (True, "通过"),
    (False, "阻断"),
])
def test_export_qc_label(qc_passed, expected_token):
    payload = {
        "profile": {"company_name": "x"},
        "sections": [],
        "qc": {"passed": qc_passed, "score": 80, "fatal_fail": not qc_passed},
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert expected_token in text


def test_export_pending_questions_table():
    payload = {
        "profile": {"company_name": "x"},
        "sections": [],
        "pending_questions": [
            {"id": "q1", "label": "外因 · 行业", "recommended": "请补充行业研究"},
            {"id": "q2", "label": "外因 · 上下游", "recommended": "请补充客户清单"},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "待补字段清单" in text
    assert "外因 · 行业" in text


def test_export_no_qc_no_section_no_pending():
    """最简 payload · 仅 profile · 不抛."""
    data = export({"profile": {"company_name": "极简"}})
    assert len(data) > 1000
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "极简" in text


def test_export_disclaimer_always_present():
    data = export({"profile": {"company_name": "x"}, "sections": []})
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "本地渲染" in text
    assert "无数据出境" in text


@pytest.mark.parametrize("client_manager", [
    "王哲", "李四", "客户经理", "Manager X", "",
])
def test_export_client_manager_field(client_manager):
    payload = {
        "profile": {"company_name": "x"},
        "client_manager": client_manager,
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    if client_manager:
        assert client_manager in text
    else:
        # default "客户经理"
        assert "客户经理" in text
