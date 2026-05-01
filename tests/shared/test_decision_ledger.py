# -*- coding: utf-8 -*-
"""shared.decision_ledger unit tests · BE7 (Phase B-3 · 2026-05-01).

Covers the cross-agent decision ledger per
docs/contracts/decision-ledger.md v1.0.

Hard guarantees:
1. Schema invariants (version pin, table shape, allowed values)
2. Hash determinism (same payload → same digest, key-order independent)
3. PII subject_id always hashed before storage (never plain)
4. Per-agent retention defaults (credit/report/alert/etc.)
5. Jurisdiction defaults + env override + validation
6. SQLite round-trip (record → get → query → export → review)
7. Failure isolation: write failure returns decision_id but persisted=False
8. Idempotency: re-record with same decision_id replaces (INSERT OR REPLACE)
9. Zip export shape (manifest + per-decision JSON)
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.decision_ledger import (  # noqa: E402
    ALLOWED_JURISDICTIONS,
    ALLOWED_RETENTION_CLASSES,
    DEFAULT_JURISDICTION,
    DEFAULT_RETENTION_BY_AGENT,
    LEDGER_SCHEMA_VERSION,
    DecisionLedger,
    LedgerEntry,
    LedgerWriteResult,
    RETENTION_LONG,
    RETENTION_SHORT,
    RETENTION_STANDARD,
    canonical_hash,
    canonical_json_bytes,
    default_ledger,
    export_jurisdiction,
    get_decision,
    hash_subject_id,
    query_agent,
    query_jurisdiction,
    record_decision,
    record_review,
    resolve_jurisdiction,
    resolve_retention_class,
    set_default_ledger,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_ledger(monkeypatch, tmp_path):
    """Per-test ledger backed by a fresh sqlite file. Resets the
    process-wide singleton so tests don't leak state into each other."""
    db_path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("LIUYE_LEDGER_DB_PATH", str(db_path))
    ledger = DecisionLedger(db_path)
    set_default_ledger(ledger)
    yield ledger
    set_default_ledger(None)


# ---------------------------------------------------------------------------
# 1. Schema invariants
# ---------------------------------------------------------------------------


def test_schema_version_pinned():
    """Bumping breaks the ledger contract — pin to 1.0.0."""
    assert LEDGER_SCHEMA_VERSION == "1.0.0"


def test_jurisdiction_enum_complete():
    """5 values per spec §1.4 — adding/removing is a contract change."""
    assert ALLOWED_JURISDICTIONS == frozenset({"银", "保", "证", "HQ", "BRANCH"})
    assert DEFAULT_JURISDICTION == "HQ"


def test_retention_classes_complete():
    assert ALLOWED_RETENTION_CLASSES == frozenset({
        RETENTION_SHORT, RETENTION_STANDARD, RETENTION_LONG,
    })


def test_per_agent_retention_defaults():
    """Per spec §1.3 — each of the 6 agents has a documented default."""
    assert DEFAULT_RETENTION_BY_AGENT == {
        "credit": RETENTION_STANDARD,
        "report": RETENTION_LONG,
        "alert": RETENTION_SHORT,
        "compliance": RETENTION_STANDARD,
        "channel": RETENTION_SHORT,
        "riskctrl": RETENTION_STANDARD,
    }


def test_resolve_retention_unknown_agent_falls_back():
    """Unknown agent → standard (sane default)."""
    assert resolve_retention_class("future_agent") == RETENTION_STANDARD


def test_resolve_retention_explicit_override():
    assert resolve_retention_class("credit", "long") == RETENTION_LONG


def test_resolve_retention_rejects_invalid():
    with pytest.raises(ValueError, match="retention_class"):
        resolve_retention_class("credit", "forever")


# ---------------------------------------------------------------------------
# 2. Hash determinism
# ---------------------------------------------------------------------------


