# -*- coding: utf-8 -*-
"""shared.sse_envelope — backend SSE event 共形 helper (M6 of 9).

Phase A worker-A2 · 2026-04-29.

目的:
  6 Agent (`agent_*/api.py`) SSE done event 当前 5 套形态 (Cat 4 finding):
    - channel: {candidates, metrics, data_source}                 · 缺 radar/signals/funnel
    - alert:   {} 空                                                · 全缺
    - credit:  {} 空 (live) · 完整 (mock)                            · 不对称
    - compliance: {} 空                                            · 全缺
    - report:  {session_id, report_docx_url, enterprise_profile, pending_questions, downstream_handoff}
    - riskctrl: 显式 "非 SSE" · 前端 riskctrl.ts 期待 SSE             · 矛盾
  本 helper 提供共形 envelope · 6 agent A4 worker 后续迁此入口.

API:
  EVENT_*                 · 4 event 名常量 (stage/section/done/error)
  DATA_SOURCE_*           · 5 data_source 常量 (live/mock/mock_forced/mock_fallback/cached)
  CHANNEL_PANEL_KEYS      · workspace-state-protocol §4 Channel pilot canonical 8 keys
  AGENT_PANEL_KEYS_RECOMMENDED · 6 agent recommended panel sets (initial · A4 worker spec)
  make_stage(stage, status, message="", **extras)            · → dict
  make_section(section_id, title, content, **extras)         · → dict (Agent6 报告章节)
  make_done(*, panels=None, metrics=None, data_source="live",
            session_id=None, downstream=None, **extras)      · → dict
  make_error(message, traceback="", code="")                 · → dict
  validate_panels(panels, required_keys)                     · → (ok, missing) · 测试 / runtime 用
  encode_event(evt)                                          · → SSE-encoded str (data: ...\\n\\n)

Boundary:
  · 本模块只产 dict / encoded str · 不做 SSE response wiring (StreamingResponse 是 caller 责任)
  · 6 agent api.py 当前不动 (A4 territory) · 但 helper 已就绪供迁

Usage (供 A4 worker 参考):

    from shared.sse_envelope import (
        make_stage, make_done, make_error, encode_event,
        DATA_SOURCE_LIVE, DATA_SOURCE_MOCK_FALLBACK,
        CHANNEL_PANEL_KEYS,
    )

    def my_agent_stream(req):
        try:
            yield encode_event(make_stage("intent", "running", "解析意图..."))
            ...
            yield encode_event(make_stage("rank", "done", count=10))

            yield encode_event(make_done(
                panels={
                    "candidates": [...],
                    "signals": [...],
                    "radar": [...],
                    "funnel": [...],
                    "match_dimensions": [...],
                    "product_recommendations": [...],
                    "pitch_scripts": [...],
                },
                metrics={"signalTotal": 50, "companiesFound": 12, "final": 10},
                data_source=DATA_SOURCE_LIVE,
                session_id="sess_abc",
            ))
        except Exception as e:
            yield encode_event(make_error(f"{type(e).__name__}: {e}"))
"""
from __future__ import annotations

import traceback as _traceback
from typing import Any

from shared.api_utils import sse_encode, to_jsonable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Event 名 (4 类 · stage/section/done/error)
EVENT_STAGE: str = "stage"
EVENT_SECTION: str = "section"  # Agent6 报告章节流式
EVENT_DONE: str = "done"
EVENT_ERROR: str = "error"

# data_source 枚举 (per live-fallback-banner-spec v1.0)
DATA_SOURCE_LIVE: str = "live"                  # 真实 LLM / 真实搜索路径
DATA_SOURCE_MOCK: str = "mock"                  # 历史 session / 演示模式
DATA_SOURCE_MOCK_FORCED: str = "mock_forced"    # 前端显式切 DEMO (force_mock=True)
DATA_SOURCE_MOCK_FALLBACK: str = "mock_fallback"  # 主路径 fail · 自动降级 mock
DATA_SOURCE_CACHED: str = "cached"              # 命中 LLM cache (无 LLM 调用)

# Workspace-state-protocol §4 Channel pilot canonical · 8 keys
# (后续 A4 worker 5 子按 channel pilot 复制此 pattern)
# V3 fix (2026-04-30): "conversation" 加为 8th key · 之前 ConversationPanel 走前端 mock
# state · 不从 done envelope 派生 · codex review issue 1 partial 根因 · 现 backend 显式
# 透传 conversation: [] (默认空) · 前端 normalizeBackendDone 读 evt.conversation 兜底
CHANNEL_PANEL_KEYS: tuple[str, ...] = (
    "candidates",
    "signals",
    "radar",
    "funnel",
    "match_dimensions",
    "product_recommendations",
    "pitch_scripts",
    "conversation",
)

