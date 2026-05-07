# -*- coding: utf-8 -*-
"""风控策略运营 Agent — 提示词模板

PB#2 (2026-05-06 · Q-053) 后:
- system prompt 走 shared.prompts.agent_helpers.build_riskctrl_ssot_prompt
- 旧 3 个 hardcode SYSTEM_* 常量已删除:
  · SYSTEM_RULE_PARSER (规则解析 · 已迁 helper task_type="rule_parse")
  · SYSTEM_BACKTEST_ANALYSIS (回测分析 · 已迁 helper task_type="backtest_analysis")
  · SYSTEM_ERROR_ANALYSIS (差错分析 · 已迁 helper task_type="error_analysis")
- LLM call site 全部走 helper:
  · agent.py:115 (rule_parse via llm_json)
  · agent.py:192 (rule_parse · 复用)
  · agent.py:230 (backtest_analysis via llm_chat)
  · agent.py:277 (error_analysis via llm_chat)
  · api.py:207 (rule_parse via shared.llm_caller)

fix-forward (留 PB#2 ship 后续命 commit):
- llm_judge.py:47 INTERP_SYSTEM_PROMPT (Agent2 内部 const · 不在 prompts.py · 但应接 helper)

后续 user prompt template 若需添加 · 添加在本 module · system 仍走 helper.
"""
from __future__ import annotations
