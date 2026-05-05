# -*- coding: utf-8 -*-
"""Agent4 BE9.2 · 跨客户 alert clustering (Phase B Sprint 2 · 2026-05-04).

跨客户聚合同类预警 · 检测"同 industry 多家客户同时触发某 signal" 类风险模式 ·
为 Agent4→Agent2 §6.4 handoff (pattern_detected → rule_proposal) 产 cluster 输入。

设计:
- 100% 确定性 · 不引 ML / embedding (CLAUDE.md §3.1 + onboarding 红线)
- 用 shared.similarity.jaccard_set ≥ 0.7 阈值 (per onboarding spec)
- Union-Find connected components 算法 · O(n²) 比对但 n ≤ 50000 可接受
- cluster 触发条件: ≥ 3 客户共同 pattern (per agent-handoff-schemas §6.4)

API:
- compute_clusters(hits, threshold=0.7, min_size=3) -> list[Cluster]
- compute_signal_features(cluster) -> dict (intersection of rules/kinds)
- compute_urgency_score(cluster) -> int 0-100

输入:
hits: list[dict] · 每条 dict 含:
- client_id: str (entity_id / hit_id)
- matched_rules: list[str] (e.g. ["LAW-001", "FIN-002"])
- signal_kinds: list[str] (BE5 加 · LAW→legal_signal etc)
- tier: "red" | "yellow" | "green" (RiskLevel)
- score: float
- company_name: str
- industry: Optional[str] (从 hit.target.payload.industry)
- 其他 metadata 透传

输出:
list[Cluster] · 每个 cluster:
{
  "pattern_id": "PTN-{hash[:8]}",
  "affected_clients": list[client_id],
  "common_rules": list[str],     # cluster 内所有 client 共同命中的 rule_id
  "common_kinds": list[str],     # cluster 内共同的 signal_kind
  "industries": list[str],       # cluster 内涉及行业 (去重)
  "tier_distribution": dict,     # {red: 2, yellow: 1}
  "urgency_score": int 0-100,
  "cluster_label": str,          # 人话标签
  "evidence_pointers": list[dict] # 每客户 1 个 (client_id, score, top_rule)
}
"""
from __future__ import annotations

import hashlib
from typing import Any

from shared.similarity import jaccard_set


# ---------------------------------------------------------------------------
# 公共常量
# ---------------------------------------------------------------------------


DEFAULT_JACCARD_THRESHOLD: float = 0.7  # per BE9.2 onboarding spec
DEFAULT_MIN_CLUSTER_SIZE: int = 3        # per agent-handoff-schemas §6.4 触发条件


# ---------------------------------------------------------------------------
# Union-Find for cluster discovery
# ---------------------------------------------------------------------------


