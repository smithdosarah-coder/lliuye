# -*- coding: utf-8 -*-
"""BaseScanner Protocol + ScanRequest / ScanRunResult Pydantic types.

D.5 共享扫描底座的类型骨架。所有具体 scanner（alert_customer / compliance_policy /
channel_signal / ...）都继承 BaseScanner，通过 Router + Degrader 按偏好链串起来。

设计 (mirror ``shared/sources/base.py`` 模式):
- BaseScanner 抽象基类 · `scan(request) -> ScanRunResult` 是唯一约定入口
- 每个 scanner 必须填 `name` / `agent_key` / `supported_scopes`
- 失败时设 `ok=False` + `error` · **不抛异常** (degrader 链才能继续)
- `degraded=True` 表示降级路径产生的结果 · 调用侧可做 UI 提示
- HitList 复用既有 ``shared.kb_scan.models.HitList`` (D.5 不重做模型层)

为什么不复用 ``shared/sources/`` :
- sources/ 解决 "数据源拉数据" (同一 query 多个源选最好的)
- kb_scan/ 解决 "KB × 规则 = 命中清单" (业务级扫描) · 输入输出形态不同
- 二者互补 · scanner 内部可以再调 sources.Router 取数据

Author: Worker A1 (Stage D 第 1 批) · 2026-04-28
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .models import HitItem, HitList


class ScanRequest(BaseModel):
    """统一 KB 扫描请求 · 调用方传给 Router/BaseScanner.

    字段语义:
      - ``query``: 自由文本查询 (Channel: 业务诉求; Compli: 关键词; Alert: 通常空)
      - ``kb_id``: KB 上传后的标识 · 0+ scanner 复用
      - ``scope``: scanner-specific 范围标识 · degrader 用此跳过不接的 scanner
      - ``filters``: 灵活过滤参数 (industry / region / severity 等)
      - ``limit``: 候选/命中数上限
      - ``llm_fn``: 可选 LLM caller (避全局 import · 调用方注入)
    """

    query: str = ""
    kb_id: str = ""
    scope: str = "default"
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = 10


class ScanRunResult(BaseModel):
    """BaseScanner / Router 运行输出 · 包装 HitList + 降级 / 错误元数据.

    与 ``shared/sources.QueryResult`` 同构 · 但负载是 HitList (业务命中清单)
    而非 raw items list。
    """

    ok: bool
    scanner_name: str = ""
    hits: list[HitItem] = Field(default_factory=list)
    hit_list: HitList | None = None
    summary: str = ""
    degraded: bool = False
    error: str = ""
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def hit_count(self) -> int:
        """方便上层 quick check · 不依赖 hits/hit_list 二选一."""
        if self.hit_list is not None:
            return self.hit_list.total_hit
        return len(self.hits)


class BaseScanner(ABC):
    """具体 scanner 必须继承此抽象基类.

    name / agent_key / supported_scopes 是类属性 · registry/router 完全依赖它们做匹配。
    """

    name: str = "abstract"
    agent_key: str = "shared"  # alert / compliance / channel / credit / report / riskctrl
    cost: str = "free"
    supported_scopes: set[str] = set()

    @abstractmethod
    def scan(self, request: ScanRequest) -> ScanRunResult:
        """执行扫描.

        约束:
          - 必须返回 ScanRunResult · **不允许抛异常**
          - 失败 → ``ok=False`` + ``error="..."``
          - 部分 KB 缺失 / 0 命中 → ``ok=True, hits=[]``
        """
        raise NotImplementedError

    def supports(self, scope: str) -> bool:
        """scope 路由判断 · degrader 跳过不接的 scanner.

        语义 (per test_base_scanner_supports_*):
          - 空 ``supported_scopes`` set 表示「仅接 default-等价 (default | "")」
          - 非空 set · 空 scope 字符串视为请求 "default"
          - 非空 set · 非空 scope · 走显式包含判断
        """
        if not self.supported_scopes:
            return scope in ("default", "")
        if not scope:
            return "default" in self.supported_scopes
        return scope in self.supported_scopes

    def health(self) -> bool:
        """快速可用性探测 (可选 KB 已加载 · 依赖可用等)."""
        return True


__all__ = ["BaseScanner", "ScanRequest", "ScanRunResult"]
