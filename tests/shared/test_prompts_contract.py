# -*- coding: utf-8 -*-
"""tests/shared/test_prompts_contract.py — V2 fix issue 4 (contract.py strict semantics).

Coverage:
  · 8 段 block 函数 callable + 默认 placeholder marker
  · agent_role_block role 嵌入
  · 4 conditional block 空参 → 空串
  · assemble strict=False (default) · skip placeholder · 全 placeholder 返 ""
  · assemble strict=True · skip placeholder + 抛 PendingA1SpecError
  · assemble 部分 ratify (monkeypatch 模拟 A1 spec landed) · 仅含已 ratify 段
"""
from __future__ import annotations

import pytest

from shared.prompts import (
    PendingA1SpecError,
    agent_role_block,
    assemble,
    evaluation_hook_block,
    evidence_first_block,
    few_shot_block,
    output_schema_block,
    safety_block,
    self_check_block,
    tool_use_block,
)
from shared.prompts import contract as contract_mod


# ============================================================================
# 8 段 block 函数 (skeleton)
# ============================================================================


def test_safety_block_placeholder():
    s = safety_block()
    assert isinstance(s, str)
    assert "PENDING" in s


def test_evidence_first_block_placeholder():
    s = evidence_first_block()
    assert isinstance(s, str)
    assert "PENDING" in s


def test_self_check_block_placeholder():
    s = self_check_block()
    assert isinstance(s, str)
    assert "PENDING" in s


def test_agent_role_block_role_embedded():
    """agent_role_block(role) 嵌入 role 便于 debug."""
    s = agent_role_block("agent6_report")
    assert "agent6_report" in s


def test_tool_use_block_empty():
    """无 tools → 空串."""
    assert tool_use_block(None) == ""
    assert tool_use_block([]) == ""


def test_tool_use_block_with_tools_placeholder():
    """有 tools → placeholder marker (待 A1)."""
    s = tool_use_block([{"name": "t1"}])
    assert "PENDING" in s


def test_output_schema_block_empty():
    assert output_schema_block("") == ""


def test_output_schema_block_with_hint_placeholder():
    s = output_schema_block('{"x": int}')
    assert "PENDING" in s


def test_few_shot_block_empty():
    assert few_shot_block(None) == ""
    assert few_shot_block([]) == ""


def test_few_shot_block_with_examples_placeholder():
    s = few_shot_block([{"input": "a", "output": "b"}])
    assert "PENDING" in s


def test_evaluation_hook_block_empty():
    assert evaluation_hook_block("") == ""


def test_evaluation_hook_block_with_id_placeholder():
    s = evaluation_hook_block("agent6_report")
    assert "PENDING" in s


# ============================================================================
# assemble · V2 fix issue 4 strict semantics
# ============================================================================


def test_assemble_default_skips_all_placeholder():
    """V2 fix · 默认 strict=False · 当前 8 段全 placeholder · 返 ""."""
    out = assemble(role="agent6_report")
    # 全 placeholder · 全 skip · output 应空
    assert out == ""


def test_assemble_default_no_pending_marker_in_output():
    """V2 fix · default 不再泄漏 PENDING marker 到输出."""
    out = assemble(
        role="agent1_channel",
        tools=[{"name": "x"}],
        schema_hint="{}",
        examples=[{"input": "a", "output": "b"}],
        eval_id="agent1_channel",
    )
    # placeholder 全 skip · marker 不出现
    assert "PENDING" not in out


def test_assemble_strict_raises_with_placeholder():
    """V2 fix · strict=True 且任一 section placeholder → PendingA1SpecError."""
    with pytest.raises(PendingA1SpecError) as exc_info:
        assemble(role="agent6_report", strict=True)
    msg = str(exc_info.value)
    # error 含 placeholder section 列表
    assert "safety" in msg or "evidence_first" in msg or "self_check" in msg


def test_assemble_strict_lists_pending_sections():
    """V2 fix · strict raise message 含 pending sections 列表 · 便于 debug A1 spec gap."""
    with pytest.raises(PendingA1SpecError) as exc_info:
        assemble(
            role="x",
            tools=[{"name": "t"}],
            schema_hint="{}",
            examples=[{"input": "a", "output": "b"}],
            eval_id="agent1_channel",
            strict=True,
        )
    msg = str(exc_info.value)
    # 8 段全 placeholder · 应至少含部分名
    pending_sections = ["safety", "evidence_first", "agent_role", "tool_use",
                       "output_schema", "self_check", "few_shot", "evaluation_hook"]
    assert any(name in msg for name in pending_sections)


def test_assemble_with_partial_ratify(monkeypatch):
    """V2 fix · 部分 section ratify (模拟 A1 spec landed) · output 仅含 ratified 段."""
    # 模拟 safety_block ratified · 其他仍 placeholder
    monkeypatch.setattr(
        contract_mod, "safety_block",
        lambda: "## SAFETY · 不输出 PII / 不编造数字",
    )

    out = assemble(role="agent6_report", strict=False)
    # 仅 safety 段进 output (其他全 placeholder skip)
    assert "## SAFETY" in out
    assert "不输出 PII" in out
    # placeholder marker 不在 output (V2)
    assert "PENDING" not in out


def test_assemble_strict_passes_when_all_ratified(monkeypatch):
    """V2 fix · 全 section ratify 后 strict=True 不抛 · output 含全 8 段."""
    # 模拟 8 段全 ratify (A1 spec done · A2/A4 fill)
    monkeypatch.setattr(contract_mod, "safety_block",
                        lambda: "## SAFETY")
    monkeypatch.setattr(contract_mod, "evidence_first_block",
                        lambda: "## EVIDENCE")
    monkeypatch.setattr(contract_mod, "agent_role_block",
                        lambda role: f"## ROLE: {role}")
    monkeypatch.setattr(contract_mod, "tool_use_block",
                        lambda tools=None: "## TOOLS" if tools else "")
    monkeypatch.setattr(contract_mod, "output_schema_block",
                        lambda hint="": f"## SCHEMA: {hint}" if hint else "")
    monkeypatch.setattr(contract_mod, "self_check_block",
                        lambda: "## SELF_CHECK")
    monkeypatch.setattr(contract_mod, "few_shot_block",
                        lambda examples=None, max_n=3: "## FEW_SHOT" if examples else "")
    monkeypatch.setattr(contract_mod, "evaluation_hook_block",
                        lambda eval_id="": f"## EVAL: {eval_id}" if eval_id else "")

    out = assemble(
        role="agent6_report",
        tools=[{"name": "x"}],
        schema_hint="{}",
        examples=[{"input": "a", "output": "b"}],
        eval_id="agent6_report",
        strict=True,
    )
    # 全 8 段都 ratified · 应都进 output
    assert "## SAFETY" in out
    assert "## EVIDENCE" in out
    assert "## ROLE: agent6_report" in out
    assert "## TOOLS" in out
    assert "## SCHEMA: {}" in out
    assert "## SELF_CHECK" in out
    assert "## FEW_SHOT" in out
    assert "## EVAL: agent6_report" in out
    # 用 \n\n 分隔
    assert "\n\n" in out


def test_assemble_strict_raises_when_partial_ratify(monkeypatch):
    """V2 fix · 部分 ratify 时 strict=True 仍抛 (有 placeholder 就 raise)."""
    monkeypatch.setattr(contract_mod, "safety_block", lambda: "## SAFETY")
    # 其他仍 placeholder

    with pytest.raises(PendingA1SpecError):
        assemble(role="agent6_report", strict=True)
