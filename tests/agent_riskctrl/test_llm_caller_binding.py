# -*- coding: utf-8 -*-
"""LLMJudge 迁 shared.llm_caller.LLMCaller 的 binding test (Phase A worker-A4 · 2026-04-29).

Per onboarding §5 step 5 + draft §4.3 ACK trailer caller 3 deprecation path:
  · LLMJudge._get_client() 返 LLMCaller (不再 LLMClient)
  · agent_id="riskctrl" / endpoint="judge"
  · 业务 API (judge / compute_rule_interpretability) 不变 · 仅 transport 替换
  · 无 key 路径 unavailable status 仍生效

不验真 LLM 调用 (会在网络抖动 / 无 key 环境 flaky) · 仅验 caller binding shape.
"""
from __future__ import annotations

import pytest

from agent_riskctrl.llm_judge import LLMJudge
from shared.llm_caller import LLMCaller


def test_llm_judge_no_key_returns_none():
    """无 api_key 时 _get_client() 返 None · is_available() False."""
    judge = LLMJudge(provider="deepseek", api_key="")
    assert judge.is_available() is False
    assert judge._get_client() is None


def test_llm_judge_with_key_binds_llm_caller():
    """有 api_key 时 _get_client() 返 LLMCaller (不再 LLMClient)."""
    judge = LLMJudge(provider="deepseek", api_key="sk-test-fake-key")
    assert judge.is_available() is True

    client = judge._get_client()
    assert client is not None
    assert isinstance(client, LLMCaller), (
        f"Expected LLMCaller binding (caller 3 migration) · got {type(client).__name__}"
    )
    assert client.agent_id == "riskctrl"
    assert client.endpoint == "judge"


def test_llm_judge_caller_lazy_init():
    """_get_client() 二次调用返同一实例 (lazy init · 不重复构造)."""
    judge = LLMJudge(provider="deepseek", api_key="sk-test-fake-key")
    c1 = judge._get_client()
    c2 = judge._get_client()
    assert c1 is c2


def test_llm_judge_unavailable_status_path():
    """无 key 时 judge() 返 unavailable status · 不 crash."""
    judge = LLMJudge(provider="deepseek", api_key="")
    result = judge.judge({"system": "sys", "user": "user"})
    assert result["status"] == "unavailable"
    assert result["score"] is None
    assert "rationale" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
