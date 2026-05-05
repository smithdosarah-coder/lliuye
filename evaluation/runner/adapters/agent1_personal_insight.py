# -*- coding: utf-8 -*-
"""
evaluation.runner.adapters.agent1_personal_insight — Agent1 个人画像 (BE12 子域) 评估 adapter

Sprint 3 BE13 POC scaffold (per phase-b-charter v2.2 line 212 · B7 Week 7-8 减半 0.75-1 周)

锚定 schema: agent_channel/personal_insight.py @ 9479428
    PersonalInsightPayload {candidate_id, person_features, product_fit, compliance_check,
                            talking_points, pii_redacted, latency_ms}

4 维度加权评价 (per BE13 brief · POC-4-DIMS · 替代旧"经营策略 20%"维度名):
    person_features_accuracy             35%   PersonFeatures 6 字段填充 + oracle 重合
    product_fit_score                    25%   ProductFit.fit_score 归一化 + 推荐有效性
    compliance_talkpoints_completeness   20%   ComplianceCheck + TalkingPoints 完整性
    pii_latency_compliance               20%   pii_redacted 强制 + latency_ms 软分

PREP-ONLY 状态 (per Codex R3 dissent residual #3 · 只允许 discovery · 不允许 stub PR ship scope):
    BE12 真业务 ship (LLM grounded talking_points + compliance sources + PII redact 全实装)
    前 · runner --agent personal_insight 仅返 SKIP/PENDING (artifact 缺) · 不引入误导基线。

接通时机 (worker B4-channel BE12 真业务 DONE 后):
    1. 启用 _LAZY_MODULES 注册 (registry.py 加 "personal_insight")
    2. artifact runtime dump 路径定 (建议 evaluation/manual/personal_insight_latest.json)
    3. oracle gold 标注落地 (建议 evaluation/manual/personal_insight_oracle.json · PM 设计 · 反 5 原则 #1 盲测)
    4. 跑首轮 baseline · 写 evaluation/baselines/YYYY-MM-DD-be13-poc-first-run.md

Artifact 协议 (BE12 真业务 ship 后 · 本 adapter 消费此格式):
    {
        "runs": [
            {
                "candidate_id": "...",
                "payload": <PersonalInsightPayload from agent_channel/personal_insight.py>,
                "endpoint_status": 200,
                "schema_valid": true,
                "llm_calls": {"total": N, "success": M, "audit_ids": [...]},
                "ledger_decision_id": "uuid"  # BE7 上链 id (verify 用)
            },
            ...
        ],
        "oracle": {  # 可选 · oracle_path 到位时合并
            "gold_person_features_by_candidate_id": {
                "<cid>": {"role": "...", "industry_yr": ..., ...},
                ...
            }
        }
    }
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..base_evaluator import REPO_ROOT, BaseEvaluator
from ..registry import register_evaluator
from ..schemas import EvalRun, MetricOutcome


# ============================================================
# 路径常量
# ============================================================
DEFAULT_RUNTIME = REPO_ROOT / "evaluation" / "manual" / "personal_insight_latest.json"
ORACLE_PATH = REPO_ROOT / "evaluation" / "manual" / "personal_insight_oracle.json"

PREP_SOURCE = "prep_awaiting_be12_real_business_ship"

# PersonFeatures 6 字段 schema 锚 (per agent_channel/personal_insight.py @ 9479428)
PERSON_FEATURES_KEYS = (
    "role", "industry_yr", "education", "age_range",
    "risk_appetite", "decision_path",
)
STUB_PLACEHOLDER = "未能自动填写"

# 4 维度权重 (per yaml · POC-4-DIMS)
DIMENSION_WEIGHTS = {
    "person_features_accuracy": 0.35,
    "product_fit_score": 0.25,
    "compliance_talkpoints_completeness": 0.20,
    "pii_latency_compliance": 0.20,
}

# latency budget (ms) per yaml · pii_latency_compliance
LATENCY_TIER1_MS = 5000     # ≤ 5s   → score 1.0
LATENCY_TIER2_MS = 10000    # ≤ 10s  → score 0.7
LATENCY_TIER3_MS = 30000    # ≤ 30s  → score 0.3


# ============================================================
# Adapter
# ============================================================
@register_evaluator("personal_insight")
class Agent1PersonalInsightEvaluator(BaseEvaluator):
    """BE13 POC 4 维度评价 adapter · scaffold 等 BE12 真业务接通.

    NOT 加入 registry._LAZY_MODULES (per PREP-ONLY · 不影响 --all 基线 · 仅显式 import 触发).
    BE12 真业务 ship 后 worker 改 registry._LAZY_MODULES 加 "personal_insight" 启用 --all.
    """

    agent_id = "personal_insight"
    config_name = "agent1_personal_insight.yaml"

    # ------------------------------------------------------------
    # Artifact loading
    # ------------------------------------------------------------
    def _load_oracle(self) -> dict[str, Any] | None:
        """加载 PM 设计的 gold oracle (反 5 原则 #1 盲测 · adapter 不预知).

        预期格式 (BE12 真业务 ship 时由 PM 设计落地):
          {
            "source": "pm-design-be13-poc",
            "generated_at": "...",
            "gold_person_features_by_candidate_id": {"<cid>": {...PersonFeatures...}},
            "difficulty_tier": {"<cid>": "easy|medium|hard|extreme"}  # 反 5 原则 #2 难度分层
          }
        """
        if not ORACLE_PATH.exists():
            return None
        try:
            return json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def load_artifacts(self, run: EvalRun) -> dict[str, Any]:
        if run.artifacts:
            art_path = Path(run.artifacts[0])
            if not art_path.is_absolute():
                art_path = REPO_ROOT / art_path
        elif DEFAULT_RUNTIME.exists():
            art_path = DEFAULT_RUNTIME
        else:
            return {
                "artifact_path": None,
                "error": (
                    f"{PREP_SOURCE} · no runtime dump · BE12 真业务 ship 后 worker 落 "
                    f"{DEFAULT_RUNTIME.relative_to(REPO_ROOT)} 即可"
                ),
                "runs": [],
                "oracle": self._load_oracle(),
            }

        try:
            payload = json.loads(art_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {
                "artifact_path": str(art_path),
                "error": f"load error: {e}",
                "runs": [],
                "oracle": self._load_oracle(),
            }

        return {
            "artifact_path": str(art_path),
            "runs": payload.get("runs") or [],
            "oracle": self._load_oracle() or payload.get("oracle"),
        }

    # ------------------------------------------------------------
    # Common metrics (5)
    # ------------------------------------------------------------
    def compute_common_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        runs: list[dict] = artifacts.get("runs") or []
        art_path = artifacts.get("artifact_path")
        out: list[MetricOutcome] = []

        if not runs:
            for n in ("field_completeness", "evidence_rate", "hallucination_rate",
                     "tool_success_rate", "task_completion_rate"):
                out.append(self._pending(n, "common"))
            return out

        # field_completeness · 7 顶层字段非空占比
        top_keys = ("candidate_id", "person_features", "product_fit",
                    "compliance_check", "talking_points", "pii_redacted", "latency_ms")
        filled_total = 0
        for r in runs:
            payload = r.get("payload") or {}
            filled_total += sum(
                1 for k in top_keys
                if payload.get(k) not in (None, "", [], {})
            )
        out.append(self.mark(
            "field_completeness",
            filled_total / (len(runs) * len(top_keys)),
            method="deterministic",
            evidence=[art_path] if art_path else [],
            note=f"{filled_total}/{len(runs)*len(top_keys)} top-level slot 非空",
            kind="common",
        ))

        # evidence_rate · compliance.sources ≥1 + talking.objection_responses 含证据 占比
        with_ev = 0
        for r in runs:
            p = r.get("payload") or {}
            comp = p.get("compliance_check") or {}
            talk = p.get("talking_points") or {}
            if (comp.get("sources") and len(comp["sources"]) >= 1) or (
                talk.get("objection_responses") and len(talk["objection_responses"]) >= 1
            ):
                with_ev += 1
        out.append(self.mark(
            "evidence_rate",
            with_ev / len(runs),
            method="deterministic",
            evidence=[art_path] if art_path else [],
            note=f"{with_ev}/{len(runs)} 含 compliance.sources 或 talking.objections",
            kind="common",
        ))

        # hallucination_rate · BE12 真业务 ship 后接产品目录 + 合规字典 校验 · scaffold pending
        out.append(self._pending(
            "hallucination_rate", "common",
            "scaffold pending: BE12 真业务 ship 后接产品目录 + 合规标签字典做 unresolvable 判定",
        ))

        # tool_success_rate · llm_calls.success / total
        tc_total = sum((r.get("llm_calls") or {}).get("total", 0) for r in runs)
        tc_success = sum((r.get("llm_calls") or {}).get("success", 0) for r in runs)
        if tc_total > 0:
            out.append(self.mark(
                "tool_success_rate",
                tc_success / tc_total,
                method="deterministic",
                evidence=[art_path] if art_path else [],
                note=f"{tc_success}/{tc_total} shared/llm_caller 调用成功 (含 fallback chain)",
                kind="common",
            ))
        else:
            out.append(self._pending("tool_success_rate", "common"))

        # task_completion_rate · endpoint 200 + schema_valid 占比
        ok = sum(
            1 for r in runs
            if r.get("endpoint_status") == 200 and r.get("schema_valid")
        )
        out.append(self.mark(
            "task_completion_rate",
            ok / len(runs),
            method="deterministic",
            evidence=[art_path] if art_path else [],
            note=f"{ok}/{len(runs)} GET 200 + PersonalInsightPayload schema valid",
            kind="common",
        ))
        return out

    # ------------------------------------------------------------
    # Domain metrics (4 weighted dimensions)
    # ------------------------------------------------------------
    def compute_domain_metrics(self, artifacts: dict[str, Any]) -> list[MetricOutcome]:
        runs: list[dict] = artifacts.get("runs") or []
        oracle: dict | None = artifacts.get("oracle")
        art_path = artifacts.get("artifact_path")
        out: list[MetricOutcome] = []

        if not runs:
            for n in DIMENSION_WEIGHTS:
                out.append(self._pending(n, "domain"))
            return out

        out.append(self._dim_person_features(runs, oracle, art_path))
        out.append(self._dim_product_fit(runs, art_path))
        out.append(self._dim_compliance_talkpoints(runs, art_path))
        out.append(self._dim_pii_latency(runs, art_path))
        return out

    # ------------------------------------------------------------
    # 维度 1 · person_features_accuracy (35%)
    # ------------------------------------------------------------
    def _dim_person_features(
        self, runs: list[dict], oracle: dict | None, art_path: str | None,
    ) -> MetricOutcome:
        """组合分: filled_ratio * 0.7 + oracle_match * 0.3 (oracle 缺失时 score = filled_ratio)."""
        filled_ratios: list[float] = []
        oracle_matches: list[float] = []
        gold_map = (oracle or {}).get("gold_person_features_by_candidate_id") or {}

        for r in runs:
            pf = (r.get("payload") or {}).get("person_features") or {}
            cid = (r.get("payload") or {}).get("candidate_id")

            filled_count = sum(
                1 for k in PERSON_FEATURES_KEYS
                if pf.get(k) not in (None, "", 0, STUB_PLACEHOLDER)
            )
            filled_ratios.append(filled_count / len(PERSON_FEATURES_KEYS))

            if cid and cid in gold_map:
                gold = gold_map[cid]
                match_count = sum(
                    1 for k in PERSON_FEATURES_KEYS
                    if pf.get(k) is not None and gold.get(k) is not None
                    and str(pf.get(k)).strip() == str(gold.get(k)).strip()
                )
                oracle_matches.append(match_count / len(PERSON_FEATURES_KEYS))

        avg_filled = sum(filled_ratios) / len(filled_ratios) if filled_ratios else 0.0

        if oracle_matches:
            avg_oracle = sum(oracle_matches) / len(oracle_matches)
            score = avg_filled * 0.7 + avg_oracle * 0.3
            note = (
                f"filled_ratio={avg_filled:.4f}*0.7 + oracle_match={avg_oracle:.4f}*0.3 "
                f"= {score:.4f} · {len(oracle_matches)}/{len(runs)} cid 含 gold"
            )
        else:
            score = avg_filled
            note = (
                f"filled_ratio={avg_filled:.4f} (oracle 未到位 · 仅算 deterministic 70% 部分 ·"
                f" BE12 真业务 ship + PM 落 oracle 后启用 30% oracle_match)"
            )

        return self.mark(
            "person_features_accuracy",
            score,
            method="deterministic",
            evidence=[art_path] if art_path else [],
            note=note,
        )

    # ------------------------------------------------------------
    # 维度 2 · product_fit_score (25%)
    # ------------------------------------------------------------
    def _dim_product_fit(
        self, runs: list[dict], art_path: str | None,
    ) -> MetricOutcome:
        """组合分: normalized_fit * 0.6 + has_recommend * 0.2 + has_reason * 0.2."""
        scores: list[float] = []
        for r in runs:
            pf = (r.get("payload") or {}).get("product_fit") or {}
            fit_score = pf.get("fit_score", 0)
            try:
                normalized_fit = max(0.0, min(1.0, float(fit_score) / 100.0))
            except (TypeError, ValueError):
                normalized_fit = 0.0
            has_recommend = 1.0 if len(pf.get("recommended_products") or []) >= 1 else 0.0
            has_reason = 1.0 if len(pf.get("fit_reasons") or []) >= 1 else 0.0
            score = normalized_fit * 0.6 + has_recommend * 0.2 + has_reason * 0.2
            scores.append(score)

        avg = sum(scores) / len(scores) if scores else 0.0
        return self.mark(
            "product_fit_score",
            avg,
            method="deterministic",
            evidence=[art_path] if art_path else [],
            note=(
                f"avg(normalized_fit*0.6 + has_recommend*0.2 + has_reason*0.2) over "
                f"{len(scores)} runs = {avg:.4f}"
            ),
        )

    # ------------------------------------------------------------
    # 维度 3 · compliance_talkpoints_completeness (20%)
    # ------------------------------------------------------------
    def _dim_compliance_talkpoints(
        self, runs: list[dict], art_path: str | None,
    ) -> MetricOutcome:
        """组合分: compliance(0.40 总) + talking(0.50 总) · 缓冲 0.10."""
        scores: list[float] = []
        for r in runs:
            p = r.get("payload") or {}
            comp = p.get("compliance_check") or {}
            talk = p.get("talking_points") or {}

            # compliance 子项 (0.40 总)
            aml_known = 0.15 if comp.get("aml_risk") not in (None, "", "未知") else 0.0
            sources_ge1 = 0.15 if len(comp.get("sources") or []) >= 1 else 0.0
            last_checked_set = 0.10 if comp.get("last_checked") else 0.0

            # talking 子项 (0.50 总)
            opener = talk.get("opener") or ""
            closing = talk.get("closing") or ""
            opener_set = 0.10 if opener else 0.0
            closing_set = 0.10 if closing else 0.0
            key_msg_ge1 = 0.10 if len(talk.get("key_messages") or []) >= 1 else 0.0
            obj_ge1 = 0.10 if len(talk.get("objection_responses") or []) >= 1 else 0.0
            opener_no_ph = 0.10 if (opener and STUB_PLACEHOLDER not in opener) else 0.0

            score = (
                aml_known + sources_ge1 + last_checked_set
                + opener_set + closing_set + key_msg_ge1 + obj_ge1 + opener_no_ph
            )
            scores.append(score)

        avg = sum(scores) / len(scores) if scores else 0.0
        return self.mark(
            "compliance_talkpoints_completeness",
            avg,
            method="deterministic",
            evidence=[art_path] if art_path else [],
            note=(
                f"avg(compliance 0.40 总 + talking 0.50 总) over {len(scores)} runs "
                f"= {avg:.4f}  (满分 0.90 + 缓冲 0.10)"
            ),
        )

    # ------------------------------------------------------------
    # 维度 4 · pii_latency_compliance (20%)
    # ------------------------------------------------------------
    def _dim_pii_latency(
        self, runs: list[dict], art_path: str | None,
    ) -> MetricOutcome:
        """组合分: pii_gate * (0.5 + latency_score * 0.5) · PII 必通 · latency 软分."""
        scores: list[float] = []
        pii_fail_count = 0
        for r in runs:
            p = r.get("payload") or {}
            pii_redacted = bool(p.get("pii_redacted"))
            if not pii_redacted:
                pii_fail_count += 1
                scores.append(0.0)
                continue

            latency = p.get("latency_ms", 0)
            try:
                latency_ms = float(latency)
            except (TypeError, ValueError):
                latency_ms = float("inf")

            if latency_ms <= LATENCY_TIER1_MS:
                latency_score = 1.0
            elif latency_ms <= LATENCY_TIER2_MS:
                latency_score = 0.7
            elif latency_ms <= LATENCY_TIER3_MS:
                latency_score = 0.3
            else:
                latency_score = 0.0

            scores.append(0.5 + latency_score * 0.5)  # PII 通过保底 0.5 + latency 软分 0.5

        avg = sum(scores) / len(scores) if scores else 0.0
        note = (
            f"avg(pii_gate * (0.5 + latency_score*0.5)) over {len(scores)} runs = {avg:.4f} · "
            f"pii_fail={pii_fail_count}/{len(scores)} (任何 pii_redacted=False 直接 0)"
        )
        return self.mark(
            "pii_latency_compliance",
            avg,
            method="deterministic",
            evidence=[art_path] if art_path else [],
            note=note,
        )

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _pending(self, name: str, kind: str, custom_note: str | None = None) -> MetricOutcome:
        return MetricOutcome(
            name=name,
            value=None,
            target=self._lookup_target(name, kind) or "n/a",
            passed=None,
            method="manual",
            note=custom_note or (
                f"{PREP_SOURCE} · scaffold pending: BE12 真业务 ship + runtime dump 到位后启用"
            ),
        )


# ============================================================
# 4 维加权综合分 helper (POC verdict 用 · 不在 BaseEvaluator 框架内)
# ============================================================
def compute_weighted_poc_verdict(
    metrics: list[MetricOutcome],
) -> dict[str, Any]:
    """根据 4 维度 metric.value 计算加权综合分 (per yaml POC-4-DIMS).

    Returns:
        {
            "weighted_score": float | None,
            "verdict": "PASS" | "PARTIAL" | "FAIL" | "PENDING",
            "per_dim": {"<dim_name>": {"value": ..., "weight": ..., "contribution": ...}},
            "missing_dims": [...]
        }

    BE12 真业务 ship 前 · 任何 dim value=None → verdict=PENDING (不误导基线).
    """
    by_name = {m.name: m for m in metrics if m.name in DIMENSION_WEIGHTS}
    per_dim = {}
    missing = []
    weighted_total = 0.0
    weight_covered = 0.0

    for dim_name, weight in DIMENSION_WEIGHTS.items():
        m = by_name.get(dim_name)
        if m is None or m.value is None:
            missing.append(dim_name)
            per_dim[dim_name] = {"value": None, "weight": weight, "contribution": None}
            continue
        contribution = m.value * weight
        per_dim[dim_name] = {
            "value": round(m.value, 4),
            "weight": weight,
            "contribution": round(contribution, 4),
        }
        weighted_total += contribution
        weight_covered += weight

    if missing:
        return {
            "weighted_score": None,
            "verdict": "PENDING",
            "per_dim": per_dim,
            "missing_dims": missing,
            "note": (
                f"{PREP_SOURCE} · {len(missing)}/4 维度 SKIP · "
                f"BE12 真业务 ship + artifact runtime dump 到位后跑首轮"
            ),
        }

    return {
        "weighted_score": round(weighted_total, 4),
        "verdict": "PASS" if weighted_total >= 0.85 else (
            "PARTIAL" if weighted_total >= 0.70 else "FAIL"
        ),
        "per_dim": per_dim,
        "missing_dims": [],
        "note": "all 4 dims computed · weighted by 35/25/20/20",
    }
