# -*- coding: utf-8 -*-
"""liuye_service.tests.test_audit_ledger — Q3 façade upgrade integration tests.

Per W2-backend brief §4.4 + ``liuye_service/CLAUDE.md`` §5 + root §3.7.5.

Five integration test surfaces (NOT shadowing the W1 ``test_audit.py``
which covers the silent-fail / outbox enqueue happy path):

1. **parent_turn_id end-to-end**: ``record_liuye_decision`` with
   parent_turn_id forwards to ``shared.decision_ledger.record`` and
   the ``decisions.parent_turn_id`` sqlite column is populated. Re-reads
   via ``get_decision`` echo it back.

2. **Agent2 cross-mode case**: Cowork DSL turn writes ledger A with
   parent_turn_id=None · Managed backtest turn writes ledger B with
   parent_turn_id=A.turn_id · ``get_decision(B)['parent_turn_id'] ==
   A.turn_id``. This is the canonical use case for the v1.1 schema bump
   (PM 2026-05-11 ratify · liuye-final-spec-v3 必修 perfect-check-6).

3. **LedgerReviewEvent append-only**: ``record_review_event`` with the
   same ``(decision_id, idempotency_key)`` twice → 1 row + same event_id
   returned both times (idempotent semantic per v3 §2.5 + 必修 #69).

4. **Subject_id PII hash invariant**: passing plain PII subject_id
   produces a hashed value in sqlite (16-hex prefix per Q3 ratify).
   Plain PII NEVER lands on disk.

5. **schema_version pin**: ``LEDGER_SCHEMA_VERSION`` is 1.1.0 (Q3
   ratify · the bump that introduced ``parent_turn_id``).

These tests use a per-test tmp_path sqlite so they NEVER touch the
production ``data/ledger/decisions.sqlite``.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from liuye_service.audit import record_liuye_decision
from liuye_service.ledger_review import (
    list_review_events,
    record_review_event,
)
from shared.decision_ledger.schema import LEDGER_SCHEMA_VERSION
from shared.decision_ledger.store import DecisionLedger, set_default_ledger


# ---------------------------------------------------------------------------
# Fixtures · isolated sqlite per test
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_ledger(tmp_path: Path):
    """Provide a DecisionLedger backed by a tmp sqlite · clean per test."""
    db = tmp_path / "isolated_decisions.sqlite"
    ledger = DecisionLedger(db_path=db)
    # Inject as the default so liuye_service.audit + ledger_review pick it up.
    set_default_ledger(ledger)
    yield ledger
    # Reset · prevents test bleed into the next test's default_ledger().
    set_default_ledger(None)


# ---------------------------------------------------------------------------
# 1. parent_turn_id end-to-end · audit.py → store → sqlite column
# ---------------------------------------------------------------------------


def test_parent_turn_id_persists_to_sqlite(isolated_ledger: DecisionLedger) -> None:
    """``record_liuye_decision(parent_turn_id=X)`` writes X into sqlite."""
    decision_id = record_liuye_decision(
        agent_id="credit",
        endpoint="/api/liuye/sessions",
        input_payload={"applied_product": "CORP_CREDIT"},
        output_payload={"verdict": "PASS"},
        evidence_chain={"trace_id": "trace_p1"},
        decision_id="dec_p1_001",
        parent_turn_id="turn_parent_xyz",
    )
    assert decision_id == "dec_p1_001"
    # Real sqlite query · NOT the façade.
    with sqlite3.connect(isolated_ledger.db_path) as conn:
        row = conn.execute(
            "SELECT decision_id, agent_id, parent_turn_id FROM decisions "
            "WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "dec_p1_001"
    assert row[1] == "credit"
    assert row[2] == "turn_parent_xyz"


def test_parent_turn_id_default_none(isolated_ledger: DecisionLedger) -> None:
    """Single-mode callers (no parent_turn_id) write NULL."""
    decision_id = record_liuye_decision(
        agent_id="channel",
        endpoint="/api/liuye/sessions",
        input_payload={"q": "single mode"},
        output_payload={"candidates": []},
        evidence_chain={"trace_id": "trace_p2"},
        decision_id="dec_p2_001",
    )
    with sqlite3.connect(isolated_ledger.db_path) as conn:
        row = conn.execute(
            "SELECT parent_turn_id FROM decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    assert row[0] is None


# ---------------------------------------------------------------------------
# 2. Agent2 cross-mode case · Cowork DSL → Managed backtest
# ---------------------------------------------------------------------------


def test_agent2_cross_mode_handoff_links_via_parent_turn_id(
    isolated_ledger: DecisionLedger,
) -> None:
    """Cowork DSL turn (A) → Managed backtest turn (B) with parent_turn_id=A.

    This is the canonical Agent2 use case per root §3.1.1 · DSL generation
    is Cowork (single SSE turn) · backtest is Managed (50000-row KS · ≥1min).
    The two ledger entries link via parent_turn_id so audit can trace
    "where did this backtest come from".
    """
    # Cowork DSL turn writes ledger A (no parent).
    dsl_turn_id = "turn_dsl_cowork_001"
    decision_a = record_liuye_decision(
        agent_id="riskctrl",
        endpoint="/api/liuye/agent2/dsl",
        input_payload={"intent": "block fraud_high"},
        output_payload={"dsl": "amount > 100k AND risk > 0.8"},
        evidence_chain={"trace_id": "trace_dsl", "turn_id": dsl_turn_id},
        decision_id="dec_dsl_001",
        parent_turn_id=None,  # explicit None for clarity
    )

    # Managed backtest turn writes ledger B with parent_turn_id=DSL turn.
    decision_b = record_liuye_decision(
        agent_id="riskctrl",
        endpoint="/api/liuye/agent2/backtest",
        input_payload={"dsl_decision_id": decision_a, "sample_rows": 50000},
        output_payload={"ks": 0.42, "approval_rate": 0.68},
        evidence_chain={"trace_id": "trace_backtest"},
        decision_id="dec_backtest_001",
        parent_turn_id=dsl_turn_id,  # Cross-mode link · key invariant
    )

    # Verify both via sqlite query · NOT the façade.
    with sqlite3.connect(isolated_ledger.db_path) as conn:
        conn.row_factory = sqlite3.Row
        row_a = conn.execute(
            "SELECT * FROM decisions WHERE decision_id = ?", (decision_a,),
        ).fetchone()
        row_b = conn.execute(
            "SELECT * FROM decisions WHERE decision_id = ?", (decision_b,),
        ).fetchone()
    assert row_a is not None and row_b is not None
    assert row_a["parent_turn_id"] is None
    assert row_b["parent_turn_id"] == dsl_turn_id

    # Verify the idx_parent_turn index exists · queries on the link column
    # are O(log n) not O(n).
    with sqlite3.connect(isolated_ledger.db_path) as conn:
        indexes = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND tbl_name = 'decisions'",
            ).fetchall()
        ]
    assert "idx_parent_turn" in indexes, (
        "Cross-mode query performance requires idx_parent_turn"
    )


def test_query_by_parent_turn_id_returns_children(
    isolated_ledger: DecisionLedger,
) -> None:
    """``SELECT WHERE parent_turn_id = ?`` returns all child decisions."""
    parent = "turn_parent_001"
    for i in range(3):
        record_liuye_decision(
            agent_id="riskctrl",
            endpoint=f"/api/liuye/agent2/child_{i}",
            input_payload={"i": i},
            output_payload={"result": i * 2},
            evidence_chain={"trace_id": f"trace_{i}"},
            decision_id=f"dec_child_{i}",
            parent_turn_id=parent,
        )
    # One sibling with a different parent · MUST NOT match.
    record_liuye_decision(
        agent_id="riskctrl",
        endpoint="/api/liuye/agent2/other",
        input_payload={"x": 1},
        output_payload={"y": 2},
        evidence_chain={},
        decision_id="dec_other",
        parent_turn_id="turn_unrelated",
    )

    with sqlite3.connect(isolated_ledger.db_path) as conn:
        rows = conn.execute(
            "SELECT decision_id FROM decisions WHERE parent_turn_id = ? "
            "ORDER BY decision_id",
            (parent,),
        ).fetchall()
    ids = [r[0] for r in rows]
    assert ids == ["dec_child_0", "dec_child_1", "dec_child_2"]


# ---------------------------------------------------------------------------
# 3. LedgerReviewEvent append-only · idempotency_key dedup
# ---------------------------------------------------------------------------


def test_review_event_idempotent_same_event_id(
    isolated_ledger: DecisionLedger,
) -> None:
    """Same (decision_id, idempotency_key) twice → 1 row · same event_id."""
    # First record · creates the parent decision.
    decision_id = record_liuye_decision(
        agent_id="credit",
        endpoint="/api/liuye/sessions",
        input_payload={"x": 1},
        output_payload={"y": 2},
        evidence_chain={},
        decision_id="dec_review_001",
    )

    # Same idempotency_key twice.
    first = record_review_event(
        decision_id=decision_id,
        reviewer_id="user_credit_review_001",
        action="approve",
        idempotency_key="idem_first_attempt",
        comment="LGTM",
    )
    second = record_review_event(
        decision_id=decision_id,
        reviewer_id="user_credit_review_001",
        action="approve",
        idempotency_key="idem_first_attempt",  # same key
        comment="LGTM",
    )
    assert first.event_id == second.event_id, (
        "idempotency_key dedup violated · same key produced different event_ids"
    )

    # Verify only 1 row via raw sqlite.
    with sqlite3.connect(isolated_ledger.db_path) as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM ledger_review_events "
            "WHERE decision_id = ? AND idempotency_key = ?",
            (decision_id, "idem_first_attempt"),
        ).fetchone()[0]
    assert cnt == 1, f"expected 1 row, got {cnt}"


def test_review_event_different_idempotency_key_creates_new_row(
    isolated_ledger: DecisionLedger,
) -> None:
    """Different idempotency_keys on same decision_id → 2 rows + 2 event_ids."""
    decision_id = "dec_two_reviews"
    record_liuye_decision(
        agent_id="credit",
        endpoint="/api/liuye/sessions",
        input_payload={"x": 1},
        output_payload={"y": 2},
        evidence_chain={},
        decision_id=decision_id,
    )
    first = record_review_event(
        decision_id=decision_id, reviewer_id="r1", action="approve",
        idempotency_key="idem_a", comment="ok",
    )
    second = record_review_event(
        decision_id=decision_id, reviewer_id="r1", action="request_changes",
        idempotency_key="idem_b", comment="please revise",
    )
    assert first.event_id != second.event_id

    events = list_review_events(decision_id=decision_id)
    assert len(events) == 2
    # appended_at ASC ordering · approve comes first.
    assert events[0].action == "approve"
    assert events[1].action == "request_changes"


# ---------------------------------------------------------------------------
# 4. PII hash invariant · subject_id is hashed in sqlite
# ---------------------------------------------------------------------------


def test_subject_id_hashed_in_sqlite(isolated_ledger: DecisionLedger) -> None:
    """Plain PII subject_id (统一社会信用代码) NEVER lands plain on disk."""
    plain_pii = "91110000123456789X"  # 统一社会信用代码 example
    decision_id = record_liuye_decision(
        agent_id="credit",
        endpoint="/api/liuye/sessions",
        input_payload={"company": "test"},
        output_payload={"verdict": "PASS"},
        evidence_chain={},
        decision_id="dec_pii_001",
        subject_id=plain_pii,
    )
    with sqlite3.connect(isolated_ledger.db_path) as conn:
        row = conn.execute(
            "SELECT subject_id FROM decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    persisted = row[0]
    assert persisted is not None
    assert persisted != plain_pii, (
        "PII hash invariant violated · plain subject_id reached sqlite"
    )
    # 16-hex prefix per hash_subject_id contract.
    assert len(persisted) == 16
    assert all(c in "0123456789abcdef" for c in persisted)


# ---------------------------------------------------------------------------
# 5. Schema version pin · 1.1.0 (Q3 ratify · parent_turn_id introduction)
# ---------------------------------------------------------------------------


def test_schema_version_pinned_to_1_1_0() -> None:
    """``LEDGER_SCHEMA_VERSION`` MUST be 1.1.0 (parent_turn_id introduced).

    Bumping this constant requires (a) a sqlite migration in
    ``_SCHEMA_MIGRATIONS`` and (b) a fresh decisions-log entry per root
    §3.7.5. This test is the canary.
    """
    assert LEDGER_SCHEMA_VERSION == "1.1.0", (
        f"Schema version drifted · expected 1.1.0, got {LEDGER_SCHEMA_VERSION}. "
        "Bump requires migration + decisions-log entry per root §3.7.5."
    )
