# -*- coding: utf-8 -*-
"""Agent3 BE2 (Phase B-3 · 2026-05-01) — decision graph unit tests.

Covers the audit-grade evidence graph builder
(`agent_credit.decision_graph`) plus its wiring via
`DecisionEngine.run_stream()` and the demo fixture.

Hard guarantees:
1. Schema invariants (version pin, required envelope keys)
2. peer_gap nodes link feature ↔ peer_benchmark ↔ peer_gap (BE2 core)
3. rule_hit edges (triggered / threshold_of / caused) wire to decision
4. Threshold + version recorded on every rule node
5. Snapshot stability — graph builds when a node lacks data
6. Demo fixture loads + matches schema exactly
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_credit.decision_engine import DecisionEngine  # noqa: E402
from agent_credit.decision_graph import (  # noqa: E402
    SCHEMA_VERSION,
    DecisionGraph,
    GraphEdge,
    GraphNode,
    build_decision_graph,
    load_industry_baselines,
)
from agent_credit.risk_appetite_config import RiskAppetiteConfig  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


CORP_SAMPLE_PROFILE: dict = {
    "company_name": "众智达科技",
    "industry": "I65-互联网与相关服务",
    "establishment_date": "2018-06",
    "employee_count": 86,
    "financial_anchors": {
        "revenue_latest": 18650.0,
        "revenue_prev": 16230.0,
        "net_profit_latest": 1235.0,
        "net_profit_prev": 820.0,
        "total_assets": 16956.5,
        "total_liabilities": 7206.5,
        "net_assets": 9750.0,
        "accounts_receivable": 4380.0,
        "inventory": 2150.0,
        "operating_cash_flow": 791.2,
        "short_term_borrowing": 2200.0,
        "ebitda": 1985.0,
    },
    "guarantee_info": {"type": "房产抵押+保证人", "collateral_value": 1500.0},
    "request": {"amount": 800.0, "term_months": 24, "purpose": "补充流动资金"},
}


@pytest.fixture(scope="module")
def corp_engine_result():
    """Run the real DecisionEngine end-to-end so we exercise wiring,
    not just the builder in isolation."""
    return DecisionEngine().run(CORP_SAMPLE_PROFILE, "corporate")


@pytest.fixture
def corp_graph(corp_engine_result) -> dict:
    return corp_engine_result.advice.decision_graph


# ---------------------------------------------------------------------------
# 1. Schema invariants
# ---------------------------------------------------------------------------


def _assert_amount_shape(graph: dict, label: str) -> None:
    decision_node = next(
        node for node in graph["nodes"] if node["id"] == "decision::final"
    )
    for mirror_name, mirror in (
        ("decision node", decision_node),
        ("decision_summary", graph["decision_summary"]),
    ):
        assert "amount_provided" in mirror, f"{label}: {mirror_name} missing flag"
        assert isinstance(mirror["amount_provided"], bool)
        assert "approved_amount" in mirror, f"{label}: {mirror_name} missing amount"
        if mirror["amount_provided"]:
            assert isinstance(mirror["approved_amount"], (int, float))
            assert not isinstance(mirror["approved_amount"], bool)
        else:
            assert mirror["approved_amount"] is None


def test_generated_graph_amount_shape(corp_graph):
    _assert_amount_shape(corp_graph, "generated corporate graph")


def test_schema_version_pinned():
    """Pin the current compatible schema contract version.
    so any unintentional bump fails CI loudly."""
    assert SCHEMA_VERSION == "1.1.0"


def test_envelope_keys_present(corp_graph):
    required = {
        "schema_version", "engine", "engine_version", "appetite",
        "subject_name", "segment", "built_at", "decision_summary",
        "nodes", "edges", "peer_gap_summary", "missing_evidence",
    }
    missing = required - set(corp_graph.keys())
    assert not missing, f"missing top-level keys: {missing}"


def test_appetite_block_shape(corp_graph):
    appetite = corp_graph["appetite"]
    assert appetite["segment"] == "corporate"
    assert "version" in appetite
    assert "client_id" in appetite


def test_engine_metadata(corp_graph):
    assert corp_graph["engine"] == "agent3.decision_engine"
    assert corp_graph["engine_version"].startswith("v")


def test_node_type_coverage(corp_graph):
    """All 7 node types per spec §2 must be exercised in the corporate
    happy-path so reviewers can rely on each kind being present."""
    expected = {
        "feature", "rule", "rule_hit", "peer_benchmark",
        "peer_gap", "score_dimension", "decision",
    }
    got = {n["type"] for n in corp_graph["nodes"]}
    assert expected.issubset(got), (
        f"missing node types: {expected - got}"
    )


def test_edge_type_coverage(corp_graph):
    """All 6 edge types per spec §3."""
    expected = {
        "triggered", "threshold_of", "compared_to",
        "derived_from", "caused", "evidenced_by",
    }
    got = {e["type"] for e in corp_graph["edges"]}
    assert expected.issubset(got), (
        f"missing edge types: {expected - got}"
    )


# ---------------------------------------------------------------------------
# 2. peer_gap evidence linkage (BE2 core)
# ---------------------------------------------------------------------------


def test_peer_gap_summary_keys_match_legacy(corp_graph):
    """peer_gap_summary must use the legacy
    CorporateScoringResult.industry_peer_gap key naming so frontends
    pivot without rename. See spec §1 + scoring_model_corporate.py:215-223.
    """
    expected = {
        "debt_ratio_gap", "net_margin_gap",
        "revenue_growth_gap", "ar_turnover_gap",
    }
    got = set(corp_graph["peer_gap_summary"].keys())
    assert expected == got, f"peer_gap_summary keys mismatch: {got}"


def test_peer_gap_node_has_full_provenance(corp_graph):
    """Each peer_gap node must reference a feature_value, peer_value,
    interpretation string, and direction — the BE2 fix for the bare
    industry_peer_gap dict that previously had no provenance."""
    gap_nodes = [n for n in corp_graph["nodes"] if n["type"] == "peer_gap"]
    assert gap_nodes, "no peer_gap nodes built"
    for node in gap_nodes:
        for k in ("metric", "label", "feature_value", "peer_value",
                  "gap", "unit", "direction", "interpretation"):
            assert k in node, f"peer_gap node missing {k}: {node}"
        assert node["direction"] in {
            "above_peer", "below_peer", "equal_to_peer", "peer_unknown",
        }


def test_peer_gap_links_feature_and_benchmark(corp_graph):
    """For every peer_gap node there must be an inbound `compared_to`
    edge from the matching feature node and from the matching
    peer_benchmark node — that's the evidence triangle BE2 unlocks."""
    gap_node_ids = {
        n["id"] for n in corp_graph["nodes"] if n["type"] == "peer_gap"
    }
    feature_to_gap = {
        e["to"] for e in corp_graph["edges"]
        if e["type"] == "compared_to"
        and e["from"].startswith("feature::")
        and e["to"].startswith("peer_gap::")
    }
    benchmark_to_gap = {
        e["to"] for e in corp_graph["edges"]
        if e["type"] == "compared_to"
        and e["from"].startswith("peer_benchmark::")
        and e["to"].startswith("peer_gap::")
    }
    for gid in gap_node_ids:
        # peer_unknown gaps may skip benchmark edge but must keep feature edge
        node = next(n for n in corp_graph["nodes"] if n["id"] == gid)
        assert gid in feature_to_gap, (
            f"peer_gap {gid} missing feature compared_to edge"
        )
        if node["direction"] != "peer_unknown":
            assert gid in benchmark_to_gap, (
                f"peer_gap {gid} missing benchmark compared_to edge"
            )


