# -*- coding: utf-8 -*-
"""IM service · Pydantic schemas (Stage D.2 · onboarding W-D2-A3).

按 docs/contracts/im-protocol.md §3 / §4 / §9:
- ImThread · ImMessage (前后端共享 source-of-truth)
- REST request / response shapes
- WebSocket inbound / outbound message types

放宽列表/字典字段类型 · 容忍 LLM / 前端混合输入。
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core domain
# ---------------------------------------------------------------------------


ThreadKind = Literal["group", "dm"]

MessageKind = Literal[
    "text",
    "system_event",
    "handoff_card",
    "file",
    "agent_output",
    "pin_ref",
]


class ImThread(BaseModel):
    id: str
    title: str
    customer_id: Optional[str] = None
    kind: ThreadKind = "group"
    participants: list[str] = Field(default_factory=list)
    last_message_at: str
    unread_count: int = 0
    created_at: str


class ImMessage(BaseModel):
    id: str
    thread_id: str
    from_id: str
    kind: MessageKind = "text"
    content: str = ""
    refs: Optional[dict[str, Any]] = None
    created_at: str


# ---------------------------------------------------------------------------
# REST · request / response
# ---------------------------------------------------------------------------


class CreateThreadRequest(BaseModel):
    title: str
    kind: ThreadKind = "group"
    participants: list[str] = Field(default_factory=list)
    customer_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    thread_id: str
    content: str = ""
    target_agent: Optional[str] = None
    kind: MessageKind = "text"
    refs: Optional[dict[str, Any]] = None


class SendMessageResponse(BaseModel):
    message: ImMessage
    ack: Literal["queued", "stored"] = "stored"


class MessageListResponse(BaseModel):
    thread_id: str
    messages: list[ImMessage] = Field(default_factory=list)
    limit: int
    before: Optional[str] = None


class ThreadListResponse(BaseModel):
    user_id: str
    threads: list[ImThread] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# WebSocket envelopes
# ---------------------------------------------------------------------------


class WsInboundSubscribe(BaseModel):
    type: Literal["subscribe"]
    thread_id: str


class WsInboundTyping(BaseModel):
    type: Literal["typing"]
    thread_id: str


class WsInboundAckRead(BaseModel):
    type: Literal["ack_read"]
    thread_id: str
    up_to: str


class WsInboundResync(BaseModel):
    type: Literal["resync"]
    thread_id: str
    since: str


# server → client envelope (no strict pydantic enforcement · 前端解析灵活)

class WsOutboundMessage(BaseModel):
    type: Literal["message"] = "message"
    thread_id: str
    message: ImMessage


class WsOutboundTyping(BaseModel):
    type: Literal["typing"] = "typing"
    thread_id: str
    user_id: str


class WsOutboundAgentProgress(BaseModel):
    type: Literal["agent_progress"] = "agent_progress"
    thread_id: str
    stage: str
    pct: float = 0.0


class WsOutboundAgentOutput(BaseModel):
    type: Literal["agent_output"] = "agent_output"
    thread_id: str
    message: ImMessage


class WsOutboundError(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
