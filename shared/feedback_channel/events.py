# -*- coding: utf-8 -*-
"""FeedbackEvent + FeedbackType + emit_feedback."""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# 6 agent 白名单 (per CLAUDE.md §11)
_ALLOWED_AGENTS = frozenset({"channel", "report", "credit", "alert", "compliance", "riskctrl"})


class FeedbackType(str, enum.Enum):
    """4 闭环路径 (per cross-agent-feedback-protocol.md §6).

    ABI lock: 这 4 值不许改 · 加新值走 RFC.
    """

    APPROVAL_OVERRIDE = "approval_override"  # credit → riskctrl
    LOAN_OUTCOME = "loan_outcome"            # alert → riskctrl
    POLICY_VIOLATION = "policy_violation"    # compliance → credit + riskctrl
    SCORE_DRIFT = "score_drift"              # riskctrl → credit


@dataclass
class FeedbackEvent:
    """单条 feedback event · 跨 agent 反向流 · 复用 ledger 存储.

    per cross-agent-feedback-protocol.md §2 schema.
    """

    feedback_type: FeedbackType
    producer_agent: str            # 6 agent 白名单
    consumer_agents: list[str]     # ≥ 1 个 · 决定 retention (M1)
    original_decision_id: str      # 上游决策 id · 回溯链
    subject_entity_key: str        # per entity-resolution v1.1
    payload: dict[str, Any]        # 业务数据 · per feedback_type
    event_id: str = field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:16]}")
    ts: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))

    def __post_init__(self) -> None:
        # 输入校验 (failure isolation: producer 自己捕获)
        if self.producer_agent not in _ALLOWED_AGENTS:
            raise ValueError(f"producer_agent {self.producer_agent!r} 不在 6 agent 白名单")
        if not self.consumer_agents:
            raise ValueError("consumer_agents 必 ≥ 1 个")
        for a in self.consumer_agents:
            if a not in _ALLOWED_AGENTS:
                raise ValueError(f"consumer_agent {a!r} 不在 6 agent 白名单")
        if not self.original_decision_id:
            raise ValueError("original_decision_id required (回溯链)")
        if not self.subject_entity_key:
            raise ValueError("subject_entity_key required (per entity-resolution v1.1)")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["feedback_type"] = self.feedback_type.value
        return d


def resolve_feedback_retention(consumer_agents: list[str]) -> str:
    """M1 · feedback event retention 继承 consumer agent · 取 MAX (long > standard > short).

    理由 (per cross-agent-feedback-protocol §3 M1):
    - producer 可能 short retention (e.g. alert 90d)
    - 沿 producer 90d 后 raw entry 淘汰 → 链路丢
    - 沿 consumer 确保 consumer 业务周期内可回溯
    """
    from shared.decision_ledger.schema import (
        DEFAULT_RETENTION_BY_AGENT,
        RETENTION_LONG,
        RETENTION_SHORT,
        RETENTION_STANDARD,
    )
    rank = {RETENTION_SHORT: 0, RETENTION_STANDARD: 1, RETENTION_LONG: 2}
    classes = [
        DEFAULT_RETENTION_BY_AGENT.get(a, RETENTION_STANDARD)
        for a in consumer_agents
    ]
    return max(classes, key=lambda c: rank[c])


def emit_feedback(
    event: FeedbackEvent,
    *,
    ledger: Optional[Any] = None,
    jurisdiction: Optional[str] = None,
) -> dict[str, Any]:
    """Producer 入口 · 把 feedback event 写入 ledger.

    Args:
        event: FeedbackEvent 实例
        ledger: DecisionLedger 实例 (默认 default_ledger())
        jurisdiction: 跨域 (per CLAUDE.md §3.7.5 · 默认 HQ)

    Returns: {ok: bool, event_id: str, retention_class: str, error: str | None}
    """
    if ledger is None:
        from shared.decision_ledger import default_ledger
        ledger = default_ledger()

    result = ledger.record_feedback(
        producer_agent=event.producer_agent,
        consumer_agents=event.consumer_agents,
        feedback_type=event.feedback_type.value,
        original_decision_id=event.original_decision_id,
        subject_entity_key=event.subject_entity_key,
        payload=event.payload,
        decision_id=event.event_id,
        ts=event.ts,
        jurisdiction=jurisdiction,
    )
    return {
        "ok": result.persisted,
        "event_id": result.decision_id,
        "retention_class": resolve_feedback_retention(event.consumer_agents),
        "error": result.error,
    }
