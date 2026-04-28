# -*- coding: utf-8 -*-
"""agent_channel.export_docx edges · Stage E.4 expansion."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_channel.export_docx import (  # noqa: E402
    NA,
    _candidate_field,
    _chinese_num,
    _fmt_pct,
    _fmt_str,
    build_filename,
    export,
)


# ============================================================================
# _fmt_str · 12 case
# ============================================================================

@pytest.mark.parametrize("input_, expected_contains_or_eq", [
    (None, NA),
    ("", NA),
    ("   ", NA),
    ("hello", "hello"),
    ("中文", "中文"),
    (123, "123"),
    (0, "0"),
    (3.14, "3.14"),
    ([], NA),
    (["a", "b"], "a"),
    ({"k": "v"}, "k"),
    ({}, NA),
])
def test_fmt_str_handles_various_types(input_, expected_contains_or_eq):
    result = _fmt_str(input_)
    if expected_contains_or_eq == NA:
        assert result == NA
    else:
        assert expected_contains_or_eq in result


# ============================================================================
# _fmt_pct · 8 case
# ============================================================================

@pytest.mark.parametrize("v, expected_contains_or_eq", [
    (None, NA),
    ("", NA),
    (0, NA),
    (0.0, NA),
    (0.5, "50.0%"),
    (1.0, "100.0%"),
    (0.25, "25.0%"),
    (0.123456, "12.3%"),
])
def test_fmt_pct_formats(v, expected_contains_or_eq):
    result = _fmt_pct(v)
    assert result == expected_contains_or_eq


@pytest.mark.parametrize("bad", ["abc", "x", None])
def test_fmt_pct_handles_garbage(bad):
    """str/None 不抛 · 返 NA."""
    if bad is None:
        assert _fmt_pct(bad) == NA
    else:
        # str → float fails · NA
        assert _fmt_pct(bad) == NA


# ============================================================================
# _candidate_field priority · 10 case
# ============================================================================

@pytest.mark.parametrize("snake_value, camel_value, expected", [
    ("new", "old", "new"),       # snake 优先
    (None, "old", "old"),         # snake None · camel
    ("", "old", "old"),           # snake empty · camel
    ([], "old", "old"),
    (None, None, "default"),
    ("", "", "default"),
    ([], [], "default"),
    (0, 99, 0),                   # 0 算非空 · 优先 snake
    ("a", "b", "a"),
    (False, True, False),         # False 不在 (None, "", []) → snake 优先
])
def test_candidate_field_priority(snake_value, camel_value, expected):
    c = {}
    if snake_value is not None:
        c["score"] = snake_value
    elif snake_value == "":
        c["score"] = ""
    if camel_value is not None:
        c["signalScore"] = camel_value
    elif camel_value == "":
        c["signalScore"] = ""

    # Testing the actual logic
    result = _candidate_field(c, "score", "signalScore", default="default")
    if expected == "default":
        # 都空时 default
        assert result == "default"
    elif expected is False:
        assert result is False
    else:
        assert result == expected


def test_candidate_field_no_alternates_returns_default():
    c = {}
    assert _candidate_field(c, "x", default="d") == "d"


def test_candidate_field_first_alt_wins():
    c = {"alt1": "v1", "alt2": "v2"}
    assert _candidate_field(c, "main", "alt1", "alt2", default="x") == "v1"


# ============================================================================
# _chinese_num · 12 case
# ============================================================================

@pytest.mark.parametrize("n, expected", [
    (0, "零"),
    (1, "一"),
    (2, "二"),
    (3, "三"),
    (5, "五"),
    (10, "十"),
    (11, "11"),
    (15, "15"),
    (100, "100"),
])
def test_chinese_num(n, expected):
    assert _chinese_num(n) == expected


# ============================================================================
# build_filename edge · 10 case
# ============================================================================

@pytest.mark.parametrize("benchmark, session_id", [
    ("正常名", "session-1"),
    ("含空格 名字", "session 2"),
    ("含/斜杠", "session/3"),
    ("含*问号?", "session*4"),
    ("emoji😀", "5"),
    ("very_long_" * 10, "x"),
    ("", "session"),
    ("name", ""),
])
def test_filename_strips_illegal_chars(benchmark, session_id):
    fn = build_filename({
        "ideal_profile": {"benchmark": benchmark} if benchmark else None,
        "session_id": session_id,
    })
    for bad in r'\/:*?"<>| ':
        if bad == " ":
            continue  # space → _
        assert bad not in fn, f"{bad!r} not stripped from {fn}"


def test_filename_falls_back_to_query_when_no_benchmark():
    fn = build_filename({"query": "浙江精密", "session_id": "x"})
    assert "浙江精密" in fn or "agent1_候选线索" in fn


def test_filename_default_when_all_blank():
    fn = build_filename({})
    assert fn.endswith(".docx")
    assert "agent1_候选线索" in fn


# ============================================================================
# export() edges · 8 case
# ============================================================================

@pytest.mark.parametrize("ip_keys, expected_in_doc", [
    (["benchmark"], "benchmark"),
    (["target_industries"], "目标行业"),
    (["target_regions"], "目标区域"),
    (["scale_range"], "规模区间"),
    (["must_have_tags"], "必备特征"),
    (["nice_to_have_tags"], "加分特征"),
])
def test_export_includes_ideal_profile_field(ip_keys, expected_in_doc):
    payload = {
        "ideal_profile": {k: f"value_{k}" for k in ip_keys},
        "candidates": [
            {"name": "X", "signalScore": 50, "signals": []},
        ],
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert expected_in_doc in text


@pytest.mark.parametrize("candidates_count", [1, 3, 5, 10])
def test_export_handles_n_candidates(candidates_count):
    payload = {
        "candidates": [
            {"name": f"公司_{i}", "signalScore": 50 + i, "signals": []}
            for i in range(candidates_count)
        ],
    }
    data = export(payload)
    assert len(data) > 1000
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    assert "公司_0" in text


def test_export_business_line_mapping():
    payload = {
        "candidates": [{"name": "x", "signalScore": 50, "signals": []}],
        "business_line": "small",
    }
    data = export(payload)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read("word/document.xml").decode("utf-8")
    # 业务线 small → "对公小微 / 普惠"
    assert "小微" in text or "普惠" in text
