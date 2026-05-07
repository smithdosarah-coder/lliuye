# -*- coding: utf-8 -*-
"""Agent4 贷中风险预警 - 提示词集合

PB#2 (2026-05-06 · Q-053) 后:
- system prompt 走 shared.prompts.agent_helpers.build_alert_ssot_prompt
- 旧 7 个 hardcode SYSTEM_* 常量 + worker-A4-alert (2026-04-29) 加的
  build_alert_system_prompt shim + _ROLE_FALLBACK 已全部删除
- 实际 production LLM call site: scan_engine._llm_disposition (单点)
- audit verify: SYSTEM_* 常量已 0 production import (test 也无依赖) · 安全删

后续 user prompt template 若需添加 · 添加在本 module · system 仍走 helper.
"""
from __future__ import annotations
