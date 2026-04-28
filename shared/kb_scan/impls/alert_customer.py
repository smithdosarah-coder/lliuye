# -*- coding: utf-8 -*-
"""AlertCustomerScannerAdapter — 包装 ``agent_alert.customer_scanner.CustomerScanner``.

D.5 · BaseScanner 接口实装 · 让 ``shared/kb_scan/Router`` 可路由 Agent4
贷中批量扫描。

Scope: ``batch_loan_customers`` (or ``default``) — 全量在贷客户跨规则匹配。

使用:
    from shared.kb_scan.router import ScannerRouter
    from shared.kb_scan.base import ScanRequest

    result = ScannerRouter().scan(
        "agent_alert.batch_loan_scan",
        ScanRequest(scope="batch_loan_customers", kb_id="kb_xxx"),
    )
    # result.hit_list = HitList (RED/YELLOW/GREEN 分级 · 排序好的)
"""
from __future__ import annotations

import logging
from typing import Any

from ..base import BaseScanner, ScanRequest, ScanRunResult
from ..models import HitList

logger = logging.getLogger(__name__)


class AlertCustomerScannerAdapter(BaseScanner):
    """包装 CustomerScanner · 不重写业务."""

    name = "alert_customer"
    agent_key = "alert"
    cost = "free"
    supported_scopes = {"batch_loan_customers", "default"}

    def __init__(
        self,
        kb: Any | None = None,
        search_provider: Any | None = None,
        matcher: Any | None = None,
    ) -> None:
        """允许调用方注入 kb/provider/matcher · 不传时由 health() 探测装载."""
        self._kb = kb
        self._provider = search_provider
        self._matcher = matcher
        self._scanner: Any | None = None

    def _resolve_scanner(self) -> Any | None:
        """lazy 装载 CustomerScanner · 现 KB / SearchProvider 缺失时返 None."""
        if self._scanner is not None:
            return self._scanner
        try:
            from agent_alert.customer_scanner import CustomerScanner
            from agent_alert.knowledge_base import AlertKnowledgeBase
            from shared.kb_scan.search_provider import (
                MockSearchProvider,
            )
        except ImportError as e:
            logger.warning("[alert_customer] import failed: %s", e)
            return None

        kb = self._kb
        if kb is None:
            try:
                kb = AlertKnowledgeBase()
            except (RuntimeError, ValueError, TypeError, OSError) as e:
                logger.warning("[alert_customer] AlertKnowledgeBase init: %s", e)
                return None

        provider = self._provider or MockSearchProvider()
        try:
            self._scanner = CustomerScanner(
                kb=kb, search_provider=provider, matcher=self._matcher,
            )
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError) as e:
            logger.warning("[alert_customer] CustomerScanner init: %s", e)
            return None
        return self._scanner

    def health(self) -> bool:
        return self._resolve_scanner() is not None

    def scan(self, request: ScanRequest) -> ScanRunResult:
        scanner = self._resolve_scanner()
        if scanner is None:
            return ScanRunResult(
                ok=False,
                scanner_name=self.name,
                error="alert CustomerScanner unavailable (KB or SearchProvider missing)",
            )
        try:
            hit_list: HitList = scanner.scan_all()
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
                KeyError) as e:
            return ScanRunResult(
                ok=False,
                scanner_name=self.name,
                error=f"{type(e).__name__}: {e}",
            )

        return ScanRunResult(
            ok=True,
            scanner_name=self.name,
            hits=list(hit_list.hits),
            hit_list=hit_list,
            summary=hit_list.scan_summary,
        )


__all__ = ["AlertCustomerScannerAdapter"]