def test_canonical_hash_key_order_independent():
    a = {"company": "测试", "amount": 300, "decision": "批准"}
    b = {"decision": "批准", "amount": 300, "company": "测试"}
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_unicode_stable():
    """中文 keys/values must hash deterministically."""
    payload = {"客户": "众智达科技", "评分": 87}
    h1 = canonical_hash(payload)
    h2 = canonical_hash(json.loads(json.dumps(payload, ensure_ascii=False)))
    assert h1 == h2
    # Hash is hex SHA-256 → 64 chars
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_canonical_hash_payload_change_changes_hash():
    a = {"decision": "批准", "amount": 300}
    b = {"decision": "拒绝", "amount": 300}
    assert canonical_hash(a) != canonical_hash(b)


def test_canonical_json_bytes_drops_whitespace():
    blob = canonical_json_bytes({"a": 1, "b": [2, 3]})
    assert blob == b'{"a":1,"b":[2,3]}'


# ---------------------------------------------------------------------------
# 3. PII subject_id hashing
# ---------------------------------------------------------------------------


def test_hash_subject_id_returns_16_hex():
    h = hash_subject_id("91110000xxxxxxxxxx")
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_subject_id_empty_returns_none():
    assert hash_subject_id("") is None
    assert hash_subject_id(None) is None


def test_hash_subject_id_deterministic():
    assert hash_subject_id("91110000xxxxxxxxxx") == hash_subject_id("91110000xxxxxxxxxx")


def test_subject_id_never_persisted_plain(tmp_ledger):
    plain = "91110000ABCDEFGHIJ"
    record_decision(
        agent_id="credit", endpoint="/api/credit/decision",
        input_payload={}, output_payload={}, evidence_chain={},
        subject_id=plain,
    )
    rows = query_agent("credit")
    assert rows
    stored = rows[0]["subject_id"]
    assert stored != plain, "subject_id leaked plaintext into ledger"
    assert stored == hash_subject_id(plain)


# ---------------------------------------------------------------------------
# 4. Jurisdiction resolution
# ---------------------------------------------------------------------------


def test_jurisdiction_default_hq(monkeypatch):
    monkeypatch.delenv("LIUYE_LEDGER_JURISDICTION", raising=False)
    assert resolve_jurisdiction() == "HQ"


def test_jurisdiction_env_override(monkeypatch):
    monkeypatch.setenv("LIUYE_LEDGER_JURISDICTION", "银")
    assert resolve_jurisdiction() == "银"


def test_jurisdiction_explicit_override_wins(monkeypatch):
    monkeypatch.setenv("LIUYE_LEDGER_JURISDICTION", "银")
    assert resolve_jurisdiction("BRANCH") == "BRANCH"


def test_jurisdiction_rejects_invalid():
    with pytest.raises(ValueError, match="jurisdiction"):
        resolve_jurisdiction("USA")


# ---------------------------------------------------------------------------
# 5. SQLite round-trip
# ---------------------------------------------------------------------------


def test_record_then_get_round_trip(tmp_ledger):
    decision_id = record_decision(
        agent_id="credit", endpoint="/api/credit/decision",
        input_payload={"company": "测试", "amount": 800},
        output_payload={"decision": "批准", "approved": 600},
        evidence_chain={"schema_version": "1.0.0", "nodes": [{"id": "x"}]},
        subject_name="测试公司",
    )
    assert decision_id  # non-empty
    record = get_decision(decision_id)
    assert record is not None
    assert record["agent_id"] == "credit"
    assert record["jurisdiction"] == "HQ"
    assert record["retention_class"] == RETENTION_STANDARD
    assert record["subject_name"] == "测试公司"
    assert record["evidence_chain"]["nodes"][0]["id"] == "x"
    # Hashes are stable + nontrivial
    assert len(record["input_hash"]) == 64
    assert len(record["output_hash"]) == 64


