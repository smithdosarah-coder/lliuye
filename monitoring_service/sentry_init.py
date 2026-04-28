# -*- coding: utf-8 -*-
"""Sentry SDK init (Stage E.2 · onboarding W-E2-A3).

按 onboarding:
- DSN 走 .env (SENTRY_DSN)
- auto-instrument FastAPI · catch unhandled + 5xx
- DSN 缺时 silent skip · 不阻断主进程
- 缺 sentry_sdk dep 时 NoOp · 同样不崩

Env 配置:
- SENTRY_DSN          (必 · 缺则 disable)
- SENTRY_ENVIRONMENT  (默认 "production")
- SENTRY_TRACES_SAMPLE_RATE (默认 0.1 · 减 trace 量)
- SENTRY_RELEASE      (可选 · git sha)
"""
from __future__ import annotations

import os
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Optional dependency · graceful fallback
# ---------------------------------------------------------------------------

try:
    import sentry_sdk  # type: ignore[import]
    from sentry_sdk.integrations.fastapi import FastApiIntegration  # type: ignore[import]
    from sentry_sdk.integrations.starlette import StarletteIntegration  # type: ignore[import]
    _SENTRY_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dep
    sentry_sdk = None  # type: ignore[assignment]
    FastApiIntegration = None  # type: ignore[assignment, misc]
    StarletteIntegration = None  # type: ignore[assignment, misc]
    _SENTRY_AVAILABLE = False


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_initialized: bool = False
_init_status: dict[str, Any] = {
    "available": _SENTRY_AVAILABLE,
    "initialized": False,
    "dsn_present": False,
    "environment": "",
    "skip_reason": "",
}


def is_sentry_available() -> bool:
    return _SENTRY_AVAILABLE


def get_init_status() -> dict[str, Any]:
    """Caller (e.g. /health/extended) 可读取当前 Sentry 状态."""
    return dict(_init_status)


def init_sentry(
    *,
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    traces_sample_rate: Optional[float] = None,
    release: Optional[str] = None,
) -> bool:
    """初始化 Sentry · 返 True 表 init 成功 · False 表 silent skip.

    优先级: 显式传参 > env · DSN 缺则跳过 · sentry_sdk 缺则跳过.
    Idempotent · 多次调 OK.
    """
    global _initialized

    _init_status["available"] = _SENTRY_AVAILABLE
    if not _SENTRY_AVAILABLE:
        _init_status["skip_reason"] = "sentry_sdk not installed"
        return False

    if _initialized:
        return True

    actual_dsn = (dsn or os.environ.get("SENTRY_DSN", "")).strip()
    _init_status["dsn_present"] = bool(actual_dsn)
    if not actual_dsn:
        _init_status["skip_reason"] = "SENTRY_DSN env not set"
        return False

    actual_env = (environment or os.environ.get("SENTRY_ENVIRONMENT", "production")).strip()
    actual_release = (release or os.environ.get("SENTRY_RELEASE", "")).strip() or None

    if traces_sample_rate is None:
        try:
            actual_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        except ValueError:
            actual_rate = 0.1
    else:
        actual_rate = traces_sample_rate
    actual_rate = max(0.0, min(1.0, actual_rate))

    integrations = []
    if FastApiIntegration is not None:
        integrations.append(FastApiIntegration())
    if StarletteIntegration is not None:
        integrations.append(StarletteIntegration())

    try:
        sentry_sdk.init(  # type: ignore[union-attr]
            dsn=actual_dsn,
            environment=actual_env,
            release=actual_release,
            traces_sample_rate=actual_rate,
            integrations=integrations,
            send_default_pii=False,
        )
    except Exception as e:  # noqa: BLE001 · 防 sentry init 自身崩
        _init_status["skip_reason"] = f"init failed: {type(e).__name__}: {e}"
        return False

    _initialized = True
    _init_status.update({
        "initialized": True,
        "environment": actual_env,
        "traces_sample_rate": actual_rate,
        "release": actual_release or "",
        "skip_reason": "",
    })
    return True


def reset_for_tests() -> None:
    """测试用 · 清状态 · 让 init_sentry 可重新跑."""
    global _initialized
    _initialized = False
    _init_status.update({
        "initialized": False,
        "dsn_present": False,
        "environment": "",
        "skip_reason": "",
    })


def capture_exception(error: BaseException) -> None:
    """显式 capture · 业务 except 分支用 · sentry 不可用时 silent."""
    if not _SENTRY_AVAILABLE or not _initialized:
        return
    try:
        sentry_sdk.capture_exception(error)  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass


def capture_message(message: str, *, level: str = "info") -> None:
    """显式 capture text message · 不可用时 silent."""
    if not _SENTRY_AVAILABLE or not _initialized:
        return
    try:
        sentry_sdk.capture_message(message, level=level)  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
