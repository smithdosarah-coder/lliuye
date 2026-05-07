"""Unit tests for ``agent_channel.sse_extras`` · Stage B.5 + Q-041 fix-forward.

锁定:
  - Q-041 4 字段 (industry/geo/scale/similarity) 不再硬编 NA
  - 8 维 radar 全字段非空 0-100
  - match_dimensions / product_recommendations / pitch_scripts 形状契约
  - ``_build_final_output`` 输出包 legacy + 新 snake_case 双键
"""
from __future__ import annotations

from agent_channel.sse_extras import (
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


def _sample_item() -> dict:
    """杭州精密制造 · 中标 + 扩产 + 专精特新 信号样本。"""
    return {
        "company_name": "浙江精密零部件有限公司",
        "signalScore": 60,
        "signalCount": 3,
        "signals": [
            {
                "signal_type": "bidding",
                "signal_title": "中标 2000 万订单 · 精密机械装备",
                "signal_detail": "杭州 萧山 精密机械产线 · 一期 50 台设备采购",
                "signal_date": "2026-04-15",
                "signal_source": "chinabidding",
                "source_url": "https://chinabidding.cn/xxx",
            },
            {
                "signal_type": "growth",
                "signal_title": "扩产新项目环评公示 浙江",
                "signal_detail": "新建年产 5 万台精密齿轮产线",
                "signal_date": "2026-03-20",
                "signal_source": "gov.cn",
                "source_url": "https://env.gov.cn/yyy",
            },
            {
                "signal_type": "recognition",
                "signal_title": "入选浙江省专精特新企业名单",
                "signal_detail": "省级 专精特新 中小企业",
                "signal_date": "2026-01-10",
                "signal_source": "zjjxt.gov.cn",
                "source_url": "https://zjjxt.gov.cn/zzz",
            },
        ],
        "qcc": {
            "industry": "精密零部件 / 装备制造",
            "registered_address": "浙江省杭州市萧山区精进路 200 号",
            "registered_capital": "5000 万",
            "founded": "2015-06-10",
            "uscc": "913301020000000011",
            "legalRep": "张三",
            "employees": 180,
        },
        "matchTags": [
            {"label": "近期扩产", "matched": True, "detail": "新建年产 5 万台齿轮产线"},
            {"label": "专精特新", "matched": True, "detail": "入选省级名单"},
            {"label": "近期中标", "matched": True, "detail": "中标 2000 万订单"},
        ],
        "recommendedProducts": [
            "设备贷 / 固定资产贷款",
            "流动资金贷款",
        ],
        "pitch": "您好，注意到浙江精密零部件有限公司中标 2000 万订单，我行可提供设备贷支持。",
    }


def _sample_tags() -> list[dict]:
    return [
        {"category": "区域", "value": "浙江"},
        {"category": "行业", "value": "精密零部件"},
    ]


def test_extract_metadata_uses_qcc_industry():
    md = extract_metadata(_sample_item())
    assert md["industry"], "industry must not be empty"
    assert md["industry"] != NA, f"Q-041 fix: industry hardcoded NA bug · got {md['industry']}"
    assert "精密" in md["industry"] or "装备" in md["industry"]


def test_extract_metadata_geo_from_address():
    md = extract_metadata(_sample_item())
    assert md["geo"] != NA, f"Q-041 fix: geo hardcoded NA · got {md['geo']}"
    # 应抽出 浙江 或 杭州 (regions list 命中)
    assert any(r in md["geo"] for r in ("浙江", "杭州", "萧山"))


def test_extract_metadata_scale_from_capital():
    md = extract_metadata(_sample_item())
    assert md["scale"] != NA, f"Q-041 fix: scale hardcoded NA · got {md['scale']}"
    # 5000 万注册 + 180 员工 → 小型 (capital 路径) 或 小型 (员工 < 300)
    assert md["scale"] in ("微型", "小型", "中型", "大型")


def test_extract_metadata_fallback_na_when_blank():
    bare = {"company_name": "未知公司", "signals": [], "qcc": {}}
    md = extract_metadata(bare)
    # 全 NA 兜底 · 不会抛异常
    assert md["industry"] == NA
    assert md["geo"] == NA
    assert md["scale"] == NA


def test_compute_similarity_in_range():
    sim = compute_similarity(_sample_item(), "浙江 精密零部件 找类似的", _sample_tags())
    assert 0.0 <= sim <= 1.0
    # 强匹配 (浙江 + 精密零部件 命中) · 应 > 0.4
    assert sim > 0.4, f"strong match expected sim > 0.4 · got {sim}"


def test_compute_similarity_no_overlap():
    sim = compute_similarity(_sample_item(), "深圳 SaaS B2B", [
        {"category": "区域", "value": "深圳"},
        {"category": "行业", "value": "SaaS"},
    ])
    # 完全不沾边的 query · 应 ≤ 0.5
    assert sim <= 0.5


def test_build_radar_8axis_full_8_keys_in_range():
    md = extract_metadata(_sample_item())
    radar = build_radar_8axis(_sample_item(), 0.7, md, _sample_tags())
    assert len(radar) == 8, f"expected 8 axes · got {len(radar)}"
    for axis, score in radar.items():
        assert isinstance(axis, str) and axis
        assert isinstance(score, int)
        assert 0 <= score <= 100, f"{axis}={score} out of range"


def test_build_match_dimensions_shape():
    md = extract_metadata(_sample_item())
    dims = build_match_dimensions(_sample_item(), _sample_tags(), md)
    assert dims, "match_dimensions empty"
    for d in dims:
        assert "dim_name" in d
        assert "hit_evidence" in d
        assert "score" in d
        assert isinstance(d["score"], int)
        assert 0 <= d["score"] <= 100


def test_build_product_recommendations_top3_structured():
    products = build_product_recommendations(_sample_item(), similarity=0.7)
    assert len(products) == 3, f"top3 expected · got {len(products)}"
    for p in products:
        assert "product_name" in p
        assert "fit_score" in p
        assert "intro" in p
        assert "category" in p
        assert isinstance(p["fit_score"], int)
        assert 40 <= p["fit_score"] <= 100


def test_build_pitch_scripts_replaces_company_with_placeholder():
    scripts = build_pitch_scripts(_sample_item())
    assert len(scripts) == 1
    s = scripts[0]
    assert s["customer_name_placeholder"] == CUSTOMER_NAME_PLACEHOLDER
    assert CUSTOMER_NAME_PLACEHOLDER in s["script_text"]
    # 公司名应已替换 · 原始 pitch 含 "浙江精密零部件有限公司" 应被替换为 {客户名}
    assert "浙江精密零部件有限公司" not in s["script_text"]


def test_build_pitch_scripts_empty_when_no_pitch():
    item = _sample_item()
    item["pitch"] = ""
    assert build_pitch_scripts(item) == []


def test_enrich_candidate_full_keys():
    extras = enrich_candidate(_sample_item(), "浙江 精密零部件", _sample_tags())
    expected_keys = {
        # Q-041 4 字段 (不破)
        "industry", "geo", "scale", "similarity",
        # Q-054 B1 第 5 维度 + 降级原因
        "signal_density", "signal_density_reason",
        # B.5 衍生
        "radar_8axis", "match_dimensions",
        "product_recommendations", "pitch_scripts",
    }
    assert set(extras.keys()) == expected_keys, (
        f"extras keys mismatch · got {set(extras.keys())}"
    )
    assert extras["industry"] != NA
    assert extras["geo"] != NA
    assert extras["scale"] != NA
    assert isinstance(extras["similarity"], float)
    assert 0.0 <= extras["similarity"] <= 1.0
    # Q-054 第 5 维度 · 0-1 float · reason 是 str (空 = 正常 / 非空 = 降级)
    assert isinstance(extras["signal_density"], float)
    assert 0.0 <= extras["signal_density"] <= 1.0
    assert isinstance(extras["signal_density_reason"], str)


def test_build_final_output_emits_legacy_and_new_keys():
    """`_build_final_output` 整合 · legacy camelCase + 新 snake_case 双键并存。"""
    from agent_channel.realtime_stream import _build_final_output

    enriched = [_sample_item()]
    candidates = _build_final_output(
        enriched, _sample_tags(), query="浙江 精密零部件 找像的", llm=None,
    )
    assert len(candidates) == 1
    c = candidates[0]

    # legacy camelCase (production 已消费 · 不动)
    legacy_keys = {
        "name", "signalScore", "signalCount", "source", "signals",
        "region", "industry", "uscc", "registeredCapital", "founded",
        "legalRep", "employees", "mainBusiness",
        "matchTags", "recommendedProducts", "pitch", "dataSources",
    }
    for k in legacy_keys:
        assert k in c, f"legacy key {k} missing"

    # B.5 新 snake_case (前端 b.5b 步消费) + Q-054 5 维度
    new_keys = {
        "score", "geo", "scale", "similarity",
        "signal_density", "signal_density_reason",
        "radar_8axis", "match_dimensions",
        "product_recommendations", "pitch_scripts",
    }
    for k in new_keys:
        assert k in c, f"new key {k} missing"

    # Q-041 fix:industry / geo / scale / similarity 必非 NA 兜底
    assert c["industry"] != NA, "Q-041 industry still NA · check qcc + extras path"
    assert c["geo"] != NA, "Q-041 geo still NA"
    assert c["scale"] != NA, "Q-041 scale still NA"
    assert isinstance(c["similarity"], float)
    assert 0.0 <= c["similarity"] <= 1.0

    # Q-054 B1 · 第 5 维度 candidate metadata 共生
    assert isinstance(c["signal_density"], float), "signal_density must be float"
    assert 0.0 <= c["signal_density"] <= 1.0, "signal_density must be in [0, 1]"

    # score 是 signalScore 别名
    assert c["score"] == c["signalScore"]


def test_build_final_output_handles_blank_qcc():
    """qcc 全空 · 走 signal text 兜底 · 不抛异常 · 输出有 NA."""
    from agent_channel.realtime_stream import _build_final_output

    item = {
        "company_name": "空白公司",
        "signalScore": 0,
        "signalCount": 0,
        "signals": [],
        "qcc": {},
        "matchTags": [],
        "recommendedProducts": [],
        "pitch": "",
    }
    candidates = _build_final_output([item], [], query="", llm=None)
    assert len(candidates) == 1
    c = candidates[0]
    # NA 兜底 · 不抛异常
    assert c["industry"] == NA
    assert c["geo"] == NA
    assert c["scale"] == NA
    assert c["similarity"] == 0.0
    # 8 维 radar 仍有结构
    assert isinstance(c["radar_8axis"], dict)
    assert len(c["radar_8axis"]) == 8
    # pitch_scripts 空 list (pitch 为空)
    assert c["pitch_scripts"] == []
    # product_recommendations 仍补到 3 (fallback 链)
    assert len(c["product_recommendations"]) == 3
