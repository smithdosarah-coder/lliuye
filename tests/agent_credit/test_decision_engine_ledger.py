# -*- coding: utf-8 -*-
"""Agent3 → cross-agent ledger integration tests · BE7 (Phase B-3).

End-to-end: drive `DecisionEngine.run_stream()` and assert the decision
landed in the cross-agent ledger with the right shape (BE2 graph as
evidence_chain, default jurisdiction, default retention class).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_credit.decision_engine import DecisionEngine  # noqa: E402
from shared.decision_ledger import (  # noqa: E402
    DecisionLedger,
    LEDGER_SCHEMA_VERSION,
    RETENTION_STANDARD,
    get_decision,
    set_default_ledger,
)


CORP_PROFILE: dict = {
    "company_name": "众智达科技",
    "industry": "I65-互联网与相关服务",
    "establishment_date": "2018-06",
    "employee_count": 86,
    "financial_anchors": {
        "revenue_latest": 18650.0, "revenue_prev": 16230.0,
        "net_profit_latest": 1235.0, "net_profit_prev": 820.0,
        "total_assets": 16956.5, "total_liabilities": 7206.5,
        "net_assets": 9750.0, "accounts_receivable": 4380.0,
        "inventory": 2150.0, "operating_cash_flow": 791.2,
        "short_term_borrowing": 2200.0, "ebitda": 1985.0,
    },
    "guarantee_info": {"type": "房产抵押+保证人", "collateral_value": 1500.0},
    "request": {"amount": 800.0, "term_months": 24, "purpose": "补充流动资金"},
}


@pytest.fixture
def fresh_ledger(tmp_path, monkeypatch):
    db_path = tmp_path / "credit_ledger.sqlite"
    monkeypatch.setenv("LIUYE_LEDGER_DB_PATH", str(db_path))
    ledger = DecisionLedger(db_path)
    set_default_ledger(ledger)
    yield ledger
    set_default_ledger(None)


def _drive_engine(profile: dict, segment: str = "corporate"):
    """Run the engine and return (stages_seen, ledger_payload, advice)."""
    engine = DecisionEngine()
    stages: list[str] = []
    ledger_payload: dict | None = None
    advice = None
    for stage, payload in engine.run_stream(profile, segment):
        stages.append(stage)
        if stage == "ledger_done" and isinstance(payload, dict):
            ledger_payload = payload
        if stage == "all_done":
            advice = payload.advice
    return stages, ledger_payload, advice


# ---------------------------------------------------------------------------
# 1. Stage sequence
# ---------------------------------------------------------------------------


def test_run_stream_emits_ledger_stages(fresh_ledger):
    stages, _, _ = _drive_engine(CORP_PROFILE)
    # Ledger stages MUST follow graph stages, MUST precede all_done
    assert "graph_done" in stages
    assert "ledger_persisting" in stages
    assert "ledger_done" in stages
    assert stages.index("graph_done") < stages.index("ledger_persisting")
    assert stages.index("ledger_persisting") < stages.index("ledger_done")
    assert stages.index("ledger_done") < stages.index("all_done")


# ---------------------------------------------------------------------------
# 2. Ledger entry shape
# ---------------------------------------------------------------------------


def test_decision_persists_to_ledger(fresh_ledger):
    _, ledger_payload, advice = _drive_engine(CORP_PROFILE)
    assert ledger_payload is not None
    assert ledger_payload["persisted"] is True
    decision_id = ledger_payload["decision_id"]
    assert decision_id

    row = get_decision(decision_id)
    assert row is not None
    assert row["agent_id"] == "credit"
    assert row["endpoint"] == "/api/credit/decision"
    assert row["jurisdiction"] == "HQ"
    assert row["retention_class"] == RETENTION_STANDARD
    assert row["subject_name"] == advice.subject_name


def test_evidence_chain_carries_decision_graph(fresh_ledger):
    """The ledger evidence_chain must equal the BE2 decision_graph
    (so auditors trace decision → graph → feature/rule/peer_gap source)."""
    _, ledger_payload, advice = _drive_engine(CORP_PROFILE)
    row = get_decision(ledger_payload["decision_id"])
    ev = row["evidence_chain"]
    assert isinstance(ev, dict)
    assert ev.get("schema_version") == "1.1.0"  # nullable amount + explicit flag
    # Has at least one decision node (BE2 always emits one)
    types = {n["type"] for n in ev.get("nodes", [])}
    assert "decision" in types


def test_advice_id_matches_ledger_decision_id(fresh_ledger):
    """advice.advice_id is overwritten with ledger decision_id (1:1
    mapping · spec §4.1)."""
    _, ledger_payload, advice = _drive_engine(CORP_PROFILE)
    assert advice.advice_id == ledger_payload["decision_id"]


# ---------------------------------------------------------------------------
# 3. Failure isolation (BE7 hard line — ledger is observation, not block)
# ---------------------------------------------------------------------------


def test_ledger_failure_does_not_break_decision(monkeypatch, tmp_path):
    """Force record_decision to raise; the engine must still emit
    all_done with a complete DecisionPipelineResult."""
    # Inject a broken ledger that can't write
    set_default_ledger(None)
    bad_dir = tmp_path / "broken"
    bad_dir.mkdir()
    monkeypatch.setenv("LIUYE_LEDGER_DB_PATH", str(bad_dir))
    # bad path = directory, sqlite open will fail at write time

    engine = DecisionEngine()
    stages = []
    ledger_payload = None
    final = None
    for stage, payload in engine.run_stream(CORP_PROFILE, "corporate"):
        stages.append(stage)
        if stage == "ledger_done":
            ledger_payload = payload
        if stage == "all_done":
            final = payload

    # Decision flow completed
    assert "all_done" in stages
    assert final is not None
    assert final.advice is not None
    assert final.advice.decision in {"批准", "有条件批准", "拒绝"}

    # Ledger event still emitted (with persisted=False)
    assert ledger_payload is not None
    assert ledger_payload.get("persisted") is False
    set_default_ledger(None)


# ---------------------------------------------------------------------------
# 4. Hash determinism across re-runs (tamper-detection foundation)
# ---------------------------------------------------------------------------


def test_repeated_decision_same_input_same_hash(fresh_ledger):
    """Running the same profile twice → identical input_hash. (output_hash
    can drift if the engine pulls in a non-deterministic LLM, but we don't
    use LLM here; the deterministic 4-step pipeline is the input.)"""
    _, p1, _ = _drive_engine(CORP_PROFILE)
    _, p2, _ = _drive_engine(CORP_PROFILE)
    row1 = get_decision(p1["decision_id"])
    row2 = get_decision(p2["decision_id"])
    assert row1["input_hash"] == row2["input_hash"]
