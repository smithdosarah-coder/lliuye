# -*- coding: utf-8 -*-
"""liuye_service.tests.test_permissions_v2 — W2 3-tier real-fire + REST grant/deny path.

Per W2-backend brief §4.6 + ``liuye_service/CLAUDE.md`` §8 + v3 §2.5 +
liuye-sse-event-matrix.md §3 Q2.

Test surfaces (NOT shadowing W1 permission test — this is the W2 hardening
layer focused on 3-tier real-fire, grant/deny REST round-trip, idempotency
gate, and persona mismatch handling):

1. **3-tier risk classification**: ACTION_RISK_TIER returns low / medium /
   high for the 3 canonical case (LE-04a download · A3-NEW Decision submit ·
   LE-05 sign-off · KB upload · F-053 上链 · LE-04b ZIP).
2. **Idempotency_key gate**: high-tier + medium-tier write actions REQUIRE
   idempotency_key; low-tier never does.
3. **emit_permission_request payload shape**: produces ``request_id`` /
   ``risk_tier`` / ``idempotency_key`` / etc. matching wire spec (v3 §2.1).
4. **grant happy path**: idempotency_key match + persona match →
   ``orchestrator.resume_turn`` called · LedgerReviewEvent written.
5. **grant idempotency mismatch**: returns False, no orchestrator call.
6. **grant persona mismatch**: returns False, no orchestrator call.
7. **deny path**: ``orchestrator.abort_turn`` called with reason ·
   LedgerReviewEvent written with action='reject'.
8. **3 risk scenarios real fire**: low (kb_manifest_download · LE-04a)
   medium (credit_decision_submit · A3-NEW) high (ledger_sign_off · LE-05).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

import pytest

from liuye_service.permissions import (
    ACTION_RISK_TIER,
    IDEMPOTENCY_REQUIRED_ACTIONS,
    deny,
    emit_permission_request,
    grant,
    requires_idempotency_key,
    risk_tier_for,
)
from liuye_service.schemas import LedgerReviewEvent, PermissionRequest


# ---------------------------------------------------------------------------
# Stub orchestrator + SSE writer + review writer · in-memory · no I/O
# ---------------------------------------------------------------------------


class StubOrchestrator:
    """Minimal in-memory orchestrator stub satisfying OrchestratorHandle."""

    def __init__(self) -> None:
        self.holds: dict[str, PermissionRequest] = {}
        self.resumed: list[tuple[str, str]] = []  # (turn_id, request_id)
        self.aborted: list[tuple[str, str]] = []   # (turn_id, reason)

    async def resume_turn(
        self, turn_id: str, *, after_permission: PermissionRequest,
    ) -> bool:
        self.resumed.append((turn_id, after_permission.id))
        return True

    async def abort_turn(
        self,
        turn_id: str,
        *,
        reason: str,
        code: str = "PERMISSION_DENIED",
    ) -> bool:
        self.aborted.append((turn_id, reason))
        return True

    def get_permission_hold(self, request_id: str) -> Optional[PermissionRequest]:
        return self.holds.get(request_id)

    def clear_permission_hold(self, request_id: str) -> None:
        self.holds.pop(request_id, None)


class StubSSEWriter:
    """Captures emit() calls for assertion."""

    def __init__(self) -> None:
        self.emitted: list[dict[str, Any]] = []

    async def emit(
        self,
        *,
        event: str,
        payload: dict[str, Any],
        turn_id: str,
        trace_id: str,
        tool_call_id: Optional[str] = None,
    ) -> None:
        self.emitted.append({
            "event": event,
            "payload": payload,
            "turn_id": turn_id,
            "trace_id": trace_id,
            "tool_call_id": tool_call_id,
        })


def make_request(
    *,
    action: str = "credit_decision_submit",
    risk_tier: str = "medium",
    idempotency_key: str = "idem_test_001",
    required_persona: Optional[list[str]] = None,
    turn_id: str = "turn_test_001",
    explanation: str = "请确认上链提交",
) -> PermissionRequest:
    """Test factory · default well-formed PermissionRequest."""
    return PermissionRequest(
        id=f"req_{uuid.uuid4().hex[:12]}",
        action=action,
        risk_tier=risk_tier,  # type: ignore[arg-type]
        idempotency_key=idempotency_key,
        required_persona=required_persona,
        explanation=explanation,
        turn_id=turn_id,
    )


# ---------------------------------------------------------------------------
# 1. 3-tier risk classification · 6 canonical cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action,expected_tier", [
    # low → inline notice
    ("kb_manifest_download", "low"),   # LE-04a 下载 manifest
    ("im_send", "low"),
    ("session_logout", "low"),
    ("thread_pin", "low"),
    # medium → blocking modal
    ("credit_decision_submit", "medium"),  # A3-NEW
    ("ledger_write", "medium"),            # F-053 上链
    ("report_export_docx", "medium"),      # F-052-export
    ("kb_upload", "medium"),
    # high → drawer with reason
    ("ledger_sign_off", "high"),           # LE-05 签字
    ("managed_zip_export", "high"),        # LE-04b
    ("pipl_overseas_call", "high"),
    ("out_of_scope_persona_op", "high"),
])
def test_3_tier_classification(action: str, expected_tier: str) -> None:
    assert risk_tier_for(action) == expected_tier
    assert ACTION_RISK_TIER.get(action) == expected_tier


def test_unregistered_action_defaults_to_medium() -> None:
    """Unknown action → medium (safer default · prompts user via modal)."""
    assert risk_tier_for("unknown_future_action") == "medium"


# ---------------------------------------------------------------------------
# 2. Idempotency_key gate
# ---------------------------------------------------------------------------


def test_high_tier_requires_idempotency_key() -> None:
    """All high-tier actions REQUIRE idempotency_key (irreversible)."""
    for action, tier in ACTION_RISK_TIER.items():
        if tier == "high":
            assert requires_idempotency_key(action), (
                f"high-tier action {action} must require idempotency_key"
            )


def test_medium_write_actions_require_idempotency() -> None:
    """Medium-tier write paths (state mutations) require idempotency."""
    assert requires_idempotency_key("credit_decision_submit")
    assert requires_idempotency_key("ledger_write")
    assert requires_idempotency_key("report_handoff_pass")


def test_low_tier_never_requires_idempotency() -> None:
    """Low-tier actions are read-only / observational · no idem required."""
    for action, tier in ACTION_RISK_TIER.items():
        if tier == "low":
            assert not requires_idempotency_key(action), (
                f"low-tier action {action} should not require idempotency_key"
            )


def test_idempotency_required_set_is_subset_of_registry() -> None:
    """Sanity · IDEMPOTENCY_REQUIRED_ACTIONS only references registered actions."""
    for action in IDEMPOTENCY_REQUIRED_ACTIONS:
        assert action in ACTION_RISK_TIER, (
            f"{action} requires idempotency but is not in ACTION_RISK_TIER"
        )


# ---------------------------------------------------------------------------
# 3. emit_permission_request · 11th SSE event payload shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_permission_request_payload_shape() -> None:
    """Emitted payload has request_id / risk_tier / idempotency_key matching wire."""
    writer = StubSSEWriter()
    req = make_request(
        action="credit_decision_submit", risk_tier="medium",
        idempotency_key="idem_emit_001",
    )
    await emit_permission_request(req, writer, trace_id="trace_emit_001")
    assert len(writer.emitted) == 1
    evt = writer.emitted[0]
    assert evt["event"] == "permission.request"
    assert evt["turn_id"] == "turn_test_001"
    assert evt["trace_id"] == "trace_emit_001"
    payload = evt["payload"]
    # ``id`` in PermissionRequest → ``request_id`` in wire payload (matrix §3 Q2).
    assert "request_id" in payload
    assert "id" not in payload, "PermissionRequest.id MUST be renamed to request_id on wire"
    assert payload["risk_tier"] == "medium"
    assert payload["idempotency_key"] == "idem_emit_001"
    assert payload["action"] == "credit_decision_submit"
    # Internal-only fields stripped from wire payload.
    assert "turn_id" not in payload
    assert "tool_call_id" not in payload


@pytest.mark.asyncio
async def test_emit_permission_request_missing_turn_id_no_emit() -> None:
    """Defence in depth · request without turn_id MUST NOT emit (logged warn)."""
    writer = StubSSEWriter()
    req = PermissionRequest(
        id="req_x",
        action="credit_decision_submit",
        risk_tier="medium",
        idempotency_key="idem_x",
        turn_id=None,  # No turn_id · should not emit
    )
    await emit_permission_request(req, writer, trace_id="trace_x")
    assert writer.emitted == []


# ---------------------------------------------------------------------------
# 4-7. grant / deny REST path (driven by stub orchestrator + review writer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grant_happy_path_resumes_turn_and_writes_review() -> None:
    """Idempotency_key match + persona match → resume_turn + LedgerReviewEvent write."""
    orch = StubOrchestrator()
    req = make_request(
        action="credit_decision_submit",
        required_persona=["credit_reviewer"],
        idempotency_key="idem_grant_001",
    )
    orch.holds[req.id] = req

    review_writes: list[LedgerReviewEvent] = []

    async def fake_review_writer(event: LedgerReviewEvent) -> bool:
        review_writes.append(event)
        return True

    ok = await grant(
        request_id=req.id,
        persona_id="user_alice_001",
        idempotency_key="idem_grant_001",
        reviewer_role="credit_reviewer",
        orchestrator=orch,
        review_writer=fake_review_writer,
        comment="Approved at AC review",
    )
    assert ok is True
    assert len(orch.resumed) == 1
    assert orch.resumed[0] == (req.turn_id, req.id)
    # Hold cleared.
    assert req.id not in orch.holds
    # ReviewWriter received an 'approve' event.
    assert len(review_writes) == 1
    assert review_writes[0].action == "approve"
    assert review_writes[0].reviewer_id == "user_alice_001"
    assert review_writes[0].comment == "Approved at AC review"


@pytest.mark.asyncio
async def test_grant_idempotency_mismatch_rejected() -> None:
    """Mismatched idempotency_key → False · NO resume_turn call · hold persists."""
    orch = StubOrchestrator()
    req = make_request(idempotency_key="idem_correct")
    orch.holds[req.id] = req

    ok = await grant(
        request_id=req.id,
        persona_id="user_x",
        idempotency_key="idem_WRONG",
        reviewer_role="credit_reviewer",
        orchestrator=orch,
    )
    assert ok is False
    assert orch.resumed == []
    # Hold should persist · user can retry with correct key.
    assert req.id in orch.holds


@pytest.mark.asyncio
async def test_grant_persona_mismatch_rejected() -> None:
    """Reviewer role not in required_persona → False."""
    orch = StubOrchestrator()
    req = make_request(
        required_persona=["audit_committee"],
        idempotency_key="idem_p_test",
    )
    orch.holds[req.id] = req

    ok = await grant(
        request_id=req.id,
        persona_id="user_x",
        idempotency_key="idem_p_test",
        reviewer_role="credit_reviewer",  # not in required_persona
        orchestrator=orch,
    )
    assert ok is False
    assert orch.resumed == []


@pytest.mark.asyncio
async def test_grant_unknown_request_id_returns_false() -> None:
    """grant on unknown request_id → False · noop."""
    orch = StubOrchestrator()
    ok = await grant(
        request_id="req_unknown",
        persona_id="user_x",
        idempotency_key="idem_x",
        reviewer_role="any",
        orchestrator=orch,
    )
    assert ok is False
    assert orch.resumed == []


@pytest.mark.asyncio
async def test_deny_aborts_turn_and_writes_reject_review() -> None:
    """deny → orchestrator.abort_turn(reason) · LedgerReviewEvent(action='reject')."""
    orch = StubOrchestrator()
    req = make_request(idempotency_key="idem_deny_001")
    orch.holds[req.id] = req

    review_writes: list[LedgerReviewEvent] = []

    async def fake_review_writer(event: LedgerReviewEvent) -> bool:
        review_writes.append(event)
        return True

    ok = await deny(
        request_id=req.id,
        persona_id="user_bob_001",
        reason="不符合合规要求",
        orchestrator=orch,
        review_writer=fake_review_writer,
    )
    assert ok is True
    assert len(orch.aborted) == 1
    assert orch.aborted[0] == (req.turn_id, "不符合合规要求")
    # Hold cleared.
    assert req.id not in orch.holds
    # ReviewWriter received a 'reject' event with the reason as comment.
    assert len(review_writes) == 1
    assert review_writes[0].action == "reject"
    assert review_writes[0].comment == "不符合合规要求"


@pytest.mark.asyncio
async def test_deny_unknown_request_id_returns_false() -> None:
    orch = StubOrchestrator()
    ok = await deny(
        request_id="req_unknown",
        persona_id="x",
        reason="x",
        orchestrator=orch,
    )
    assert ok is False
    assert orch.aborted == []


# ---------------------------------------------------------------------------
# 8. 3 risk scenarios real fire · low / medium / high
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_low_risk_le04a_download_manifest_inline() -> None:
    """LE-04a kb_manifest_download is low-tier · inline notice · no idem needed."""
    assert risk_tier_for("kb_manifest_download") == "low"
    assert not requires_idempotency_key("kb_manifest_download")

    orch = StubOrchestrator()
    writer = StubSSEWriter()
    req = make_request(
        action="kb_manifest_download", risk_tier="low",
        idempotency_key="idem_low_001",  # technically not required but harmless
    )
    orch.holds[req.id] = req
    await emit_permission_request(req, writer, trace_id="trace_low")
    assert writer.emitted[0]["payload"]["risk_tier"] == "low"

    # Grant immediately · low-tier never blocks long.
    ok = await grant(
        request_id=req.id,
        persona_id="user_low_001",
        idempotency_key="idem_low_001",
        reviewer_role="rm",
        orchestrator=orch,
    )
    assert ok is True
    assert len(orch.resumed) == 1


@pytest.mark.asyncio
async def test_medium_risk_a3_decision_submit_modal() -> None:
    """A3-NEW credit_decision_submit medium · blocking modal · idem required."""
    assert risk_tier_for("credit_decision_submit") == "medium"
    assert requires_idempotency_key("credit_decision_submit")

    orch = StubOrchestrator()
    writer = StubSSEWriter()
    req = make_request(
        action="credit_decision_submit", risk_tier="medium",
        required_persona=["credit_reviewer", "audit_committee"],
        idempotency_key="idem_medium_a3_001",
    )
    orch.holds[req.id] = req
    await emit_permission_request(req, writer, trace_id="trace_medium")
    payload = writer.emitted[0]["payload"]
    assert payload["risk_tier"] == "medium"
    assert payload["required_persona"] == ["credit_reviewer", "audit_committee"]

    review_writes: list[LedgerReviewEvent] = []

    async def writer_fn(event: LedgerReviewEvent) -> bool:
        review_writes.append(event)
        return True

    ok = await grant(
        request_id=req.id,
        persona_id="user_credit_reviewer_alice",
        idempotency_key="idem_medium_a3_001",
        reviewer_role="credit_reviewer",
        orchestrator=orch,
        review_writer=writer_fn,
        comment="符合授信红线",
    )
    assert ok is True
    assert len(review_writes) == 1
    assert review_writes[0].action == "approve"
    assert review_writes[0].comment == "符合授信红线"


@pytest.mark.asyncio
async def test_high_risk_le05_sign_off_drawer_with_reason() -> None:
    """LE-05 ledger_sign_off high · drawer · idem required · denial path written."""
    assert risk_tier_for("ledger_sign_off") == "high"
    assert requires_idempotency_key("ledger_sign_off")

    orch = StubOrchestrator()
    writer = StubSSEWriter()
    req = PermissionRequest(
        id=f"req_{uuid.uuid4().hex[:12]}",
        action="ledger_sign_off",
        risk_tier="high",
        idempotency_key="idem_high_le05_001",
        required_persona=["compliance_officer"],
        reason_required=True,
        rule_source="policy.ledger_signoff",
        scope="once",
        explanation="LE-05 高风险签字 · 请在抽屉填写签字理由",
        consequences=[
            "签字后决策不可撤回",
            "进入合规审计链 · 90 天内可被监管抽查",
            "签字人对该决策承担连带责任",
        ],
        turn_id="turn_le05_001",
    )
    orch.holds[req.id] = req
    await emit_permission_request(req, writer, trace_id="trace_high")
    payload = writer.emitted[0]["payload"]
    assert payload["risk_tier"] == "high"
    assert payload["reason_required"] is True
    assert len(payload["consequences"]) == 3

    # Compliance officer denies with reason.
    review_writes: list[LedgerReviewEvent] = []

    async def writer_fn(event: LedgerReviewEvent) -> bool:
        review_writes.append(event)
        return True

    ok = await deny(
        request_id=req.id,
        persona_id="user_compliance_bob",
        reason="风险敞口超过单笔限额 · 退回客户经理修改额度",
        orchestrator=orch,
        review_writer=writer_fn,
    )
    assert ok is True
    assert len(orch.aborted) == 1
    assert orch.aborted[0][0] == "turn_le05_001"
    assert "风险敞口超过单笔限额" in orch.aborted[0][1]
    assert len(review_writes) == 1
    assert review_writes[0].action == "reject"
