# -*- coding: utf-8 -*-
"""HitRanker: 对 HitItem 排序、分级、组装成 HitList。"""

from __future__ import annotations
import uuid
from datetime import datetime

from .models import HitItem, HitList, RiskLevel


class HitRanker:
    """通用的 hits → HitList 组装器。"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    def build(
        self,
        hits: list[HitItem],
        kb_summary: str = "",
        scan_summary: str = "",
        total_scanned: int = 0,
        level_thresholds: tuple[float, float] = (70.0, 40.0),
    ) -> HitList:
        # 若 hits 未分级，按分数自动分级
        hi, mid = level_thresholds
        for h in hits:
            if h.level not in (RiskLevel.RED, RiskLevel.YELLOW, RiskLevel.GREEN, RiskLevel.INFO):
                h.level = self._level_from_score(h.score, hi, mid)
            elif h.level == RiskLevel.INFO:
                pass  # 保留
        # 按（level 优先级，score 降序）排序
        order = {RiskLevel.RED: 0, RiskLevel.YELLOW: 1, RiskLevel.GREEN: 2, RiskLevel.INFO: 3}
        hits_sorted = sorted(hits, key=lambda h: (order.get(h.level, 9), -h.score))
        for i, h in enumerate(hits_sorted):
            h.rank = i + 1

        hl = HitList(
            list_id=f"{self.agent_name}_{uuid.uuid4().hex[:8]}",
            agent_name=self.agent_name,
            generated_at=datetime.now().isoformat(),
            kb_summary=kb_summary,
            scan_summary=scan_summary,
            total_scanned=total_scanned,
            hits=hits_sorted,
        )
        hl.recount()
        return hl

    @staticmethod
    def _level_from_score(score: float, hi: float, mid: float) -> RiskLevel:
        if score >= hi:
            return RiskLevel.RED
        if score >= mid:
            return RiskLevel.YELLOW
        return RiskLevel.GREEN
