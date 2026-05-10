# -*- coding: utf-8 -*-
"""shared.feedback_channel · cross-agent feedback channel.

per docs/contracts/cross-agent-feedback-protocol.md v1.0 (Phase A.5 · 2026-05-09).

闭合红线 #9 "审批/贷后反馈丢链路":
- 6 agent 现状全前向流 · 加反向流让下游决策回流到上游策略 agent
- 4 闭环路径: approval_override / loan_outcome / policy_violation / score_drift

设计:
- 复用 shared/decision_ledger/ BE7 sqlite 存储 (feedback events 是 LedgerEntry 的 is_feedback=True 子类)
- watcher 后台 cron 拉 ledger 新 feedback entry · 5 min 默认 (env override)
- subscriber 注册 callback per feedback_type
- 失败隔离: subscriber raise 不影响 last_read_id 前进 · per-event 错误不阻塞 stream

API:
  - FeedbackEvent · dataclass
  - FeedbackType · enum (4 值锁定 ABI)
  - emit_feedback(...) · producer 入口 · 写入 ledger
  - FeedbackWatcher(consumer_agent) · 后台拉 + 派发
  - subscribe decorator (作 watcher.subscribe(type) 注册 callback)
  - resolve_feedback_retention · M1 · 取 MAX(consumer retention)
"""
from .events import (
    FeedbackEvent,
    FeedbackType,
    emit_feedback,
    resolve_feedback_retention,
)
from .watcher import FeedbackWatcher

__all__ = [
    "FeedbackEvent",
    "FeedbackType",
    "FeedbackWatcher",
    "emit_feedback",
    "resolve_feedback_retention",
]
