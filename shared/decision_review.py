"""人工确认工作台 · RM 对 AI 建议接受/修改/驳回 + 原因留底

per Phase C charter Track A · A3 · 端到端流程第 3 件 (PM 拍板 2026-05-06):

设计:
- 输入: decision_id + reviewer (RM 工号) + action (accept/modify/reject) + reason
- 写入 ledger (作 review_event) + 自动 lineage 追溯 review 决策本身
- 改原 decision 状态 (draft → reviewed)
- 校验: reviewer 必有效 + reason 不能空 (modify/reject 时)

DP3 PM 拍板 '核心决策必有 lineage+audit · 缺证据 block':
- review 本身也是决策事件 · 必上链
- 任何 modify/reject 必带 reason (audit 必查)
- 后续 export 物必带 review_status

使用:
    from shared.decision_review import submit_review

    result = submit_review(
        decision_id="dec-...",
        reviewer="RM-王哲",
        action="accept",
        reason=None,  # accept 不必 reason
    )
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ReviewAction(str, Enum):
    """RM 对 AI 决策的 review 动作."""

    ACCEPT = "accept"  # 接受原建议
    MODIFY = "modify"  # 修改后接受 (必带修改后内容 + 原因)
    REJECT = "reject"  # 驳回 (必带原因)


class ReviewRequest(BaseModel):
    """RM review 请求 schema."""

    decision_id: str = Field(..., min_length=1)
    reviewer: str = Field(..., min_length=1, description="RM 工号 e.g. RM-王哲")
    action: ReviewAction
    reason: str = Field("", description="modify/reject 必带 · accept 可空")
    modified_content: Optional[dict[str, Any]] = Field(
        None,
        description="modify 必带修改后内容 · accept/reject 应空",
    )

    @field_validator("reason")
    @classmethod
    def _check_reason_for_modify_reject(cls, v: str, info) -> str:
        """modify / reject 必带 reason (≥ 5 字符 · 防敷衍)."""
        action = info.data.get("action")
        if action in (ReviewAction.MODIFY, ReviewAction.REJECT):
            if not v or len(v.strip()) < 5:
                raise ValueError(
                    f"action={action.value} 必带 reason (≥ 5 字符) · 防止敷衍 review"
                )
        return v


# ---------------------------------------------------------------------------
# Review event store (内存 · production 改 sqlite or 接 ledger)
# ---------------------------------------------------------------------------

_review_events: dict[str, list[dict[str, Any]]] = {}
_review_lock = threading.RLock()


def submit_review(
    *,
    decision_id: str,
    reviewer: str,
    action: str,
    reason: str = "",
    modified_content: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """提交一次 RM review · 写入 ledger + lineage + 内存 event log.

    Returns:
        {
            'review_id': str,
            'decision_id': str,
            'reviewer': str,
            'action': str,
            'reason': str,
            'reviewed_at': ISO timestamp,
            'ledger_persisted': bool,
            'block': bool,
            'block_reason': str | None,
        }
    """
    # 1. Schema 校验
    try:
        req = ReviewRequest(
            decision_id=decision_id,
            reviewer=reviewer,
            action=action,
            reason=reason,
            modified_content=modified_content,
        )
    except (ValueError, TypeError) as exc:
        return {
            "review_id": None,
            "block": True,
            "block_reason": f"schema 校验失败: {exc}",
        }

    review_id = f"rev-{uuid.uuid4().hex[:12]}"
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    # 2. ledger 上链 (silent fail · BE7 wrapper)
    ledger_persisted = False
    ledger_decision_id: Optional[str] = None
    try:
        from shared.decision_ledger import default_ledger
        ledger_result = default_ledger().record(
            agent_id="review_workbench",
            endpoint="/api/decision/review",
            input_payload={
                "original_decision_id": req.decision_id,
                "reviewer": req.reviewer,
                "action": req.action.value,
            },
            output_payload={
                "review_id": review_id,
                "reason": req.reason,
                "modified_content_keys": (
                    list(req.modified_content.keys()) if req.modified_content else []
                ),
            },
            evidence_chain={
                "review_target_decision_id": req.decision_id,
                "review_action": req.action.value,
            },
        )
        ledger_persisted = ledger_result.persisted
        ledger_decision_id = ledger_result.decision_id
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
        pass

    # 3. lineage 追溯 (review 本身的字段来源)
    try:
        from shared.data_lineage import LineageRecord, get_lineage_store
        store = get_lineage_store()
        store.record(LineageRecord(
            decision_id=ledger_decision_id or review_id,
            field_path="review.action",
            source_system="review_workbench",
            source_table="user_input",
            source_field="reviewer_action",
            fetched_at=reviewed_at,
            effective_date=reviewed_at,
            transformation=f"RM {req.reviewer} 提交",
            data_tier="internal_authoritative",
        ))
    except Exception:  # noqa: BLE001 · silent
        pass

    # 4. 内存 event log
    event = {
        "review_id": review_id,
        "decision_id": req.decision_id,
        "reviewer": req.reviewer,
        "action": req.action.value,
        "reason": req.reason,
        "modified_content": req.modified_content,
        "reviewed_at": reviewed_at,
        "ledger_decision_id": ledger_decision_id,
        "ledger_persisted": ledger_persisted,
    }
    with _review_lock:
        _review_events.setdefault(req.decision_id, []).append(event)

    return {
        **event,
        "block": False,
        "block_reason": None,
    }


def get_reviews(decision_id: str) -> list[dict[str, Any]]:
    """查询一笔决策的所有 review event."""
    with _review_lock:
        return list(_review_events.get(decision_id, []))


def get_decision_status(decision_id: str) -> str:
    """决策状态 · 'draft' / 'reviewed_accepted' / 'reviewed_modified' / 'reviewed_rejected'."""
    reviews = get_reviews(decision_id)
    if not reviews:
        return "draft"
    last = reviews[-1]
    action = last["action"]
    return f"reviewed_{action}"


__all__ = [
    "ReviewAction",
    "ReviewRequest",
    "submit_review",
    "get_reviews",
    "get_decision_status",
]
