# -*- coding: utf-8 -*-
"""CompliancePolicyScannerAdapter — 包装 ``agent_compliance.policy_scanner.scan_latest_policies``.

D.5 · BaseScanner 接口实装 · 让 ``shared/kb_scan/Router`` 可路由 Agent5 政策巡检。

Scope: ``policy_scan`` (or ``default``) — 从 gov.cn / pbc / flk_npc / tavily 偏好链
拉最新政策候选清单。底层是 ``shared/sources/Router`` 的 thin wrapper · 把 raw item
列表转成 HitList shape 进 ScanRunResult。
"""
from __future__ import annotations

import logging

from ..base import BaseScanner, ScanRequest, ScanRunResult
from ..models import (
    Evidence,
    HitItem,
    HitList,
    RiskLevel,
    ScanTarget,
)

logger = logging.getLogger(__name__)


class CompliancePolicyScannerAdapter(BaseScanner):
    """包装 scan_latest_policies · 不重写业务."""

    name = "compliance_policy"
    agent_key = "compliance"
    cost = "free"
    supported_scopes = {"policy_scan", "default"}

    def __init__(self, llm_fn=None) -> None:
        self._llm_fn = llm_fn

    def health(self) -> bool:
        try:
            from agent_compliance import policy_scanner  # noqa: F401
        except ImportError:
            return False
        return True

    def scan(self, request: ScanRequest) -> ScanRunResult:
        try:
            from agent_compliance.policy_scanner import scan_latest_policies
        except ImportError as e:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error=f"policy_scanner import failed: {e}",
            )

        try:
            raw = scan_latest_policies(
                query=request.query, limit=request.limit, llm_fn=self._llm_fn,
            )
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
                KeyError) as e:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error=f"{type(e).__name__}: {e}",
            )

        # raw item dict 列表 → HitList shape (供 Router 调用方统一消费)
        hits: list[HitItem] = []
        for idx, item in enumerate(raw):
            raw_item = item.get("raw_item", {}) or {}
            url = item.get("source_url", "") or raw_item.get("url", "")
            src_name = item.get("source_name", "")
            target_id = (
                str(raw_item.get("id", ""))
                or str(raw_item.get("title", ""))[:32]
                or f"policy_{idx}"
            )
            hits.append(
                HitItem(
                    hit_id=f"compliance_policy_{idx:03d}",
                    rank=idx + 1,
                    level=RiskLevel.YELLOW,  # 默认未 parse · 标 yellow 提醒上层 LLM 解析
                    score=1.0 - idx * 0.05,  # 排序稳定 · 早出现 score 高
                    target=ScanTarget(
                        target_id=target_id,
                        target_type="policy_clause",
                        payload={
                            "title": raw_item.get("title", ""),
                            "snippet": raw_item.get("content", "")[:300],
                            "raw_item": raw_item,
                            "source_name": src_name,
                            "source_url": url,
                            "fetched_at": item.get("fetched_at", ""),
                        },
                    ),
                    evidences=[
                        Evidence(
                            source=src_name or "policy_scanner",
                            snippet=raw_item.get("content", "")[:200],
                            url=url,
                        ),
                    ],
                    extras={
                        "policy_doc": item.get("policy_doc"),
                    },
                ),
            )

        hit_list = HitList(
            list_id=f"compliance_policy_{request.query[:16] or 'default'}",
            agent_name="compliance",
            kb_summary="",
            scan_summary=(
                f"政策扫描 · query={request.query or '金融监管'} · "
                f"返 {len(hits)} 条候选 (按上层 LLM lazy parse 进 PolicyDocument)"
            ),
            total_scanned=len(hits),
            hits=hits,
        )
        hit_list.recount()

        return ScanRunResult(
            ok=True,
            scanner_name=self.name,
            hits=hits,
            hit_list=hit_list,
            summary=hit_list.scan_summary,
        )


__all__ = ["CompliancePolicyScannerAdapter"]
