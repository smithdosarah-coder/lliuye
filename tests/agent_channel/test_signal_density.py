# -*- coding: utf-8 -*-
"""Unit tests for ``agent_channel.signal_density`` · Q-054 B1 第 5 维度.

8 case 覆盖 (per AGENT_IDENTITY plan):
  1. 空 signals → 0.0 + reason="未能自动填写: no_signals"
  2. 1 fresh biz signal (LLM None · static prior) → ~0.2833 (1.0 × 0.85 / 3)
  3. 全 signal 缺 signal_date → 0.0 + reason="未能自动填写: missing_dates"
  4. 全 90+ 天外 signal → 极低 (recency_w ≤ 0.7 · 远低于满分)
  5. LLM 越界 (返 1.5) → static fallback + reason="llm_out_of_range" + evidence file 写入
  6. LLM unavailable (raise) → static fallback + reason="llm_unavailable" + 不写 evidence
  7. 5 type 30 天内全活跃 (LLM 高分) → ≥ 0.6
  8. signal_type 未识别 → ClaimType.GENERIC + UNKNOWN_SALIENCE=0.30
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from agent_channel.signal_density import (
    SIGNAL_DENSITY_NORMALIZATION_DIVISOR,
    STATIC_SALIENCE_PRIOR,
    UNKNOWN_SALIENCE,
    compute_signal_density,
    compute_signal_salience,
    signal_type_to_claim_type,
)
from shared.evidence_freshness import ClaimType


REF_DATE = datetime(2026, 5, 7)


# ============================================================================
# Helpers
# ============================================================================

def _signal(stype: str, date: str = "", title: str = "", detail: str = "") -> dict:
    return {
        "signal_type": stype,
        "signal_date": date,
        "signal_title": title or f"{stype} signal",
        "signal_detail": detail or "...",
    }


class _FakeLLM:
    """Mock LLMCaller · returns chat_json 给定 payload."""
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def chat_json(self, *args, **kwargs):
        self.calls += 1
        return SimpleNamespace(json_payload=self.payload)


class _BrokenLLM:
    """Mock LLMCaller · raise on chat_json."""
    def chat_json(self, *args, **kwargs):
        raise RuntimeError("connection refused")


# ============================================================================
# Case 1: 空 signals
# ============================================================================

def test_case1_empty_signals_returns_zero_with_reason():
    result = compute_signal_density({"signals": []}, reference_date=REF_DATE)
    assert result["signal_density"] == 0.0
    assert "no_signals" in result["signal_density_reason"]
    assert "未能自动填写" in result["signal_density_reason"]


# ============================================================================
# Case 2: 1 fresh biz · static prior (LLM None)
# ============================================================================

def test_case2_one_fresh_biz_static_prior():
    item = {"signals": [_signal("biz", "2026-05-01", "股权变更")]}
    result = compute_signal_density(item, llm=None, reference_date=REF_DATE)
    # 1.0 (recency · fd=6 < 30) × 0.85 (static prior biz) / 3.0 = 0.2833
    expected = 1.0 * STATIC_SALIENCE_PRIOR["biz"] / SIGNAL_DENSITY_NORMALIZATION_DIVISOR
    assert result["signal_density"] == pytest.approx(expected, abs=0.001)
    assert result["signal_density_reason"] == ""


# ============================================================================
# Case 3: 全缺 signal_date
# ============================================================================

def test_case3_missing_dates_returns_zero_with_reason():
    item = {"signals": [
        _signal("biz", date="", title="股权变更"),
        _signal("bidding", date="", title="中标"),
    ]}
    result = compute_signal_density(item, reference_date=REF_DATE)
    assert result["signal_density"] == 0.0
    assert "missing_dates" in result["signal_density_reason"]
    assert "未能自动填写" in result["signal_density_reason"]


# ============================================================================
# Case 4: 全 90+ 天外 (低 recency)
# ============================================================================

def test_case4_all_stale_signals_low_density():
    # Signals 1+ years old · recency_w ≤ 0.4
    item = {"signals": [
        _signal("biz", "2024-05-01", "股权变更"),     # ~735 days · weight=0.05
        _signal("bidding", "2025-01-01", "中标"),     # ~490 days · weight=0.2
    ]}
    result = compute_signal_density(item, llm=None, reference_date=REF_DATE)
    # 0.05*0.85 + 0.2*0.7 = 0.0425 + 0.14 = 0.1825 / 3 = 0.0608
    assert result["signal_density"] < 0.1, (
        f"stale signals must yield low density · got {result['signal_density']}"
    )
    assert result["signal_density_reason"] == ""


# ============================================================================
# Case 5: LLM 越界 → static fallback + evidence 写入
# ============================================================================

def test_case5_llm_out_of_range_falls_back_static_and_writes_evidence(
    tmp_path, monkeypatch,
):
    # 重定向 _PROJECT_ROOT 到 tmp_path · 防污染真 evidence/
    import agent_channel.signal_density as sd_mod
    monkeypatch.setattr(sd_mod, "_PROJECT_ROOT", tmp_path)

    llm = _FakeLLM({
        "per_signal": [
            {"idx": 0, "salience": 1.5},   # 越界
            {"idx": 1, "salience": 0.7},
        ],
        "reason": "test",
    })
    item = {"signals": [
        _signal("biz", "2026-05-01", "股权变更"),
        _signal("bidding", "2026-04-15", "中标"),
    ]}
    result = compute_signal_density(item, llm=llm, reference_date=REF_DATE)

    # 1 越界 → 整批 fallback static · biz 0.85 + bidding 0.70
    expected = (0.85 + 0.70) / SIGNAL_DENSITY_NORMALIZATION_DIVISOR
    assert result["signal_density"] == pytest.approx(expected, abs=0.001)
    assert "llm_out_of_range" in result["signal_density_reason"]

    # evidence file 写入 · prompt 版本冻结
    evidence_files = list((tmp_path / "evidence").glob("llm_out_of_range_*.md"))
    assert len(evidence_files) == 1, "evidence file must be written"
    content = evidence_files[0].read_text(encoding="utf-8")
    assert "v1.0-2026-05-07" in content, "prompt version must be frozen in evidence"
    assert "1.5" in content, "out-of-range value must be recorded"


# ============================================================================
# Case 6: LLM unavailable (raise) → static fallback · 不写 evidence
# ============================================================================

def test_case6_llm_unavailable_falls_back_static_no_evidence(tmp_path, monkeypatch):
    import agent_channel.signal_density as sd_mod
    monkeypatch.setattr(sd_mod, "_PROJECT_ROOT", tmp_path)

    item = {"signals": [_signal("biz", "2026-05-01", "股权变更")]}
    result = compute_signal_density(item, llm=_BrokenLLM(), reference_date=REF_DATE)

    expected = STATIC_SALIENCE_PRIOR["biz"] / SIGNAL_DENSITY_NORMALIZATION_DIVISOR
    assert result["signal_density"] == pytest.approx(expected, abs=0.001)
    assert result["signal_density_reason"] == "llm_unavailable"

    # LLM 不可达 ≠ 越界 · 不写 evidence
    evidence_dir = tmp_path / "evidence"
    assert not evidence_dir.exists() or not list(evidence_dir.glob("llm_out_of_range_*.md"))


# ============================================================================
# Case 7: 5 type 30 天内全活跃 + LLM 高分 → 高密度
# ============================================================================

def test_case7_dense_recent_signals_with_llm_high_score():
    # 5 fresh signals · LLM 全打 0.9
    llm = _FakeLLM({
        "per_signal": [{"idx": i, "salience": 0.9} for i in range(5)],
        "reason": "high salience all",
    })
    item = {"signals": [
        _signal("biz", "2026-05-01", "股权变更"),
        _signal("bidding", "2026-04-25", "中标"),
        _signal("growth", "2026-04-20", "扩产"),
        _signal("tech", "2026-04-15", "专利"),
        _signal("recognition", "2026-04-10", "专精特新"),
    ]}
    result = compute_signal_density(item, llm=llm, reference_date=REF_DATE)
    # 5 × 1.0 (all < 30 days) × 0.9 / 3.0 = 1.5 → clamp to 1.0
    assert result["signal_density"] >= 0.6, (
        f"dense recent signals must yield high density · got {result['signal_density']}"
    )
    assert result["signal_density_reason"] == ""
    assert llm.calls == 1, "batch · 1 LLM call for all signals"


# ============================================================================
# Case 8: 未识别 signal_type → GENERIC + UNKNOWN_SALIENCE
# ============================================================================

def test_case8_unknown_signal_type_falls_back_generic():
    # 未识别 type
    assert signal_type_to_claim_type("xxx_unknown") == ClaimType.GENERIC

    # 单 signal salience 走 UNKNOWN_SALIENCE
    sal, reason = compute_signal_salience({"signal_type": "xxx_unknown"})
    assert sal == UNKNOWN_SALIENCE
    assert reason == ""

    # density 用 UNKNOWN_SALIENCE
    item = {"signals": [_signal("xxx_unknown", "2026-05-01")]}
    result = compute_signal_density(item, reference_date=REF_DATE)
    expected = 1.0 * UNKNOWN_SALIENCE / SIGNAL_DENSITY_NORMALIZATION_DIVISOR
    assert result["signal_density"] == pytest.approx(expected, abs=0.001)


# ============================================================================
# Q-041 4 字段非回归 (sanity guard · sse_extras.test_sse_extras 已主测此项)
# ============================================================================

def test_q041_4_fields_preserved_via_enrich_candidate():
    """confirm enrich_candidate 仍出 Q-041 4 字段 + 新 signal_density · 不破契约."""
    from agent_channel.sse_extras import enrich_candidate

    item = {
        "company_name": "Test Co",
        "qcc": {"industry": "半导体", "registered_address": "上海市浦东"},
        "signals": [_signal("biz", "2026-05-01")],
    }
    extras = enrich_candidate(
        item, query="半导体 长三角", tags=[], llm=None,
    )
    # Q-041 4 字段 · 必齐
    for k in ("industry", "geo", "scale", "similarity"):
        assert k in extras, f"Q-041 4 字段 {k} 缺 · 破契约"
    # Q-054 第 5 维度 · 必齐
    assert "signal_density" in extras
    assert "signal_density_reason" in extras
    assert isinstance(extras["signal_density"], float)
    assert 0.0 <= extras["signal_density"] <= 1.0
