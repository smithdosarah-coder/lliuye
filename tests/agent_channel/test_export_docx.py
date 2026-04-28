"""Unit + endpoint tests for ``agent_channel.export_docx`` · Stage B.7 · gap #12.

锁定:
  - .docx 字节是合法 zip · 含 word/document.xml + [Content_Types].xml
  - 全字段 payload (mock-style) · IdealProfile + Top10 + radar/dims/products/pitch
    全部进 docx
  - 极简 payload (live-style · 仅 candidates) · 仍渲出合法文件 · 不抛
  - filename 含 benchmark + session_id · 非法字符已过滤
  - POST /api/channel/export_docx 端点 200 · content-disposition attachment + UTF-8
    + Content-Type vnd...wordprocessingml.document
"""
from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient

from agent_channel.api import app
from agent_channel.export_docx import build_filename, export


def _full_candidate(rank: int = 1) -> dict:
    """完整 B.5 字段 candidate · mock-style."""
    return {
        # legacy camelCase
        "name": f"浙江精密样本-{rank} 有限公司",
        "signalScore": 60 + rank,
        "signalCount": 3,
        "source": "external",
        "signals": [
            {
                "type": "bidding",
                "title": f"中标 {rank}500 万订单 · 精密机械装备",
                "detail": "杭州 萧山 精密机械产线 · 一期 50 台设备采购",
                "date": "2026-04-15",
                "source": "chinabidding",
                "url": "https://chinabidding.cn/xxx",
            },
            {
                "type": "growth",
                "title": "扩产新项目环评公示 浙江",
                "detail": "新建年产 5 万台精密齿轮产线",
                "date": "2026-03-20",
                "source": "gov.cn",
                "url": "https://env.gov.cn/yyy",
            },
        ],
        "region": "浙江",
        "industry": "精密零部件",
        "uscc": "913301020000000011",
        "registeredCapital": "5000 万",
        "founded": "2015-06-10",
        "legalRep": "张三",
        "employees": 180,
        "mainBusiness": "精密齿轮 / 轴承",
        "matchTags": [
            {"label": "近期扩产", "matched": True, "detail": "新建 5 万台齿轮产线"},
            {"label": "专精特新", "matched": True, "detail": "省级名单"},
        ],
        "recommendedProducts": ["设备贷 / 固定资产贷款", "流动资金贷款"],
        "pitch": "您好，注意到贵司中标 1500 万订单，我行可提供设备贷支持。",
        "dataSources": [{"label": "chinabidding", "hint": "..."}, {"label": "gov.cn", "hint": "..."}],
        # B.5 snake_case
        "score": 60 + rank,
        "geo": "浙江 · 杭州",
        "scale": "小型",
        "similarity": 0.78 - rank * 0.05,
        "radar_8axis": {
            "信号密度": 60,
            "行业匹配": 80,
            "区域匹配": 75,
            "规模匹配": 70,
            "近期活跃度": 50,
            "资质含金量": 60,
            "技术强度": 65,
            "相似度": int((0.78 - rank * 0.05) * 100),
        },
        "match_dimensions": [
            {"dim_name": "行业匹配", "hit_evidence": "目标 精密零部件 · 候选 精密零部件", "score": 90},
            {"dim_name": "区域匹配", "hit_evidence": "目标 浙江 · 候选 浙江·杭州", "score": 90},
            {"dim_name": "信号丰富度", "hit_evidence": "2 类 · 共 3 条", "score": 65},
        ],
        "product_recommendations": [
            {
                "product_name": "设备贷 / 固定资产贷款",
                "fit_score": 90,
                "intro": "针对企业新购置生产设备 / 厂房改扩建的中长期贷款 · 期限 3-5 年",
                "category": "对公贷款",
            },
            {
                "product_name": "流动资金贷款",
                "fit_score": 75,
                "intro": "用于日常经营周转 · 一年期 · 满足中标 / 订单交付前的备货资金需求",
                "category": "对公贷款",
            },
            {
                "product_name": "保理 / 应收质押融资",
                "fit_score": 60,
                "intro": "应收账款质押 / 转让 · 解决 B2B 账期占款 · 期限 3-12 月",
                "category": "供应链金融",
            },
        ],
        "pitch_scripts": [
            {
                "customer_name_placeholder": "{客户名}",
                "script_text": "您好，{客户名}，注意到贵司中标 1500 万订单，我行可提供设备贷。",
                "source": "agent6",
            }
        ],
    }


def _full_payload() -> dict:
    return {
        "session_id": "11111111-2222-4333-8444-555555555555",
        "ideal_profile": {
            "benchmark": "宁波华联轴承（标杆）",
            "target_industries": ["精密零部件", "装备制造"],
            "target_regions": ["浙江", "江苏"],
            "scale_range": "小型 · 50-300 人",
            "revenue_range": "5000 万 - 5 亿",
            "must_have_tags": ["专精特新", "高新技术"],
            "nice_to_have_tags": ["省级技术中心", "ISO9001"],
            "exclude_tags": ["失信被执行", "经营异常"],
            "policy_context": "浙江省制造业高质量发展若干政策",
            "qualifications": ["专精特新 (省级)", "高新技术企业"],
            "growth_stage": "成长期",
            "key_signals": ["中标", "扩产", "专利"],
            "reasoning": (
                "标杆客户为宁波华联轴承（轴承行业头部 · 专精特新省级）。"
                "look-alike 取行业 (精密零部件 / 装备制造) + 区域 (长三角浙江为主) +"
                "规模 (小型 5000 万-5 亿营收) + 资质 (专精特新 + 高新技术) 四维特征叠加。"
            ),
        },
        "candidates": [_full_candidate(i) for i in range(1, 4)],
        "business_line": "corporate",
        "client_manager": "王哲（华东·上海第一支行）",
        "query": "找像宁波华联轴承的小微精密零部件企业",
    }


