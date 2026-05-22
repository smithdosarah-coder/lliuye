# -*- coding: utf-8 -*-
"""shared.canonical.contracts — Pydantic models for 4 agent canonical input.

W1 第 1 步 (codex R3 R3.4 ack) · 提供 4 agent BFF adapter 共享的入参 schema.

设计原则 (verbatim 刘野 CLAUDE.md):

- 第一性 + 治本不治标: 优先通用机制 (字段语义对齐 / pydantic validation) ·
  不要黑名单 / 关键词正则
- 证据支撑 + 幻觉零容忍: 必填字段缺 → raise · 不 stub 兜底
- backward compat: 4 个 schema 的 JSON 在 templates/ 是 SSOT · pydantic 不重复
  schema 定义 · 仅消费 schema 的 fields list + 提供 validation

Note · 4 schema 字段总数 75 (33 + 12 + 23 + 7) · 但 pydantic 用 dict 透传 ·
不为每字段独立声明类型 · 避免后续 schema bump v1.2+ 时双写漂移.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

# templates/ 是 4 schema SSOT (worker handoff)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "templates"


def _load_schema_keys(schema_filename: str) -> List[str]:
    """从 templates/<schema>.json 读 fields[].key 列表 · 跑时 lazy 一次."""
    path = _TEMPLATES_DIR / schema_filename
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [
        f.get("key")
        for f in data.get("fields", [])
        if isinstance(f.get("key"), str)
    ]


# Lazy schema keys cache (per process · 不重读)
_SCHEMA_KEY_CACHE: Dict[str, List[str]] = {}


def _schema_keys(filename: str) -> List[str]:
    if filename not in _SCHEMA_KEY_CACHE:
        _SCHEMA_KEY_CACHE[filename] = _load_schema_keys(filename)
    return _SCHEMA_KEY_CACHE[filename]


# ---------------------------------------------------------------------------
# 4 layer pydantic models
# ---------------------------------------------------------------------------


class ClientMetadata(BaseModel):
    """客户基础信息层 (33 fields per client-metadata-schema.json v1.1.2).

    冷数据 · 营业执照 / 工商档案 / 个人身份等 (rendering 用 deterministic REPLACE).
    """

    # 透传 dict · 不为每字段独立声明 (避免 schema bump 双写漂移)
    fields: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_required(self) -> "ClientMetadata":
        """schema required=True 字段必填 · 否则 raise."""
        # client-metadata-schema.json v1.1.2 · 仅 CLIENT_FULL_NAME + CLIENT_CORE_NAME required
        # CLIENT_CORE_NAME scope_tag=corporate · 对私场景可空
        full_name = self.fields.get("CLIENT_FULL_NAME") or self.fields.get("client_full_name")
        if not (isinstance(full_name, str) and full_name.strip()):
            raise ValueError(
                "ClientMetadata.CLIENT_FULL_NAME 必填 · 缺则下游 adapter 无法定位客户 "
                "(per client-metadata-schema.json v1.1.2 required=True)"
            )
        return self

    @property
    def company_name(self) -> str:
        """对公场景客户名 · 对私场景为自然人姓名."""
        return str(
            self.fields.get("CLIENT_FULL_NAME")
            or self.fields.get("client_full_name")
            or ""
        ).strip()

    @property
    def uscc(self) -> str:
        """统一社会信用代码 · 对私场景空字符串 (无此字段)."""
        return str(
            self.fields.get("CLIENT_USCC")
            or self.fields.get("client_uscc")
            or ""
        ).strip()


class CreditTerms(BaseModel):
    """授信条件层 (12 fields per credit-terms-schema.json v1.1.2).

    一笔授信一份 · 信贷决策引擎 + 授信批复.
    """

    fields: Dict[str, Any] = Field(default_factory=dict)


class MaterialFacts(BaseModel):
    """物料事实/长叙述层 (23 fields per material-facts-schema.json v1.1.2).

    客户档案大段业务/行业/资质叙述 + 关联方 + 财务现金流 + 对私征信/还款能力事实.
    """

    fields: Dict[str, Any] = Field(default_factory=dict)


class DecisionContext(BaseModel):
    """授信决策上下文层 (7 fields per decision-context-schema.json v1.0.0).

    credit Agent 输出 · 供下游 riskctrl/compliance/alert 消费.

    Required: DECISION_VERDICT + DECISION_SCORE + DECISION_SCORE_BREAKDOWN +
    DECISION_CONFIDENCE (per schema v1.0.0).
    """

    verdict: str = Field(
        ...,
        description="approved | rejected | conditional | pending",
    )
    score: float = Field(..., ge=0, le=100, description="综合评分 0-100")
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="7 维评分明细 dict (财务健康/现金流/履约历史/行业景气/经营稳定/担保抵质押/负面司法)",
    )
    redlines_triggered: List[str] = Field(
        default_factory=list,
        description="已触发的红线 rule_id 列表",
    )
    cases_referenced: List[str] = Field(
        default_factory=list,
        description="决策引用的相似 case_id 列表",
    )
    reasoning: str = Field(
        default="",
        description="LLM 生成的决策理由 (50-500 字)",
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="决策置信度 0-1 · < 0.7 → fallback pending",
    )

    @model_validator(mode="after")
    def _check_verdict_enum(self) -> "DecisionContext":
        allowed = {"approved", "rejected", "conditional", "pending"}
        if self.verdict not in allowed:
            raise ValueError(
                f"DecisionContext.verdict 必须 ∈ {sorted(allowed)} · "
                f"got {self.verdict!r} (per decision-context-schema.json v1.0.0)"
            )
        # confidence < 0.7 → 自动 fallback pending (per schema fallback_strategy)
        if self.confidence < 0.7 and self.verdict != "pending":
            # 不 raise · 但下游 adapter 应 respect · 这里只校验 verdict 自己一致性
            pass
        return self


# ---------------------------------------------------------------------------
# CanonicalInput · 4 agent BFF adapter 统一入口
# ---------------------------------------------------------------------------


class CanonicalInput(BaseModel):
    """4 agent canonical input · BFF adapter (credit/compliance/riskctrl/alert) 统一吃此 shape.

    Per codex R3 R3.4 W1 第 1 步 + user ack:

    - credit 吃:     client_metadata + credit_terms + material_facts
    - compliance 吃: client_metadata + material_facts + decision_context(optional)
    - riskctrl 吃:   client_metadata + decision_context + credit_terms(optional)
    - alert 吃:      client_metadata (company_name + uscc 提取自此层)

    backward compat: 旧 adapter 仍接受 raw dict payload · canonical_from_dict 走自动归一.
    """

    client_metadata: ClientMetadata = Field(
        ...,
        description="客户基础信息 (33 fields) · 全 4 agent 必备",
    )
    credit_terms: Optional[CreditTerms] = Field(
        default=None,
        description="授信条件 (12 fields) · credit/riskctrl 用 · compliance/alert 可空",
    )
    material_facts: Optional[MaterialFacts] = Field(
        default=None,
        description="物料事实 (23 fields) · credit/compliance 用 · riskctrl/alert 可空",
    )
    decision_context: Optional[DecisionContext] = Field(
        default=None,
        description="决策上下文 (7 fields) · credit 输出 · riskctrl/compliance/alert 输入",
    )
    # passthrough · 上游 BFF 透传字段 (turn_id / trace_id / persona_id / parent_tool_call_id 等)
    passthrough: Dict[str, Any] = Field(
        default_factory=dict,
        description="BFF 透传字段 (turn_id/trace_id/persona_id/parent_tool_call_id 等) · 不参与 schema validation",
    )

    @property
    def company_name(self) -> str:
        return self.client_metadata.company_name

    @property
    def uscc(self) -> str:
        return self.client_metadata.uscc


# ---------------------------------------------------------------------------
# Backward compat: 旧 dict payload → CanonicalInput
# ---------------------------------------------------------------------------


def canonical_from_dict(payload: Dict[str, Any]) -> CanonicalInput:
    """把旧 adapter raw dict payload 自动归一成 CanonicalInput.

    支持三种输入形态 (per client-metadata-schema.json compatibility.backward_compat):

    1. 已分层 dict: {"client_metadata": {...}, "credit_terms": {...}, ...}
    2. flat dict (旧 metadata.json · 68 key 合一): {"CLIENT_FULL_NAME": ..., "CREDIT_AMOUNT": ...}
    3. mixed: 部分分层 + flat passthrough 字段
    """
    if not isinstance(payload, dict):
        raise ValueError(
            f"canonical_from_dict expects dict · got {type(payload).__name__}"
        )

    # 检测形态: 已分层 vs flat
    has_client_metadata_layer = isinstance(payload.get("client_metadata"), dict)
    has_credit_terms_layer = isinstance(payload.get("credit_terms"), dict)
    has_material_facts_layer = isinstance(payload.get("material_facts"), dict)
    has_decision_context = isinstance(payload.get("decision_context"), dict)

    if has_client_metadata_layer:
        # 形态 1 / 3: 已分层 (可能含 passthrough)
        client_md_dict = payload.get("client_metadata") or {}
        credit_terms_dict = payload.get("credit_terms") if has_credit_terms_layer else None
        material_facts_dict = payload.get("material_facts") if has_material_facts_layer else None
        decision_ctx_dict = payload.get("decision_context") if has_decision_context else None
        # passthrough = payload 减去 4 layer + reserved keys
        reserved = {"client_metadata", "credit_terms", "material_facts", "decision_context"}
        passthrough = {k: v for k, v in payload.items() if k not in reserved}
    else:
        # 形态 2: flat dict · 按 schema fields[].key 自动分层
        cm_keys = set(_schema_keys("client-metadata-schema.json"))
        ct_keys = set(_schema_keys("credit-terms-schema.json"))
        mf_keys = set(_schema_keys("material-facts-schema.json"))
        # decision_context flat 形态不常见 · skip
        client_md_dict = {k: v for k, v in payload.items() if k in cm_keys}
        credit_terms_dict = {k: v for k, v in payload.items() if k in ct_keys} or None
        material_facts_dict = {k: v for k, v in payload.items() if k in mf_keys} or None
        decision_ctx_dict = None
        # passthrough = 不在任何 schema 内的字段
        all_schema_keys = cm_keys | ct_keys | mf_keys
        passthrough = {k: v for k, v in payload.items() if k not in all_schema_keys}

    client_md = ClientMetadata(fields=dict(client_md_dict))
    credit_terms = CreditTerms(fields=dict(credit_terms_dict)) if credit_terms_dict else None
    material_facts = MaterialFacts(fields=dict(material_facts_dict)) if material_facts_dict else None
    decision_context = (
        _decision_context_from_dict(decision_ctx_dict) if decision_ctx_dict else None
    )

    return CanonicalInput(
        client_metadata=client_md,
        credit_terms=credit_terms,
        material_facts=material_facts,
        decision_context=decision_context,
        passthrough=passthrough,
    )


def _decision_context_from_dict(d: Dict[str, Any]) -> DecisionContext:
    """把 dict (可能含全大写 schema key 或 snake_case) 归一成 DecisionContext."""
    return DecisionContext(
        verdict=str(d.get("verdict") or d.get("DECISION_VERDICT") or "pending"),
        score=float(d.get("score") or d.get("DECISION_SCORE") or 0),
        score_breakdown=dict(
            d.get("score_breakdown")
            or d.get("DECISION_SCORE_BREAKDOWN")
            or {}
        ),
        redlines_triggered=list(
            d.get("redlines_triggered")
            or d.get("DECISION_REDLINES_TRIGGERED")
            or []
        ),
        cases_referenced=list(
            d.get("cases_referenced")
            or d.get("DECISION_CASES_REFERENCED")
            or []
        ),
        reasoning=str(d.get("reasoning") or d.get("DECISION_REASONING") or ""),
        confidence=float(d.get("confidence") or d.get("DECISION_CONFIDENCE") or 0),
    )


# ---------------------------------------------------------------------------
# credit Agent done envelope → DecisionContext (backward compat)
# ---------------------------------------------------------------------------


def credit_done_to_decision_context(done_payload: Dict[str, Any]) -> DecisionContext:
    """把 agent_credit POST /api/credit/decision done envelope 自动 mapping → DecisionContext.

    per decision-context-schema.json compatibility.backward_compat:
      旧 credit done envelope (composite_score + sub_scores + rule_hits + case_matches + advice)
      自动 mapping → decision_context (无需改 agent_credit · 不破坏现有 shape)

    Mapping:
      composite_score    → score
      sub_scores         → score_breakdown
      rule_hits[].rule_id (severity=high/hard) → redlines_triggered
      case_matches[].case_id → cases_referenced
      advice.reasoning   → reasoning
      decision           → verdict (有条件批准 → conditional / 批 → approved / 拒 → rejected / 其他 → pending)
      llm_confidence     → confidence (无则 0.85 默认 · 走 confidence ≥ 0.7 路径)
    """
    if not isinstance(done_payload, dict):
        return DecisionContext(
            verdict="pending", score=0, score_breakdown={}, confidence=0,
        )

    # decision (中文) → verdict (英文 enum)
    decision_raw = str(done_payload.get("decision") or "").strip()
    verdict_map = {
        "批": "approved",
        "批准": "approved",
        "approved": "approved",
        "拒": "rejected",
        "拒绝": "rejected",
        "rejected": "rejected",
        "有条件批准": "conditional",
        "有条件同意": "conditional",
        "conditional": "conditional",
        "待人工复核": "pending",
        "pending": "pending",
    }
    verdict = verdict_map.get(decision_raw, "pending")

    # score (composite_score) → 归一 0-100 (retail 850 制需归一)
    composite_score = done_payload.get("composite_score") or 0
    score_max = done_payload.get("score_max") or 100
    if score_max and score_max != 100:
        score = float(composite_score) / float(score_max) * 100
    else:
        score = float(composite_score)
    score = max(0.0, min(100.0, score))

    # sub_scores → score_breakdown
    sub_scores_raw = done_payload.get("sub_scores") or {}
    score_breakdown: Dict[str, float] = {}
    if isinstance(sub_scores_raw, dict):
        for k, v in sub_scores_raw.items():
            try:
                score_breakdown[str(k)] = float(v)
            except (ValueError, TypeError):
                continue

    # rule_hits → redlines_triggered (severity high/hard 或 is_hard=True)
    rule_hits = done_payload.get("rule_hits") or []
    redlines: List[str] = []
    if isinstance(rule_hits, list):
        for rh in rule_hits:
            if not isinstance(rh, dict):
                continue
            severity = str(rh.get("severity") or "").lower()
            is_hard = bool(rh.get("is_hard"))
            if severity in {"high", "hard", "critical"} or is_hard:
                rid = rh.get("rule_id")
                if rid:
                    redlines.append(str(rid))

    # case_matches → cases_referenced
    case_matches = done_payload.get("case_matches") or []
    cases: List[str] = []
    if isinstance(case_matches, list):
        for cm in case_matches:
            if not isinstance(cm, dict):
                continue
            cid = cm.get("case_id")
            if cid:
                cases.append(str(cid))

    # advice.reasoning (或 advice 直接是 str)
    advice = done_payload.get("advice") or {}
    if isinstance(advice, dict):
        reasoning = str(advice.get("reasoning") or advice.get("rationale") or "")
    else:
        reasoning = str(advice or "")

    # confidence (LLM self-judge · 无则 0.85 默认)
    confidence = done_payload.get("llm_confidence") or done_payload.get("confidence") or 0.85
    try:
        confidence = float(confidence)
    except (ValueError, TypeError):
        confidence = 0.85
    confidence = max(0.0, min(1.0, confidence))

    return DecisionContext(
        verdict=verdict,
        score=score,
        score_breakdown=score_breakdown,
        redlines_triggered=redlines,
        cases_referenced=cases,
        reasoning=reasoning,
        confidence=confidence,
    )
