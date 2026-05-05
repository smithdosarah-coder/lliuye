# -*- coding: utf-8 -*-
"""agent_compliance.violation_schema — auditable 7-field violation reason.

Every Agent5 violation row that crosses a worker boundary (SSE → frontend,
SSE → ledger, persisted scan → docx export) MUST carry a `ViolationReason`
that lets a 合规官 sign off without re-reading the entire policy.

The seven mandatory fields (per docs/contracts/agent-compliance-policy-registry.md §4):

  1. policy_id        — registry POL-xxxx (which policy *family*)
  2. policy_version   — registry VER-xxxx (which immutable revision)
  3. clause_id        — registry CL-xxxx (which segmented clause)
  4. conflict_field   — short label for the dimension violated
                        (e.g. "营业收入门槛" / "可疑交易报告时限")
  5. business_excerpt — verbatim slice of the business event that
                        triggered the rule (≤ 300 chars · no LLM rewrite)
  6. policy_excerpt   — verbatim slice of the clause text that was
                        violated (≤ 300 chars)
  7. confidence       — float in [0.0, 1.0] · auditor SLO threshold

Plus one *derived* narrative field:
  - review_reason    — single-sentence rationale, computed from the 7
                       fields above (no LLM dependency).

Why a separate module from scan_engine?
  - Schema must be importable by the registry, evaluation runner, ledger
    exporter, and word_export — pulling them all through scan_engine would
    create a circular dep with shared.policy_registry.
  - Pydantic validates at the boundary (front- and ledger-bound payloads)
    so a partial reason can never leak into production.

Hard line: this module does NOT call LLMs and does NOT depend on
scan_engine.run_policy_scan_and_persist. It only consumes the data
scan_engine already produces.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

# Bound the inline excerpts so a giant clause body never balloons SSE / sqlite.
EXCERPT_MAX_CHARS = 300

# Short labels mapping common business-fact field names → human-readable
# 中文 column. Used only by `derive_conflict_field` as a friendly label;
# the lookup is *not* a blacklist (per CLAUDE.md §12) — unknown fields
# fall through unchanged.
_FIELD_LABEL_MAP = {
    "amount": "金额",
    "amount_wan": "金额(万元)",
    "revenue": "营业收入",
    "revenue_wan": "营业收入(万元)",
    "registered_capital": "注册资本",
    "registered_capital_ratio": "注册资本实缴比例",
    "min_bank_share_ratio": "银行股份占比",
    "duration_months": "期限(月)",
    "max_months": "最长期限(月)",
    "min_years": "最少年限",
    "max_hours": "时限(小时)",
    "operating_years": "经营年限",
    "kyc_completed": "KYC 完成状态",
    "beneficial_owner_traced": "受益所有人追溯",
    "report_hours": "上报时限(小时)",
}


def _truncate(text: str | None, max_chars: int = EXCERPT_MAX_CHARS) -> str:
    if not text:
        return ""
    s = str(text).strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


class ViolationReason(BaseModel):
    """Auditable 7-field reason · plus derived narrative.

    Construction: prefer `build_violation_reason(rule, event, cell, …)`
    over instantiating directly — it pulls the right fields off the
    rule + event + matrix-cell triple.
    """

    policy_id: str = Field(..., description="registry POL-xxxx · which policy family")
    policy_version: str = Field(..., description="registry VER-xxxx · which immutable revision")
    clause_id: str = Field(..., description="registry CL-xxxx · which clause was violated")
    conflict_field: str = Field(..., description="short label for the dimension violated")
    business_excerpt: str = Field(..., description="verbatim business-event slice (≤300 chars)")
    policy_excerpt: str = Field(..., description="verbatim policy-clause slice (≤300 chars)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0..1 · LLM=lower, hard-rule=1.0")
    review_reason: str = Field(default="", description="derived single-sentence rationale")

    @field_validator("business_excerpt", "policy_excerpt")
    @classmethod
    def _bound_excerpt(cls, v: str) -> str:
        return _truncate(v, EXCERPT_MAX_CHARS)

    @field_validator("policy_id")
    @classmethod
    def _check_policy_id_prefix(cls, v: str) -> str:
        if not v or not v.startswith("POL-"):
            raise ValueError(f"policy_id must start with POL- (got {v!r})")
        return v

    @field_validator("policy_version")
    @classmethod
    def _check_version_id_prefix(cls, v: str) -> str:
        if not v or not v.startswith("VER-"):
            raise ValueError(f"policy_version must start with VER- (got {v!r})")
        return v

    @field_validator("clause_id")
    @classmethod
    def _check_clause_id_prefix(cls, v: str) -> str:
        if not v or not v.startswith("CL-"):
            raise ValueError(f"clause_id must start with CL- (got {v!r})")
        return v

    @field_validator("conflict_field", "business_excerpt", "policy_excerpt")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("required field cannot be empty / whitespace-only")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def is_complete(cls, payload: Any) -> bool:
        """Quick check: does an arbitrary dict satisfy this schema?"""
        if not isinstance(payload, dict):
            return False
        try:
            cls.model_validate(payload)
            return True
        except ValidationError:
            return False


# ---------------------------------------------------------------------------
# Derivation helpers
# ---------------------------------------------------------------------------


def derive_conflict_field(rule: dict, event: dict, cell: dict | None = None) -> str:
    """Pick a friendly conflict-dimension label.

    Strategy:
      1. If cell.evidence carries `field=value 超阈值 …` (hard-rule path)
         extract the field name and look it up in `_FIELD_LABEL_MAP`.
      2. Else if rule.threshold has exactly one key, label it via the map.
      3. Else fall back to rule.category + 阈值 (generic).
    """
    if cell:
        evidence = str(cell.get("evidence") or "")
        # hard-rule emits "<fkey>=<num> 超阈值 max_X=Y" / "fkey=num 低于阈值 min_X=Y"
        token = evidence.split("=", 1)[0].strip()
        if token in _FIELD_LABEL_MAP:
            return _FIELD_LABEL_MAP[token]
        if token:
            # Unknown field — surface verbatim so the auditor sees what hit
            return token

    threshold = rule.get("threshold") or {}
    if isinstance(threshold, dict) and len(threshold) == 1:
        only_key = next(iter(threshold))
        # Strip max_/min_ prefix when looking up
        norm = only_key
        for prefix in ("max_", "min_"):
            if only_key.startswith(prefix):
                norm = only_key[len(prefix):]
                break
        return _FIELD_LABEL_MAP.get(only_key) or _FIELD_LABEL_MAP.get(norm) or only_key

    return rule.get("category") or "合规阈值"


def derive_review_reason(reason: ViolationReason | dict) -> str:
    """Compute the single-sentence rationale from the 7 mandatory fields.

    Format (deterministic — no LLM):
        "{conflict_field} 不符合 {clause_id_short}「{policy_excerpt[:40]}」"
        "（业务证据: {business_excerpt[:40]}; 置信度 {confidence:.2f}）"

    A 合规官 reading this can immediately:
      - locate the clause via clause_id (registry round-trip)
      - see the violated dimension (conflict_field)
      - match against the actual business excerpt
      - calibrate trust via confidence score
    """
    if isinstance(reason, ViolationReason):
        d = reason.model_dump()
    elif isinstance(reason, dict):
        d = reason
    else:
        return ""

    cf = (d.get("conflict_field") or "").strip()
    cid = (d.get("clause_id") or "").strip()
    cid_short = cid[len("CL-"):][:8] if cid.startswith("CL-") else cid[:8]
    pol = _truncate(d.get("policy_excerpt") or "", 40)
    biz = _truncate(d.get("business_excerpt") or "", 40)
    conf = float(d.get("confidence") or 0.0)
    return (
        f"{cf} 不符合 {cid_short}「{pol}」"
        f"（业务证据: {biz}; 置信度 {conf:.2f}）"
    )


# Hard-rule evidence strings emitted by scan_engine._hard_rule_judge
# carry these substrings — when present, confidence = 1.0 (unambiguous).
_HARD_RULE_EVIDENCE_HINTS = ("超阈值", "低于阈值", "硬规则比较通过")


def _hard_rule_evidence(s: str) -> bool:
    return any(hint in (s or "") for hint in _HARD_RULE_EVIDENCE_HINTS)


def _event_to_excerpt(event: dict) -> str:
    """Pick the most useful excerpt from a business event.

    Priority: fields.raw → fields.text → fields.snippet → fields.description
    → "k=v; …" summary → "{event_type} ({event_id})".
    """
    fields = event.get("fields") or {}
    if isinstance(fields, dict):
        for key in ("raw", "text", "snippet", "description"):
            v = fields.get(key)
            if isinstance(v, str) and v.strip():
                return v
        if fields:
            return "; ".join(f"{k}={v}" for k, v in list(fields.items())[:5])
    et = event.get("event_type") or "event"
    eid = event.get("event_id") or ""
    return f"{et} ({eid})"


def build_violation_reason(
    *,
    rule: dict,
    event: dict,
    cell: dict | None = None,
    policy_id: str = "",
    policy_version: str = "",
    confidence_override: float | None = None,
) -> ViolationReason | None:
    """Construct a `ViolationReason` from a rule + event + matrix cell.

    Returns None if any of the 7 mandatory fields cannot be filled
    deterministically — caller should mark "未能自动填写" rather than
    forcing a half-valid reason (per CLAUDE.md §3.3 Evidence-First).

    Confidence:
      - 1.0 when cell.evidence carries hard-rule hints (deterministic path)
      - 0.7 when cell.status == "violate" (LLM-derived)
      - 0.5 otherwise
      - explicit `confidence_override` always wins
    """
    if not rule or not event:
        return None

    # Registry-aware id triplet — must come from the rule (clause came from
    # the registry) or be passed in by the caller.
    pid = policy_id or rule.get("policy_id") or ""
    vid = policy_version or rule.get("version_id") or rule.get("policy_version") or ""
    cid = rule.get("clause_id") or rule.get("rule_id") or ""

    if not (pid.startswith("POL-") and vid.startswith("VER-") and cid.startswith("CL-")):
        return None

    cf = derive_conflict_field(rule, event, cell)
    biz_ex = _truncate(_event_to_excerpt(event))
    pol_ex = _truncate(rule.get("policy_excerpt") or rule.get("condition") or "")

    if not biz_ex or not pol_ex or not cf:
        return None

    if confidence_override is not None:
        conf = max(0.0, min(1.0, float(confidence_override)))
    elif cell and _hard_rule_evidence(cell.get("evidence", "")):
        conf = 1.0
    elif cell and cell.get("status") == "violate":
        conf = 0.7
    else:
        conf = 0.5

    try:
        reason = ViolationReason(
            policy_id=pid,
            policy_version=vid,
            clause_id=cid,
            conflict_field=cf,
            business_excerpt=biz_ex,
            policy_excerpt=pol_ex,
            confidence=conf,
        )
    except ValidationError:
        return None
    reason.review_reason = derive_review_reason(reason)
    return reason


__all__ = [
    "EXCERPT_MAX_CHARS",
    "ViolationReason",
    "build_violation_reason",
    "derive_conflict_field",
    "derive_review_reason",
]
