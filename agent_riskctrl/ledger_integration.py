# -*- coding: utf-8 -*-
"""agent_riskctrl.ledger_integration — DSL 部署决策上链 (BE7 集成).

CLAUDE.md §3.7.5 跨 Agent decision ledger defaults:
  - jurisdiction default = 'HQ'
  - agent_id = 'riskctrl' · retention = 'standard' (5y · 银保监 archive)
  - DSL deploy 决策必上链 · 风险经理签字 + 审计可回溯

设计:
  - silent-fail: ledger 写入失败不破 deploy 流程 (per §3.7.5 失败隔离)
  - evidence_chain 含: backtest_summary + ks_improvement + rule_count +
    champion_challenger 推荐 (供审计员回到原始证据)
  - subject_id_hashed 用 ruleset_id (DSL 是策略级决策 · 不是客户级)

Public surface:
  - ``record_dsl_deploy(...)`` 上链 helper
  - ``record_rubric_sync(...)`` 同步 rubric 决策上链
  - ``record_backtest_decision(...)`` 单次回测决策上链
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_dsl_deploy(
    *,
    ruleset_id: str,
    dsl_version: str,
    rule_count: int,
    affected_segments: list[str],
    backtest_summary: dict,
    approver_user_id: str | None = None,
    deploy_endpoint: str = "/api/riskctrl/dsl_deploy",
    ledger=None,  # type: ignore[no-untyped-def]
) -> str:
    """DSL 部署决策上链 (per CLAUDE.md §3.7.5).

    决策含义: 风险经理签字 · DSL ruleset 上线 · 触发 Agent4 全量重扫 +
    Agent3 rubric 同步.

    Args:
        ruleset_id: 策略 ID
        dsl_version: 部署版本号 (e.g. v1.2.0)
        rule_count: 规则条数
        affected_segments: 影响 segment list
        backtest_summary: 回测元信息 (KS / pass_rate / bad_rate / profit / KS_improvement)
        approver_user_id: 签字人 (None 时上链不带 reviewer)
        deploy_endpoint: 决策对应 endpoint
        ledger: 测试可注入 · None=用 default_ledger

    Returns:
        decision_id (即使写失败也返回 · silent-fail per §3.7.5)
    """
    try:
        from shared.decision_ledger import record_decision
    except ImportError as e:
        logger.warning("decision_ledger import failed: %s · skip on-chain", e)
        return f"riskctrl-dsl-{dsl_version}-import-failed"

    input_payload = {
        "ruleset_id": ruleset_id,
        "dsl_version": dsl_version,
        "rule_count": rule_count,
        "affected_segments": affected_segments,
    }
    output_payload = {
        "intent_type": "dsl_deployed",
        "deploy_endpoint": deploy_endpoint,
        "trigger_alert_rebuild": True,
        "trigger_credit_rubric_sync": True,
    }
    evidence_chain = {
        "source_module": "agent_riskctrl/ledger_integration.py",
        "decision_class": "dsl_deploy",
        "backtest_summary": backtest_summary,
        "champion_challenger_used": True,
        "approver_role": "risk_manager",
        "approver_user_id": approver_user_id or "<not_signed>",
    }

    try:
        # subject_id 用 ruleset_id (策略级决策)
        decision_id = record_decision(
            agent_id="riskctrl",
            endpoint=deploy_endpoint,
            input_payload=input_payload,
            output_payload=output_payload,
            evidence_chain=evidence_chain,
            jurisdiction=None,        # → resolve_jurisdiction default HQ
            retention_class=None,     # → 走 §3.7.5 riskctrl=standard 5y
            subject_name=f"DSL ruleset {ruleset_id} v{dsl_version}",
            subject_id=ruleset_id,    # store.py 内部会 hash · 但 ruleset_id 非 PII
            ledger=ledger,
        )
        logger.info(
            "dsl_deploy on-chain · decision_id=%s ruleset=%s version=%s",
            decision_id, ruleset_id, dsl_version,
        )
        return decision_id
    except (RuntimeError, ValueError, OSError, Exception) as e:  # noqa: BLE001
        logger.warning(
            "ledger record_decision failed (silent-fail per §3.7.5): %s", e,
        )
        return f"riskctrl-dsl-{dsl_version}-write-failed"


def record_rubric_sync(
    *,
    dsl_version_old: str,
    dsl_version_new: str,
    rubric_diff: dict,
    affected_segments: list[str],
    ledger=None,  # type: ignore[no-untyped-def]
) -> str:
    """Rubric 同步决策上链 (Agent3 ack 路径)."""
    try:
        from shared.decision_ledger import record_decision
    except ImportError as e:
        logger.warning("decision_ledger import failed: %s", e)
        return f"riskctrl-rubric-{dsl_version_new}-import-failed"

    input_payload = {
        "dsl_version_old": dsl_version_old,
        "dsl_version_new": dsl_version_new,
        "affected_segments": affected_segments,
    }
    output_payload = {
        "intent_type": "dsl_versioned",
        "rubric_diff_size": {
            "added": len(rubric_diff.get("added", [])),
            "modified": len(rubric_diff.get("modified", [])),
            "removed": len(rubric_diff.get("removed", [])),
        },
    }
    evidence_chain = {
        "source_module": "agent_riskctrl/ledger_integration.py",
        "decision_class": "rubric_sync",
        "rubric_diff": rubric_diff,
    }

    try:
        return record_decision(
            agent_id="riskctrl",
            endpoint="/api/credit/rubric_sync",
            input_payload=input_payload,
            output_payload=output_payload,
            evidence_chain=evidence_chain,
            subject_name=f"rubric sync {dsl_version_old} → {dsl_version_new}",
            ledger=ledger,
        )
    except (RuntimeError, ValueError, OSError, Exception) as e:  # noqa: BLE001
        logger.warning("rubric_sync on-chain failed: %s", e)
        return f"riskctrl-rubric-{dsl_version_new}-write-failed"


def record_backtest_decision(
    *,
    ruleset_id: str,
    csv_path: str,
    metrics: dict,
    business_metrics: dict | None = None,
    ledger=None,  # type: ignore[no-untyped-def]
) -> str:
    """单次回测决策上链 · 给审计员回看 KS/通过率/坏账率.

    单次 backtest 严格说不算"决策"(没签字) · 但银保监审计要求每次跑过的
    回测可追溯 · 因此也上链 (retention=short 90 days · §3.7.5 alert 同档)
    """
    try:
        from shared.decision_ledger import record_decision
    except ImportError as e:
        logger.warning("decision_ledger import failed: %s", e)
        return f"riskctrl-bt-{ruleset_id}-import-failed"

    input_payload = {
        "ruleset_id": ruleset_id,
        "csv_path": csv_path,
    }
    evidence_chain = {
        "source_module": "agent_riskctrl/ledger_integration.py",
        "decision_class": "backtest_run",
        "metrics": metrics,
        "business_metrics": business_metrics or {},
    }

    try:
        return record_decision(
            agent_id="riskctrl",
            endpoint="/api/riskctrl/backtest",
            input_payload=input_payload,
            output_payload={"intent_type": "backtest_done"},
            evidence_chain=evidence_chain,
            retention_class="short",  # 单次回测 90 天足够 · 不是签字决策
            subject_name=f"backtest run for ruleset {ruleset_id}",
            ledger=ledger,
        )
    except (RuntimeError, ValueError, OSError, Exception) as e:  # noqa: BLE001
        logger.warning("backtest decision on-chain failed: %s", e)
        return f"riskctrl-bt-{ruleset_id}-write-failed"


__all__ = [
    "record_backtest_decision",
    "record_dsl_deploy",
    "record_rubric_sync",
]
