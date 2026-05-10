# -*- coding: utf-8 -*-
"""DecisionGraph — Agent3 BE2 (Phase B-3 · 2026-05-01) audit-grade evidence graph.

Wraps the existing 4-step deterministic pipeline (decision_engine.py 1-114)
without touching it. Builds a structured node/edge graph that lets the
审贷员 (credit reviewer) trace every conclusion back to:

  1. feature snapshot   — value + source (file:method)
  2. rule + rule_hit    — id, threshold, severity, version
  3. peer benchmark/gap — same-industry comparison (BE2 core: links the
                          existing CorporateScoringResult.industry_peer_gap
                          dict, which prior to this module was a leaf value
                          with no provenance chain)
  4. score dimension    — weight + weighted contribution + source
  5. decision           — final advice with caused-by anchors

Schema contract: docs/contracts/agent-credit-decision-graph.md v1.0
                 SCHEMA_VERSION constant tracks it.

Pure deterministic. No LLM. No ML. Optional `decision_graph` field on
DecisionAdvice — existing consumers ignore it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .risk_appetite_config import RiskAppetiteConfig

SCHEMA_VERSION = "1.0.0"
ENGINE_NAME = "agent3.decision_engine"
ENGINE_VERSION = "v3.1"
DEFAULT_APPETITE_VERSION = "default-2026-04"

_AGENT_DIR = Path(__file__).parent
_BASELINES_PATH = _AGENT_DIR / "mock_data" / "industry_baselines_v2.json"
_RULES_DIR = _AGENT_DIR / "mock_data"

# 4 corporate peer-gap metrics (per spec §4) — kept in sync with
# scoring_model_corporate._score_financial + scoring_model_corporate.score
# (industry_peer_gap dict). Direction tells the reviewer whether
# above_peer is a positive or negative signal.
_PEER_METRICS_CORPORATE: tuple[dict[str, Any], ...] = (
    {
        "metric": "debt_ratio",
        "feature_path": "financial.debt_ratio",
        "peer_path": "industry.debt_ratio_median",
        "above_is_bad": True,
        "unit": "ratio",
        "label": "资产负债率",
    },
    {
        "metric": "net_margin",
        "feature_path": "financial.net_margin",
        "peer_path": "industry.net_margin_median",
        "above_is_bad": False,
        "unit": "ratio",
        "label": "净利率",
    },
    {
        "metric": "revenue_growth",
        "feature_path": "financial.revenue_growth",
        "peer_path": "industry.revenue_growth_median",
        "above_is_bad": False,
        "unit": "ratio",
        "label": "营收增长率",
    },
    {
        "metric": "ar_turnover_days",
        "feature_path": "financial.ar_turnover_days",
        "peer_path": "industry.ar_turnover_days_median",
        "above_is_bad": True,
        "unit": "days",
        "label": "应收账款周转天数",
        # 与 CorporateScoringResult.industry_peer_gap 历史 key 对齐
        # (scoring_model_corporate.py:222) 便于前端复用同一字典 key
        "summary_key": "ar_turnover_gap",
    },
)

_DIMENSION_SOURCES_CORPORATE: dict[str, str] = {
    "financial": "scoring_model_corporate.py::_score_financial",
    "industry": "scoring_model_corporate.py::_score_industry",
    "operational": "scoring_model_corporate.py::_score_operational",
    "guarantee": "scoring_model_corporate.py::_score_guarantee",
}

_DEFAULT_WEIGHTS_CORPORATE: dict[str, float] = {
    "financial": 0.35,
    "industry": 0.15,
    "operational": 0.25,
    "guarantee": 0.25,
}

_RETAIL_CATEGORY_SOURCES: dict[str, str] = {
    "repayment_capacity": "scoring_model_retail.py::score::repayment_capacity",
    "repayment_willingness": "scoring_model_retail.py::score::repayment_willingness",
    "stability": "scoring_model_retail.py::score::stability",
    "collateral": "scoring_model_retail.py::score::collateral",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = {"id": self.id, "type": self.type}
        out.update(self.payload)
        return out


@dataclass(frozen=True)
class GraphEdge:
    from_id: str
    to_id: str
    type: str

    def to_dict(self) -> dict:
        return {"from": self.from_id, "to": self.to_id, "type": self.type}


@dataclass
class DecisionGraph:
    schema_version: str = SCHEMA_VERSION
    engine: str = ENGINE_NAME
    engine_version: str = ENGINE_VERSION
    appetite: dict = field(default_factory=dict)
    subject_name: str = ""
    segment: str = ""
    built_at: str = ""
    decision_summary: dict = field(default_factory=dict)
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    peer_gap_summary: dict = field(default_factory=dict)
    missing_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "appetite": dict(self.appetite),
            "subject_name": self.subject_name,
            "segment": self.segment,
            "built_at": self.built_at,
            "decision_summary": dict(self.decision_summary),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "peer_gap_summary": dict(self.peer_gap_summary),
            "missing_evidence": list(self.missing_evidence),
        }

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_industry_baselines() -> dict:
    """Load `mock_data/industry_baselines_v2.json` keyed by industry code.

    Returns the `industries` dict (or empty dict on read failure). Mirrors
    feature_extractor._load_baselines so the graph and the scorer agree on
    the same baseline source.
    """
    try:
        raw = json.loads(_BASELINES_PATH.read_text(encoding="utf-8"))
        return raw.get("industries", {}) or {}
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {}


def _appetite_block(
    appetite: RiskAppetiteConfig | None,
    segment: str,
) -> dict[str, Any]:
    if appetite is None:
        return {
            "segment": segment,
            "version": DEFAULT_APPETITE_VERSION,
            "client_id": "",
        }
    # client_id is not stored on RiskAppetiteConfig directly; default to ""
    # unless overrides are present (treat any override as "non-default").
    has_overrides = bool(getattr(appetite, "rule_threshold_overrides", {}))
    return {
        "segment": appetite.segment or segment,
        "version": (
            f"{DEFAULT_APPETITE_VERSION}+overrides"
            if has_overrides
            else DEFAULT_APPETITE_VERSION
        ),
        "client_id": "",
    }


def _rule_version_marker(
    appetite: RiskAppetiteConfig | None,
    rule_id: str,
) -> str:
    """`<engine_version>+<appetite_marker>` per spec §2."""
    overrides = getattr(appetite, "rule_threshold_overrides", {}) or {}
    if rule_id in overrides:
        return f"{ENGINE_VERSION}+override"
    return f"{ENGINE_VERSION}+default"


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _round(value: Any, places: int = 4) -> Any:
    if _is_number(value):
        return round(float(value), places)
    return value


def _interpret_gap(metric: dict[str, Any], gap: float) -> tuple[str, str]:
    """Returns (direction, interpretation). Pure template, no LLM."""
    label = metric["label"]
    unit = metric["unit"]
    above_is_bad = metric["above_is_bad"]

    eq_threshold = 1.0 if unit == "days" else 0.001
    if abs(gap) < eq_threshold:
        return "equal_to_peer", f"{label}与同业中位基本持平"

    if gap > 0:
        direction = "above_peer"
        if unit == "days":
            magnitude = f"{gap:.0f} 天"
        else:
            magnitude = f"{gap * 100:.1f}pp"
        polarity = "高于" + ("（不利）" if above_is_bad else "（利好）")
    else:
        direction = "below_peer"
        if unit == "days":
            magnitude = f"{abs(gap):.0f} 天"
        else:
            magnitude = f"{abs(gap) * 100:.1f}pp"
        polarity = "低于" + ("（利好）" if above_is_bad else "（不利）")
    return direction, f"{label}{polarity}同业中位 {magnitude}"


# ---------------------------------------------------------------------------
# Node builders
# ---------------------------------------------------------------------------


def _build_feature_node(
    key: str,
    value: Any,
    *,
    source: str = "feature_extractor.py::_extract_corporate",
) -> GraphNode:
    return GraphNode(
        id=f"feature::{key}",
        type="feature",
        payload={
            "key": key,
            "value": _round(value),
            "source": source,
            "feature_path": key,
        },
    )


def _build_rule_node(
    rule_id: str,
    rule_name: str,
    threshold: Any,
    operator: str,
    severity: str,
    appetite: RiskAppetiteConfig | None,
    segment: str,
) -> GraphNode:
    return GraphNode(
        id=f"rule::{rule_id}",
        type="rule",
        payload={
            "rule_id": rule_id,
            "rule_name": rule_name,
            "threshold": _round(threshold),
            "operator": operator,
            "severity": severity,
            "version": _rule_version_marker(appetite, rule_id),
            "source": f"red_line_rules_{segment}.json#{rule_id}",
        },
    )


def _build_rule_hit_node(hit: Any) -> GraphNode:
    rid = getattr(hit, "rule_id", "") or ""
    return GraphNode(
        id=f"rule_hit::{rid}",
        type="rule_hit",
        payload={
            "rule_id": rid,
            "actual": _round(getattr(hit, "actual_value", None)),
            "threshold": _round(getattr(hit, "threshold", None)),
            "severity": getattr(hit, "severity", "green"),
            "can_waive": bool(getattr(hit, "can_waive", True)),
            "description": getattr(hit, "description", ""),
        },
    )


def _build_peer_benchmark_node(
    industry_code: str,
    metric: str,
    value: Any,
) -> GraphNode:
    return GraphNode(
        id=f"peer_benchmark::{industry_code}::{metric}",
        type="peer_benchmark",
        payload={
            "industry_code": industry_code,
            "metric": metric,
            "value": _round(value),
            "source": (
                f"industry_baselines_v2.json#{industry_code}#{metric}_median"
            ),
        },
    )


def _build_peer_gap_node(
    metric_def: dict[str, Any],
    feature_value: Any,
    peer_value: Any,
    gap: float,
) -> GraphNode:
    direction, interpretation = _interpret_gap(metric_def, gap)
    return GraphNode(
        id=f"peer_gap::{metric_def['metric']}",
        type="peer_gap",
        payload={
            "metric": metric_def["metric"],
            "label": metric_def["label"],
            "feature_value": _round(feature_value),
            "peer_value": _round(peer_value),
            "gap": _round(gap),
            "unit": metric_def["unit"],
            "direction": direction,
            "interpretation": interpretation,
        },
    )


def _build_score_dimension_node_corporate(
    dimension: str,
    score: int,
    weight: float,
    sub_scores: dict | None,
) -> GraphNode:
    return GraphNode(
        id=f"score::{dimension}",
        type="score_dimension",
        payload={
            "dimension": dimension,
            "score": int(score),
            "weight": _round(weight),
            "weighted": _round(score * weight, 2),
            "source": _DIMENSION_SOURCES_CORPORATE.get(
                dimension, "scoring_model_corporate.py"
            ),
            "sub_scores": dict(sub_scores or {}),
        },
    )


def _build_score_dimension_node_retail(
    category: str,
    score: int,
    weight: float,
) -> GraphNode:
    return GraphNode(
        id=f"score::{category}",
        type="score_dimension",
        payload={
            "dimension": category,
            "score": int(score),
            "weight": _round(weight),
            "weighted": _round(score * weight, 2),
            "source": _RETAIL_CATEGORY_SOURCES.get(
                category, "scoring_model_retail.py"
            ),
            "sub_scores": {},
        },
    )


def _build_decision_node(
    advice: Any,
    rule_hits: list,
) -> GraphNode:
    decision = getattr(advice, "decision", "") or ""
    blocking = [
        getattr(h, "rule_id", "")
        for h in (rule_hits or [])
        if getattr(h, "severity", "") == "red"
    ]
    if blocking:
        anchor = f"硬红线 {', '.join(blocking)} 触发 → {decision}"
    elif decision == "拒绝":
        anchor = "评分等级或确定性约束触发拒绝"
    elif rule_hits:
        anchor = f"软告警 {len(rule_hits)} 条 + 评分定档 → {decision}"
    else:
        anchor = f"评分定档 + 无红线 → {decision}"
    return GraphNode(
        id="decision::final",
        type="decision",
        payload={
            "decision": decision,
            "approved_amount": _round(getattr(advice, "approved_amount", 0), 1),
            "approved_term_months": int(
                getattr(advice, "approved_term_months", 0) or 0
            ),
            "interest_rate": _round(getattr(advice, "interest_rate", 0)),
            "rate_benchmark": getattr(advice, "rate_benchmark", "") or "",
            "risk_grade": getattr(advice, "risk_grade", "") or "",
            "composite_score": int(
                getattr(advice, "composite_score", 0) or 0
            ),
            "rationale_anchor": anchor,
        },
    )


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_decision_graph(
    *,
    features: dict,
    scoring: Any,
    rule_hits: Iterable,
    advice: Any,
    segment: str,
    appetite: RiskAppetiteConfig | None = None,
    baselines: dict | None = None,
) -> DecisionGraph:
    """Build a DecisionGraph from a single Agent3 decision pipeline run.

    Args:
        features: features_snapshot (already _-prefix-filtered as in
                  AdvisorFormatter)
        scoring:  CorporateScoringResult | RetailScoringResult
        rule_hits: iterable of RedLineHit
        advice:   DecisionAdvice (read-only — graph is attached afterward
                  by the caller)
        segment:  "corporate" | "retail"
        appetite: RiskAppetiteConfig (versioning + override marker)
        baselines: dict from load_industry_baselines() (corporate only;
                   pass None to load lazily)

    Pure function. No I/O beyond optional baselines load. No LLM.
    """
    rule_hits_list = list(rule_hits or [])
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen_node_ids: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()
    missing: list[str] = []

    def _add_node(node: GraphNode) -> None:
        if node.id in seen_node_ids:
            return
        seen_node_ids.add(node.id)
        nodes.append(node)

    def _add_edge(from_id: str, to_id: str, edge_type: str) -> None:
        # Both endpoints must exist; silently drop dangling edges so the
        # graph stays valid even when a corner-case feature key is missing.
        if from_id not in seen_node_ids or to_id not in seen_node_ids:
            return
        key = (from_id, to_id, edge_type)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append(GraphEdge(from_id=from_id, to_id=to_id, type=edge_type))

    subject_name = (
        getattr(advice, "subject_name", "")
        or features.get("meta.company_name")
        or features.get("meta.name")
        or ""
    )

    # ---- decision node first (so `caused`/`evidenced_by` edges resolve) ----
    decision_node = _build_decision_node(advice, rule_hits_list)
    _add_node(decision_node)

    # ---- rule + rule_hit + triggered/threshold_of/caused edges ----
    rules_meta = _load_rules_meta(segment)
    feature_source = (
        "feature_extractor.py::_extract_corporate"
        if segment == "corporate"
        else "feature_extractor.py::_extract_retail"
    )
    for hit in rule_hits_list:
        rid = getattr(hit, "rule_id", "") or ""
        if not rid:
            continue
        meta = rules_meta.get(rid, {})
        rule_node = _build_rule_node(
            rule_id=rid,
            rule_name=getattr(hit, "rule_name", "") or meta.get("name", ""),
            threshold=getattr(hit, "threshold", meta.get("default_threshold")),
            operator=meta.get("operator", ">"),
            severity=getattr(hit, "severity", meta.get("severity", "green")),
            appetite=appetite,
            segment=segment,
        )
        hit_node = _build_rule_hit_node(hit)
        _add_node(rule_node)
        _add_node(hit_node)

        feature_expr = meta.get("feature_expr")
        if feature_expr:
            feature_value = features.get(feature_expr)
            feature_node = _build_feature_node(
                feature_expr, feature_value, source=feature_source
            )
            _add_node(feature_node)
            _add_edge(feature_node.id, hit_node.id, "triggered")
        _add_edge(rule_node.id, hit_node.id, "threshold_of")
        _add_edge(hit_node.id, decision_node.id, "caused")

    # ---- score dimensions + derived_from + evidenced_by ----
    if segment == "corporate":
        weights = _DEFAULT_WEIGHTS_CORPORATE
        if appetite is not None and appetite.dimension_weights:
            weights = {**weights, **appetite.dimension_weights}
        # Phase B.2.1 hotfix · sub_scores 改 int dict 后 evidence detail 走 sub_details
        sub_details = getattr(scoring, "sub_details", {}) or {}
        for dim in ("financial", "industry", "operational", "guarantee"):
            score_attr = f"{dim}_score"
            if not hasattr(scoring, score_attr):
                continue
            dim_node = _build_score_dimension_node_corporate(
                dimension=dim,
                score=getattr(scoring, score_attr, 0) or 0,
                weight=weights.get(dim, _DEFAULT_WEIGHTS_CORPORATE[dim]),
                sub_scores=sub_details.get(dim),  # detail dict · for evidence chain
            )
            _add_node(dim_node)
            _add_edge(dim_node.id, decision_node.id, "evidenced_by")
        # derived_from edges: link known financial features into financial dim.
        # Only add edges for nodes that were actually created (rule-hit feature
        # nodes); avoid creating dangling feature nodes just for visualization.
        for fpath in (
            "financial.debt_ratio",
            "financial.net_margin",
            "financial.revenue_growth",
            "financial.ar_turnover_days",
            "financial.current_ratio",
        ):
            fid = f"feature::{fpath}"
            if fid in seen_node_ids:
                _add_edge(fid, "score::financial", "derived_from")
    else:  # retail
        category_scores = getattr(scoring, "category_scores", {}) or {}
        # Use canonical retail weights from PRD §6.6 / appetite when present
        retail_default_weights = {
            "repayment_capacity": 0.30,
            "repayment_willingness": 0.25,
            "stability": 0.25,
            "collateral": 0.20,
        }
        weights = retail_default_weights
        if appetite is not None and appetite.dimension_weights:
            weights = {**retail_default_weights, **appetite.dimension_weights}
        for cat, raw_score in category_scores.items():
            dim_node = _build_score_dimension_node_retail(
                category=cat,
                score=int(raw_score or 0),
                weight=weights.get(cat, 0.0),
            )
            _add_node(dim_node)
            _add_edge(dim_node.id, decision_node.id, "evidenced_by")

    # ---- peer benchmark + peer_gap + compared_to (corporate only) ----
    peer_summary: dict[str, Any] = {}
    if segment == "corporate":
        if baselines is None:
            baselines = load_industry_baselines()
        industry_code = (
            features.get("meta.industry_code")
            or features.get("industry.code")
            or ""
        )
        if not industry_code:
            missing.append("industry.code")
        baseline_row = baselines.get(industry_code, {}) if industry_code else {}
        if not baseline_row and industry_code:
            missing.append(f"industry_baselines#{industry_code}")

        for metric_def in _PEER_METRICS_CORPORATE:
            feature_value = features.get(metric_def["feature_path"])
            peer_value = features.get(metric_def["peer_path"])
            if peer_value is None and baseline_row:
                # Fall back to industry_baselines_v2.json when the feature
                # extractor didn't propagate the median (e.g. mock fixtures).
                peer_value = baseline_row.get(
                    f"{metric_def['metric']}_median"
                )

            if not _is_number(feature_value):
                missing.append(metric_def["feature_path"])
                continue

            # feature node — created lazily so we don't dangle if not used
            feature_node = _build_feature_node(
                metric_def["feature_path"],
                feature_value,
                source=feature_source,
            )
            _add_node(feature_node)

            if not _is_number(peer_value):
                # peer unknown — still emit a peer_gap node with peer_unknown
                # so the reviewer can see the missing benchmark explicitly.
                gap_node = GraphNode(
                    id=f"peer_gap::{metric_def['metric']}",
                    type="peer_gap",
                    payload={
                        "metric": metric_def["metric"],
                        "label": metric_def["label"],
                        "feature_value": _round(feature_value),
                        "peer_value": None,
                        "gap": None,
                        "unit": metric_def["unit"],
                        "direction": "peer_unknown",
                        "interpretation": (
                            f"{metric_def['label']}缺同业基准 "
                            f"(industry_code={industry_code or '未知'})"
                        ),
                    },
                )
                _add_node(gap_node)
                _add_edge(feature_node.id, gap_node.id, "compared_to")
                summary_key = metric_def.get(
                    "summary_key", f"{metric_def['metric']}_gap"
                )
                peer_summary[summary_key] = None
                continue

            gap = float(feature_value) - float(peer_value)
            benchmark_node = _build_peer_benchmark_node(
                industry_code or "UNKNOWN",
                metric_def["metric"],
                peer_value,
            )
            gap_node = _build_peer_gap_node(
                metric_def, feature_value, peer_value, gap
            )
            _add_node(benchmark_node)
            _add_node(gap_node)
            _add_edge(feature_node.id, gap_node.id, "compared_to")
            _add_edge(benchmark_node.id, gap_node.id, "compared_to")
            _add_edge(feature_node.id, benchmark_node.id, "compared_to")
            summary_key = metric_def.get(
                "summary_key", f"{metric_def['metric']}_gap"
            )
            peer_summary[summary_key] = _round(gap)

    # ---- decision_summary mirror for at-a-glance access ----
    decision_summary = {
        "decision": getattr(advice, "decision", "") or "",
        "approved_amount": _round(getattr(advice, "approved_amount", 0), 1),
        "approved_term_months": int(
            getattr(advice, "approved_term_months", 0) or 0
        ),
        "interest_rate": _round(getattr(advice, "interest_rate", 0)),
        "rate_benchmark": getattr(advice, "rate_benchmark", "") or "",
        "risk_grade": getattr(advice, "risk_grade", "") or "",
        "composite_score": int(getattr(advice, "composite_score", 0) or 0),
    }

    return DecisionGraph(
        schema_version=SCHEMA_VERSION,
        engine=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        appetite=_appetite_block(appetite, segment),
        subject_name=subject_name,
        segment=segment,
        built_at=datetime.now().isoformat(timespec="seconds"),
        decision_summary=decision_summary,
        nodes=nodes,
        edges=edges,
        peer_gap_summary=peer_summary,
        missing_evidence=missing,
    )


# ---------------------------------------------------------------------------
# Rule metadata loader (cached)
# ---------------------------------------------------------------------------


_RULES_META_CACHE: dict[str, dict[str, dict]] = {}


def _load_rules_meta(segment: str) -> dict[str, dict]:
    """Load rule definitions keyed by rule_id from
    `mock_data/red_line_rules_{segment}.json`. Cached per segment.
    Returns empty dict when the file is missing or malformed — the graph
    still builds, but rule nodes use whatever metadata the RedLineHit carries.
    """
    if segment in _RULES_META_CACHE:
        return _RULES_META_CACHE[segment]
    path = _RULES_DIR / f"red_line_rules_{segment}.json"
    if not path.exists():
        _RULES_META_CACHE[segment] = {}
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        _RULES_META_CACHE[segment] = {}
        return {}
    rules = raw.get("rules", []) or []
    keyed = {r.get("id", ""): r for r in rules if r.get("id")}
    _RULES_META_CACHE[segment] = keyed
    return keyed


def reset_rules_cache() -> None:
    """Test hook — clears the per-segment rules-meta cache."""
    _RULES_META_CACHE.clear()
