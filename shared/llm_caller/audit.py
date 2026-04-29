# -*- coding: utf-8 -*-
"""shared.llm_caller.audit — per-call LLM audit hook (M3 of 5).

Phase A worker-A2 · 2026-04-29 · audit layer · silent-fail wrapper.

API:
    with_audit(...)       · context manager · 包 single LLM call · 自动落 audit log
    record_llm_call(...)  · 低级直接 record · 等价 audit_service._record_safe 的 wrapper
    extract_audit_extras(result)  · 从 ProviderResult 抽 tokens / region / provider_name

设计原则:
  · 与 audit_service 现有 3 hook 互补:
    - decorators.audit_llm_call(...)  · 包 FastAPI route function (latency = 包路由)
    - stream_helpers.audit_stream_event(...) · SSE generator finally 显式记 (含 stream 真实延迟)
    - 本模块 with_audit                · per-call client-side audit (caller 显式 with)
  · silent-fail · audit_service 缺失时 no-op · 不阻塞业务
  · 银保监合规底线 (留痕 + PIPL): provider region / model / tokens 全部进 audit log

使用:
    from shared.llm_caller import chat_with_fallback
    from shared.llm_caller.audit import with_audit

    with with_audit(agent_id="channel", endpoint="/api/channel/run") as audit:
        result = chat_with_fallback("system", "user")
        audit.attach(result)
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from shared.llm_caller.provider import ProviderResult

logger = logging.getLogger(__name__)


@dataclass
class AuditHandle:
    """audit ctx 内部 handle · attach ProviderResult 后 finally 落 log."""

    agent_id: str
    endpoint: str
    model: str = ""
    user_id: str | None = None
    t0: float = 0.0
    error: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def attach(self, result: ProviderResult) -> None:
        """从 ProviderResult 抽 tokens / region / provider_name 注入 extras + 覆盖 model."""
        merged = extract_audit_extras(result)
        # ProviderResult.model 优先于 ctx 默认 model
        if result.model:
            self.model = result.model
        self.extras.update(merged)


def extract_audit_extras(result: ProviderResult) -> dict[str, Any]:
    """从 ProviderResult 抽 audit-relevant 字段 · 给 _record_safe 的 extras kwarg."""
    extras: dict[str, Any] = {}
    if result.input_tokens is not None:
        extras["input_tokens"] = result.input_tokens
    if result.output_tokens is not None:
        extras["output_tokens"] = result.output_tokens
    if result.model:
        extras["model"] = result.model
    if result.provider_name:
        extras["provider_name"] = result.provider_name
    if result.region:
        extras["region"] = result.region
    if result.cached:
        extras["cached"] = True
    if result.metadata:
        # fallback_chain / fallback_tried / 自定义 metadata
        for k, v in result.metadata.items():
            extras.setdefault(f"meta_{k}", v)
    return extras


def record_llm_call(
    *,
    agent_id: str,
    endpoint: str,
    model: str,
    latency_ms: int,
    error: str | None = None,
    extras: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> None:
    """Silent-fail wrapper · 调 audit_service._record_safe · 不可用 no-op."""
    try:
        from audit_service.decorators import _record_safe  # noqa: PLC0415
    except ImportError:
        return
    try:
        _record_safe(
            agent_id=agent_id,
            endpoint=endpoint,
            model=model,
            user_id=user_id,
            latency_ms=latency_ms,
            error=error,
            extras=extras,
        )
    except Exception as e:  # noqa: BLE001 — last-resort guard · audit 不阻塞业务
        logger.warning("[shared.llm_caller.audit] record_llm_call failed: %s", e)


@contextmanager
def with_audit(
    *,
    agent_id: str,
    endpoint: str,
    model: str = "",
    user_id: str | None = None,
) -> Iterator[AuditHandle]:
    """Context manager · 包 single LLM call · 自动 latency / error 落 audit log.

    Args:
        agent_id:  channel / credit / report / alert / compliance / riskctrl
        endpoint:  端点或 caller 标识 (供 audit log 区分 client-side vs route-side)
        model:     默认模型名 · ProviderResult.model 会覆盖
        user_id:   可选 · 来自 Depends(require_user) 的 sub

    Yields:
        AuditHandle · caller .attach(result) 注入 tokens / region 等

    Behavior:
        - 进入: 记 t0
        - 退出: 算 latency_ms · 异常存 error · finally 落 audit (silent fail)
        - 异常透传 · 不吞
    """
    handle = AuditHandle(
        agent_id=agent_id,
        endpoint=endpoint,
        model=model,
        user_id=user_id,
        t0=time.time(),
    )
    try:
        yield handle
    except Exception as e:
        handle.error = f"{type(e).__name__}: {e}"
        raise
    finally:
        latency_ms = int((time.time() - handle.t0) * 1000)
        record_llm_call(
            agent_id=handle.agent_id,
            endpoint=handle.endpoint,
            model=handle.model,
            latency_ms=latency_ms,
            error=handle.error,
            extras=handle.extras or None,
            user_id=handle.user_id,
        )


__all__ = [
    "AuditHandle",
    "extract_audit_extras",
    "record_llm_call",
    "with_audit",
]