# ---------------------------------------------------------------------------
# 3. rule_hit linkage
# ---------------------------------------------------------------------------


def test_every_rule_hit_caused_decision(corp_graph):
    """rule_hit → decision::final via `caused` edge — without this the
    审贷员 cannot trace back which red line drove the rejection."""
    hit_node_ids = {
        n["id"] for n in corp_graph["nodes"] if n["type"] == "rule_hit"
    }
    caused_edges = {
        e["from"] for e in corp_graph["edges"]
        if e["type"] == "caused" and e["to"] == "decision::final"
    }
    if hit_node_ids:
        assert hit_node_ids.issubset(caused_edges), (
            f"rule_hits without `caused` edge: "
            f"{hit_node_ids - caused_edges}"
        )


def test_every_rule_hit_has_threshold_of_edge(corp_graph):
    hit_node_ids = {
        n["id"] for n in corp_graph["nodes"] if n["type"] == "rule_hit"
    }
    threshold_edges = {
        e["to"] for e in corp_graph["edges"] if e["type"] == "threshold_of"
    }
    if hit_node_ids:
        assert hit_node_ids.issubset(threshold_edges)


def test_red_severity_anchor_in_rationale(corp_graph):
    """When a red-severity rule hit exists, the decision node's
    `rationale_anchor` must call it out by id."""
    decision_node = next(
        n for n in corp_graph["nodes"] if n["type"] == "decision"
    )
    red_hits = [
        n for n in corp_graph["nodes"]
        if n["type"] == "rule_hit" and n["severity"] == "red"
    ]
    if red_hits:
        anchor = decision_node["rationale_anchor"]
        for h in red_hits:
            assert h["rule_id"] in anchor, (
                f"red hit {h['rule_id']} missing from rationale_anchor: "
                f"{anchor}"
            )


