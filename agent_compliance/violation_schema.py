# -*- coding: utf-8 -*-
"""agent_compliance.violation_schema — auditable 8-field violation reason + freshness.

Every Agent5 violation row that crosses a worker boundary (SSE → frontend,
SSE → ledger, persisted scan → docx export) MUST carry a `ViolationReason`
that lets a 合规官 sign off without re-reading the entire policy.

The eight mandatory fields (per docs/contracts/agent-compliance-policy-registry.md §4
+ ALL IN Phase B step 4 · 红线 #8 监管条款必带原文 hash):

  1. policy_id          — registry POL-xxxx (which policy *family*)
  2. policy_version     — registry VER-xxxx (which immutable revision)
  3. clause_id          — registry CL-xxxx (which segmented clause)
  4. conflict_field     — short label for the dimension violated
                          (e.g. "营业收入门槛" / "可疑交易报告时限")
  5. business_excerpt   — verbatim slice of the business event that
                          triggered the rule (≤ 300 chars · no LLM rewrite)
  6. policy_excerpt     — verbatim slice of the clause text that was
                          violated (≤ 300 chars)
  7. confidence         — float in [0.0, 1.0] · auditor SLO threshold
  8. clause_text_hash   — sha256 of full clause body (16 hex prefix) ·
                          篡改防御 · 红线 #8 (监管条款无原文 hash 即 abort)

Plus three *freshness* fields (CLAUDE.md §3.5.1 + §3.7.5 · ALL IN step 4):
  - evidence_date       — ISO YYYY-MM-DD · 政策生效/抓取日期 (空时退化为 retrieved_at)
  - freshness_days      — int · 距 retrieved_at 的天数 (-1 = 不可计算)
  - staleness_passed    — bool · 政策 365d SLA 内 (True) / 失效 (False)

Plus one *derived* narrative field:
  - review_reason       — single-sentence rationale, computed from the 8
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

import hashlib
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

# Bound the inline excerpts so a giant clause body never balloons SSE / sqlite.
EXCERPT_MAX_CHARS = 300

# clause_text_hash 截 16 hex (per shared/evidence_drawer Evidence.content_hash 同 schema)
CLAUSE_HASH_PREFIX_HEX = 16

# Policy 时效 SLA · per shared/evidence_freshness FRESHNESS_SLA_DAYS["policy"]
POLICY_FRESHNESS_SLA_DAYS = 365

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
    """Auditable 8-field reason + 3 freshness · plus derived narrative.

    Construction: prefer `build_violation_reason(rule, event, cell, …)`
    over instantiating directly — it pulls the right fields off the
    rule + event + matrix-cell triple.

    ALL IN Phase B step 4 (2026-05-09): 加 clause_text_hash (红线 #8) +
    evidence_date / freshness_days / staleness_passed (CLAUDE.md §3.5.1 政策 365d).
    """

    policy_id: str = Field(..., description="registry POL-xxxx · which policy family")
    policy_version: str = Field(..., description="registry VER-xxxx · which immutable revision")
    clause_id: str = Field(..., description="registry CL-xxxx · which clause was violated")
    conflict_field: str = Field(..., description="short label for the dimension violated")
    business_excerpt: str = Field(..., description="verbatim business-event slice (≤300 chars)")
    policy_excerpt: str = Field(..., description="verbatim policy-clause slice (≤300 chars)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0..1 · LLM=lower, hard-rule=1.0")
    clause_text_hash: str = Field(..., description="sha256(clause body) 前 16 hex · 红线 #8 篡改防御")
    review_reason: str = Field(default="", description="derived single-sentence rationale")

    # Freshness (ALL IN step 4 · CLAUDE.md §3.5.1 第 6 原则)
    evidence_date: str = Field(default="", description="ISO YYYY-MM-DD · 政策生效/抓取日 · 空表示不可知")
    retrieved_at: str = Field(default="", description="ISO YYYY-MM-DD · 本次扫描时间")
    freshness_days: int = Field(default=-1, description="距 retrieved_at 的天数 · -1 = 不可计算")
    staleness_passed: bool = Field(default=True, description="True = 政策 365d SLA 内 · False = 失效需重抓")

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

    @field_validator("clause_text_hash")
    @classmethod
    def _check_hash_format(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("clause_text_hash 不能空 (红线 #8)")
        s = v.strip().lower()
        if len(s) != CLAUSE_HASH_PREFIX_HEX:
            raise ValueError(f"clause_text_hash must be {CLAUSE_HASH_PREFIX_HEX} hex chars (got len={len(s)})")
        # 验 hex 字符 (0-9 a-f)
        try:
            int(s, 16)
        except ValueError as e:
            raise ValueError(f"clause_text_hash must be hex (got {v!r})") from e
        return s

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


def compute_clause_text_hash(clause_text: str) -> str:
    """sha256(clause body).hexdigest()[:16] · 红线 #8 篡改防御 anchor.

    输入空 → 返空字符串 (caller 决定是否当 None 处理).
    与 shared.evidence_drawer.Evidence.content_hash 同 schema (前 16 hex).
    """
    if not clause_text or not clause_text.strip():
        return ""
    return hashlib.sha256(clause_text[:1024].encode("utf-8")).hexdigest()[:CLAUSE_HASH_PREFIX_HEX]


def _today_iso() -> str:
    """ISO YYYY-MM-DD · today's local date · stable for tests via monkeypatch."""
    return date.today().isoformat()


def _parse_iso_date(s: str) -> date | None:
    """ISO YYYY-MM-DD → date · None on parse failure (容错 · 不抛)."""
    if not s or not s.strip():
        return None
    s = s.strip()
    # 试 datetime.fromisoformat (含 time 也接) · 退化到 date.fromisoformat
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None


def compute_freshness(
    evidence_date: str,
    retrieved_at: str,
    *,
    sla_days: int = POLICY_FRESHNESS_SLA_DAYS,
) -> tuple[int, bool]:
    """计算 (freshness_days, staleness_passed).

    Args:
        evidence_date: 政策生效/抓取日期 ISO (空 → 用 retrieved_at)
        retrieved_at: 本次扫描时间 ISO (空 → today)
        sla_days: 政策 SLA · 默认 365 天

    Returns:
        (freshness_days, staleness_passed):
          freshness_days: 距 retrieved_at 的天数 · -1 if evidence_date 不可解析
          staleness_passed: True if freshness_days <= sla_days · 也 True if 不可计算 (容错)
    """
    ev = _parse_iso_date(evidence_date)
    rt = _parse_iso_date(retrieved_at) or date.today()
    if ev is None:
        # 无 evidence_date · 不可计算 · 容错通过 (caller 可决定是否提 RFC 加严)
        return -1, True
    delta = (rt - ev).days
    if delta < 0:
        # 未来日期 · 异常 · 视作通过 (容错 · 但 freshness_days 用 abs)
        delta = abs(delta)
    return delta, delta <= sla_days


def build_violation_reason(
    *,
    rule: dict,
    event: dict,
    cell: dict | None = None,
    policy_id: str = "",
    policy_version: str = "",
    confidence_override: float | None = None,
    policy_meta: dict | None = None,
    retrieved_at: str | None = None,
) -> ViolationReason | None:
    """Construct a `ViolationReason` from a rule + event + matrix cell + policy_meta.

    Returns None if any of the 8 mandatory fields cannot be filled
    deterministically — caller should mark "未能自动填写" rather than
    forcing a half-valid reason (per CLAUDE.md §3.3 Evidence-First).

    ALL IN Phase B step 4 (2026-05-09):
      - 加 clause_text_hash 计算 (rule.policy_excerpt or rule.condition · 16 hex)
      - 加 evidence_date / freshness_days / staleness_passed (policy_meta.effective_date)
      - 接收 policy_meta + retrieved_at · caller 透传 scan-time metadata

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
    # 优先 policy_excerpt (registry 加载) · 退化到 condition (heuristic 抽取)
    pol_full = rule.get("policy_excerpt") or rule.get("condition") or ""
    biz_ex = _truncate(_event_to_excerpt(event))
    pol_ex = _truncate(pol_full)

    if not biz_ex or not pol_ex or not cf:
        return None

    # ALL IN step 4: clause_text_hash 红线 #8 闭环
    clause_hash = compute_clause_text_hash(pol_full)
    if not clause_hash:
        # 政策原文真为空 (异常) · 不能补 hash · 拒绝构造
        return None

    if confidence_override is not None:
        conf = max(0.0, min(1.0, float(confidence_override)))
    elif cell and _hard_rule_evidence(cell.get("evidence", "")):
        conf = 1.0
    elif cell and cell.get("status") == "violate":
        conf = 0.7
    else:
        conf = 0.5

    # ALL IN step 4: freshness 三字段
    meta = policy_meta or {}
    ev_date = (
        str(meta.get("effective_date") or "")
        or str(meta.get("fetched_at") or "")
        or str(rule.get("evidence_date") or "")
    ).strip()
    rt_iso = (retrieved_at or _today_iso()).strip()
    freshness_days, staleness_passed = compute_freshness(ev_date, rt_iso)

    try:
        reason = ViolationReason(
            policy_id=pid,
            policy_version=vid,
            clause_id=cid,
            conflict_field=cf,
            business_excerpt=biz_ex,
            policy_excerpt=pol_ex,
            confidence=conf,
            clause_text_hash=clause_hash,
            evidence_date=ev_date,
            retrieved_at=rt_iso,
            freshness_days=freshness_days,
            staleness_passed=staleness_passed,
        )
    except ValidationError:
        return None
    reason.review_reason = derive_review_reason(reason)
    return reason


__all__ = [
    "EXCERPT_MAX_CHARS",
    "CLAUSE_HASH_PREFIX_HEX",
    "POLICY_FRESHNESS_SLA_DAYS",
    "ViolationReason",
    "build_violation_reason",
    "compute_clause_text_hash",
    "compute_freshness",
    "derive_conflict_field",
    "derive_review_reason",
]
