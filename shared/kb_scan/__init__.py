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

D.5 共享底座 (Stage D 第 1 批 · 2026-04-28 · W-D5-A1):
- base.py       : BaseScanner Protocol + ScanRequest + ScanRunResult
- registry.py   : name → BaseScanner 实例查找
- degrader.py   : 偏好链 fallback 执行
- router.py     : ScannerRouter (按 domain 路由)
- impls/        : per-Agent BaseScanner 适配器 (alert_customer / compliance_policy /
                  channel_signal · 不重写业务 · 仅 wrap)
- bootstrap_scanners() : 一次性注册 impls + 调各 agent kb_scan_config.init()
"""

from .base import BaseScanner, ScanRequest, ScanRunResult
from .hit_ranker import HitRanker
from .knowledge_base import KnowledgeBase
from .matcher import Matcher, SimilarityScorer
from .models import (
    CompanyProfile,
    Evidence,
    HitItem,
    HitList,
    IdealProfile,
    RiskLevel,
    RuleItem,
    RuleType,
    ScanResult,
    ScanTarget,
)
from .router import ScannerRouter
from .rule_extractor import RuleExtractor
from .search_provider import (
    MockSearchProvider,
    SearchProvider,
    WebSearchProvider,
    build_search_provider,
)

__all__ = [
    "BaseScanner",
    "ScanRequest",
    "ScanRunResult",
    "ScannerRouter",
    "RiskLevel", "RuleType", "RuleItem", "CompanyProfile", "IdealProfile",
    "ScanTarget", "ScanResult", "Evidence", "HitItem", "HitList",
    "SearchProvider", "MockSearchProvider", "WebSearchProvider",
    "build_search_provider",
    "KnowledgeBase", "RuleExtractor",
    "Matcher", "SimilarityScorer", "HitRanker",
    "bootstrap_scanners",
]


def bootstrap_scanners() -> dict[str, bool]:
    """注册 D.5 共享 scanner impls + 各 agent 偏好链.

    幂等 · 多次调用安全 · 返各步骤状态字典 (失败不抛 · 记入 status)。
    模式与 ``shared.sources.bootstrap()`` 一致。

    Returns:
        ``{"scanner.<name>": bool, "prefs.<agent>": bool}`` map。
    """
    status: dict[str, bool] = {}

    # --- 注册具体 scanner adapter ---
    impls_to_register = [
        ("alert_customer", "AlertCustomerScannerAdapter"),
        ("compliance_policy", "CompliancePolicyScannerAdapter"),
        ("channel_signal", "ChannelSignalScannerAdapter"),
    ]
    for mod_name, cls_name in impls_to_register:
        try:
            module = __import__(
                f"shared.kb_scan.impls.{mod_name}", fromlist=[cls_name],
            )
            cls = getattr(module, cls_name)
            from .registry import register
            register(cls())
            status[f"scanner.{mod_name}"] = True
        except (ImportError, ModuleNotFoundError, AttributeError, RuntimeError,
                ValueError, TypeError) as e:
            status[f"scanner.{mod_name}"] = False
            status[f"scanner.{mod_name}.err"] = (  # type: ignore[assignment]
                f"{type(e).__name__}: {e}"
            )

    # --- 调各 agent 的偏好注册 (kb_scan_config.init) ---
    for agent_mod in ["agent_alert", "agent_compliance", "agent_channel"]:
        try:
            module = __import__(
                f"{agent_mod}.kb_scan_config", fromlist=["init"],
            )
            module.init()
            status[f"prefs.{agent_mod}"] = True
        except ModuleNotFoundError:
            # 未配 kb_scan_config.py 是允许的
            status[f"prefs.{agent_mod}"] = False
        except (ImportError, AttributeError, RuntimeError, ValueError,
                TypeError) as e:
            status[f"prefs.{agent_mod}"] = False
            status[f"prefs.{agent_mod}.err"] = (  # type: ignore[assignment]
                f"{type(e).__name__}: {e}"
            )

    return status
