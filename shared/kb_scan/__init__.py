# -*- coding: utf-8 -*-
"""知识库扫描范式（Agent1/4/5 共享底座）

核心组件：
- models       : 通用 Pydantic 模型（RuleItem/CompanyProfile/HitList 等）
- search_provider : 搜索数据源抽象 + Mock/Web 实现（一行切换）
- knowledge_base  : 知识库装载器（规则/客户/条款）
- rule_extractor  : LLM 从非结构化文档抽取规则
- matcher         : 目标 × 规则 → 命中项
- hit_ranker      : 命中项排序与分级
- exporters       : 导出 Excel/Word 榜单
"""

from .models import (
    RiskLevel,
    RuleType,
    RuleItem,
    CompanyProfile,
    IdealProfile,
    ScanTarget,
    ScanResult,
    Evidence,
    HitItem,
    HitList,
)
from .search_provider import (
    SearchProvider,
    MockSearchProvider,
    WebSearchProvider,
    build_search_provider,
)
from .knowledge_base import KnowledgeBase
from .rule_extractor import RuleExtractor
from .matcher import Matcher, SimilarityScorer
from .hit_ranker import HitRanker

__all__ = [
    "RiskLevel", "RuleType", "RuleItem", "CompanyProfile", "IdealProfile",
    "ScanTarget", "ScanResult", "Evidence", "HitItem", "HitList",
    "SearchProvider", "MockSearchProvider", "WebSearchProvider",
    "build_search_provider",
    "KnowledgeBase", "RuleExtractor",
    "Matcher", "SimilarityScorer", "HitRanker",
]
