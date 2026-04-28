# -*- coding: utf-8 -*-
"""audit_service.decorators — ``@audit_llm_call`` decorator for FastAPI endpoint hardening.

设计:
  - 包装 sync / async endpoint handler · 不改业务逻辑
  - pre-hook: 记 t0 · 解 user_id (从 ``user`` Depends kwarg `payload["sub"]`)
  - post-hook: 记 latency_ms · error (异常类型 + msg) · 调 ``default_recorder().record()``
  - **silent fail** (audit 失败不阻塞业务) · log warning · 业务异常正常 raise
  - tokens / cost / prompt / response 任选 · caller 通过 kwarg ``audit_extras`` 显式注入
    (例 SSE done event 后 set audit_extras 触发 capture)

使用:
    from audit_service.decorators import audit_llm_call

    @app.post("/api/channel/run")
    @audit_llm_call(agent_id="channel", endpoint="/api/channel/run", model="deepseek-chat")
    async def channel_run(req: Req, user=Depends(require_user)):
        ...
"""
from __future__ import annotations

import functools
import inspect
import logging
import time
from datetime import datetime
from typing import Any, Awaitable, Callable

from .recorder import LLMCall, default_recorder

logger = logging.getLogger(__name__)


def _extract_user_id(*args: Any, **kwargs: Any) -> str | None:
    """尝试从函数 kwargs 中拿 ``user`` payload (来自 ``Depends(require_user)``)."""
    user = kwargs.get("user")
    if isinstance(user, dict):
        sub = user.get("sub")
        if sub:
            return str(sub)
    return None


def _record_safe(
    *,
    agent_id: str,
    endpoint: str,
    model: str,
    user_id: str | None,
    latency_ms: int,
    error: str | None,
    extras: dict[str, Any] | None = None,
) -> None:
    """落地一条 LLMCall · 任何异常吞掉 (audit 不阻塞业务)."""
    try:
        extras = extras or {}
        call = LLMCall(
            ts=datetime.now().isoformat(timespec="seconds"),
            user_id=user_id,
            agent_id=agent_id,
            endpoint=endpoint,
            model=extras.get("model") or model,
            prompt=extras.get("prompt"),
            response=extras.get("response"),
            input_tokens=extras.get("input_tokens"),
            output_tokens=extras.get("output_tokens"),
            cost_cny=extras.get("cost_cny"),
            latency_ms=latency_ms,
            error=error,
        )
        default_recorder().record(call)
    except Exception as e:  # noqa: BLE001 — last-resort guard
        logger.warning("[audit_service] decorator record failed: %s", e)


def audit_llm_call(
    *,
    agent_id: str,
    endpoint: str,
    model: str = "deepseek-chat",
):
    """endpoint decorator · pre/post hook 写 audit log.

    Args:
        agent_id: channel / credit / report / alert / compliance / riskctrl
        endpoint: 端点 URL (供 audit log 区分)
        model: LLM 模型名 (默认 deepseek-chat · 各 endpoint 显式覆盖)
    """

    def deco(
        fn: Callable[..., Any] | Callable[..., Awaitable[Any]],
    ) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                t0 = time.time()
                user_id = _extract_user_id(*args, **kwargs)
                err: str | None = None
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    raise
                finally:
                    latency_ms = int((time.time() - t0) * 1000)
                    extras = kwargs.get("__audit_extras__")  # caller 可注入
                    _record_safe(
                        agent_id=agent_id,
                        endpoint=endpoint,
                        model=model,
                        user_id=user_id,
                        latency_ms=latency_ms,
                        error=err,
                        extras=extras if isinstance(extras, dict) else None,
                    )
            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.time()
            user_id = _extract_user_id(*args, **kwargs)
            err: str | None = None
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                raise
            finally:
                latency_ms = int((time.time() - t0) * 1000)
                extras = kwargs.get("__audit_extras__")
                _record_safe(
                    agent_id=agent_id,
                    endpoint=endpoint,
                    model=model,
                    user_id=user_id,
                    latency_ms=latency_ms,
                    error=err,
                    extras=extras if isinstance(extras, dict) else None,
                )
        return sync_wrapper

    return deco


__all__ = ["audit_llm_call"]