# ---------------------------------------------------------------------------
# 4. Threshold + version recorded on rule nodes
# ---------------------------------------------------------------------------


def test_rule_node_records_version_and_source(corp_graph):
    rule_nodes = [n for n in corp_graph["nodes"] if n["type"] == "rule"]
    assert rule_nodes, "no rule nodes built"
    for node in rule_nodes:
        assert node["version"].startswith("v3.1"), (
            f"rule version not engine-versioned: {node}"
        )
        assert node["source"].startswith("red_line_rules_corporate.json#")
        assert "threshold" in node
        assert node["operator"] in {">", ">=", "<", "<=", "==", "!="}


def test_appetite_override_marker():
    """Custom appetite overrides bump the version marker so reviewers see
    they're looking at a non-default config."""
    appetite = RiskAppetiteConfig(
        segment="corporate",
        rule_threshold_overrides={"corp_rl_003": 0.6},
    )
    graph = build_decision_graph(
        features={
            "meta.industry_code": "I65",
            "industry.code": "I65",
            "industry.debt_ratio_median": 0.45,
            "industry.net_margin_median": 0.09,
            "industry.revenue_growth_median": 0.15,
            "industry.ar_turnover_days_median": 95,
            "financial.debt_ratio": 0.78,
            "financial.net_margin": 0.04,
            "financial.revenue_growth": -0.05,
            "financial.ar_turnover_days": 110,
        },
        scoring=_FakeCorpScoring(),
        rule_hits=[_FakeHit("corp_rl_003", "资产负债率过高",
                            actual_value=0.78, threshold=0.6,
                            severity="red")],
        advice=_FakeAdvice(decision="拒绝", risk_grade="D", composite_score=42),
        segment="corporate",
        appetite=appetite,
    )
    rule_node = next(
        n for n in graph.nodes if n.id == "rule::corp_rl_003"
    )
    assert rule_node.payload["version"] == "v3.1+override"
    assert graph.appetite["version"].endswith("+overrides")


# ---------------------------------------------------------------------------
# 5. Snapshot stability — degraded inputs must not break the build
# ---------------------------------------------------------------------------


def test_missing_industry_code_marks_evidence(monkeypatch):
    """If industry.code is absent we should still build a graph; the
    missing baseline is reported via missing_evidence so the reviewer
    sees it explicitly rather than getting a half-rendered chart."""
    graph = build_decision_graph(
        features={
            "financial.debt_ratio": 0.78,
            "financial.net_margin": 0.04,
            "financial.revenue_growth": -0.05,
            "financial.ar_turnover_days": 110,
        },
        scoring=_FakeCorpScoring(),
        rule_hits=[],
        advice=_FakeAdvice(),
        segment="corporate",
        baselines={},
    )
    assert "industry.code" in graph.missing_evidence
    # Nodes still build for peer_gap with peer_unknown direction
    gap_nodes = [n for n in graph.nodes if n.type == "peer_gap"]
    assert gap_nodes
    assert all(
        n.payload["direction"] == "peer_unknown" for n in gap_nodes
    )


def test_no_rule_hits_still_builds_decision_node():
    graph = build_decision_graph(
        features={"meta.industry_code": "I65"},
        scoring=_FakeCorpScoring(),
        rule_hits=[],
        advice=_FakeAdvice(decision="批准", risk_grade="A",
                           composite_score=88),
        segment="corporate",
    )
    decision_node = next(
        n for n in graph.nodes if n.id == "decision::final"
    )
    assert decision_node.payload["decision"] == "批准"
    # `caused` edges absent when there are no rule_hits
    assert not any(e.type == "caused" for e in graph.edges)


def test_generated_graph_missing_amount_is_explicit_null():
    graph = build_decision_graph(
        features={"meta.industry_code": "I65"},
        scoring=_FakeCorpScoring(),
        rule_hits=[],
        advice=_FakeAdvice(amount_provided=False),
        segment="corporate",
    ).to_dict()
    _assert_amount_shape(graph, "generated missing-amount graph")


