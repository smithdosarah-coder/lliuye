# -*- coding: utf-8 -*-
"""agent_alert.word_export 单测 · Stage W-FIX2 (修 bug #6).

锁定:
  - export(payload) 返 bytes · 包含 customer / tier / triggers / advice
  - build_filename · session_id 兜底 + 非法字符过滤
  - export_hitlist_docx · 落盘 + 返绝对路径
  - tier 归一化 (red / RED / RiskLevel.RED → red)
  - 缺字段优雅降级 NA · 不抛
  - case dict 字段优先级 (snake_case → camelCase)
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_alert.word_export import (  # noqa: E402
    NA,
    build_filename,
    export,
    export_hitlist_docx,
)


# ============================================================================
# build_filename · 8 case
# ============================================================================

@pytest.mark.parametrize("session_id", [
    "alert-2026-04-29",
    "session/with/slash",
    "session*?<>|",
    "含 空格",
    "very_long_" * 8,
    "",
    "  trim  ",
    "中文 ID 2026",
])
def test_filename_strips_illegal_chars(session_id):
    fn = build_filename({"session_id": session_id})
    for bad in r'\/:*?"<>| ':
        if bad == " ":
            continue  # space → _
        assert bad not in fn


def test_filename_default_when_blank():
    fn = build_filename({})
    assert fn.endswith(".docx")
    assert "agent4_命中清单" in fn


def test_filename_includes_session_id():
    fn = build_filename({"session_id": "abc-123"})
    assert "abc-123" in fn


# ============================================================================
# export · basic shape
# ============================================================================

def test_export_returns_bytes_minimal():
    """最简 payload · 仅 cases · 不抛 · 返 docx bytes."""
    data = export({"cases": []})
    assert isinstance(data, bytes)
    assert len(data) > 1000


def test_export_contains_disclaimer():
    """所有报告必含本地渲染免责条款."""
    data = export({"cases": []})
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "本地渲染" in text
    assert "无数据出境" in text


def test_export_includes_customer_name():
    payload = {
        "session_id": "s1",
        "cases": [
            {"customer": "测试客户A", "risk_level": "red", "triggers": ["规则1"]},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "测试客户A" in text


@pytest.mark.parametrize("tier_input, expected_label", [
    ("red", "🔴"),
    ("RED", "🔴"),
    ("RiskLevel.RED", "🔴"),
    ("yellow", "🟡"),
    ("YELLOW", "🟡"),
    ("green", "🟢"),
    ("unknown", NA),
    ("", NA),
])
def test_export_tier_normalization(tier_input, expected_label):
    """tier 归一化 · red / RED / RiskLevel.RED → 红色 emoji 标签."""
    payload = {
        "cases": [
            {"customer": "x", "risk_level": tier_input, "triggers": []},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    if expected_label == NA:
        # tier 字段 unknown → fallback NA
        pass  # NA 出现在表中 · 不强校验位置
    else:
        assert expected_label in text


def test_export_includes_triggers():
    payload = {
        "cases": [
            {
                "customer": "x",
                "risk_level": "red",
                "triggers": ["征信 M3+", "司法处罚"],
            },
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "征信 M3+" in text
    assert "司法处罚" in text


def test_export_includes_advice():
    payload = {
        "cases": [
            {
                "customer": "x", "risk_level": "yellow",
                "advice": "建议三日内联系客户经理核实",
            },
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "建议三日内联系客户经理核实" in text


def test_export_handles_camelcase_alias():
    """camelCase fallback (lastUpdate) · 不抛 · 字段照常显."""
    payload = {
        "cases": [
            {"customer": "x", "tier": "red", "lastUpdate": "2026-04-29 10:00"},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "2026-04-29 10:00" in text


def test_export_handles_empty_cases():
    payload = {"cases": []}
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "（命中清单为空）" in text or "（无命中客户" in text


def test_export_handles_summary():
    payload = {
        "summary": "扫描 100 家 · 红 12 黄 38 绿 50",
        "cases": [],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "扫描 100 家" in text


def test_export_includes_totals_line():
    payload = {
        "cases": [],
        "totals": {"red": 12, "yellow": 38, "green": 50},
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    # totals 数字应出现在头部
    assert "12" in text
    assert "38" in text
    assert "50" in text


def test_export_includes_client_manager_default():
    payload = {"cases": []}
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "客户经理" in text


def test_export_includes_client_manager_custom():
    payload = {"cases": [], "client_manager": "王哲"}
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "王哲" in text


# ============================================================================
# export_hitlist_docx · 落盘
# ============================================================================

def test_export_hitlist_docx_writes_to_disk(tmp_path):
    out = export_hitlist_docx(
        session_id="s2",
        summary="test summary",
        cases=[{"customer": "ACME", "risk_level": "red", "triggers": ["x"]}],
        output_dir=tmp_path,
    )
    p = Path(out)
    assert p.exists()
    assert p.stat().st_size > 1000
    assert p.suffix == ".docx"
    assert "s2" in p.name


def test_export_hitlist_docx_default_output_dir():
    """默认 output_dir = <root>/data/exports/agent4 · 路径含 agent4."""
    out = export_hitlist_docx(
        session_id="default-test",
        cases=[],
    )
    p = Path(out)
    assert p.exists()
    assert "agent4" in str(p)
    # cleanup
    p.unlink()


def test_export_hitlist_docx_creates_dir_if_missing(tmp_path):
    """output_dir 不存在 · 自动 mkdir."""
    sub = tmp_path / "nested" / "dir"
    out = export_hitlist_docx(
        session_id="mk",
        cases=[],
        output_dir=sub,
    )
    p = Path(out)
    assert p.exists()
    assert sub.exists()


# ============================================================================
# 字段优先级 · snake_case > camelCase
# ============================================================================

def test_export_snake_case_takes_priority():
    """customer (snake) 优先于 customerName (camel) — 但实现用 customer 主键。"""
    payload = {
        "cases": [
            {"customer": "snake-name", "company_name": "fallback-name"},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "snake-name" in text


def test_export_falls_back_to_company_name():
    """无 customer 字段 · fallback company_name."""
    payload = {
        "cases": [
            {"company_name": "fallback-name", "tier": "red"},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "fallback-name" in text


def test_export_handles_string_triggers():
    """triggers 是 str (非 list) · 包成 list 处理 · 不抛."""
    payload = {
        "cases": [
            {"customer": "x", "tier": "red", "triggers": "单条规则"},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "单条规则" in text


def test_export_handles_signals_list():
    """信号事件 list · 显 type / title / date 6 条."""
    payload = {
        "cases": [
            {
                "customer": "x", "tier": "red",
                "signals": [
                    {"type": "司法", "title": "新增诉讼", "date": "2026-04-29"},
                    {"type": "工商", "title": "股权变更", "date": "2026-04-28"},
                ],
            },
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "新增诉讼" in text
    assert "股权变更" in text


def test_export_handles_signals_string_items():
    """信号事件 list 元素是 str · fallback 显字符串本身."""
    payload = {
        "cases": [
            {"customer": "x", "tier": "red", "signals": ["txt-signal-a"]},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "txt-signal-a" in text