def test_record_assigns_decision_id_when_omitted(tmp_ledger):
    """UUID4 generation when caller doesn't pass decision_id."""
    did = record_decision(
        agent_id="credit", endpoint="/api/credit/decision",
        input_payload={}, output_payload={}, evidence_chain={},
    )
    # uuid4 string with dashes → 36 chars
    assert len(did) == 36 and did.count("-") == 4


def test_record_honors_explicit_decision_id(tmp_ledger):
    did = record_decision(
        agent_id="credit", endpoint="/api/credit/decision",
        input_payload={}, output_payload={}, evidence_chain={},
        decision_id="custom-id-001",
    )
    assert did == "custom-id-001"
    assert get_decision("custom-id-001")["decision_id"] == "custom-id-001"


def test_query_agent_filters_by_agent(tmp_ledger):
    record_decision(agent_id="credit", endpoint="/c", input_payload={},
                    output_payload={}, evidence_chain={})
    record_decision(agent_id="report", endpoint="/r", input_payload={},
                    output_payload={}, evidence_chain={})
    record_decision(agent_id="credit", endpoint="/c", input_payload={},
                    output_payload={}, evidence_chain={})
    assert len(query_agent("credit")) == 2
    assert len(query_agent("report")) == 1
    assert len(query_agent("alert")) == 0


def test_query_jurisdiction_filters(tmp_ledger):
    record_decision(agent_id="credit", endpoint="/c", input_payload={},
                    output_payload={}, evidence_chain={}, jurisdiction="银")
    record_decision(agent_id="credit", endpoint="/c", input_payload={},
                    output_payload={}, evidence_chain={}, jurisdiction="HQ")
    assert len(query_jurisdiction("银")) == 1
    assert len(query_jurisdiction("HQ")) == 1
    assert len(query_jurisdiction("BRANCH")) == 0


def test_count_matches_query(tmp_ledger):
    for _ in range(5):
        record_decision(agent_id="credit", endpoint="/c",
                        input_payload={}, output_payload={},
                        evidence_chain={})
    assert tmp_ledger.count(agent_id="credit") == 5
    assert tmp_ledger.count(agent_id="report") == 0


# ---------------------------------------------------------------------------
# 6. Failure isolation (BE7 hard line)
# ---------------------------------------------------------------------------


def test_invalid_jurisdiction_returns_failure_result(tmp_ledger):
    """Caller bug surfaces as persisted=False but decision_id still
    returned so the caller can echo to client."""
    result = tmp_ledger.record(
        agent_id="credit", endpoint="/c",
        input_payload={}, output_payload={}, evidence_chain={},
        jurisdiction="USA",
    )
    assert isinstance(result, LedgerWriteResult)
    assert result.persisted is False
    assert "jurisdiction" in (result.error or "")
    assert result.decision_id  # non-empty


def test_record_decision_facade_returns_id_on_failure(tmp_ledger):
    """Façade always returns the id even when underlying write fails."""
    did = record_decision(
        agent_id="credit", endpoint="/c",
        input_payload={}, output_payload={}, evidence_chain={},
        jurisdiction="USA",  # invalid
    )
    assert did  # Caller can echo to client
    # ...but row must NOT be in ledger
    assert get_decision(did) is None


def test_sqlite_disk_failure_isolated(tmp_path):
    """Ledger pointing at a directory (not file) should silent-fail."""
    bad_path = tmp_path / "not_a_file"
    bad_path.mkdir()  # path is a dir → sqlite open will fail downstream
    ledger = DecisionLedger(bad_path / "x" / "ledger.sqlite")
    # Init may or may not fail depending on platform; the contract is
    # that record() never raises.
    result = ledger.record(
        agent_id="credit", endpoint="/c",
        input_payload={}, output_payload={}, evidence_chain={},
    )
    assert isinstance(result, LedgerWriteResult)
    # decision_id always present
    assert result.decision_id


# ---------------------------------------------------------------------------
# 7. Idempotency
# ---------------------------------------------------------------------------


