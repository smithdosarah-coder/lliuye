# -*- coding: utf-8 -*-
"""Pytest for agent_channel.ideal_profile (master plan §B.6b · onboarding W-B-A3).

不调真 LLM · 全部用 fake llm_client 注入 · 离线可跑。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_channel.ideal_profile import (
    IdealProfile12,
    IdealProfileResult,
    KBNotFoundError,
    extract_ideal_profile,
    kb_blob_to_text,
    load_kb_blob,
)


# ---------------------------------------------------------------------------
# 测试用 fake LLM client
# ---------------------------------------------------------------------------


class _FakeLLMOK:
    """返回完整 12 维 JSON · confidence + reasoning 齐全."""

    def chat_json(self, system, user, schema_hint="", temperature=None):
        return {
            "ideal_profile": {
                "industry_focus": ["制造业", "智能装备"],
                "scale_preference": ["小型", "微型"],
                "geo_coverage": ["浙江", "江苏"],
                "stage": "成长期",
                "capital_relation": "独立民营",
                "business_size": "营收 1000-5000 万",
                "employee_size": "50-200 人",
                "customer_type": ["B2B", "整车厂"],
                "product_keywords": ["精密加工", "汽车零部件"],
                "value_chain_position": "上游",
                "growth_signals": ["专精特新", "发明专利≥3"],
                "risk_signals": ["应收账款偏高"],
            },
            "confidence_score": 0.85,
            "reasoning_text": "30 家客户 65% 浙江制造业 · 政策聚焦专精特新 · 因此画像锁定...",
        }


class _FakeLLMRootDims:
    """返回根级 12 维（不套 ideal_profile · 测兼容性）."""

    def chat_json(self, system, user, schema_hint="", temperature=None):
        return {
            "industry_focus": ["信息技术"],
            "scale_preference": ["中型"],
            "geo_coverage": ["深圳"],
            "stage": "成熟期",
            "capital_relation": "上市",
            "business_size": "营收 1 亿+",
            "employee_size": "200+ 人",
            "customer_type": ["B2C"],
            "product_keywords": ["SaaS"],
            "value_chain_position": "下游",
            "growth_signals": ["国家高新"],
            "risk_signals": [],
            "confidence_score": 0.6,
            "reasoning_text": "test root level",
        }


class _FakeLLMBad:
    """返回非 dict · 测降级."""

    def chat_json(self, system, user, schema_hint="", temperature=None):
        return "not a dict"


class _FakeLLMRaisesTimeout:
    def chat_json(self, system, user, schema_hint="", temperature=None):
        raise TimeoutError("simulated LLM timeout")


class _FakeLLMRaisesRuntime:
    def chat_json(self, system, user, schema_hint="", temperature=None):
        raise RuntimeError("chat_json failed retries")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_kb_blob():
    return {
        "kb_id": "test-kb-001",
        "kb_type": "customer_list",
        "n_rows": 30,
        "summary_text": "30 家浙江制造业小微客户 · 行业 TOP3 制造业 65% / 批发零售 18% / 建筑 9% · 标签 专精特新 32%",
        "rows": [
            {"company_name": "杭州精工", "industry": "制造业", "region": "浙江省杭州市"},
            {"company_name": "宁波智造", "industry": "制造业", "region": "浙江省宁波市"},
        ],
    }


# ---------------------------------------------------------------------------
# Test 1: happy path · 12 维全字段 shape
# ---------------------------------------------------------------------------


def test_extract_full_12_dims_shape(fake_kb_blob):
    """LLM 返回完整 12 维 → IdealProfileResult 12 维全到位 + confidence + reasoning."""
    result = extract_ideal_profile(fake_kb_blob, kb_type="customer_list", llm_client=_FakeLLMOK())

    assert isinstance(result, IdealProfileResult)
    assert isinstance(result.ideal_profile, IdealProfile12)

    # 12 维全部存在（Pydantic 字段断言）
    expected_dims = {
        "industry_focus", "scale_preference", "geo_coverage", "stage",
        "capital_relation", "business_size", "employee_size", "customer_type",
        "product_keywords", "value_chain_position", "growth_signals", "risk_signals",
    }
    actual_dims = set(IdealProfile12.model_fields.keys())
    assert actual_dims == expected_dims, f"12 维缺失或多出: {actual_dims ^ expected_dims}"

    # 抽样验内容
    assert "制造业" in result.ideal_profile.industry_focus
    assert result.ideal_profile.stage == "成长期"
    assert "上游" == result.ideal_profile.value_chain_position
    assert result.confidence_score == 0.85
    assert "30 家客户" in result.reasoning_text


def test_root_level_12_dims_compat(fake_kb_blob):
    """LLM 返回根级 12 维（无 ideal_profile 包装）也能解析."""
    result = extract_ideal_profile(fake_kb_blob, kb_type="customer_list", llm_client=_FakeLLMRootDims())

    assert result.ideal_profile.stage == "成熟期"
    assert "SaaS" in result.ideal_profile.product_keywords
    assert result.confidence_score == 0.6


# ---------------------------------------------------------------------------
# Test 2: degrade path · 非 dict 返回
# ---------------------------------------------------------------------------


def test_degrade_on_non_dict_llm_output(fake_kb_blob):
    """LLM 返回非 dict → 全空 profile + confidence=0.0 + 标降级原因."""
    result = extract_ideal_profile(fake_kb_blob, kb_type="customer_list", llm_client=_FakeLLMBad())

    assert result.ideal_profile.industry_focus == []
    assert result.ideal_profile.stage == ""
    assert result.confidence_score == 0.0
    assert "降级" in result.reasoning_text or "已降级" in result.reasoning_text


def test_degrade_on_runtime_error(fake_kb_blob):
    """LLM raise RuntimeError (chat_json 重试耗尽) → 降级返空."""
    result = extract_ideal_profile(fake_kb_blob, kb_type="customer_list", llm_client=_FakeLLMRaisesRuntime())

    assert result.ideal_profile.industry_focus == []
    assert result.confidence_score == 0.0
    assert "RuntimeError" in result.reasoning_text or "调用失败" in result.reasoning_text


# ---------------------------------------------------------------------------
# Test 3: timeout path → LLMTimeoutError 上抛 (endpoint 转 504)
# ---------------------------------------------------------------------------


def test_timeout_raises_llm_timeout_error(fake_kb_blob):
    """LLM raise TimeoutError → 抛 LLMTimeoutError (caller 转 504)."""
    from agent_channel.ideal_profile import LLMTimeoutError

    with pytest.raises(LLMTimeoutError):
        extract_ideal_profile(fake_kb_blob, kb_type="customer_list", llm_client=_FakeLLMRaisesTimeout())


# ---------------------------------------------------------------------------
# Test 4: KB blob loader · 缺文件 → KBNotFoundError
# ---------------------------------------------------------------------------


def test_load_kb_blob_missing_raises():
    with pytest.raises(KBNotFoundError):
        load_kb_blob("definitely-no-such-kb-id-xyz123")


def test_load_kb_blob_reads(tmp_path, monkeypatch):
    """写一个临时 kb 文件 · 验 load_kb_blob 能正确读出."""
    import agent_channel.ideal_profile as mod

    fake_dir = tmp_path / "channel_kb"
    fake_dir.mkdir()
    payload = {"kb_id": "abc", "kb_type": "policy", "summary_text": "test policy text"}
    (fake_dir / "abc.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(mod, "KB_DIR", fake_dir)
    blob = mod.load_kb_blob("abc")
    assert blob["kb_id"] == "abc"
    assert blob["summary_text"] == "test policy text"


# ---------------------------------------------------------------------------
# Test 5: kb_blob_to_text 优先级 · summary > raw > rows
# ---------------------------------------------------------------------------


def test_kb_blob_to_text_summary_priority():
    blob = {"summary_text": "S", "raw_text": "R", "rows": [{"a": 1}]}
    assert kb_blob_to_text(blob) == "S"


def test_kb_blob_to_text_raw_fallback():
    blob = {"summary_text": "", "raw_text": "R", "rows": [{"a": 1}]}
    assert kb_blob_to_text(blob) == "R"


def test_kb_blob_to_text_rows_fallback():
    blob = {"rows": [{"company_name": "X"}]}
    text = kb_blob_to_text(blob)
    assert "company_name" in text
    assert "X" in text


def test_kb_blob_to_text_empty():
    assert "空" in kb_blob_to_text({})


# ---------------------------------------------------------------------------
# Test 6: 类型容错 · LLM 返 str 而非 list 时仍能解析
# ---------------------------------------------------------------------------


class _FakeLLMTypeMix:
    def chat_json(self, system, user, schema_hint="", temperature=None):
        return {
            "ideal_profile": {
                "industry_focus": "制造业",     # 该是 list · 测自动包装
                "scale_preference": ["小型"],
                "geo_coverage": None,           # 该是 list · 测 None 容错
                "stage": "成长期",
                "capital_relation": 12345,      # 该是 str · 测强转
                "business_size": "",
                "employee_size": "",
                "customer_type": [],
                "product_keywords": [],
                "value_chain_position": "",
                "growth_signals": [],
                "risk_signals": [],
            },
            "confidence_score": "0.5",          # 该是 float · 测强转
            "reasoning_text": "type mix test",
        }


def test_type_coercion_tolerance(fake_kb_blob):
    """LLM 返回字段类型不准（list 给成 str / str 给成数字 / null）→ 强制规整."""
    result = extract_ideal_profile(fake_kb_blob, kb_type="customer_list", llm_client=_FakeLLMTypeMix())

    assert result.ideal_profile.industry_focus == ["制造业"]    # str 自动包成 list
    assert result.ideal_profile.geo_coverage == []              # None → []
    assert result.ideal_profile.capital_relation == "12345"     # 数字强转 str
    assert result.confidence_score == 0.5                       # str 强转 float
