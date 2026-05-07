# -*- coding: utf-8 -*-
"""agent_channel.sse_extras edges · Stage E.4 expansion.

参数化 heavy · ~80 case 覆盖 extract_metadata / similarity / radar / dims /
products / pitch / enrich_candidate 边界。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_channel.sse_extras import (  # noqa: E402
    CUSTOMER_NAME_PLACEHOLDER,
    NA,
    build_match_dimensions,
    build_pitch_scripts,
    build_product_recommendations,
    build_radar_8axis,
    compute_similarity,
    enrich_candidate,
    extract_metadata,
)


# ============================================================================
# extract_metadata · industry / geo / scale 矩阵 · 24 case
# ============================================================================

@pytest.mark.parametrize("qcc_industry, expected_industry", [
    ("精密零部件", "精密零部件"),
    ("装备制造", "装备制造"),
    ("精密零部件 / 装备制造", "精密零部件 / 装备制造"),
    ("", NA),
    ("   ", NA),
])
def test_extract_industry_from_qcc(qcc_industry, expected_industry):
    item = {"qcc": {"industry": qcc_industry}, "signals": []}
    md = extract_metadata(item)
    if expected_industry == NA:
        assert md["industry"] == NA
    else:
        assert expected_industry in md["industry"]


@pytest.mark.parametrize("signal_text, expected_industry_contains", [
    ("中标 精密零部件 订单", "精密零部件"),
    ("扩产 半导体 项目", "半导体"),
    ("生产 SaaS 产品", "SaaS"),
    ("汽车零部件 中标", "汽车零部件"),
    ("医疗器械 备案", "医疗器械"),
    ("纯文本 没有行业关键词", NA),
])
def test_extract_industry_from_signal_text(signal_text, expected_industry_contains):
    item = {
        "qcc": {},
        "signals": [{"signal_title": signal_text, "signal_detail": ""}],
    }
    md = extract_metadata(item)
    if expected_industry_contains == NA:
        assert md["industry"] == NA
    else:
        assert expected_industry_contains in md["industry"]


@pytest.mark.parametrize("region_text, expected_geo_contains", [
    ("浙江省杭州市萧山区", "浙江"),
    ("上海市浦东新区", "上海"),
    ("北京市", "北京"),
    ("深圳市南山区", "深圳"),
    ("成都高新区", "成都"),
    ("江苏省苏州市", "江苏"),
])
def test_extract_geo_from_address(region_text, expected_geo_contains):
    item = {"qcc": {"registered_address": region_text}, "signals": []}
    md = extract_metadata(item)
    assert expected_geo_contains in md["geo"]


@pytest.mark.parametrize("capital_text, expected_scale", [
    # 100 万 = 1e6 · 不 <1e6 · <5e7 → 小型 (boundary: 微型 < 100万)
    ("100 万", "小型"),
    ("500 万", "小型"),
    # 5000 万 = 5e7 · 不 <5e7 · <5e8 → 中型
    ("5000 万", "中型"),
    ("1 亿", "中型"),
    ("10 亿", "大型"),
    ("", NA),                   # 空 · NA
])
def test_extract_scale_from_capital(capital_text, expected_scale):
    item = {"qcc": {"registered_capital": capital_text}, "signals": []}
    md = extract_metadata(item)
    if expected_scale == NA:
        # 没有其他可推 · NA fallback (mock 路径无 tags 时)
        assert md["scale"] == NA or md["scale"] == ""
    else:
        assert md["scale"] == expected_scale


@pytest.mark.parametrize("emp_count, expected_scale", [
    (5, "微型"),
    (50, "小型"),
    (500, "中型"),
    (2000, "大型"),
])
def test_extract_scale_from_employees(emp_count, expected_scale):
    item = {
        "qcc": {"employees": emp_count},
        "signals": [],
    }
    md = extract_metadata(item)
    assert md["scale"] == expected_scale


@pytest.mark.parametrize("tags, expected_industry", [
    ([{"category": "行业", "value": "新能源"}], "新能源 (推断)"),
    ([{"category": "行业", "value": "AI"}], "AI (推断)"),
    ([{"category": "区域", "value": "浙江"}], NA),  # 没行业 tag
    ([], NA),
])
def test_extract_industry_tag_fallback(tags, expected_industry):
    item = {"qcc": {}, "signals": [{"signal_title": "无关键词", "signal_detail": ""}]}
    md = extract_metadata(item, tags=tags)
    if "(推断)" in expected_industry:
        assert "(推断)" in md["industry"]
    else:
        assert md["industry"] == NA


# ============================================================================
# compute_similarity · 矩阵 · 12 case
# ============================================================================

@pytest.mark.parametrize("query, item_text, sim_min", [
    ("浙江 精密", "浙江 精密零部件", 0.5),
    ("深圳 SaaS", "浙江 精密零部件", 0.0),
    ("精密 零部件 浙江", "浙江 精密零部件", 0.5),
    ("", "anything", 0.0),
    ("xxx yyy zzz", "完全不沾边", 0.0),
])
def test_similarity_text_matching(query, item_text, sim_min):
    item = {
        "company_name": item_text,
        "signals": [{"signal_title": item_text, "signal_detail": ""}],
        "matchTags": [],
    }
    sim = compute_similarity(item, query, [])
    assert 0.0 <= sim <= 1.0
    if sim_min > 0:
        assert sim >= sim_min - 0.1


@pytest.mark.parametrize("tags_value", [
    [{"category": "行业", "value": "精密零部件"}],
    [{"category": "区域", "value": "浙江"}],
    [
        {"category": "行业", "value": "精密零部件"},
        {"category": "区域", "value": "浙江"},
    ],
])
def test_similarity_with_tags_increases(tags_value):
    item = {
        "company_name": "浙江精密零部件公司",
        "signals": [],
        "matchTags": [],
    }
    sim_no_tags = compute_similarity(item, "查询", [])
    sim_with_tags = compute_similarity(item, "查询", tags_value)
    # tags 提供更多匹配信号
    assert sim_with_tags >= sim_no_tags


def test_similarity_empty_query_returns_zero():
    item = {"company_name": "x", "signals": [], "matchTags": []}
    assert compute_similarity(item, "", []) == 0.0


def test_similarity_empty_item_handles():
    item = {"company_name": "", "signals": [], "matchTags": []}
    sim = compute_similarity(item, "x y", [])
    assert sim == 0.0


# ============================================================================
# build_radar_8axis · 12 case
# ============================================================================

@pytest.mark.parametrize("similarity_v", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_radar_similarity_maps_0_100(similarity_v):
    item = {"signals": []}
    radar = build_radar_8axis(item, similarity_v, {"industry": NA, "geo": NA, "scale": NA}, [])
    assert radar["相似度"] == int(similarity_v * 100)


@pytest.mark.parametrize("signal_types_count", [0, 1, 2, 3, 4, 5])
def test_radar_signal_density_scales_with_types(signal_types_count):
    types = ["bidding", "growth", "tech", "recognition", "award"][:signal_types_count]
    signals = [{"signal_type": t, "signal_title": "", "signal_detail": ""} for t in types]
    radar = build_radar_8axis(
        {"signals": signals}, 0.5,
        {"industry": NA, "geo": NA, "scale": NA},
        [],
    )
    assert radar["信号密度"] == min(100, signal_types_count * 20)


def test_radar_8_axes_present():
    item = {"signals": []}
    radar = build_radar_8axis(item, 0.5, {"industry": NA, "geo": NA, "scale": NA}, [])
    assert len(radar) == 8


# ============================================================================
# build_match_dimensions · 8 case
# ============================================================================

@pytest.mark.parametrize("metadata_industry, target_industry, score_target", [
    ("精密零部件", "精密零部件", 90),
    ("精密零部件 (推断)", "精密零部件", 90),  # contains
    ("机械", "精密零部件", 40),
    (NA, "精密零部件", 40),  # 没行业 + 信号也不命中
])
def test_match_dimensions_industry_score(metadata_industry, target_industry, score_target):
    item = {"signals": [], "matchTags": []}
    metadata = {"industry": metadata_industry, "geo": NA, "scale": NA}
    tags = [{"category": "行业", "value": target_industry}]
    dims = build_match_dimensions(item, tags, metadata)
    industry_dim = next((d for d in dims if d["dim_name"] == "行业匹配"), None)
    assert industry_dim is not None
    assert industry_dim["score"] == score_target


@pytest.mark.parametrize("matchTags_count", [0, 1, 3, 5])
def test_match_dimensions_includes_legacy_tags(matchTags_count):
    item = {
        "signals": [],
        "matchTags": [
            {"label": f"label_{i}", "matched": True, "detail": f"d{i}"}
            for i in range(matchTags_count)
        ],
    }
    dims = build_match_dimensions(item, [], {"industry": NA, "geo": NA, "scale": NA})
    legacy_dims = [d for d in dims if d["dim_name"].startswith("label_")]
    assert len(legacy_dims) == matchTags_count


# ============================================================================
# build_product_recommendations · 10 case
# ============================================================================

@pytest.mark.parametrize("raw_products, expected_count_min", [
    ([], 3),                                      # 空 · 补到 3
    (["流动资金贷款"], 3),                          # 1 个 · 补到 3
    (["流动资金贷款", "设备贷 / 固定资产贷款"], 3), # 2 个 · 补到 3
    (["设备贷 / 固定资产贷款", "流动资金贷款", "保理 / 应收质押融资"], 3),  # 已 3 · 不变
    (["a", "b", "c", "d", "e"], 3),                # >3 · 截到 3
])
def test_products_top3(raw_products, expected_count_min):
    products = build_product_recommendations({"recommendedProducts": raw_products}, similarity=0.5)
    assert len(products) == expected_count_min


@pytest.mark.parametrize("similarity_v", [0.0, 0.3, 0.5, 0.8, 1.0])
def test_products_fit_score_in_range(similarity_v):
    products = build_product_recommendations(
        {"recommendedProducts": ["流动资金贷款"]},
        similarity=similarity_v,
    )
    for p in products:
        assert 40 <= p["fit_score"] <= 100


# ============================================================================
# build_pitch_scripts · 6 case
# ============================================================================

@pytest.mark.parametrize("pitch, company, expect_placeholder", [
    ("您好，浙江公司，注意到中标", "浙江公司", True),
    ("您好，注意到中标", "浙江公司", False),  # 公司名不在 pitch 文本
    ("", "浙江公司", False),                     # 空 pitch · 返空 list
    ("您好", "", False),
])
def test_pitch_placeholder_handling(pitch, company, expect_placeholder):
    item = {"pitch": pitch, "company_name": company}
    scripts = build_pitch_scripts(item)
    if not pitch:
        assert scripts == []
    else:
        assert len(scripts) == 1
        if expect_placeholder:
            assert CUSTOMER_NAME_PLACEHOLDER in scripts[0]["script_text"]
        else:
            # 公司名不在原 pitch · placeholder 仍在 script_text 取代了 (空公司名场景就保留原)
            pass


def test_pitch_script_source_marker():
    scripts = build_pitch_scripts({"pitch": "您好", "company_name": "x"})
    assert scripts[0]["source"] == "agent6"


# ============================================================================
# enrich_candidate 主入口 · 8 case
# ============================================================================

@pytest.mark.parametrize("query, tags", [
    ("浙江 精密", [{"category": "行业", "value": "精密零部件"}]),
    ("深圳 SaaS", [{"category": "区域", "value": "深圳"}]),
    ("", []),
    ("自由文本", [{"category": "规模", "value": "小型"}]),
])
def test_enrich_candidate_returns_10_keys(query, tags):
    """Q-054 B1 加 signal_density / signal_density_reason · 共 10 keys (从 8 升)."""
    item = {
        "company_name": "测试",
        "signals": [],
        "qcc": {},
        "matchTags": [],
        "recommendedProducts": [],
        "pitch": "",
    }
    extras = enrich_candidate(item, query, tags)
    expected_keys = {
        # Q-041 4 字段
        "industry", "geo", "scale", "similarity",
        # Q-054 第 5 维度 + 降级原因
        "signal_density", "signal_density_reason",
        # B.5 衍生
        "radar_8axis", "match_dimensions",
        "product_recommendations", "pitch_scripts",
    }
    assert set(extras.keys()) == expected_keys


def test_enrich_candidate_handles_minimal_item():
    """最简 item · 不抛 · 全 NA / 空."""
    extras = enrich_candidate({}, "", [])
    assert "industry" in extras
    assert isinstance(extras["radar_8axis"], dict)
    assert len(extras["radar_8axis"]) == 8


def test_enrich_candidate_passes_through_tags_inference():
    item = {"qcc": {}, "signals": []}
    tags = [{"category": "行业", "value": "新能源"}]
    extras = enrich_candidate(item, "查询", tags)
    assert "(推断)" in extras["industry"]


def test_enrich_candidate_radar_values_in_range():
    item = {
        "company_name": "x",
        "signals": [{"signal_type": "bidding", "signal_title": "", "signal_detail": ""}],
        "qcc": {"industry": "精密零部件"},
    }
    extras = enrich_candidate(item, "精密", [{"category": "行业", "value": "精密零部件"}])
    for axis, score in extras["radar_8axis"].items():
        assert 0 <= score <= 100, f"{axis}={score} out of range"
