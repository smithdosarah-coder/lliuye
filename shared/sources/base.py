# -*- coding: utf-8 -*-
"""BaseSource protocol + shared Pydantic types.

分层数据源架构的类型骨架。所有具体源（tavily / akshare / gov_cn / pbc / flk_npc）
都继承 BaseSource，通过 Router + Degrader 按偏好链串起来。

设计要点:
- 每条 QueryResult 必须带 evidence 列表；空 evidence 视为 ok=False（CLAUDE.md 证据支撑原则）。
- source_name 必须填，便于调用侧审计 + 前端展示数据来源。
- degraded=True 表示这条结果是偏好链降级路径产生的，调用侧可以做 UI 提示。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceTier(str, Enum):
    """数据源分层。越靠前权威性越高、UI 上越值得强调来源。"""

    OFFICIAL = "official"       # gov.cn / pbc / flk / sse 等官方站
    AGGREGATOR = "aggregator"   # akshare / ifind / caixin 等聚合源
    WEB_SEARCH = "web_search"   # tavily 等通用搜索


class Evidence(BaseModel):
    """一条「证据」——支撑 result item 的原始出处。

    Agent 把这个字段透传到前端/报告时，用户可以点 source_url 回到原文验证，
    满足银行/金融客户「所有数字/结论都要有出处」的底线。
    """

    source_name: str
    source_url: str = ""
    fetched_at: str
    raw_excerpt: str = ""
    confidence: float = 1.0


class QueryRequest(BaseModel):
    """调用方传给 Router 的请求。

    query_type 是路由关键字段。同一个 domain（例如 agent_credit.profile）可能
    对应多种 query_type，每个 source 通过 supported_query_types 自行判断是否接单。
    """

    query: str
    query_type: str            # research | financial | policy | law | news | macro | generic | ...
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = 10


class QueryResult(BaseModel):
    """单个 source 的返回。Router 也复用这个结构对外暴露最终结果。"""

    ok: bool
    items: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    source_name: str = ""
    degraded: bool = False
    error: str = ""
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class BaseSource(ABC):
    """具体源必须继承此抽象基类。

    name / tier / supported_query_types 是类属性；registry / router 完全依赖它们做匹配。
    """

    name: str = "abstract"
    tier: SourceTier = SourceTier.WEB_SEARCH
    cost: str = "free"
    supported_query_types: set[str] = set()

    @abstractmethod
    def query(self, request: QueryRequest) -> QueryResult:
        """执行查询。必须返回 QueryResult，不允许抛异常——失败时设 ok=False + error。"""
        raise NotImplementedError

    def supports(self, query_type: str) -> bool:
        return query_type in self.supported_query_types

    def health(self) -> bool:
        """快速可用性探测（例如检查 API key / 网络）。Router 跳过 health()=False 的源。"""
        return True
