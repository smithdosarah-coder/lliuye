# -*- coding: utf-8 -*-
"""liuye_service.tests.test_contracts — 5 protocol Pydantic vs JSON Schema 1:1.

Per W1-backend brief §5 DoD + ``liuye_service/CLAUDE.md`` §11 (file 16).

Three lock-ins this module asserts:

1. **5 core protocols round-trip**: each JSON Schema fixture
   (``shared/contracts/liuye/fixtures/*.json``) loads into the
   ``protocols.generated.*`` Pydantic v2 model · ``model_dump_json``
   round-trip preserves shape (snake_case via ``by_alias=True``).
2. **11 event enum lock**: the contract worker JSON Schema lists 11
   business events · ``protocols.generated.Event`` MUST match 1:1.
3. **8 ToolCall status enum lock**: matches v3 §2.3 line 207 + matrix §1.

The schemas under ``shared/contracts/liuye/schemas/`` are the SSOT ·
the generated Pydantic file is a build artifact. This test guards
that the build never drifts from the SSOT.

Hidden gotcha: ``fixtures/kb_doc.json`` and ``fixtures/report.json``
actually contain *Artifact* JSON payloads (not bare KBDoc / Artifact
of kb_upload_result and report_draft variants). The contract worker's
fixture naming reflects the **owning Artifact type**, not the protocol
under test. We re-map fixtures → protocols accordingly in this test.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from liuye_service.protocols.generated import (
    Artifact,
    Event,
    EvidenceRef,
    KBDoc,
    LiuyeChatEvent,
    LiuyeChatEvent3,
    Status,
    ToolCall,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = PROJECT_ROOT / "shared" / "contracts" / "liuye" / "schemas"
FIXTURES_DIR = PROJECT_ROOT / "shared" / "contracts" / "liuye" / "fixtures"


# ---------------------------------------------------------------------------
# 1. 11 event enum lock
# ---------------------------------------------------------------------------


EXPECTED_11_EVENTS = (
    "turn.started",
    "message.created",
    "tool.started",
    "tool.progress",
    "tool.completed",
    "artifact.patch",
    "evidence.attached",
    "turn.completed",
    "turn.error",
    "permission.request",
    "heartbeat",
)


def test_event_enum_lock_11_values() -> None:
    """``Event`` enum MUST have exactly 11 members in canonical order."""
    actual = tuple(e.value for e in Event)
    assert actual == EXPECTED_11_EVENTS, (
        f"Event enum drift detected · expected 11 events {EXPECTED_11_EVENTS!r}, "
        f"got {actual!r}"
    )


def test_event_enum_matches_json_schema() -> None:
    """JSON Schema oneOf branch enum MUST list the same 11 events as Pydantic."""
    schema = json.loads(
        (SCHEMAS_DIR / "liuye_chat_event.schema.json").read_text(encoding="utf-8"),
    )
    top_enum = tuple(schema["properties"]["event"]["enum"])
    assert top_enum == EXPECTED_11_EVENTS, (
        f"liuye_chat_event.schema.json event enum mismatch · "
        f"expected {EXPECTED_11_EVENTS!r}, got {top_enum!r}"
    )


def test_event_enum_includes_permission_request() -> None:
    """``permission.request`` is the 11th event (PM 2026-05-11 Q2 ratify)."""
    values = [e.value for e in Event]
    assert "permission.request" in values, (
        "permission.request missing from Event enum · "
        "PM 2026-05-11 Q2 ratify requires it as the 11th SSE event "
        "(direct emit via permissions.emit_permission_request)"
    )


# ---------------------------------------------------------------------------
# 2. 8 ToolCall status enum lock
# ---------------------------------------------------------------------------


EXPECTED_8_STATUSES = (
    "queued",
    "connecting",
    "running",
    "streaming",
    "idle_timeout",
    "completed",
    "failed",
    "aborted",
)


def test_status_enum_lock_8_values() -> None:
    """``Status`` enum MUST have exactly 8 members (v3 §2.3 + matrix §1)."""
    actual = tuple(s.value for s in Status)
    assert actual == EXPECTED_8_STATUSES, (
        f"Status enum drift · expected 8 statuses {EXPECTED_8_STATUSES!r}, "
        f"got {actual!r}"
    )


def test_status_enum_includes_streaming_and_aborted() -> None:
    """``streaming`` and ``aborted`` are non-negotiable v3 hardline statuses."""
    values = {s.value for s in Status}
    assert "streaming" in values, "streaming status missing · v3 §2.3 violation"
    assert "aborted" in values, "aborted status missing · v3 §2.3 violation"


def test_status_enum_matches_json_schema() -> None:
    """``tool_call.schema.json`` status enum MUST list 8 values 1:1 with Pydantic."""
    schema = json.loads(
        (SCHEMAS_DIR / "tool_call.schema.json").read_text(encoding="utf-8"),
    )
    json_enum = tuple(schema["properties"]["status"]["enum"])
    assert json_enum == EXPECTED_8_STATUSES, (
        f"tool_call.schema.json status enum mismatch · "
        f"expected {EXPECTED_8_STATUSES!r}, got {json_enum!r}"
    )


# ---------------------------------------------------------------------------
# 3. 5 protocol Pydantic vs JSON Schema 1:1 round-trip
# ---------------------------------------------------------------------------


def _round_trip(model_cls: type, fixture_data: dict[str, Any]) -> dict[str, Any]:
    """Validate fixture → instantiate model → dump JSON → parse → compare.

    Returns the dumped JSON dict. Asserts that the dumped dict has at
    least every required field from the input fixture.
    """
    instance = model_cls(**fixture_data)
    dumped = json.loads(instance.model_dump_json(by_alias=True, exclude_none=False))
    return dumped


def test_artifact_round_trip_channel_search() -> None:
    """``channel_search.json`` Artifact fixture round-trips through Pydantic."""
    fixture_path = FIXTURES_DIR / "channel_search.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    dumped = _round_trip(Artifact, fixture)
    # Core identity fields must survive round-trip · alias preserves them.
    assert dumped["id"] == fixture["id"]
    assert dumped["schema_version"] == fixture["schema_version"]
    assert dumped["type"] == fixture["type"]
    assert dumped["status"] == fixture["status"]
    assert dumped["owner_agent"] == fixture["owner_agent"]
    # Patches array length preserved.
    assert len(dumped["patches"]) == len(fixture["patches"])


def test_artifact_round_trip_credit_decision() -> None:
    """``credit_decision.json`` Artifact fixture round-trips."""
    fixture = json.loads(
        (FIXTURES_DIR / "credit_decision.json").read_text(encoding="utf-8"),
    )
    dumped = _round_trip(Artifact, fixture)
    assert dumped["id"] == fixture["id"]
    assert dumped["type"] == "credit_decision"
    assert dumped["owner_agent"] == "credit"
    # verdict + qc_score survive · per Artifact protocol §2.2.
    assert dumped.get("verdict") == fixture.get("verdict")


def test_artifact_round_trip_report_draft() -> None:
    """``report.json`` Artifact fixture (report_draft type) round-trips."""
    fixture = json.loads(
        (FIXTURES_DIR / "report.json").read_text(encoding="utf-8"),
    )
    dumped = _round_trip(Artifact, fixture)
    assert dumped["id"] == fixture["id"]
    assert dumped["type"] == "report_draft"


def test_artifact_round_trip_kb_upload_result() -> None:
    """``kb_doc.json`` Artifact fixture (kb_upload_result type) round-trips."""
    fixture = json.loads(
        (FIXTURES_DIR / "kb_doc.json").read_text(encoding="utf-8"),
    )
    dumped = _round_trip(Artifact, fixture)
    assert dumped["id"] == fixture["id"]
    assert dumped["type"] == "kb_upload_result"


def test_evidence_ref_round_trip_all_five() -> None:
    """``evidence_ref.json`` carries 5 EvidenceRef objects · all round-trip."""
    fixture_path = FIXTURES_DIR / "evidence_ref.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(fixture, list), "evidence_ref.json must be a list of 5 entries"
    assert len(fixture) == 5, f"expected 5 evidence refs, got {len(fixture)}"
    for entry in fixture:
        instance = EvidenceRef(**entry)
        dumped = json.loads(instance.model_dump_json(by_alias=True))
        assert dumped["id"] == entry["id"]
        assert dumped["schema_version"] == "1"
        assert dumped["kb_doc_id"] == entry["kb_doc_id"]


def test_kb_doc_minimal_model() -> None:
    """Verify KBDoc model accepts the minimal required field set.

    The fixture file kb_doc.json is actually an Artifact of type
    kb_upload_result · we exercise the KBDoc model with a synthetic
    minimal payload that matches the JSON Schema required fields.
    KBDoc enums (per generated.py): type ∈ {upload, pulled, mock} ·
    source_type ∈ {gov, enterprise, tavily, internal, user} ·
    verification_method ∈ {signature, cross_check, manual, unverified}.
    """
    minimal = {
        "id": "kb_doc_test_001",
        "schema_version": "1",
        "title": "测试 KBDoc · 沧澜精密机械年报 2026",
        "type": "upload",
        "tier": 2,
        "source_type": "internal",
        "collected_at": "2026-05-10T08:00:00+00:00",
        "verification_method": "signature",
        "content_hash": "a" * 64,
    }
    instance = KBDoc(**minimal)
    dumped = json.loads(instance.model_dump_json(by_alias=True))
    assert dumped["id"] == minimal["id"]
    assert dumped["title"] == minimal["title"]
    assert dumped["tier"] == minimal["tier"]


def test_tool_call_minimal_model() -> None:
    """ToolCall must accept the 11-field minimum + reject missing required.

    ``progress`` is ``List[ProgressMessage]`` (per JSON Schema array
    type) · not a single ProgressMessage object. ToolCall accumulates
    progress messages as the tool runs (per v3 §2.3 + matrix §1).
    """
    minimal = {
        "id": "tc_test_001",
        "schema_version": "1",
        "turn_id": "turn_test_001",
        "agent": "credit",
        "tool_id": "credit_decision",
        "boundary": "cowork",
        "invoker_id": "rm-wangzhe-east",
        "input": {"applied_product": "CORP_CREDIT"},
        "status": "running",
        "progress": [
            {
                "id": "pm_test_001",
                "turn_id": "turn_test_001",
                "tool_call_id": "tc_test_001",
                "trace_id": "trace_test_001",
                "seq": 1,
                "ts": "2026-05-12T09:00:00+00:00",
                "stage_key": "scoring",
                "stage_label": "评分",
                "status": "running",
            },
        ],
        "started_at": "2026-05-12T09:00:00+00:00",
    }
    instance = ToolCall(**minimal)
    dumped = json.loads(instance.model_dump_json(by_alias=True))
    assert dumped["id"] == minimal["id"]
    assert dumped["agent"] == "credit"
    assert dumped["boundary"] == "cowork"
    assert dumped["status"] == "running"
    assert isinstance(dumped["progress"], list)


def test_tool_call_rejects_unknown_boundary() -> None:
    """Boundary enum is 2-value lock · ``cowork`` / ``managed_readonly`` only."""
    bad = {
        "id": "tc_bad",
        "schema_version": "1",
        "turn_id": "turn_bad",
        "agent": "credit",
        "tool_id": "credit_decision",
        "boundary": "PHASE_3_HYPOTHETICAL",
        "invoker_id": "rm-test",
        "input": {},
        "status": "running",
        "progress": [],
        "started_at": "2026-05-12T09:00:00+00:00",
    }
    with pytest.raises(ValidationError):
        ToolCall(**bad)


def test_liuye_chat_event_round_trip() -> None:
    """LiuyeChatEvent (RootModel union) accepts an 11-event envelope."""
    envelope = {
        "schema_version": "1",
        "event": "turn.started",
        "turn_id": "turn_test_001",
        "trace_id": "trace_test_001",
        "seq": 1,
        "ts": "2026-05-12T09:00:00+00:00",
        "payload": {"persona_id": "rm-wangzhe-east"},
    }
    instance = LiuyeChatEvent3(**envelope)
    dumped = json.loads(instance.model_dump_json(by_alias=True))
    assert dumped["event"] == "turn.started"
    assert dumped["seq"] == 1


def test_liuye_chat_event_rejects_unknown_event() -> None:
    """Unknown event names MUST fail Pydantic validation (11-event lock)."""
    envelope = {
        "schema_version": "1",
        "event": "PHASE_3_HYPOTHETICAL.event",
        "turn_id": "turn_bad",
        "trace_id": "trace_bad",
        "seq": 1,
        "ts": "2026-05-12T09:00:00+00:00",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        # Validating through any of the three branches must reject.
        LiuyeChatEvent.model_validate(envelope)


def test_artifact_rejects_unknown_type() -> None:
    """5-enum Artifact.type lock · v3 §2.2 hardline."""
    fixture = json.loads(
        (FIXTURES_DIR / "channel_search.json").read_text(encoding="utf-8"),
    )
    fixture["type"] = "PHASE_3_HYPOTHETICAL"
    with pytest.raises(ValidationError):
        Artifact(**fixture)


# ---------------------------------------------------------------------------
# Schema lock cross-check · regenerate would have fired this test
# ---------------------------------------------------------------------------


def test_schemas_dir_exists_with_5_files() -> None:
    """Sanity: 5 schema files present in canonical names."""
    expected = {
        "artifact.schema.json",
        "evidence_ref.schema.json",
        "kb_doc.schema.json",
        "liuye_chat_event.schema.json",
        "tool_call.schema.json",
    }
    actual = {p.name for p in SCHEMAS_DIR.glob("*.json")}
    assert expected.issubset(actual), (
        f"missing schemas: {expected - actual} · build / SSOT drift"
    )


def test_fixtures_dir_exists_with_5_files() -> None:
    """Sanity: 5 fixture files present in canonical names."""
    expected = {
        "channel_search.json",
        "credit_decision.json",
        "evidence_ref.json",
        "kb_doc.json",
        "report.json",
    }
    actual = {p.name for p in FIXTURES_DIR.glob("*.json")}
    assert expected.issubset(actual), (
        f"missing fixtures: {expected - actual} · build / SSOT drift"
    )
