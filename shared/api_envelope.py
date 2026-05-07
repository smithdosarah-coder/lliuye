"""API Envelope · 统一返回 + mode/degraded/reason

per Phase C grounded report Tier 0.2 (PM 5/7 拍板 · Codex+Claude R2 共识):

设计 (Codex R2):
    { ok, data, error, meta }

- `ok` (bool): 二元成功失败 · 机器可判定
- `data`: 业务数据 (ok=true 时)
- `error`: 错误对象 (ok=false 时 · 含 category + origin + message)
- `meta`: 运行真实性
  - mode: "production" / "demo" / "mock_fallback" / "degraded"
  - degraded (bool)
  - reason (str | null) · 降级原因
  - correlation_id (str)
  - timestamp (ISO)
  - generated_at (ISO · 不可伪造)

R3 共识硬规 (degraded + ok 组合):
- ok=true + mode=production · OK
- ok=true + mode=degraded · OK (有 banner)
- ok=true + mode=mock_fallback · 仅 demo/sandbox tenant · 正式 tenant 必返 ok=false 或 degraded=true+blocked_for_business=true
- ok=false + error≠null + 业务 result=null · OK
- ok=true + error≠null · 禁止
- ok=false + data≠null · 禁止

使用:
    from shared.api_envelope import envelope_ok, envelope_error, envelope_degraded

    return envelope_ok(data={...}, mode="production")
    return envelope_error(category="validation", message="...", origin="api")
    return envelope_degraded(data={...}, reason="llm-timeout", origin="llm")
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Literal, Optional

# Mode 4 状态 (Codex R2 + Claude R2 互融合)
EnvelopeMode = Literal["production", "demo", "mock_fallback", "degraded"]

# Error category (Codex R2 业务行为为主)
ErrorCategory = Literal[
    "validation",          # 输入缺/格式错
    "auth",                # 未登录/权限不足/token 失效
    "dependency_unavailable",  # SQLite/API/LLM 服务不可用
    "timeout",             # API/LLM/DB 超时
    "rate_limited",        # LLM/API 限流
    "data_incomplete",     # 成功但缺关键字段
    "data_stale",          # 用了过期缓存
    "conflict",            # 并发冲突 · 需 reload/merge
    "business_rule",       # 业务政策拒绝 (额度不足 / KYC 未过 / 账户冻结)
    "llm_invalid_output",  # LLM 输出格式错
    "internal_unknown",    # 兜底未分类异常
]

# Error origin (system 层归因 · 内部 debug 用)
ErrorOrigin = Literal["llm", "audit", "persistence", "data", "business", "api", "auth"]


def _current_mode() -> EnvelopeMode:
    """当前运行 mode · 默认 production · 用 LIUYE_RUNTIME_MODE 覆盖."""
    return os.environ.get("LIUYE_RUNTIME_MODE", "production")  # type: ignore[return-value]


def _new_correlation_id() -> str:
    return f"cor-{uuid.uuid4().hex[:12]}"


def envelope_ok(
    data: Any,
    *,
    mode: Optional[EnvelopeMode] = None,
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """成功响应 · ok=true · mode 默认 current."""
    return {
        "ok": True,
        "data": data,
        "error": None,
        "meta": {
            "mode": mode or _current_mode(),
            "degraded": False,
            "reason": None,
            "correlation_id": correlation_id or _new_correlation_id(),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
    }


def envelope_degraded(
    data: Any,
    *,
    reason: str,
    origin: Optional[ErrorOrigin] = None,
    mode: EnvelopeMode = "degraded",
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """降级响应 · ok=true + mode=degraded · 业务可消费但有 banner."""
    return {
        "ok": True,
        "data": data,
        "error": None,
        "meta": {
            "mode": mode,
            "degraded": True,
            "reason": reason,
            "origin": origin,
            "correlation_id": correlation_id or _new_correlation_id(),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
    }


def envelope_error(
    *,
    category: ErrorCategory,
    message: str,
    origin: Optional[ErrorOrigin] = None,
    details: Optional[dict[str, Any]] = None,
    mode: EnvelopeMode = "production",
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """错误响应 · ok=false · category 业务行为 + origin 系统层."""
    return {
        "ok": False,
        "data": None,
        "error": {
            "category": category,
            "origin": origin,
            "message": message,
            "details": details or {},
        },
        "meta": {
            "mode": mode,
            "degraded": False,
            "reason": None,
            "correlation_id": correlation_id or _new_correlation_id(),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
    }


def envelope_mock_fallback(
    data: Any,
    *,
    reason: str = "llm-disabled",
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Mock fallback 响应.

    R3 共识 (Codex 立场胜):
    - 正式 tenant 默认禁 mock_fallback · 应返 ok=false 或 degraded blocked_for_business
    - sandbox/demo tenant 才用此 envelope
    - 默认 ok=false · 调用方明确知道不可作业务事实
    """
    return {
        "ok": False,
        "data": data,  # 留 data 给调用方仅作 demo/sandbox 显示
        "error": {
            "category": "dependency_unavailable",
            "origin": "llm",
            "message": "LLM/真实数据源不可用 · 走 mock fallback · 不可作业务事实",
            "details": {"blocked_for_business": True, "mock_reason": reason},
        },
        "meta": {
            "mode": "mock_fallback",
            "degraded": True,
            "reason": reason,
            "blocked_for_business": True,
            "correlation_id": correlation_id or _new_correlation_id(),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        },
    }


__all__ = [
    "EnvelopeMode",
    "ErrorCategory",
    "ErrorOrigin",
    "envelope_ok",
    "envelope_degraded",
    "envelope_error",
    "envelope_mock_fallback",
]
