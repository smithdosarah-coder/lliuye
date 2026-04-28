# -*- coding: utf-8 -*-
"""audit_service.middleware — FastAPI middleware (alternative to decorator).

适合:
  - 全局自动审计所有 ``/api/*`` 调用 (不需逐 endpoint 加 decorator)
  - 不能拿 LLM token / cost (中间件层不知 LLM 调用细节) · 仅记 endpoint / latency / error

何时用 middleware vs decorator:
  - decorator: 显式 mark "这个 endpoint 是 LLM call" · 区分非 LLM endpoint
  - middleware: 全局兜底 · 防止漏标 LLM endpoint
  - 一般 decorator 优先 · middleware 用做 belt-and-suspenders

实装为 ASGI middleware (Starlette 兼容) · 接 ``FastAPI.add_middleware`` 用。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# 默认审计 prefix · 调用方可覆盖
DEFAULT_AUDIT_PATHS = (
    "/api/channel/",
    "/api/credit/",
    "/api/report/",
    "/api/alert/",
    "/api/compliance/",
    "/api/riskctrl/",
)


class AuditLogMiddleware:
    """ASGI middleware · 路径 prefix 命中即记审计 (best-effort)."""

    def __init__(
        self,
        app: Any,
        audit_paths: tuple[str, ...] = DEFAULT_AUDIT_PATHS,
        agent_resolver: Any = None,
    ) -> None:
        self.app = app
        self.audit_paths = audit_paths
        self.agent_resolver = agent_resolver or _default_agent_resolver

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not any(path.startswith(p) for p in self.audit_paths):
            await self.app(scope, receive, send)
            return

        t0 = time.time()
        err: str | None = None
        status_code: int | None = None

        async def _send_with_capture(msg: Any) -> None:
            nonlocal status_code
            if msg.get("type") == "http.response.start":
                status_code = msg.get("status")
            await send(msg)

        try:
            await self.app(scope, receive, _send_with_capture)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            raise
        finally:
            try:
                from .recorder import LLMCall, default_recorder

                latency_ms = int((time.time() - t0) * 1000)
                agent_id = self.agent_resolver(path)
                # middleware 层不知 user_id (cookie 还没解析) · 留空
                # 错误优先 · 否则 4xx/5xx 也算 error
                if err is None and status_code is not None and status_code >= 400:
                    err = f"HTTP {status_code}"
                default_recorder().record(
                    LLMCall(
                        ts=datetime.now().isoformat(timespec="seconds"),
                        user_id=None,
                        agent_id=agent_id,
                        endpoint=path,
                        model="middleware",
                        latency_ms=latency_ms,
                        error=err,
                    ),
                )
            except Exception as audit_err:  # noqa: BLE001
                logger.warning("[audit_service] middleware record failed: %s", audit_err)


def _default_agent_resolver(path: str) -> str:
    """从 ``/api/<agent>/...`` 取 agent 名 · 失败返 unknown."""
    if path.startswith("/api/"):
        rest = path[len("/api/"):]
        head = rest.split("/", 1)[0]
        if head:
            return head
    return "unknown"


__all__ = ["AuditLogMiddleware", "DEFAULT_AUDIT_PATHS"]
