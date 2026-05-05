# -*- coding: utf-8 -*-
"""Agent4 BE9.3 · Agent4→Agent2 §6.4 handoff (Phase B Sprint 2 · 2026-05-04).

per docs/contracts/agent-handoff-schemas.md v1.1 §6.4:
  反向链 · Agent4.pattern_detected → Agent2.rule_proposal

触发:
  Agent4 跨客户聚合分析 detect "≥ 3 客户共同模式" (BE9.1+BE9.2 输出 cluster)

时序:
  异步 · Agent2 排队评估 · 不阻塞 Agent4

传输:
  POST /api/riskctrl/rule_proposal (Agent2 一侧实装 · 本模块仅产 payload)

Payload 关键字段 (per spec §6.4):
  - schema_version: "1.0"
  - intent_type: "pattern_to_rule_proposal"
  - source_agent: "alert"
  - target_agent: "riskctrl"
  - pattern_id: str (cluster.pattern_id · "PTN-..." 格式)
  - pattern_description: str (人话描述 · cluster_label)
  - affected_clients: list[client_id] (≥ 3 per spec)
  - signal_features: list[dict] (含 rule/kind/industry/tier 共同特征)
  - proposal_type: "new_rule" | "rule_update"
  - urgency_score: int 0-100

消费侧约束 (Agent2):
  必读 pattern_features + affected_clients · 风险经理 review · 决定是否生成 DSL
  · 不强制 (Agent2 是后台引擎 · 风险经理拍板)

API:
  build_pattern_proposal(cluster) -> dict
  build_proposals_for_clusters(clusters) -> list[dict]
  is_proposal_valid(proposal) -> bool (基础形态校验 · 给 Agent2 消费侧做防御)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


SCHEMA_VERSION = "1.0"
SOURCE_AGENT = "alert"
TARGET_AGENT = "riskctrl"
INTENT_TYPE = "pattern_to_rule_proposal"
MIN_AFFECTED_CLIENTS = 3  # per agent-handoff-schemas §6.4 触发条件


# ---------------------------------------------------------------------------
# Builder · cluster → handoff payload
# ---------------------------------------------------------------------------


def build_pattern_proposal(
    cluster: dict[str, Any],
    *,
    proposal_type: str | None = None,
) -> dict[str, Any]:
    """从 alert_clusterer.compute_clusters 输出的单 cluster 构 handoff payload.

    Args:
        cluster: alert_clusterer 输出 · 含 pattern_id / affected_clients /
                 common_rules / common_kinds / urgency_score / industries
        proposal_type: 显式覆盖 · 默认按 cluster 内规则启发推断
                       - 若 cluster 全 cross-industry 且 size ≥ 5 → "new_rule"
                       - 否则 "rule_update" (微调现有 rule 阈值)

    Returns:
        dict · per docs/contracts/agent-handoff-schemas.md §6.4 schema
        - schema_version="1.0"
        - intent_type="pattern_to_rule_proposal"
        - source_agent="alert" / target_agent="riskctrl"
        - pattern_id / pattern_description / affected_clients
        - signal_features: list[dict] · 共同特征
        - proposal_type / urgency_score
        - generated_at: ISO 8601

    Raises:
        ValueError: cluster 缺 pattern_id / affected_clients < 3
    """
    pattern_id = cluster.get("pattern_id", "")
    if not pattern_id:
        raise ValueError("cluster 必须含非空 pattern_id")

    affected = list(cluster.get("affected_clients") or [])
    if len(affected) < MIN_AFFECTED_CLIENTS:
        raise ValueError(
            f"§6.4 触发条件未满足 · affected_clients={len(affected)} < "
            f"min={MIN_AFFECTED_CLIENTS}",
        )

    common_rules = list(cluster.get("common_rules") or [])
    common_kinds = list(cluster.get("common_kinds") or [])
    industries = list(cluster.get("industries") or [])
    tier_dist = dict(cluster.get("tier_distribution") or {})
    cluster_label = cluster.get("cluster_label") or ""

    # 启发式 proposal_type · 跨行业大 cluster → 提议加新 rule (跨域风险) ·
    # 否则微调现有 rule 阈值 (rule_update)
    if proposal_type is None:
        if len(industries) >= 2 and len(affected) >= 5:
            proposal_type = "new_rule"
        else:
            proposal_type = "rule_update"

    # signal_features · per cluster 维度抽取
    signal_features: list[dict[str, Any]] = []
    for rule in common_rules:
        signal_features.append({
            "feature_type": "matched_rule",
            "value": rule,
            "source": "agent4.cross_matcher",
            "occurrence": len(affected),
        })
    for kind in common_kinds:
        signal_features.append({
            "feature_type": "signal_kind",
            "value": kind,
            "source": "agent4.signal_quality",
            "occurrence": len(affected),
        })
    for ind in industries:
        signal_features.append({
            "feature_type": "industry",
            "value": ind,
            "source": "agent4.cross_matcher",
            "occurrence": sum(1 for _ in industries),  # filler · BE9.3 spec-only
        })
    if tier_dist:
        signal_features.append({
            "feature_type": "tier_distribution",
            "value": tier_dist,
            "source": "agent4.alert_clusterer",
            "occurrence": sum(tier_dist.values()),
        })

    description = cluster_label or (
        f"{len(affected)} 客户跨 {len(industries) or 1} 行业触发共同 "
        f"{len(common_rules)} 条规则 + {len(common_kinds)} 类信号 · "
        f"建议风控 review 是否新增/调整 rule"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "intent_type": INTENT_TYPE,
        "source_agent": SOURCE_AGENT,
        "target_agent": TARGET_AGENT,
        "pattern_id": pattern_id,
        "pattern_description": description,
        "affected_clients": affected,
        "signal_features": signal_features,
        "proposal_type": proposal_type,
        "urgency_score": int(cluster.get("urgency_score", 0) or 0),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        # 透传 evidence_pointers 给 Agent2 风险经理 drill-down (非 spec 必要 · enrichment)
        "evidence_pointers": list(cluster.get("evidence_pointers") or []),
    }


def build_proposals_for_clusters(
    clusters: list[dict],
) -> list[dict]:
    """对一批 cluster 一次性产 handoff payloads · 跳过不满足 §6.4 触发条件的.

    Returns:
        list[dict] · 满足 ≥ 3 客户 触发条件的 cluster proposal · 已按 urgency desc 排序
    """
    proposals: list[dict] = []
    for c in clusters:
        try:
            proposals.append(build_pattern_proposal(c))
        except ValueError:
            # 不满足触发条件 · 跳过 · 不报错
            continue
    proposals.sort(key=lambda p: p.get("urgency_score", 0), reverse=True)
    return proposals


# ---------------------------------------------------------------------------
# Validator · 给 Agent2 消费侧做防御 (spec compliance check)
# ---------------------------------------------------------------------------


_REQUIRED_KEYS = (
    "schema_version",
    "intent_type",
    "source_agent",
    "target_agent",
    "pattern_id",
    "pattern_description",
    "affected_clients",
    "signal_features",
    "proposal_type",
    "urgency_score",
)


def is_proposal_valid(proposal: dict[str, Any]) -> bool:
    """基础 schema 校验 · 给 Agent2 一侧消费时做防御.

    Returns True 当且仅当:
        - 所有 required keys 在
        - schema_version == "1.0"
        - source_agent == "alert" / target_agent == "riskctrl"
        - intent_type == "pattern_to_rule_proposal"
        - len(affected_clients) >= 3
        - proposal_type ∈ {"new_rule", "rule_update"}
        - urgency_score in [0, 100]
    """
    if not isinstance(proposal, dict):
        return False
    for k in _REQUIRED_KEYS:
        if k not in proposal:
            return False
    if proposal.get("schema_version") != SCHEMA_VERSION:
        return False
    if proposal.get("source_agent") != SOURCE_AGENT:
        return False
    if proposal.get("target_agent") != TARGET_AGENT:
        return False
    if proposal.get("intent_type") != INTENT_TYPE:
        return False
    affected = proposal.get("affected_clients") or []
    if not isinstance(affected, list) or len(affected) < MIN_AFFECTED_CLIENTS:
        return False
    if proposal.get("proposal_type") not in ("new_rule", "rule_update"):
        return False
    score = proposal.get("urgency_score", -1)
    if not isinstance(score, int) or score < 0 or score > 100:
        return False
    return True


__all__ = [
    "INTENT_TYPE",
    "MIN_AFFECTED_CLIENTS",
    "SCHEMA_VERSION",
    "SOURCE_AGENT",
    "TARGET_AGENT",
    "build_pattern_proposal",
    "build_proposals_for_clusters",
    "is_proposal_valid",
]
