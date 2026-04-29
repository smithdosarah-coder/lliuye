# -*- coding: utf-8 -*-
"""shared.prompts — Phase A worker-A2 shared prompt assembly package.

Contains:
  · contract.py · 8 段 LLM prompt template per worker-A1 spec
                  (docs/contracts/llm-prompt-contract.md · v1 待 worker-A1 ratify)

Boundary:
  · 本包是 shared 业务 prompt 内容层 · 与 shared/llm_caller/prompts.py 区别:
    - llm_caller/prompts.py · string-assembly utility (build_chat_messages 等)
    - shared/prompts/contract.py · 实际业务 prompt 文本 (8 段 · safety / evidence /
       role / tools / schema / self-check / few-shot / eval-hook)
"""
from __future__ import annotations

from shared.prompts.contract import (
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

__all__ = [
    "PendingA1SpecError",
    "agent_role_block",
    "assemble",
    "evaluation_hook_block",
    "evidence_first_block",
    "few_shot_block",
    "output_schema_block",
    "safety_block",
    "self_check_block",
    "tool_use_block",
]