class _UnionFind:
    """O(α(n)) Union-Find · 单元 cluster discovery 引擎."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path compression
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1

    def groups(self) -> dict[int, list[int]]:
        out: dict[int, list[int]] = {}
        for i in range(len(self.parent)):
            r = self.find(i)
            out.setdefault(r, []).append(i)
        return out


# ---------------------------------------------------------------------------
# Hit normalization · 容忍 dict / pydantic obj 输入
# ---------------------------------------------------------------------------


def _hit_field(hit: Any, key: str, default: Any = None) -> Any:
    if isinstance(hit, dict):
        return hit.get(key, default)
    return getattr(hit, key, default)


def _hit_signature(hit: dict) -> set:
    """提取 hit 的 signal signature (rule_ids ∪ signal_kinds) 用于 jaccard.

    设计:
    - 同时含 rule_ids (细粒度) + signal_kinds (粗粒度) · 多 client 共有一组 rule
      或一组 kind 都触发聚类 · 鲁棒
    - rule_ids 与 kinds 用 prefix 区分 (`r:LAW-001` vs `k:legal_signal`) · 防 namespace 冲突
    """
    rules = _hit_field(hit, "matched_rules", []) or []
    kinds = _hit_field(hit, "signal_kinds", []) or []
    sig: set = set()
    for r in rules:
        if r:
            sig.add(f"r:{r}")
    for k in kinds:
        if k:
            sig.add(f"k:{k}")
    return sig


# ---------------------------------------------------------------------------
# Public · compute_clusters
# ---------------------------------------------------------------------------


def compute_clusters(
    hits: list[dict],
    *,
    threshold: float = DEFAULT_JACCARD_THRESHOLD,
    min_size: int = DEFAULT_MIN_CLUSTER_SIZE,
) -> list[dict]:
    """对 hits 跨客户聚类 · jaccard ≥ threshold 视作同 cluster.

    Args:
        hits: list[dict] · 每条至少含 client_id + matched_rules + signal_kinds
        threshold: jaccard 阈值 (默认 0.7)
        min_size: cluster 最小客户数 (默认 3 · per §6.4)

    Returns:
        list[Cluster] · 已按 urgency_score desc 排序

    复杂度:
        O(n²) jaccard 计算 · n=50000 上限 (per CLAUDE.md §3.7.1) ·
        实际 batch_scan 单次 ~100-1000 客户 · 性能足够
    """
    if not hits:
        return []

    # 计算签名
    signatures = [_hit_signature(h) for h in hits]
    n = len(hits)
    uf = _UnionFind(n)

    # 配对 union (跳过空签名)
    for i in range(n):
        if not signatures[i]:
            continue
        for j in range(i + 1, n):
            if not signatures[j]:
                continue
            sim = jaccard_set(signatures[i], signatures[j])
            if sim >= threshold:
                uf.union(i, j)

    # 组装 clusters
    groups = uf.groups()
    clusters: list[dict] = []
    for member_idxs in groups.values():
        if len(member_idxs) < min_size:
            continue
        members = [hits[i] for i in member_idxs]
        cluster = _build_cluster(members)
        clusters.append(cluster)

    clusters.sort(key=lambda c: c.get("urgency_score", 0), reverse=True)
    return clusters


# ---------------------------------------------------------------------------
# Cluster builder
# ---------------------------------------------------------------------------


_TIER_WEIGHT = {"red": 3, "yellow": 2, "green": 1}


def _build_cluster(members: list[dict]) -> dict:
    """从 cluster members 算 cluster metadata."""
    client_ids = [_hit_field(m, "client_id") or _hit_field(m, "hit_id") or "" for m in members]
    client_ids = [c for c in client_ids if c]

    # 共同 rules / kinds (intersection)
    rule_sets = [set(_hit_field(m, "matched_rules", []) or []) for m in members]
    common_rules: set = rule_sets[0].copy() if rule_sets else set()
    for s in rule_sets[1:]:
        common_rules &= s

    kind_sets = [set(_hit_field(m, "signal_kinds", []) or []) for m in members]
    common_kinds: set = kind_sets[0].copy() if kind_sets else set()
    for s in kind_sets[1:]:
        common_kinds &= s

    # industries (仅去重 · 不要求 intersection)
    industries: set = set()
    for m in members:
        ind = _hit_field(m, "industry")
        if not ind:
            # fallback: 从 nested target.payload.industry 找
            target = _hit_field(m, "target") or {}
            payload = target.get("payload") if isinstance(target, dict) else getattr(target, "payload", {})
            ind = (payload or {}).get("industry") if isinstance(payload, dict) else None
        if ind:
            industries.add(str(ind))

    # tier distribution
    tier_dist: dict[str, int] = {}
    for m in members:
        tier = (_hit_field(m, "tier") or _hit_field(m, "level") or "").lower()
        if hasattr(tier, "value"):
            tier = str(tier.value).lower()
        else:
            tier = str(tier).lower()
        tier_dist[tier] = tier_dist.get(tier, 0) + 1

    urgency = compute_urgency_score(
        size=len(members),
        tier_dist=tier_dist,
        common_rules_count=len(common_rules),
    )

    # pattern_id = stable hash of sorted (common_rules + common_kinds)
    sig_key = "|".join(sorted(common_rules) + sorted(common_kinds))
    pattern_hash = hashlib.sha256(sig_key.encode("utf-8")).hexdigest()[:8] if sig_key else "empty"
    pattern_id = f"PTN-{pattern_hash}"

    label = _build_cluster_label(common_rules, common_kinds, len(members))

    evidence_pointers = []
    for m in members:
        cid = _hit_field(m, "client_id") or _hit_field(m, "hit_id") or ""
        rules = _hit_field(m, "matched_rules", []) or []
        evidence_pointers.append({
            "client_id": cid,
            "company_name": _hit_field(m, "company_name", "") or "",
            "score": float(_hit_field(m, "score", 0.0) or 0.0),
            "top_rule": rules[0] if rules else "",
            "tier": (_hit_field(m, "tier") or _hit_field(m, "level") or "").lower(),
            "scenario_key": _hit_field(m, "scenario_key", "") or "",
        })

    return {
        "pattern_id": pattern_id,
        "affected_clients": client_ids,
        "common_rules": sorted(common_rules),
        "common_kinds": sorted(common_kinds),
        "industries": sorted(industries),
        "tier_distribution": tier_dist,
        "urgency_score": urgency,
        "cluster_label": label,
        "size": len(members),
        "evidence_pointers": evidence_pointers,
    }


def compute_urgency_score(
    *,
    size: int,
    tier_dist: dict[str, int],
    common_rules_count: int,
) -> int:
    """0-100 urgency · cluster 大小 + tier 严重度 + 共同 rule 数加权.

    设计:
    - size 越大 cluster 越紧迫 (∼ 30 分权重)
    - red 客户多 → 紧迫 (∼ 50 分权重)
    - 共同 rule 数 → 模式越聚焦越紧迫 (∼ 20 分权重)
    - 100% 确定性 · 不调 LLM
    """
    # size: 3 → 0 / 5 → 10 / 10 → 20 / 30+ → 30
    size_score = min(30, max(0, (size - 3) * 3))

    total_clients = sum(tier_dist.values()) or 1
    red_ratio = tier_dist.get("red", 0) / total_clients
    yellow_ratio = tier_dist.get("yellow", 0) / total_clients
    tier_score = int(50 * red_ratio + 25 * yellow_ratio)

    # rule count: 0 → 0 / 1 → 5 / 3 → 15 / 5+ → 20
    rule_score = min(20, common_rules_count * 5)

    return min(100, size_score + tier_score + rule_score)


def _build_cluster_label(
    common_rules: set,
    common_kinds: set,
    size: int,
) -> str:
    """生成人话 cluster label · evidence-first 不编 (per CLAUDE.md §3.3).

    例: "5 客户共触发 legal_signal+financial_signal · LAW-002+FIN-002"
    """
    kinds_part = "+".join(sorted(common_kinds)) if common_kinds else "无共同 kind"
    rules_part = "+".join(sorted(common_rules)[:3]) if common_rules else "无共同 rule"
    if common_rules:
        return f"{size} 客户共触发 {kinds_part} · {rules_part}"
    return f"{size} 客户共触发 {kinds_part}"


__all__ = [
    "DEFAULT_JACCARD_THRESHOLD",
    "DEFAULT_MIN_CLUSTER_SIZE",
    "compute_clusters",
    "compute_urgency_score",
]
