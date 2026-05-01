# -*- coding: utf-8 -*-
"""agent_report.handoff_section_supplement — Sprint 1 BE3 §6.2 反向链 scaffold.

Per docs/contracts/agent-handoff-schemas.md v1.1 §6.2:
  Agent3.report_gap → Agent6.section_supplement
  · Agent3 评分发现 ReportJSON 字段为 __UNFILLED__ 且属于评分必需字段
  · 同步 (HTTP) · 阻塞 Agent3 评分流 · Agent6 补完后回调

Sprint 1 范围 (per Codex 插入点 1 V2 final answer Q2):
  scaffold 仅 · 接 payload + Pydantic 校验 + emit ack event (received not processed) ·
  不实装 partial section run · 留 Phase B-3 fix-forward
  (per Schema §6.7 owner = A4-credit V3 + A4-report V3 双侧 · Phase B-3)

ack vs done 区分 (PM + Codex Q2 verdict):
  - Sprint 1 用 event: section_supplement_ack (received not processed)
  - frontend Sprint 1 不应触发 Agent3 re-score (等 B-3 fix-forward)
  - Phase B-3 升级路径: ack → done · received_sections → supplemented_sections ·
    supplement_status: scaffold_ack → ran_partial · partial_section_run_pending 字段移除

红线 (per docs/contracts/agent-report-material-gap.md §6):
  - 不实装 partial section run (Sprint 1 scaffold)
  - 不破 v16 mock 路径
  - frontend 看到 ack 不应误以为 partial run 完成
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import AsyncIterator, Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# 4 章 + 已知 material kb keys (校验 gap_sections payload 元素必属之)
# ============================================================================

KNOWN_CHAPTERS = {
    "chapter_1_background",
    "chapter_2_operation",
    "chapter_3_finance",
    "chapter_4_conclusion",
}

# material_kb 14 维度命名 (与 material_gap_rules.MATERIAL_TO_SECTION_RULES key align)
KNOWN_MATERIAL_KEYS = {
    "basic_info", "shareholders", "controller", "r_and_d",
    "business", "upstream_top5", "downstream_top5", "orders", "affiliates",
    "financing", "bank_flows", "tax_data", "credit_history",
    "risk_info",
}

KNOWN_GAP_SECTION_KEYS = KNOWN_CHAPTERS | KNOWN_MATERIAL_KEYS


# ============================================================================
# Pydantic schema · §6.2 payload 严格契约
# ============================================================================

class SectionSupplementRequest(BaseModel):
    """§6.2 反向链 payload · Agent3 → Agent6.

    Schema verbatim per docs/contracts/agent-handoff-schemas.md §6.2:
      schema_version: "1.0" · intent_type: "report_gap_supplement" ·
      source_agent: "credit" · target_agent: "report" · report_id ·
      gap_sections: list[str] · requesting_decision_id · urgency
    """
    schema_version: Literal["1.0"]
    intent_type: Literal["report_gap_supplement"]
    source_agent: Literal["credit"]
    target_agent: Literal["report"]
    report_id: str = Field(min_length=1)
    gap_sections: list[str] = Field(min_length=1)
    requesting_decision_id: str = Field(min_length=1)
    urgency: Literal["blocking", "advisory"]

    @field_validator("gap_sections")
    @classmethod
    def gap_sections_must_be_known(cls, v: list[str]) -> list[str]:
        """gap_sections 元素必属 KNOWN_GAP_SECTION_KEYS · 否则 422."""
        unknown = [s for s in v if s not in KNOWN_GAP_SECTION_KEYS]
        if unknown:
            raise ValueError(
                f"gap_sections 含未知 key: {unknown} · "
                f"必属 4 章锚点 ∪ material_kb 14 维度命名"
            )
        return v


# ============================================================================
# SSE helper (复用 v16_runner _sse 风格)
# ============================================================================

def _sse(event: str, data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {body}\n\n"


# ============================================================================
# 主入口 · handle_section_supplement (async generator · SSE stream)
# ============================================================================

async def handle_section_supplement(
    request: SectionSupplementRequest,
) -> AsyncIterator[str]:
    """Sprint 1 scaffold · 接 payload + 校验 (Pydantic) + emit ack event.

    Sprint 1 = received not processed (per Codex V2 Q2):
    - frontend 接 ack event 后 · UI 显示 "已收到 · partial run 等 B-3 实装"
    - 不应触发 Agent3 re-score (等 B-3 fix-forward 后才升级 done event)

    Phase B-3 升级路径:
    - event: section_supplement_ack → section_supplement_done
    - received_sections → supplemented_sections
    - supplement_status: "scaffold_ack" → "ran_partial"
    - 移除 partial_section_run_pending 字段
    - 真跑 v16 partial section run (需 v16_pipeline 支持 section_filter 参数)
    """
    # ---- 1. emit started event (与 v16 fill SSE envelope 同形) ----
    yield _sse("section_supplement_started", {
        "report_id": request.report_id,
        "gap_sections": request.gap_sections,
        "scaffold_mode": True,
        "urgency": request.urgency,
    })
    # 让 await yield 协程切换 (frontend 收到 started 后 ack 前有 idle 窗口)
    await asyncio.sleep(0.05)

    # ---- 2. emit ack event (received not processed) ----
    now = datetime.now(timezone(timedelta(hours=8)))
    yield _sse("section_supplement_ack", {
        "report_id": request.report_id,
        "received_sections": request.gap_sections,        # ← 改名: 不是 supplemented (避免误导)
        "scaffold_mode": True,
        "partial_section_run_pending": "Phase B-3",
        "supplement_status": "scaffold_ack",              # B-3 改 "ran_partial"
        "received_at": now.isoformat(timespec="seconds"),
        "requesting_decision_id": request.requesting_decision_id,
        "next_step": (
            "Phase B-3 fix-forward 后 Agent3 重评 (per §6.2 消费侧约束) · "
            "Sprint 1 frontend 不应触发 re-score · 仅 UI 显示 \"已收到\""
        ),
    })


# ============================================================================
# Sync helper (test 用 · 不走 SSE)
# ============================================================================

def build_ack_payload(request: SectionSupplementRequest) -> dict:
    """非 SSE 测试 helper · 返 ack event payload dict (test_handoff_scaffold_ack 用)."""
    now = datetime.now(timezone(timedelta(hours=8)))
    return {
        "report_id": request.report_id,
        "received_sections": request.gap_sections,
        "scaffold_mode": True,
        "partial_section_run_pending": "Phase B-3",
        "supplement_status": "scaffold_ack",
        "received_at": now.isoformat(timespec="seconds"),
        "requesting_decision_id": request.requesting_decision_id,
        "next_step": (
            "Phase B-3 fix-forward 后 Agent3 重评 (per §6.2 消费侧约束) · "
            "Sprint 1 frontend 不应触发 re-score · 仅 UI 显示 \"已收到\""
        ),
    }
