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
        # ROI #5 · 即使 path 不在 audit_paths 也要 set contextvar (decorator/stream_helpers
        # 用 contextvar 拿 e2e_run_id) · 否则 /api/auth/login 等非 audit_paths 的 LLM
        # endpoint 拿不到 run_id. 早 set 早覆盖整个 request 生命周期.
        run_id = _extract_e2e_run_id_from_scope(scope)
        ctx_token = None
        if run_id:
            from .recorder import e2e_run_id_var
            ctx_token = e2e_run_id_var.set(run_id)

        if not any(path.startswith(p) for p in self.audit_paths):
            try:
                await self.app(scope, receive, send)
            finally:
                if ctx_token is not None:
                    from .recorder import e2e_run_id_var
                    e2e_run_id_var.reset(ctx_token)
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
                        # e2e_run_id 由 record() 从 contextvar 自动拿
                    ),
                )
            except Exception as audit_err:  # noqa: BLE001
                logger.warning("[audit_service] middleware record failed: %s", audit_err)
            # ROI #5 · reset contextvar (避免泄漏到下一个 request · 仅同协程影响 ·
            # 但严谨起见显式 reset · 防 starlette 复用 task 时残留)
            if ctx_token is not None:
                try:
                    from .recorder import e2e_run_id_var
                    e2e_run_id_var.reset(ctx_token)
                except Exception:  # noqa: BLE001
                    pass


def _extract_e2e_run_id_from_scope(scope: Any) -> str | None:
    """从 ASGI scope.headers 取 ``X-Liuye-E2E-Run-Id`` (lower-case · bytes pair list).

    ROI #5 · 本 header 由 daily-visual.yml admin-e2e job E2E 触发时注入 ·
    生产 cloudflare/nginx 不应 strip 自定义 header (实测 X-Forwarded-* 全透传) ·
    若被 strip 则 record 写 NULL · 不阻塞业务. 见 e2e-slo-2-contract.md §3.6.
    """
    headers = scope.get("headers") or []
    target = b"x-liuye-e2e-run-id"
    for name, value in headers:
        if isinstance(name, bytes) and name.lower() == target:
            try:
                v = value.decode("latin-1") if isinstance(value, bytes) else str(value)
                # sanitize: 仅允许 alphanumeric + - · 防 SQL/log injection · GH run_id
                # 仅为数字 string · 实战传 "local" / "12345" / "test-foo" 即可
                v = "".join(ch for ch in v if ch.isalnum() or ch in "-_.")
                return v[:64] or None  # 防超长 · 截 64
            except (UnicodeDecodeError, AttributeError):
                return None
    return None


def _default_agent_resolver(path: str) -> str:
    """从 ``/api/<agent>/...`` 取 agent 名 · 失败返 unknown."""
    if path.startswith("/api/"):
        rest = path[len("/api/"):]
        head = rest.split("/", 1)[0]
        if head:
            return head
    return "unknown"


__all__ = ["AuditLogMiddleware", "DEFAULT_AUDIT_PATHS"]