# 6 agent recommended panel sets · INITIAL/RECOMMENDED · A4 worker spec 后调
# (取自 docs/contracts/agent-*-spec.md + 现有 mock_sessions shape · 不锁定 · A4 可扩)
AGENT_PANEL_KEYS_RECOMMENDED: dict[str, tuple[str, ...]] = {
    "channel": CHANNEL_PANEL_KEYS,
    # Credit pilot panel set (待 A4-credit · 取 CreditWorkspace 现有消费)
    "credit": (
        "scorecard",
        "radar",
        "redlines",
        "conditions",
        "decision_rationale",
    ),
    # Alert pilot panel set (待 A4-alert · 取 AlertWorkspace 现有消费)
    "alert": (
        "hitlist",
        "evidence",
        "signal_sources",
        "disposition",
    ),
    # Compliance pilot panel set (待 A4-compli · 取 ComplianceWorkspace)
    "compliance": (
        "violations",
        "matrix",
        "events",
        "recommendations",
    ),
    # Riskctrl pilot panel set (待 A4-riskctrl · DSL 规则 + 回测)
    "riskctrl": (
        "ruleset",
        "backtest",
        "ks_curve",
        "metrics",
    ),
    # Report pilot panel set (Agent6 v16 现有 done payload)
    "report": (
        "sections",
        "enterprise_profile",
        "pending_questions",
        "downstream_handoff",
    ),
}


# ---------------------------------------------------------------------------
# Stage event
# ---------------------------------------------------------------------------


def make_stage(
    stage: str,
    status: str,
    message: str = "",
    **extras: Any,
) -> dict[str, Any]:
    """构 stage 事件 dict.

    Args:
        stage:  阶段名 · e.g. "intent" / "scan" / "rank" / "pitch"
        status: "running" / "done" / "error" / "skipped"
        message: 可读说明 · 空串则不输出
        **extras: 额外字段 · e.g. count=10, progress=0.6

    Returns:
        {"event": "stage", "stage": ..., "status": ..., [message: ...], **extras}
    """
    evt: dict[str, Any] = {
        "event": EVENT_STAGE,
        "stage": stage,
        "status": status,
    }
    if message:
        evt["message"] = message
    if extras:
        evt.update(extras)
    return evt


# ---------------------------------------------------------------------------
# Section event (Agent6 报告流式章节)
# ---------------------------------------------------------------------------


def make_section(
    section_id: str,
    title: str,
    content: str,
    **extras: Any,
) -> dict[str, Any]:
    """构 section 事件 dict (Agent6 报告流式章节).

    Args:
        section_id: 章节 id · e.g. "chapter_1_background"
        title:      章节标题 · e.g. "一、企业背景"
        content:    章节正文
        **extras:   额外字段 · e.g. evidence_count=5, audit_pass=True

    Returns:
        {"event": "section", "section": {id, title, content, **extras}}
    """
    section: dict[str, Any] = {
        "id": section_id,
        "title": title,
        "content": content,
    }
    if extras:
        section.update(extras)
    return {
        "event": EVENT_SECTION,
        "section": section,
    }


# ---------------------------------------------------------------------------
# Done event · 共形 envelope
# ---------------------------------------------------------------------------


