# -*- coding: utf-8 -*-
"""EvidenceDrawer · 6 agent 统一证据展示 component."""
from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Evidence:
    """单条证据 (展示侧 · 比 EvidenceItem 多前端字段)."""

    evidence_id: str           # uuid · 全局 unique
    claim_id: str              # caller 提供 · 关联到具体 claim (e.g. 段落 hash · field name)
    source: str                # 出处 ("gsxt:91440300708461136T" / "tavily:url")
    anchor: str                # 段落定位 (page=3§2 / cell=B7 / api_path=/x.api?p=12)
    snippet: str               # 原文摘录 (供前端 drawer 显示)
    source_tier: int           # 1-4 (per shared.data_tiers · 1=内部权威 · 4=公开web)
    source_url: Optional[str]  # 可点击 URL · None 时不可跳转
    evidence_date: Optional[str]  # ISO YYYY-MM-DD · 事件发生时间
    retrieved_at: str          # ISO YYYY-MM-DD · 抓取时间 · 算 freshness 用
    claim_type: str            # per shared.evidence_freshness.ClaimType · "news"/"financial"/...
    version: str               # caller 提供 · e.g. "v1" / "2026-05-09"
    content_hash: str          # sha256(snippet[:1024]) 前 16 hex · 防篡改
    confidence: float          # 0.0-1.0 · LLM/规则置信
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hash_snippet(snippet: str) -> str:
    """sha256 前 16 hex · 防篡改 + 作 dedup."""
    return hashlib.sha256(snippet[:1024].encode("utf-8")).hexdigest()[:16]


class EvidenceDrawer:
    """6 agent 共享证据展示 component.

    Usage:

        drawer = default_drawer()

        # 1. 各 agent 生成 claim 时同时挂证据
        eid = drawer.attach(
            claim_id="report_section_42",
            source="tavily:https://www.example.com/news/abc",
            anchor="paragraph=2",
            snippet="2025年Q3 营收 12 亿 · 同比增长 18%",
            source_tier=4,
            source_url="https://www.example.com/news/abc",
            evidence_date="2025-09-30",
            claim_type="news",
            version="v1",
            confidence=0.85,
        )

        # 2. 前端 drawer 拉某 claim 的全部证据
        payload = drawer.to_drawer_payload("report_section_42")
        # {
        #   "claim_id": "report_section_42",
        #   "evidence_count": 3,
        #   "tier_distribution": {1: 1, 4: 2},
        #   "min_tier": 1,
        #   "freshness_summary": {...},
        #   "items": [...]
        # }

        # 3. CI guard · 检查无证据 claim
        violations = drawer.verify_claims_have_evidence(["claim_a", "claim_b"])
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Evidence] = {}
        self._by_claim: dict[str, list[str]] = {}  # claim_id → [evidence_id]

    def attach(
        self,
        *,
        claim_id: str,
        source: str,
        anchor: str,
        snippet: str,
        source_tier: int,
        source_url: Optional[str] = None,
        evidence_date: Optional[str] = None,
        retrieved_at: Optional[str] = None,
        claim_type: str = "general",
        version: str = "v1",
        confidence: float = 1.0,
        meta: Optional[dict[str, Any]] = None,
    ) -> str:
        """挂一条证据到 claim · 返 evidence_id (uuid).

        相同 claim_id + content_hash + source 的证据自动 dedup · 返已有 evidence_id.
        """
        if not claim_id or not source or not snippet:
            raise ValueError("claim_id, source, snippet required")
        if not (1 <= source_tier <= 4):
            raise ValueError(f"source_tier must be 1-4 · got {source_tier}")

        content_hash = _hash_snippet(snippet)
        # dedup: 同 claim + 同 source + 同 hash → 不重复挂
        for existing_id in self._by_claim.get(claim_id, []):
            existing = self._by_id[existing_id]
            if existing.source == source and existing.content_hash == content_hash:
                return existing_id

        evidence_id = f"ev_{uuid.uuid4().hex[:16]}"
        retrieved_at = retrieved_at or time.strftime("%Y-%m-%d")
        ev = Evidence(
            evidence_id=evidence_id,
            claim_id=claim_id,
            source=source,
            anchor=anchor,
            snippet=snippet[:2048],  # 限长 · 防 OOM
            source_tier=source_tier,
            source_url=source_url,
            evidence_date=evidence_date,
            retrieved_at=retrieved_at,
            claim_type=claim_type,
            version=version,
            content_hash=content_hash,
            confidence=max(0.0, min(1.0, confidence)),
            meta=dict(meta or {}),
        )
        self._by_id[evidence_id] = ev
        self._by_claim.setdefault(claim_id, []).append(evidence_id)
        return evidence_id

    def list_evidence(self, claim_id: str) -> list[Evidence]:
        """列出某 claim 的全部证据 (按 attach 顺序)."""
        return [self._by_id[eid] for eid in self._by_claim.get(claim_id, [])]

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        return self._by_id.get(evidence_id)

    def to_drawer_payload(self, claim_id: str) -> dict[str, Any]:
        """前端 drawer 消费用 payload · 含统计 + items."""
        items = self.list_evidence(claim_id)
        if not items:
            return {
                "claim_id": claim_id,
                "evidence_count": 0,
                "tier_distribution": {},
                "min_tier": None,
                "items": [],
            }
        tier_dist: dict[int, int] = {}
        for ev in items:
            tier_dist[ev.source_tier] = tier_dist.get(ev.source_tier, 0) + 1
        return {
            "claim_id": claim_id,
            "evidence_count": len(items),
            "tier_distribution": tier_dist,
            "min_tier": min(ev.source_tier for ev in items),  # 最高权威 (tier 1=最高)
            "items": [ev.to_dict() for ev in items],
        }

    def verify_claims_have_evidence(
        self,
        claim_ids: list[str],
        *,
        min_evidence_count: int = 1,
        max_tier_allowed: int = 4,
    ) -> list[str]:
        """CI guard · 验 claims 都有证据 · 返违规 list.

        Args:
            claim_ids: 待检 claim id list
            min_evidence_count: 每 claim 至少多少条证据 (默认 1)
            max_tier_allowed: 最高 tier 允许 (默认 4 · 全 tier · 紧场景可设 3 拒纯 web)

        Returns: 违规说明 list · 空 list = 全合规
        """
        violations: list[str] = []
        for cid in claim_ids:
            items = self.list_evidence(cid)
            if len(items) < min_evidence_count:
                violations.append(
                    f"{cid!r} 仅 {len(items)} 条证据 · 阈值 ≥ {min_evidence_count}"
                )
                continue
            min_tier = min(ev.source_tier for ev in items)
            if min_tier > max_tier_allowed:
                violations.append(
                    f"{cid!r} 最高权威 tier={min_tier} · 阈值 ≤ {max_tier_allowed}"
                )
        return violations

    def stats(self) -> dict[str, Any]:
        return {
            "total_evidence": len(self._by_id),
            "total_claims": len(self._by_claim),
            "tier_distribution": {
                t: sum(1 for ev in self._by_id.values() if ev.source_tier == t)
                for t in (1, 2, 3, 4)
            },
        }


_DEFAULT: EvidenceDrawer | None = None


def default_drawer() -> EvidenceDrawer:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = EvidenceDrawer()
    return _DEFAULT
