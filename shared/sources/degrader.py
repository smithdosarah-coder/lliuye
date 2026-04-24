# -*- coding: utf-8 -*-
"""Failure degradation — 按偏好链顺序尝试每个 source。

语义:
- 链里第 1 个 ok=True 的 source 直接返回（degraded=False）。
- 从第 2 个开始成功的，返回前把 degraded 置 True，提示调用侧数据源降级了。
- 全链失败返回 ok=False + 聚合 error 字符串（"akshare: xxx; tavily: yyy"）。
- 单个 source 抛异常视为失败，但不中断链——会继续下一个。
"""
from __future__ import annotations

from .base import QueryRequest, QueryResult
from .registry import get, has


def execute_with_degradation(chain: list[str], request: QueryRequest) -> QueryResult:
    """按链尝试每个 source。

    Args:
        chain: source name 列表，按偏好从高到低排序（["akshare", "tavily"] → 先 akshare）。
        request: 具体查询请求。

    Returns:
        QueryResult：成功时 items/evidence 来自第一个成功的源；失败时 ok=False + 聚合 error。
    """
    if not chain:
        return QueryResult(
            ok=False,
            error="empty source chain",
            source_name="degrader",
        )

    errors: list[str] = []

    for idx, name in enumerate(chain):
        if not has(name):
            errors.append(f"{name}: not registered")
            continue

        source = get(name)

        # 跳过不支持当前 query_type 的源
        if not source.supports(request.query_type):
            errors.append(f"{name}: unsupported query_type={request.query_type}")
            continue

        # 跳过健康检查失败的源
        try:
            healthy = source.health()
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            healthy = False
            errors.append(f"{name}: health check raised {type(e).__name__}: {e}")
        if not healthy:
            errors.append(f"{name}: unhealthy")
            continue

        # 真正调用
        try:
            result = source.query(request)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
            continue

        if result.ok:
            # 从第 2 个开始命中的，标记 degraded=True
            if idx > 0:
                result.degraded = True
            if not result.source_name:
                result.source_name = name
            return result

        # ok=False：记录错误后继续下一个
        errors.append(f"{name}: {result.error or 'ok=False'}")

    return QueryResult(
        ok=False,
        source_name="degrader",
        error="; ".join(errors) if errors else "all sources failed",
        degraded=True,
    )