def test_dedup_edges_idempotent():
    """Re-emitting the same compared_to edge must not duplicate."""
    graph = build_decision_graph(
        features={
            "meta.industry_code": "I65",
            "industry.debt_ratio_median": 0.45,
            "industry.net_margin_median": 0.09,
            "industry.revenue_growth_median": 0.15,
            "industry.ar_turnover_days_median": 95,
            "financial.debt_ratio": 0.78,
            "financial.net_margin": 0.04,
            "financial.revenue_growth": -0.05,
            "financial.ar_turnover_days": 110,
        },
        scoring=_FakeCorpScoring(),
        rule_hits=[],
        advice=_FakeAdvice(),
        segment="corporate",
    )
    seen = set()
    for e in graph.edges:
        key = (e.from_id, e.to_id, e.type)
        assert key not in seen, f"duplicate edge: {key}"
        seen.add(key)


# ---------------------------------------------------------------------------
# 6. Demo fixture — must match schema exactly so customer demo is reliable
# ---------------------------------------------------------------------------


def test_demo_fixture_loads_and_matches_schema():
    fixture = (
        PROJECT_ROOT / "data" / "mock" / "workspace"
        / "credit" / "scenarios" / "corp-dingsheng-001.json"
    )
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert "decision_graph" in data, (
        "Stage 5a demo fixture must carry decision_graph (per spec §6)"
    )
    g = data["decision_graph"]
    assert g["schema_version"] == SCHEMA_VERSION
    _assert_amount_shape(g, "corp-dingsheng-001")
    decision_node = next(n for n in g["nodes"] if n["id"] == "decision::final")
    assert g["decision_summary"]["amount_provided"] is True
    assert g["decision_summary"]["approved_amount"] == 0
    assert decision_node["amount_provided"] is True
    assert decision_node["approved_amount"] == 0

    node_types = {n["type"] for n in g["nodes"]}
    assert {"feature", "rule", "rule_hit", "peer_benchmark",
            "peer_gap", "score_dimension", "decision"} <= node_types

    edge_types = {e["type"] for e in g["edges"]}
    assert {"triggered", "threshold_of", "compared_to",
            "derived_from", "caused", "evidenced_by"} <= edge_types

    # Every edge endpoint must resolve to an actual node id
    node_ids = {n["id"] for n in g["nodes"]}
    for edge in g["edges"]:
        assert edge["from"] in node_ids, (
            f"dangling edge.from: {edge}"
        )
        assert edge["to"] in node_ids, (
            f"dangling edge.to: {edge}"
        )

    # peer_gap_summary key naming aligned with legacy scorer dict
    assert set(g["peer_gap_summary"].keys()) == {
        "debt_ratio_gap", "net_margin_gap",
        "revenue_growth_gap", "ar_turnover_gap",
    }


# ---------------------------------------------------------------------------
# 6.1 All 6 demo scenarios carry schema-valid graphs (parameterized)
# ---------------------------------------------------------------------------


_SCENARIO_DIR = (
    PROJECT_ROOT / "data" / "mock" / "workspace" / "credit" / "scenarios"
)
_ALL_SCENARIOS = [
    "corp-dingsheng-001",
    "corp-ruiheng-002",
    "corp-zhongrui-003",
    "retail-zhangsan-001",
    "retail-lisi-002",
    "retail-wangwu-003",
]


