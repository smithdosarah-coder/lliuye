# -*- coding: utf-8 -*-
"""Agent5 合规巡检 - 提示词

PB#2 (2026-05-06 · Q-053) 后:
- system prompt 走 shared.prompts.agent_helpers.build_compliance_ssot_prompt
- 旧 7 个 hardcode SYSTEM_* 常量已删除:
  · SYSTEM_POLICY_PARSE / SYSTEM_COMPLIANCE_CHECK / SYSTEM_DEFECT_REPORT
    SYSTEM_EVENT_EXTRACT / SYSTEM_MATRIX_JUDGE / SYSTEM_RECOMMENDATION_BATCH
    SYSTEM_INTERNAL_RULE_EXTRACT
- 实际 production LLM call site:
  · compliance_checker.py:86 (走 helper)
  · policy_parser.py:62 (走 helper)
  · scan_engine.py 4 处 inline SYSTEM (POLICY_RULE_EXTRACT/BUSINESS_EVENT_EXTRACT/
    MATRIX_JUDGE/REVISION) · 留 PB#2 ship 后续命 commit cleanup
- audit verify: 5 个 SYSTEM (DEFECT_REPORT/EVENT_EXTRACT/MATRIX_JUDGE/
  RECOMMENDATION_BATCH/INTERNAL_RULE_EXTRACT) 0 production import · 直接删

后续 user prompt template 若需添加 · 添加在本 module · system 仍走 helper.
"""
from __future__ import annotations
