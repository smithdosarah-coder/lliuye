# -*- coding: utf-8 -*-
"""Prometheus metrics + FastAPI middleware (Stage E.2 · onboarding W-E2-A3).

按 onboarding 必备 metrics:
- http_requests_total{method, path, status} (Counter)
- http_request_duration_seconds{method, path} (Histogram · default buckets)
- llm_calls_total{provider, agent} (Counter)
- llm_errors_total{provider, agent, error_type} (Counter)
- llm_call_duration_seconds{provider, agent} (Histogram)
- im_ws_connections_active (Gauge)
- audit_log_writes_total{endpoint} (Counter)

设计 graceful no-dep fallback:
- prometheus_client 未装 → 全 metrics NoOp · /metrics endpoint 返空 + 头部说明
- 主进程绝不因 metric 失败而崩

middleware: 拦截 HTTP request · 记 method + path + status + duration
路径标准化: /api/credit/decision/{sid} → /api/credit/decision/:id (避免高基数 path)
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import Response


# ---------------------------------------------------------------------------
# Optional dependency · graceful fallback
# ---------------------------------------------------------------------------

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    _PROM_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dep
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    _PROM_AVAILABLE = False

    class _NoOpMetric:
        """No-op metric · 接受任意 .labels(...).inc() / .observe() / .set() · 不报错."""

        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

        def dec(self, *args, **kwargs):
            return None

    Counter = _NoOpMetric  # type: ignore[assignment, misc]
    Histogram = _NoOpMetric  # type: ignore[assignment, misc]
    Gauge = _NoOpMetric  # type: ignore[assignment, misc]
    CollectorRegistry = type("_NoOpRegistry", (), {})  # type: ignore[assignment, misc]

    def generate_latest(*args, **kwargs) -> bytes:  # type: ignore[no-redef]
        return b"# prometheus_client not installed - monitoring stub mode\n"


# ---------------------------------------------------------------------------
# Metrics 注册 · module-level singleton
# ---------------------------------------------------------------------------


def _make_registry() -> Any:
    """每次新 registry 防 test 间污染 · 支持 reset_registry()."""
    if not _PROM_AVAILABLE:
        return None
    return CollectorRegistry(auto_describe=True)


_registry: Any = _make_registry()


# 暴露 module-level 引用 · 测试可 reset_registry() + 重新 init_metrics()
_metrics: dict[str, Any] = {}


def init_metrics(registry: Any = None) -> dict[str, Any]:
    """初始化全部 metric · 返字典. registry=None 时用 module-level _registry."""
    reg = registry if registry is not None else _registry
    kwargs = {"registry": reg} if _PROM_AVAILABLE else {}

    _metrics["http_requests_total"] = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
        **kwargs,
    )
    _metrics["http_request_duration_seconds"] = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
        **kwargs,
    )
    _metrics["llm_calls_total"] = Counter(
        "llm_calls_total",
        "Total LLM calls",
        ["provider", "agent"],
        **kwargs,
    )
    _metrics["llm_errors_total"] = Counter(
        "llm_errors_total",
        "Total LLM errors",
        ["provider", "agent", "error_type"],
        **kwargs,
    )
    _metrics["llm_call_duration_seconds"] = Histogram(
        "llm_call_duration_seconds",
        "LLM call duration in seconds",
        ["provider", "agent"],
        **kwargs,
    )
    _metrics["im_ws_connections_active"] = Gauge(
        "im_ws_connections_active",
        "Number of active IM WebSocket connections",
        **kwargs,
    )
    _metrics["audit_log_writes_total"] = Counter(
        "audit_log_writes_total",
        "Total audit log writes",
        ["endpoint"],
        **kwargs,
    )
    return _metrics


def reset_registry() -> None:
    """测试用 · 重建 registry · idempotent."""
    global _registry, _metrics
    _registry = _make_registry()
    _metrics = {}
    init_metrics()


def get_metric(name: str) -> Any:
    """取 metric · 未 init 时自动 init."""
    if not _metrics:
        init_metrics()
    return _metrics.get(name)


def is_prometheus_available() -> bool:
    return _PROM_AVAILABLE


# 默认即时 init · 让 import 后即可用
init_metrics()


# ---------------------------------------------------------------------------
# Path normalization · 防高基数 (UUID / id / hash 转 :id)
# ---------------------------------------------------------------------------


_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_HEX12_RE = re.compile(r"\b[0-9a-f]{12,}\b", re.IGNORECASE)
_NUMERIC_ID_RE = re.compile(r"/(\d{3,})(?=/|$)")


def normalize_path(path: str) -> str:
    """把动态 segment 替换为 :id · 防高基数标签爆炸."""
    if not path:
        return "/"
    p = _UUID_RE.sub(":id", path)
    p = _HEX12_RE.sub(":id", p)
    p = _NUMERIC_ID_RE.sub("/:id", p)
    # 截首段保留 /api/<group>/<resource> 三段以内 · 后续全 :rest
    parts = p.split("/")
    if len(parts) > 6:
        p = "/".join(parts[:6]) + "/:rest"
    return p


# ---------------------------------------------------------------------------
# FastAPI middleware
# ---------------------------------------------------------------------------


async def http_metrics_middleware(request: Request, call_next: Callable):
    """记录 HTTP request 耗时 + 状态码."""
    start = time.perf_counter()
    method = request.method
    path = normalize_path(request.url.path)
    status_code = "500"
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception as e:
        # 5xx 异常时仍记 metric 然后 raise (Sentry 接 raise)
        status_code = "500"
        get_metric("http_requests_total").labels(
            method=method, path=path, status=status_code,
        ).inc()
        raise
    finally:
        duration = max(0.0, time.perf_counter() - start)
        get_metric("http_request_duration_seconds").labels(
            method=method, path=path,
        ).observe(duration)
        # 上面 try/except 已 cover 5xx · 这里只覆盖 200 路径
        if status_code != "500":
            get_metric("http_requests_total").labels(
                method=method, path=path, status=status_code,
            ).inc()


def install_metrics_middleware(app: FastAPI) -> None:
    """显式调用 · 把 middleware 接到 FastAPI app."""
    app.middleware("http")(http_metrics_middleware)


# ---------------------------------------------------------------------------
# /metrics endpoint
# ---------------------------------------------------------------------------


def metrics_response() -> Response:
    """Prometheus exposition format · text/plain · 注 stub 模式时返说明."""
    if not _PROM_AVAILABLE:
        body = b"# prometheus_client not installed - install via pip - stub mode\n"
        return Response(content=body, media_type="text/plain; charset=utf-8")
    body = generate_latest(_registry)
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Helper · domain code 调用便捷函数
# ---------------------------------------------------------------------------


def record_llm_call(provider: str, agent: str, duration_s: float, *,
                    error_type: Optional[str] = None) -> None:
    """业务代码调 · 记 llm 调用 + (可选) 错误."""
    get_metric("llm_calls_total").labels(provider=provider, agent=agent).inc()
    get_metric("llm_call_duration_seconds").labels(
        provider=provider, agent=agent,
    ).observe(max(0.0, duration_s))
    if error_type:
        get_metric("llm_errors_total").labels(
            provider=provider, agent=agent, error_type=error_type,
        ).inc()


def record_audit_write(endpoint: str) -> None:
    get_metric("audit_log_writes_total").labels(endpoint=endpoint).inc()


def set_im_ws_active(count: int) -> None:
    get_metric("im_ws_connections_active").set(max(0, int(count)))


def inc_im_ws_active() -> None:
    get_metric("im_ws_connections_active").inc()


def dec_im_ws_active() -> None:
    get_metric("im_ws_connections_active").dec()