@pytest.mark.parametrize("scenario_id", _ALL_SCENARIOS)
def test_every_scenario_has_valid_graph(scenario_id):
    """Each Phase B-3 demo scenario must carry a decision_graph that:
    - declares the pinned schema_version
    - contains a decision::final node
    - has score_dimension nodes evidencing the decision
    - has no dangling edges (every from/to resolves)
    Corporate scenarios additionally must carry the 4 peer_gap_summary
    keys; retail scenarios must explicitly mark
    `retail_peer_baselines_unavailable_in_v1.0_schema` in
    missing_evidence (peer_gap is corporate-only in v1.0 per spec §4)."""
    fixture = _SCENARIO_DIR / f"{scenario_id}.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert "decision_graph" in data, (
        f"{scenario_id}: missing decision_graph block"
    )
    g = data["decision_graph"]

    # Schema invariants
    assert g["schema_version"] == SCHEMA_VERSION, (
        f"{scenario_id}: schema_version mismatch"
    )
    assert g["segment"] in {"corporate", "retail"}
    assert g["engine"] == "agent3.decision_engine"
    _assert_amount_shape(g, scenario_id)

    # Decision node exists
    decision_nodes = [n for n in g["nodes"] if n["type"] == "decision"]
    assert decision_nodes and decision_nodes[0]["id"] == "decision::final"

    # At least one score_dimension evidences the decision
    score_dims = {n["id"] for n in g["nodes"] if n["type"] == "score_dimension"}
    evidenced = {
        e["from"] for e in g["edges"]
        if e["type"] == "evidenced_by" and e["to"] == "decision::final"
    }
    assert score_dims, f"{scenario_id}: no score_dimension nodes"
    assert score_dims & evidenced, (
        f"{scenario_id}: no score_dimension evidences the decision"
    )

    # No dangling edges
    node_ids = {n["id"] for n in g["nodes"]}
    for edge in g["edges"]:
        assert edge["from"] in node_ids, (
            f"{scenario_id}: dangling edge.from: {edge}"
        )
        assert edge["to"] in node_ids, (
            f"{scenario_id}: dangling edge.to: {edge}"
        )

    # peer_gap policy by segment
    if g["segment"] == "corporate":
        assert set(g["peer_gap_summary"].keys()) == {
            "debt_ratio_gap", "net_margin_gap",
            "revenue_growth_gap", "ar_turnover_gap",
        }, f"{scenario_id}: corporate scenario must carry 4 peer_gap keys"
    else:  # retail
        assert g["peer_gap_summary"] == {}, (
            f"{scenario_id}: retail scenarios must keep peer_gap_summary "
            f"empty in v1.0 schema (peer baselines are corporate-only)"
        )
        assert any(
            "retail_peer_baselines" in m for m in g["missing_evidence"]
        ), (
            f"{scenario_id}: retail scenarios must annotate the missing "
            f"peer baseline in missing_evidence"
        )

    # Rule hits, when present, must each cause the decision
    hit_ids = {n["id"] for n in g["nodes"] if n["type"] == "rule_hit"}
    if hit_ids:
        caused = {
            e["from"] for e in g["edges"]
            if e["type"] == "caused" and e["to"] == "decision::final"
        }
        assert hit_ids <= caused, (
            f"{scenario_id}: rule_hits without caused edge: "
            f"{hit_ids - caused}"
        )


def test_industry_baseline_loader_returns_known_codes():
    baselines = load_industry_baselines()
    # I65 is a stable seed in industry_baselines_v2.json
    assert "I65" in baselines
    row = baselines["I65"]
    assert "debt_ratio_median" in row


# ---------------------------------------------------------------------------
# 7. DecisionAdvice is preserved (regression — must not break existing
#    consumers that ignore unknown fields)
# ---------------------------------------------------------------------------


def test_decision_advice_existing_fields_intact(corp_engine_result):
    advice = corp_engine_result.advice
    assert advice.decision in {"批准", "有条件批准", "拒绝"}
    assert advice.composite_score >= 0
    assert isinstance(advice.features_snapshot, dict)
    assert isinstance(advice.scoring_snapshot, dict)
    # And the new field is populated
    assert isinstance(advice.decision_graph, dict)
    assert advice.decision_graph.get("schema_version") == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Helpers — minimal fakes so the builder can be exercised in isolation
# ---------------------------------------------------------------------------


class _FakeCorpScoring:
    financial_score = 28
    industry_score = 45
    operational_score = 41
    guarantee_score = 35
    composite_score = 38
    risk_grade = "D"
    sub_scores: dict = {}
    industry_peer_gap: dict = {}
    amount_methods: dict = {}


class _FakeHit:
    def __init__(self, rule_id, rule_name, actual_value, threshold, severity,
                 can_waive=False, description=""):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.actual_value = actual_value
        self.threshold = threshold
        self.severity = severity
        self.can_waive = can_waive
        self.description = description
        self.waiver_conditions: list = []


class _FakeAdvice:
    def __init__(self, decision="拒绝", approved_amount=0,
                 approved_term_months=0, interest_rate=0,
                 rate_benchmark="—", risk_grade="D", composite_score=38,
                 subject_name="测试公司", amount_provided=True):
        self.decision = decision
        self.amount_provided = amount_provided
        self.approved_amount = approved_amount
        self.approved_term_months = approved_term_months
        self.interest_rate = interest_rate
        self.rate_benchmark = rate_benchmark
        self.risk_grade = risk_grade
        self.composite_score = composite_score
        self.subject_name = subject_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