def test_re_record_same_id_replaces(tmp_ledger):
    """INSERT OR REPLACE — same decision_id overwrites, not duplicates."""
    record_decision(
        agent_id="credit", endpoint="/c", decision_id="fixed-001",
        input_payload={"v": 1}, output_payload={"d": "批准"},
        evidence_chain={},
    )
    record_decision(
        agent_id="credit", endpoint="/c", decision_id="fixed-001",
        input_payload={"v": 2}, output_payload={"d": "拒绝"},
        evidence_chain={},
    )
    rows = query_agent("credit")
    assert len(rows) == 1
    # Latest wins
    assert rows[0]["output_hash"] == canonical_hash({"d": "拒绝"})


# ---------------------------------------------------------------------------
# 8. Reviewer signature
# ---------------------------------------------------------------------------


def test_record_review_updates_row(tmp_ledger):
    did = record_decision(
        agent_id="credit", endpoint="/c",
        input_payload={}, output_payload={}, evidence_chain={},
    )
    assert record_review(did, reviewer_id="reviewer42", action="approve") is True
    row = get_decision(did)
    assert row["reviewer_id"] == "reviewer42"
    assert row["reviewer_action"] == "approve"
    assert row["reviewer_ts"]  # populated


def test_record_review_rejects_invalid_action(tmp_ledger):
    did = record_decision(
        agent_id="credit", endpoint="/c",
        input_payload={}, output_payload={}, evidence_chain={},
    )
    assert record_review(did, reviewer_id="r1", action="suplex") is False


def test_record_review_missing_id_returns_false(tmp_ledger):
    assert record_review("nonexistent", reviewer_id="r1", action="approve") is False


# ---------------------------------------------------------------------------
# 9. Zip export
# ---------------------------------------------------------------------------


def test_export_zip_contains_manifest_and_decisions(tmp_ledger):
    record_decision(agent_id="credit", endpoint="/c",
                    input_payload={"v": 1}, output_payload={"d": "批准"},
                    evidence_chain={"x": 1}, jurisdiction="HQ")
    record_decision(agent_id="report", endpoint="/r",
                    input_payload={"v": 2}, output_payload={"d": "OK"},
                    evidence_chain={}, jurisdiction="HQ")

    blob = export_jurisdiction("HQ")
    assert blob, "export returned empty bytes"

    import io
    with zipfile.ZipFile(io.BytesIO(blob), mode="r") as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        decision_files = [n for n in names if n.startswith("decisions/")]
        assert len(decision_files) == 2

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["schema_version"] == LEDGER_SCHEMA_VERSION
        assert manifest["count"] == 2
        assert manifest["filter"]["jurisdiction"] == "HQ"

        # Each decision file is a valid JSON
        for name in decision_files:
            row = json.loads(zf.read(name).decode("utf-8"))
            assert row["jurisdiction"] == "HQ"


def test_export_zip_filter_limits_rows(tmp_ledger):
    record_decision(agent_id="credit", endpoint="/c",
                    input_payload={}, output_payload={}, evidence_chain={},
                    jurisdiction="银")
    record_decision(agent_id="credit", endpoint="/c",
                    input_payload={}, output_payload={}, evidence_chain={},
                    jurisdiction="HQ")

    import io
    blob_hq = export_jurisdiction("HQ")
    with zipfile.ZipFile(io.BytesIO(blob_hq), mode="r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["count"] == 1


# ---------------------------------------------------------------------------
# 10. Default ledger singleton
# ---------------------------------------------------------------------------


def test_default_ledger_env_path(monkeypatch, tmp_path):
    set_default_ledger(None)
    db_path = tmp_path / "alt.sqlite"
    monkeypatch.setenv("LIUYE_LEDGER_DB_PATH", str(db_path))
    ledger = default_ledger()
    assert ledger.db_path == db_path
    set_default_ledger(None)