def make_done(
    *,
    panels: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    data_source: str = DATA_SOURCE_LIVE,
    session_id: str | None = None,
    downstream: dict[str, Any] | None = None,
    **extras: Any,
) -> dict[str, Any]:
    """构 done 事件 dict · 共形 panels + metrics + data_source + 可选 downstream.

    Args:
        panels:      panel 数据 dict (workspace-state-protocol §4 · key 取
                      AGENT_PANEL_KEYS_RECOMMENDED · 不强制全有)
        metrics:     运行 metrics dict · e.g. {signalTotal, companiesFound, final}
        data_source: DATA_SOURCE_* 之一 · 决定 frontend live-fallback-banner 显示
        session_id:  生成的 session id · 前端 setLiveData 时挂
        downstream:  Agent6→Agent3 / Agent3→Agent4 等 cross-agent handoff payload
        **extras:    额外顶层字段 · 兼容旧调用 (e.g. report_docx_url, enterprise_profile)

    Returns:
        {"event": "done", "data_source": ..., [session_id, downstream, metrics],
         **panels (展开到顶层), **extras}

    Raises:
        ValueError: panels / metrics / downstream / session_id / extras 全空时抛 ·
            空 done event 无 payload 对前端无意义 · 必须至少有一个 (V2 fix · codex
            review issue 2). 错误路径请用 make_error_from_exception 而非空 done.

    Note:
        panels 字段展开到 done event 顶层 (与现有 Channel done 兼容 · evt.candidates
        / evt.radar 等直接读 · 不需 evt.panels.candidates).
    """
    # V2 issue 2 · 拒空 payload · panels/metrics/downstream/session_id/extras 至少一个非空
    if not panels and not metrics and not downstream and not session_id and not extras:
        raise ValueError(
            "make_done requires at least one of panels/metrics/downstream/session_id/extras · "
            "empty done event has no payload meaning to frontend · 错误路径用 make_error 而非空 done",
        )

    evt: dict[str, Any] = {
        "event": EVENT_DONE,
        "data_source": data_source,
    }
    if session_id:
        evt["session_id"] = session_id
    if metrics:
        evt["metrics"] = dict(metrics)
    if downstream:
        evt["downstream"] = dict(downstream)
    if panels:
        # 展开到顶层 (与 workspace-state-protocol §4 Channel done shape 兼容)
        for k, v in panels.items():
            evt[k] = v
    if extras:
        evt.update(extras)
    return evt


# ---------------------------------------------------------------------------
# Error event
# ---------------------------------------------------------------------------


def make_error(
    message: str,
    traceback: str = "",
    code: str = "",
) -> dict[str, Any]:
    """构 error 事件 dict.

    Args:
        message:   人话错误描述 · e.g. "TavilySearchError: 401 Unauthorized"
        traceback: 完整 traceback 字符串 · 空则不输出 (前端只看 message)
        code:      错误码 · e.g. "LLM_TIMEOUT" / "TAVILY_KEY_INVALID"

    Returns:
        {"event": "error", "message": ..., [code: ...], [traceback: ...]}
    """
    evt: dict[str, Any] = {
        "event": EVENT_ERROR,
        "message": message,
    }
    if code:
        evt["code"] = code
    if traceback:
        evt["traceback"] = traceback
    return evt


def make_error_from_exception(
    exc: BaseException,
    *,
    code: str = "",
    include_traceback: bool = True,
) -> dict[str, Any]:
    """从 Exception 构 error 事件 · auto fill message + traceback.

    与现有 agent_*/api.py 错误处理 pattern 对齐 (`f"{type(e).__name__}: {e}"`).
    """
    message = f"{type(exc).__name__}: {exc}"
    tb = _traceback.format_exc() if include_traceback else ""
    return make_error(message, traceback=tb[-2000:] if tb else "", code=code)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_panels(
    panels: dict[str, Any] | None,
    required_keys: tuple[str, ...] | list[str],
) -> tuple[bool, list[str]]:
    """检 panels 是否含 required_keys 全集.

    Args:
        panels:        done event panels dict
        required_keys: 期望的 panel keys 集合 · e.g. CHANNEL_PANEL_KEYS

    Returns:
        (ok, missing_keys) · ok=True 时 missing_keys 为空.
    """
    if not panels:
        return False, list(required_keys)
    missing = [k for k in required_keys if k not in panels]
    return (not missing), missing


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def encode_event(evt: dict[str, Any]) -> str:
    """SSE event 编码 · re-export shared.api_utils.sse_encode.

    自动走 to_jsonable 兜 dataclass / pydantic / 自定义对象.
    """
    return sse_encode(to_jsonable(evt))


__all__ = [
    "AGENT_PANEL_KEYS_RECOMMENDED",
    "CHANNEL_PANEL_KEYS",
    "DATA_SOURCE_CACHED",
    "DATA_SOURCE_LIVE",
    "DATA_SOURCE_MOCK",
    "DATA_SOURCE_MOCK_FALLBACK",
    "DATA_SOURCE_MOCK_FORCED",
    "EVENT_DONE",
    "EVENT_ERROR",
    "EVENT_SECTION",
    "EVENT_STAGE",
    "encode_event",
    "make_done",
    "make_error",
    "make_error_from_exception",
    "make_section",
    "make_stage",
    "validate_panels",
]
