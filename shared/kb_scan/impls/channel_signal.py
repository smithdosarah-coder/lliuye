# -*- coding: utf-8 -*-
"""ChannelSignalScannerAdapter — 包装 ``agent_channel`` 候选 enrich.

D.5 · BaseScanner 接口实装 · 让 ``shared/kb_scan/Router`` 可路由 Agent1 候选丰
富 (sse_extras.enrich_candidate · B.5 deliverable)。

Scope: ``candidate_enrich`` (or ``default``) — 接收单候选 dict · 返带
match_dimensions / radar_8axis / product_recommendations / pitch_scripts 的
HitList shape (供 Router 统一调用方消费)。

注: 这是「单候选 enrich」用法 · 不替代 ``run_channel_search_stream`` SSE 主管线。
"""
from __future__ import annotations

import logging
from typing import Any

from ..base import BaseScanner, ScanRequest, ScanRunResult
from ..models import (
    Evidence,
    HitItem,
    HitList,
    RiskLevel,
    ScanTarget,
)

logger = logging.getLogger(__name__)


class ChannelSignalScannerAdapter(BaseScanner):
    """单候选 enrich 适配 · 把 sse_extras 输出归入 HitList shape."""

    name = "channel_signal"
    agent_key = "channel"
    cost = "free"
    supported_scopes = {"candidate_enrich", "default"}

    def health(self) -> bool:
        try:
            from agent_channel import sse_extras  # noqa: F401
        except ImportError:
            return False
        return True

    def scan(self, request: ScanRequest) -> ScanRunResult:
        try:
            from agent_channel.sse_extras import enrich_candidate
        except ImportError as e:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error=f"channel sse_extras import failed: {e}",
            )

        # filters 期望:
        #   {"item": {...candidate dict...},  # 必填
        #    "tags": [{"category": "行业", "value": "..."}, ...],
        #    "llm": <opt LLM caller>}
        item: dict[str, Any] = request.filters.get("item") or {}
        tags = request.filters.get("tags") or []
        llm = request.filters.get("llm")
        if not item:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error="filters.item (candidate dict) required",
            )

        try:
            extras = enrich_candidate(item, query=request.query, tags=tags, llm=llm)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError,
                KeyError) as e:
            return ScanRunResult(
                ok=False, scanner_name=self.name,
                error=f"{type(e).__name__}: {e}",
            )

        # 单候选 → 单 HitItem
        company_name = item.get("company_name") or item.get("name") or "未知公司"
        similarity = float(extras.get("similarity") or 0.0)
        level = (
            RiskLevel.RED if similarity >= 0.7
            else RiskLevel.YELLOW if similarity >= 0.4
            else RiskLevel.GREEN
        )
        hit = HitItem(
            hit_id=f"channel_signal_{company_name[:24]}",
            rank=1,
            level=level,
            score=similarity,
            target=ScanTarget(
                target_id=company_name,
                target_type="company",
                payload={
                    "name": company_name,
                    "industry": extras.get("industry"),
                    "geo": extras.get("geo"),
                    "scale": extras.get("scale"),
                },
            ),
            reasons=[
                m.get("hit_evidence", "")
                for m in (extras.get("match_dimensions") or [])
            ],
            evidences=[
                Evidence(
                    source=src.get("source_name", "")
                    if isinstance(src, dict) else str(src),
                    snippet=str(src.get("hit_evidence", "")) if isinstance(src, dict) else "",
                    url="",
                )
                for src in (extras.get("match_dimensions") or [])[:3]
            ],
            extras={
                "radar_8axis": extras.get("radar_8axis"),
                "match_dimensions": extras.get("match_dimensions"),
                "product_recommendations": extras.get("product_recommendations"),
                "pitch_scripts": extras.get("pitch_scripts"),
            },
        )

        hit_list = HitList(
            list_id=f"channel_signal_{company_name[:16]}",
            agent_name="channel",
            kb_summary="",
            scan_summary=f"候选 enrich · {company_name} · similarity={similarity:.2f}",
            total_scanned=1,
            hits=[hit],
        )
        hit_list.recount()

        return ScanRunResult(
            ok=True,
            scanner_name=self.name,
            hits=[hit],
            hit_list=hit_list,
            summary=hit_list.scan_summary,
        )


__all__ = ["ChannelSignalScannerAdapter"]