def _docx_text(data: bytes) -> str:
    """读 docx 字节 · 返 word/document.xml 文本(用于断言内容)。"""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read("word/document.xml").decode("utf-8")


# ============================================================================
# Direct export() · full payload
# ============================================================================

def test_export_full_payload_returns_valid_docx_zip():
    data = export(_full_payload())
    assert len(data) > 5000, "non-trivial size expected"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
    assert "word/document.xml" in names
    assert "[Content_Types].xml" in names


def test_export_full_payload_contains_ideal_profile_section():
    data = export(_full_payload())
    text = _docx_text(data)
    assert "理想客户画像" in text
    assert "宁波华联轴承" in text
    assert "精密零部件" in text
    assert "专精特新" in text


def test_export_full_payload_contains_topN_overview_table():
    data = export(_full_payload())
    text = _docx_text(data)
    assert "Top3 候选企业概览" in text or "Top" in text
    # 候选企业名应进表
    assert "浙江精密样本-1 有限公司" in text
    assert "浙江精密样本-2 有限公司" in text


def test_export_full_payload_renders_per_candidate_detail():
    data = export(_full_payload())
    text = _docx_text(data)
    # 8 维 radar key
    assert "信号密度" in text
    assert "相似度" in text
    # match_dimensions
    assert "行业匹配" in text
    # product recommendations + intro
    assert "设备贷" in text
    assert "对公贷款" in text
    # pitch scripts placeholder
    assert "{客户名}" in text
    # 客户经理
    assert "王哲" in text


def test_export_full_payload_includes_disclaimer():
    data = export(_full_payload())
    text = _docx_text(data)
    assert "本地渲染" in text
    assert "无数据出境" in text


# ============================================================================
# Direct export() · 极简 live payload (仅 candidates · 无 ideal_profile)
# ============================================================================

def test_export_minimal_payload_no_ideal_profile():
    payload = {
        "candidates": [
            {
                "name": "极简候选公司",
                "signalScore": 30,
                "signals": [],
            }
        ],
    }
    data = export(payload)
    assert len(data) > 1500
    text = _docx_text(data)
    # 无 IdealProfile 时 · "理想客户画像" 标题不应出现
    assert "理想客户画像" not in text
    # 但概览表 + 候选明细 + 免责仍要有
    assert "极简候选公司" in text
    assert "本地渲染" in text


def test_export_empty_candidates_in_lib_call_still_works():
    """直接 export() 接受空 candidates · 渲一份"无候选"提示文档(不报错)。

    端点层会拦 400 · 但库函数本身要容忍空 list (灰度演示场景)。
    """
    payload = {"candidates": [], "client_manager": "测试"}
    data = export(payload)
    assert len(data) > 1500
    text = _docx_text(data)
    assert "无候选企业" in text


# ============================================================================
# build_filename
# ============================================================================

def test_build_filename_uses_benchmark_and_session_id():
    payload = _full_payload()
    fn = build_filename(payload)
    assert fn.endswith(".docx")
    assert "agent1_候选线索" in fn
    # benchmark 进文件名
    assert "宁波华联轴承" in fn or "宁波华联" in fn
    # session_id 进文件名
    assert "11111111" in fn


def test_build_filename_strips_illegal_chars():
    payload = {
        "session_id": "session/with\\bad?chars",
        "ideal_profile": {"benchmark": '客户*名:"with"<illegal>|/chars'},
        "candidates": [],
    }
    fn = build_filename(payload)
    for bad in r'\/:*?"<>|':
        assert bad not in fn, f"illegal char {bad!r} present in {fn}"


def test_build_filename_falls_back_to_query_or_default():
    fn1 = build_filename({"query": "浙江 精密零部件 找像的", "candidates": []})
    assert "agent1_候选线索" in fn1
    assert fn1.endswith(".docx")

    fn2 = build_filename({"candidates": []})  # 全空兜底
    assert "agent1_候选线索" in fn2
    assert "客户" in fn2 or "look" in fn2 or len(fn2) > 20


# ============================================================================
# POST /api/channel/export_docx · 端点 smoke
# ============================================================================

def test_endpoint_returns_docx_with_attachment_disposition():
    client = TestClient(app)
    resp = client.post("/api/channel/export_docx", json=_full_payload())
    assert resp.status_code == 200, resp.text
    ct = resp.headers["content-type"]
    assert "wordprocessingml.document" in ct
    cd = resp.headers["content-disposition"]
    assert "attachment" in cd
    assert "filename*=UTF-8''" in cd  # RFC 6266 中文文件名编码段
    # 真 docx zip
    body = resp.content
    assert len(body) > 5000
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        assert "word/document.xml" in z.namelist()
    # 自定义统计 header
    assert int(resp.headers["X-Agent1-Export-Candidates"]) == 3
    assert resp.headers["X-Agent1-Export-Type"] == "docx"


def test_endpoint_rejects_empty_candidates():
    client = TestClient(app)
    resp = client.post(
        "/api/channel/export_docx",
        json={"candidates": [], "session_id": "x"},
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("error", {}).get("code") == "VALIDATION_FAILED"


def test_endpoint_minimal_payload_live_path():
    """live 路径模拟 · 仅 candidates · 端点仍 200."""
    client = TestClient(app)
    resp = client.post(
        "/api/channel/export_docx",
        json={
            "candidates": [
                {"name": "Live 模式公司", "signalScore": 25, "signals": []},
            ],
        },
    )
    assert resp.status_code == 200
    assert "wordprocessingml.document" in resp.headers["content-type"]
    assert len(resp.content) > 1500
