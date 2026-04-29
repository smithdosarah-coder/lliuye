# -*- coding: utf-8 -*-
"""audit_service.stream_helpers — SSE generator finally hook for accurate audit timing.

为何独立成文件 (相对 ``decorators.py``):
  - ``@audit_llm_call`` 包 FastAPI route function · SSE 路由返
    ``StreamingResponse(generator)`` 后 route function 立即退出 ·
    decorator 在 ``finally`` 里记 ``latency_ms`` = "包路由的时间" ·
    **不是 stream 内 LLM 调用时间** · 银保监合规留痕失真。
  - 真正应记的是 generator 跑完 (含 LLM 真实延迟) 后才落 audit ·
    所以让 SSE 路由 / generator 内部用 try/except/finally 显式调
    ``audit_stream_event(...)`` (本模块) · 把 t0 → generator 完成 / 异常
    时点的 latency 写正确。
  - decorator 同时为 sync JSON route 留用 (无 SSE 偏差)。

Author: Worker A1 (Stage W-FIX2 · 修 bug #11) · 2026-04-29
"""
from __future__ import annotations

import logging
import time
from typing import Any

from .decorators import _record_safe  # 复用 silent-fail 落盘 helper

logger = logging.getLogger(__name__)


def audit_stream_event(
    agent_id: str,
    endpoint: str,
    model: str,
    t0: float,
    *,
    user_id: str | None = None,
    error: str | None = None,
    extras: dict[str, Any] | None = None,
) -> None:
    """SSE generator finally 里调用 · 记一条精确 latency 的审计行.

    Args:
        agent_id: channel / credit / report / alert / compliance / riskctrl
        endpoint: 端点 URL · e.g. /api/alert/scan
        model: LLM 模型名 · 默认 deepseek-chat
        t0: ``time.time()`` 时间戳 · 在 SSE route 进入 generator 前记下
        user_id: 来自 ``Depends(require_user)`` 的 sub · 可空 (未登录)
        error: 异常字符串 (``f"{type(e).__name__}: {e}"``) · 默认 None
        extras: caller 可注入 ``{prompt, response, input_tokens, output_tokens,
            cost_cny, model}`` · 任一字段缺失即跳过 (silent fail)

    无返回值 · 任何异常吞掉 · audit 不阻塞业务 (复用 ``_record_safe``)。
    """
    try:
        latency_ms = int((time.time() - t0) * 1000)
        _record_safe(
            agent_id=agent_id,
            endpoint=endpoint,
            model=model,
            user_id=user_id,
            latency_ms=latency_ms,
            error=error,
            extras=extras if isinstance(extras, dict) else None,
        )
    except Exception as e:  # noqa: BLE001 — last-resort guard
        logger.warning(
            "[audit_service.stream_helpers] audit_stream_event failed: %s", e,
        )


__all__ = ["audit_stream_event"]
