"""CandidateProfile 单测 — 覆盖工厂 / handoff JSON / 额度启发式。

关键契约：
- EnterpriseProfile 子字段是 Agent3 只读消费点
- candidate_profile 是 Agent1 绿区结构
- profile_id / session_id 严格 UUID v4 格式
"""
from __future__ import annotations

import re
import uuid

from agent_channel.candidate_profile import (
    AMOUNT_CAP_YUAN,
    SCHEMA_VERSION,
    CandidateProfile,
    _estimate_amount_yuan,
    _parse_capital_yuan,
    _signal_score_to_match,
)

UUID_V4_RE = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$"
)


def _sample_candidate_dict() -> dict:
    return {
        "name": "浙江精密零部件有限公司",
        "uscc": "913301020000000011",
        "legalRep": "张三",
        "registeredCapital": "5000 万",
        "founded": "2015-06-10",
        "industry": "未获取",
        "region": "浙江",
        "employees": 120,
        "mainBusiness": "精密零部件",
        "signalScore": 45,
        "signalCount": 3,
        "signalTypes": ["bidding", "growth", "tech"],
        "belowDiversityGate": False,
        "signals": [
            {
                "type": "bidding", "title": "中标 2000 万订单",
                "detail": "一期 50 台设备采购",
                "date": "2026-03-20", "source": "chinabidding",
                "url": "https://chinabidding.cn/xxx",
            },
            {
                "type": "growth", "title": "扩产新项目",
                "detail": "环评公示",
                "date": "2026-02-15", "source": "gov.cn",
                "url": "https://env.gov.cn/yyy",
            },
            {
                "type": "tech", "title": "新专利授权",
                "detail": "精密加工",
                "date": "", "source": "cnipa",
                "url": "",
            },
        ],
        "recommendedProducts": ["设备贷 / 固定资产贷款", "流动资金贷款"],
        "pitch": "您好...",
        "dataSources": [
            {"label": "chinabidding", "hint": "..."},
            {"label": "gov.cn", "hint": "..."},
        ],
    }


def test_profile_id_and_session_id_are_uuid_v4():
    session_id = str(uuid.uuid4())
    profile = CandidateProfile.from_candidate_dict(
        _sample_candidate_dict(), session_id=session_id
    )
    assert UUID_V4_RE.match(profile.profile_id), profile.profile_id
    assert profile.session_id == session_id


def test_enterprise_profile_subset_is_agent3_consumable():
    profile = CandidateProfile.from_candidate_dict(
        _sample_candidate_dict(), session_id="s"
    )
    ep = profile.enterprise_profile
    assert ep.company_name == "浙江精密零部件有限公司"
    assert ep.unified_credit_code == "913301020000000011"
    assert ep.legal_representative == "张三"
    assert ep.employee_count == 120
    # '未获取' 占位符被清成空串
    assert ep.industry == ""


def test_signal_timeline_sorted_by_date_desc():
    profile = CandidateProfile.from_candidate_dict(
        _sample_candidate_dict(), session_id="s"
    )
    dates = [s.signal_date for s in profile.signal_timeline]
    # 空日期沉底
    assert dates == ["2026-03-20", "2026-02-15", ""]


def test_source_urls_dedup_and_drop_empty():
    profile = CandidateProfile.from_candidate_dict(
        _sample_candidate_dict(), session_id="s"
    )
    assert profile.source_urls == [
        "https://chinabidding.cn/xxx", "https://env.gov.cn/yyy",
    ]


def test_to_handoff_json_has_both_layers():
    profile = CandidateProfile.from_candidate_dict(
        _sample_candidate_dict(), session_id="s"
    )
    j = profile.to_handoff_json()
    assert j["schema_version"] == SCHEMA_VERSION
    assert "candidate_profile" in j
    assert "enterprise_profile" in j
    # Agent3 只读 enterprise_profile 子字段
    assert j["enterprise_profile"]["company_name"] == "浙江精密零部件有限公司"
    # candidate_profile 暴露 Agent1 专属
    assert j["candidate_profile"]["match_score"] == 45
    assert j["candidate_profile"]["business_line"] == "corporate"


def test_match_score_clipped_to_0_100():
    assert _signal_score_to_match(-5) == 0
    assert _signal_score_to_match(200) == 100
    assert _signal_score_to_match(65) == 65
    assert _signal_score_to_match("abc") == 0


def test_parse_capital_yuan():
    assert _parse_capital_yuan("500 万") == 5_000_000
    assert _parse_capital_yuan("1.2 亿") == 120_000_000
    assert _parse_capital_yuan("未获取") == 0
    assert _parse_capital_yuan("") == 0


def test_estimate_amount_respects_cap_and_leverage():
    # 无资本信息：按信号上限
    amt = _estimate_amount_yuan(["bidding", "growth", "recognition", "tech"], 0)
    assert amt == min(
        AMOUNT_CAP_YUAN,
        5_000_000 + 3_000_000 + 3_000_000 + 2_000_000 + 1_000_000,
    )
    # 小资本企业：被杠杆约束拉低（capital × 0.5）
    amt_small = _estimate_amount_yuan(["bidding"], 1_000_000)
    assert amt_small == 500_000
