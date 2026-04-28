# -*- coding: utf-8 -*-
"""Failure degradation — 按偏好链顺序尝试每个 scanner.

语义 (与 ``shared/sources/degrader.py`` 一致):
  - 链中第 1 个 ok=True 的 scanner 直返 (degraded=False)
  - 从第 2 个开始成功的 · 返前置 degraded=True (UI 可标降级)
  - 全链失败返 ok=False + 聚合 error ("alert_customer: xxx; compliance_policy: yyy")
  - 单 scanner 抛异常视为失败 · 不中断链 · 继续下一个
  - 不接 scope 的 scanner 直接跳过 · 不计入 error

Q-040 教训: Tavily 401 fallback 必须在 scanner 层 · 一处修全 6 Agent 受益。
"""
from __future__ import annotations

from .base import ScanRequest, ScanRunResult
from .registry import get, has


def execute_with_degradation(
    chain: list[str], request: ScanRequest,
) -> ScanRunResult:
    """按链尝试每个 scanner.

    Args:
        chain: scanner name 列表 · 偏好高 → 低
        request: ScanRequest

    Returns:
        ScanRunResult · 成功 hits/hit_list 来自第一个成功 scanner;
        失败 ok=False + 聚合 error。
    """
    if not chain:
        return ScanRunResult(
            ok=False,
            error="empty scanner chain",
            scanner_name="kb_scan.degrader",
        )

    errors: list[str] = []

    for idx, name in enumerate(chain):
        if not has(name):
            errors.append(f"{name}: not registered")
            continue

        scanner = get(name)

        # 跳过不支持当前 scope 的 scanner
        if not scanner.supports(request.scope):
            errors.append(f"{name}: unsupported scope={request.scope}")
            continue

        # 跳过 health 失败的 scanner
        try:
            healthy = scanner.health()
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
                KeyError, ImportError) as e:
            healthy = False
            errors.append(f"{name}: health raised {type(e).__name__}: {e}")
        if not healthy:
            errors.append(f"{name}: unhealthy")
            continue

        # 真正调用
        try:
            result = scanner.scan(request)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
                KeyError, ImportError) as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
            continue

        if result.ok:
            if idx > 0:
                result.degraded = True
            if not result.scanner_name:
                result.scanner_name = name
            return result

        # ok=False · 记录后继续下一个
        errors.append(f"{name}: {result.error or 'ok=False'}")

    return ScanRunResult(
        ok=False,
        scanner_name="kb_scan.degrader",
        error="; ".join(errors) if errors else "all scanners failed",
        degraded=True,
    )


__all__ = ["execute_with_degradation"]
