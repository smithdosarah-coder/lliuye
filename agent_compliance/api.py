# -*- coding: utf-8 -*-
"""agent_compliance.api — Agent5 合规雷达 FastAPI 路由模块。

端点：
  POST /api/compliance/policy_scan   — 政策事件触发巡检 (Stage C.4 · onboarding W-C3-A3)
                                       SSE · body {policy_doc, business_docs}
                                       4 阶段: 抽规则 → 抽事件 → N×M 矩阵 → 改/补/强 修订
  POST /api/compliance/matrix_check  — 同步 N×M 矩阵比对 (rules × events)
  POST /api/compliance/export_docx   — body {scan_id} · 修订意见书 .docx (改/补/强)
  GET  /api/compliance/scan          — 取持久化扫描结果 (latest 或 by scan_id)
  GET  /api/compliance/health        — 健康探针

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- POST /policy_scan 业务逻辑走 agent_compliance.scan_engine.run_policy_scan_and_persist
  (KB_DEMO 解锁 · Tavily 401 fallback · Q-040)
- 输出前过 shared.qc.placeholder_guard

empty-state 协议 (docs/contracts/empty-state-design-protocol.md):
- 所有 endpoint 均**用户主动触发** · 不自动加载 mock data
- mock 路径走 force_mock=True 显式 flag · 与 production 路径分离
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_service.dependencies import require_action  # noqa: E402
from shared.api_utils import sse_encode, to_jsonable  # noqa: E402
from shared.qc import mark_unfilled, scan as scan_placeholders  # noqa: E402
from shared.sse_envelope import (  # noqa: E402
    DATA_SOURCE_LIVE,
    DATA_SOURCE_MOCK_FALLBACK,
    DATA_SOURCE_MOCK_FORCED,
    encode_event,
    make_done,
    make_error,
    make_error_from_exception,
    make_stage,
)

# Stage E.1 · audit log decorator (silent fail if audit_service unavailable)
try:
    from audit_service.decorators import audit_llm_call  # noqa: E402
except ImportError:
    def audit_llm_call(**_kwargs):  # type: ignore[no-redef]
        def _passthrough(fn):
            return fn
        return _passthrough

app = FastAPI(title="Agent5 Compliance Radar API", version="3.2")


# ---------------------------------------------------------------------------
# QC scrub helpers
# ---------------------------------------------------------------------------


def _qc_scrub_dict(payload: dict) -> tuple[dict, list[str]]:
    """递归 scrub dict · 命中占位符替换为「未能自动填写」."""
    hits: list[str] = []

    def walk(v):
        if isinstance(v, str):
            local = scan_placeholders(v)
            if local:
                hits.extend(h.kind for h in local)
                return mark_unfilled(v)
            return v
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v

    return walk(payload), hits


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/compliance/health")
async def compliance_health():
    return {"status": "ok", "agent": "agent_compliance"}


# ---------------------------------------------------------------------------
# POST /api/compliance/policy_scan — 政策事件触发巡检 SSE (Stage C.4)
# ---------------------------------------------------------------------------


class CompliancePolicyScanRequest(BaseModel):
    policy_doc: str                  # 监管政策原文 (text)
    business_docs: list = []         # 业务记录 list[str|dict]
    policy_meta: dict | None = None  # 可选 metadata (title / source_url / fetched_at)
    force_mock: bool = False         # 强制走 mock 政策库 · 不尝试 Tavily


class CompliancePolicyDiffRequest(BaseModel):
    """policy_diff 请求 schema · 比对两份政策版本差异 (V2-issue-3 endpoint contract).

    Phase B Sprint 3 contract sub-PR 1 (2026-05-05):
    - endpoint signature + Pydantic schema + SSE response stub
    - 业务逻辑 deferred to sub-PR 2 implementation (per Q-052 atomic 跨前后端)
    """

    old_policy: str                  # 旧政策全文 (markdown / plain text)
    new_policy: str                  # 新政策全文 (markdown / plain text)
    scope: str | None = None         # 可选 · 业务范围限定 (e.g. "对公授信")


def _aggregate_recommendations(violations: list[dict]) -> list[dict]:
    """汇总 violations 各自 revisions 为 flat list · 前端 RevisionPanel 消费.

    每条 revision 加 violation_id 反向引用 · 让前端可按 violation 过滤.
    """
    out: list[dict] = []
    for v in violations or []:
        vid = v.get("violation_id", "")
        for rev in v.get("revisions", []) or []:
            if not isinstance(rev, dict):
                continue
            out.append({
                "violation_id": vid,
                "category": rev.get("category", ""),
                "title": rev.get("title", ""),
                "text": rev.get("text", ""),
            })
    return out


def _build_compliance_done_envelope(
    *,
    scan_id: str,
    payload: dict,
    duration_seconds: float,
) -> dict:
    """从 persisted scan payload 构 done envelope (per agent-compli-spec §5.3 · A4 worker).

    panels 走 AGENT_PANEL_KEYS_RECOMMENDED["compliance"] 4 keys + 顶层 extras
    (rules_preview / events_preview / policy_meta / data_source).
    """
    stats = payload.get("stats", {}) or {}
    violations = payload.get("violations", []) or []
    rules = payload.get("rules", []) or []
    events = payload.get("events", []) or []
    matrix = payload.get("matrix", []) or []
    mode_label = str(payload.get("mode", ""))

    # mode_label → data_source · web_live 主路径 · 其他都视作 fallback
    if mode_label == "web_live":
        data_source = DATA_SOURCE_LIVE
    elif mode_label == "demo_forced":
        data_source = DATA_SOURCE_MOCK_FORCED
    else:
        data_source = DATA_SOURCE_MOCK_FALLBACK

    return make_done(
        panels={
            "violations": violations,
            "matrix": matrix,
            "events": events,
            "recommendations": _aggregate_recommendations(violations),
        },
        metrics={
            "rule_count": payload.get("rule_count", len(rules)),
            "event_count": payload.get("event_count", len(events)),
            "cell_count": payload.get("cell_count", len(rules) * len(events)),
            "severe": stats.get("severe_count", 0),
            "normal": stats.get("normal_count", 0),
            "observation": stats.get("observation_count", 0),
            "violation_count": stats.get("violation_count", len(violations)),
            "duration_seconds": round(duration_seconds, 2),
        },
        data_source=data_source,
        session_id=scan_id,
        rules_preview=rules[:5],
        events_preview=events[:5],
        policy_meta=payload.get("policy_meta", {}) or {},
        mode_label=mode_label,
    )


def _record_compliance_to_ledger(
    *,
    scan_id: str,
    full_payload: dict,
    endpoint: str,
    input_summary: dict,
) -> dict:
    """Phase B.2 step 10 · ledger 上链 (per CLAUDE.md §3.7.5 + decision-ledger.md v1.0).

    compliance retention default = standard (5y · 银保监 archive)
    jurisdiction = HQ (env LIUYE_LEDGER_JURISDICTION 可覆盖)
    subject_id = policy doc_no (e.g. 金监总规〔2026〕第 9 号) · ledger.record() 内部 hash 自动

    silent-fail · ledger 是观察层不是阻塞层 · 写失败不破 SSE done envelope.
    """
    try:
        from shared.decision_ledger import default_ledger
    except ImportError as e:
        return {"persisted": False, "decision_id": "", "error": f"import: {e}"}

    policy_meta = full_payload.get("policy_meta") or {}
    violations = full_payload.get("violations") or []
    stats = full_payload.get("stats") or {}

    # subject_id: 政策文号 (有则用 doc_no · 否则用 title) · ledger 内部 hash
    subject_id = (
        str(policy_meta.get("doc_no") or "").strip()
        or str(policy_meta.get("policy_id") or "").strip()
        or str(policy_meta.get("title") or "").strip()
        or scan_id
    )
    subject_name = str(policy_meta.get("title") or "policy_scan").strip() or "policy_scan"

    # evidence_chain: 每条 violation 的 rule_id + event_id + clause_text_hash + reason 全 8 字段
    evidence_chain: list[dict] = []
    for v in violations:
        reason = v.get("reason") or {}
        evidence_chain.append({
            "violation_id": str(v.get("id") or v.get("violation_id") or ""),
            "rule_id": str(v.get("rule_id") or ""),
            "rule_article": str(v.get("rule_article") or ""),
            "event_id": str(v.get("event_id") or ""),
            "severity": str(v.get("severity") or ""),
            "evidence": str(v.get("evidence") or ""),
            "match_reason": str(v.get("match_reason") or ""),
            # ViolationReason 8 字段 (red line #8 · 监管原文 hash 必带)
            "clause_id": str(reason.get("clause_id") or ""),
            "clause_text_hash": str(reason.get("clause_text_hash") or ""),
            "policy_id": str(reason.get("policy_id") or ""),
            "policy_version": str(reason.get("policy_version") or ""),
            "evidence_date": str(reason.get("evidence_date") or ""),
            "freshness_days": reason.get("freshness_days"),
            "staleness_passed": reason.get("staleness_passed"),
        })

    output_payload = {
        "scan_id": scan_id,
        "mode": full_payload.get("mode"),
        "stats": stats,
        "violation_count": len(violations),
        "rule_count": full_payload.get("rule_count"),
        "event_count": full_payload.get("event_count"),
    }

    try:
        ledger_result = default_ledger().record(
            agent_id="compliance",
            endpoint=endpoint,
            input_payload=input_summary,
            output_payload=output_payload,
            evidence_chain=evidence_chain,
            subject_name=subject_name,
            subject_id=subject_id,
        )
        return {
            "decision_id": ledger_result.decision_id,
            "persisted": ledger_result.persisted,
            "error": ledger_result.error,
        }
    except (RuntimeError, ValueError, TypeError, OSError,
            AttributeError, KeyError, ImportError) as exc:
        return {
            "persisted": False,
            "decision_id": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _run_scan_engine_stream(
    *,
    policy_doc: str,
    business_docs: list,
    policy_meta: dict | None,
    force_mock: bool,
    extras: dict | None = None,
    endpoint: str = "/api/compliance/policy_scan",
):
    """共享的 engine SSE driver · /policy_scan + /demo/run 都走这里 (Phase B.2 真意 reframe).

    extras: 顶层 done envelope 加附加字段 (e.g. scenario_id / input_source / business_doc_sources).
    endpoint: ledger 上链时写入 endpoint 字段 (per §3.7.5 audit · 区分 demo vs 真上传).
    """
    try:
        from agent_compliance.scan_engine import (
            ScanResultNotFoundError,
            load_scan_result,
            run_policy_scan_and_persist,
        )
    except ImportError as e:
        yield encode_event(make_error(f"scan_engine import failed: {e}", code="SCAN_IMPORT_FAIL"))
        return

    import time as _time
    t_start = _time.time()
    last_scan_id: str = ""

    try:
        for evt in run_policy_scan_and_persist(
            policy_doc=policy_doc or "",
            business_docs=business_docs or [],
            policy_meta=policy_meta,
            force_mock=bool(force_mock),
        ):
            payload = to_jsonable(evt)
            cleaned, hits = _qc_scrub_dict(payload)
            # 截获 scan event · 不 forward · 留到 done envelope 拼
            if isinstance(cleaned, dict) and cleaned.get("type") == "scan":
                last_scan_id = str(cleaned.get("scan_id") or "")
                continue
            wrap = {"event": "stage", "payload": cleaned}
            if hits:
                wrap["_qc_placeholder_hits"] = hits
            yield sse_encode(wrap)

        # done envelope · 拉 persisted payload 拼共形 envelope
        if last_scan_id:
            try:
                full_payload = load_scan_result(scan_id=last_scan_id)
            except ScanResultNotFoundError as e:
                yield encode_event(make_error(
                    f"scan_id={last_scan_id} 持久化丢失: {e}",
                    code="SCAN_PERSIST_LOST",
                ))
                return

            # Phase B.2 step 10 · ledger 上链 (silent-fail · 观察层不阻塞)
            input_summary = {
                "policy_meta": policy_meta or {},
                "business_doc_count": len(business_docs or []),
                "force_mock": bool(force_mock),
                **(extras or {}),
            }
            ledger_outcome = _record_compliance_to_ledger(
                scan_id=last_scan_id,
                full_payload=full_payload,
                endpoint=endpoint,
                input_summary=input_summary,
            )
            yield encode_event(make_stage(
                "ledger_persist",
                "done" if ledger_outcome.get("persisted") else "warn",
                message=(
                    f"decision_id={ledger_outcome.get('decision_id')}"
                    if ledger_outcome.get("persisted")
                    else f"ledger 写入跳过: {ledger_outcome.get('error') or 'unknown'}"
                ),
            ))

            done_evt = _build_compliance_done_envelope(
                scan_id=last_scan_id,
                payload=full_payload,
                duration_seconds=_time.time() - t_start,
            )
            if extras:
                # extras 顶层 (per sse-envelope · done envelope 顶层 extras 自由扩展)
                for k, v in extras.items():
                    if k not in done_evt:
                        done_evt[k] = v
            # ledger meta 顶层 (审计可追溯 · 前端可显徽章)
            done_evt["ledger"] = {
                "decision_id": ledger_outcome.get("decision_id", ""),
                "persisted": bool(ledger_outcome.get("persisted")),
                "error": ledger_outcome.get("error") or None,
            }
            yield encode_event(done_evt)
        else:
            yield encode_event(make_error(
                "scan event 未发出 · run_policy_scan_and_persist 未持久化",
                code="SCAN_PERSIST_MISSING",
            ))
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        traceback.print_exc()
        yield encode_event(make_error_from_exception(e, code="SCAN_RUNTIME_ERROR"))


def _policy_scan_event_stream(req: CompliancePolicyScanRequest):
    """thin wrapper · /policy_scan 走真上传 · 不带 sample_batch extras."""
    yield from _run_scan_engine_stream(
        policy_doc=req.policy_doc or "",
        business_docs=req.business_docs or [],
        policy_meta=req.policy_meta,
        force_mock=bool(req.force_mock),
        extras={"input_source": "user_upload"},
        endpoint="/api/compliance/policy_scan",
    )


# ---------------------------------------------------------------------------
# POST /api/compliance/policy_diff — V2-issue-3 endpoint contract (B5 sub-PR 1)
#
# Phase B Sprint 3 contract sub-PR 1 · 2026-05-05
# - endpoint signature + Pydantic request schema + SSE response stub
# - 业务逻辑 deferred to sub-PR 2 implementation (per Q-052 atomic 跨前后端)
# - Depends(require_action("compliance", "invoke")) sub-PR 2 wire
# ---------------------------------------------------------------------------


def _index_rules_by_article(rules: list[dict]) -> dict[str, dict]:
    """以 article (e.g. '第十二条') 为 key index rules · 同 article 多 rule 合并 condition.

    article 缺失时退回 rule_id · 仍保证 stable key.
    """
    out: dict[str, dict] = {}
    for r in rules:
        key = (r.get("article") or "").strip() or r.get("rule_id", "")
        if not key:
            continue
        if key in out:
            # 合并 (同 article 多条 rule) · 取首条为代表 · 后续 condition merge
            existing = out[key]
            existing["condition"] = (
                existing.get("condition", "") + " | " + r.get("condition", "")
            ).strip(" |")
        else:
            out[key] = dict(r)  # shallow copy 防 mutate 原 list
    return out


def _rule_signature(rule: dict) -> tuple:
    """rule 关键字段签名 · 用于 detect modification (条件/阈值/类别/severity 任一变即 modified)."""
    return (
        (rule.get("condition") or "").strip(),
        tuple(sorted((rule.get("threshold") or {}).items())) if isinstance(rule.get("threshold"), dict) else (),
        (rule.get("category") or "").strip(),
        (rule.get("severity_hint") or "").strip().lower(),
    )


def _compute_policy_diff(old_rules: list[dict], new_rules: list[dict]) -> dict:
    """比对新旧两版规则 · 输出 added/removed/modified 三段 + summary.

    Algorithm:
      1. index by article (natural key in policy doc)
      2. set diff: added = new minus old · removed = old minus new
      3. modified: 同 article · signature 不等
    """
    old_idx = _index_rules_by_article(old_rules)
    new_idx = _index_rules_by_article(new_rules)

    added: list[dict] = [new_idx[k] for k in new_idx if k not in old_idx]
    removed: list[dict] = [old_idx[k] for k in old_idx if k not in new_idx]
    modified: list[dict] = []
    for k in sorted(set(old_idx) & set(new_idx)):
        if _rule_signature(old_idx[k]) != _rule_signature(new_idx[k]):
            modified.append({
                "article": k,
                "old": old_idx[k],
                "new": new_idx[k],
            })

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "summary": {
            "old_rule_count": len(old_rules),
            "new_rule_count": len(new_rules),
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "total_change_count": len(added) + len(removed) + len(modified),
        },
    }


def _policy_diff_event_stream(req: CompliancePolicyDiffRequest):
    """SSE event stream · 真业务 (B5 sub-PR 2 implementation · 2026-05-05).

    走 scan_engine.extract_rules_from_policy_text (LLM 优先 · 无 key fallback 启发式)
    → diff index by article → SSE stream stage events + done envelope.

    SSE shape (per sse-envelope §3 · stable for frontend integration):
      event: stage   {stage: "extract_old"  | "extract_new" | "diff", status, message, progress}
      event: done    {payload: {diffs, summary, old_policy_length, new_policy_length, scope}}
      event: error   {message, code}
    """
    try:
        from agent_compliance.scan_engine import (
            build_llm_json_caller,
            extract_rules_from_policy_text,
        )
    except ImportError as e:
        yield encode_event(make_error(f"scan_engine import failed: {e}", code="SCAN_IMPORT_FAIL"))
        return

    try:
        # LLM 优先 · 无 key 时 build_llm_json_caller 返 None · extract 自动 fallback 启发式
        llm_json = build_llm_json_caller()

        # Stage 1: extract_old
        yield encode_event(make_stage(
            stage="extract_old", status="running",
            message="抽取旧政策规则...", progress=0.0,
        ))
        old_rules = extract_rules_from_policy_text(req.old_policy or "", llm_json_caller=llm_json)
        yield encode_event(make_stage(
            stage="extract_old", status="done",
            message=f"抽取 {len(old_rules)} 条旧规则", progress=0.33,
        ))

        # Stage 2: extract_new
        yield encode_event(make_stage(
            stage="extract_new", status="running",
            message="抽取新政策规则...", progress=0.33,
        ))
        new_rules = extract_rules_from_policy_text(req.new_policy or "", llm_json_caller=llm_json)
        yield encode_event(make_stage(
            stage="extract_new", status="done",
            message=f"抽取 {len(new_rules)} 条新规则", progress=0.66,
        ))

        # Stage 3: diff (按 article 比对)
        yield encode_event(make_stage(
            stage="diff", status="running",
            message="按条款 article 比对差异...", progress=0.66,
        ))
        diff_result = _compute_policy_diff(old_rules, new_rules)
        yield encode_event(make_stage(
            stage="diff", status="done",
            message=f"diff 完毕 · 共 {diff_result['summary']['total_change_count']} 处变更",
            progress=1.0,
        ))

        # Done envelope (payload 含 diffs + summary + lengths + scope · backward compat 字段保留)
        done_payload = {
            "diffs": {
                "added": diff_result["added"],
                "removed": diff_result["removed"],
                "modified": diff_result["modified"],
            },
            "summary": diff_result["summary"],
            "old_policy_length": len(req.old_policy or ""),
            "new_policy_length": len(req.new_policy or ""),
            "scope": req.scope,
        }
        cleaned, hits = _qc_scrub_dict(done_payload)
        if hits:
            cleaned["_qc_placeholder_hits"] = hits
        yield encode_event(make_done(
            payload=cleaned,
            data_source=DATA_SOURCE_LIVE,
        ))

    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        traceback.print_exc()
        yield encode_event(make_error_from_exception(e, code="POLICY_DIFF_RUNTIME_ERROR"))


@app.post("/api/compliance/policy_diff")
async def compliance_policy_diff_post(
    req: CompliancePolicyDiffRequest,
    _user: dict = Depends(require_action("compliance", "invoke")),
):
    """POST /api/compliance/policy_diff — 比对两份政策版本差异 (V2-issue-3 · B5 sub-PR 2 真业务).

    sub-PR 1 (45b9ace + 8a01c6d): endpoint signature + Pydantic schema + SSE stub
    sub-PR 2 (此): 接 scan_engine.extract_rules_from_policy_text + require_action enforcement
                   + endpoint test (含 401/403)

    Auth (per Q-052 #8 row-level/action gate):
      - compliance_officer/admin → 200 (有 invoke action)
      - rm/credit_officer/risk_manager → 403 ACCESS_DENIED (无 compliance.invoke action)
      - 无 cookie → 401 AUTH_MISSING
    """
    if not (req.old_policy or "").strip():
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "old_policy 不能为空",
                              "details": {"field": "old_policy"}}},
        )
    if not (req.new_policy or "").strip():
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "new_policy 不能为空",
                              "details": {"field": "new_policy"}}},
        )

    return StreamingResponse(
        _policy_diff_event_stream(req),
        media_type="text/event-stream",
    )


@app.post("/api/compliance/policy_scan")
async def compliance_policy_scan_post(
    req: CompliancePolicyScanRequest,
    _user: dict = Depends(require_action("compliance", "invoke")),
):
    """政策事件触发巡检 SSE — 4 阶段 (抽规则 → 抽事件 → N×M 矩阵 → 改/补/强 修订).

    完成后写 data/compliance/sessions/{scan_id}.json + latest pointer ·
    后续 GET /api/compliance/scan + POST /api/compliance/export_docx 消费同份产物。

    Auth (ALL IN Phase B.1 fix · per Q-052 #8 row-level/action gate · 与 policy_diff 一致):
      - compliance_officer/admin → 200 (有 invoke action)
      - rm/credit_officer/risk_manager → 403 ACCESS_DENIED
      - 无 cookie → 401 AUTH_MISSING
    """
    if not (req.policy_doc or "").strip():
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "policy_doc 不能为空",
                              "details": {"field": "policy_doc"}}},
        )

    def gen():
        yield from _policy_scan_event_stream(req)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ============================================================================
# GET  /api/compliance/demo/scenarios — sample batch 列表 (前端 toggle 用)
# POST /api/compliance/demo/run       — sample batch → **真后端** pipeline
#                                       Phase B.2 (PM 2026-05-10 真意 reframe)
#   不再 yield fixture event · 走 manifest 加载 sample 政策 + compliance-kb 制度 docx
#   → run_policy_scan_and_persist · 真 LLM/Tavily/算法 → 真违规 + 真 ViolationReason
#   反 5 原则 §3.5: 内部稳态 mock OK (sample 政策 + 制度库) · 外部 Tavily 改真接
#   红线 #1 (假 live) 严禁 · mock **只能 mock 输入 · 不能 mock 结果**
# ============================================================================


class ComplianceDemoRunRequest(BaseModel):
    scenario_id: str = "online_loan"  # see manifest.scenarios keys
    force_mock: bool = False          # 透传 scan_engine · 默认 False (=真接 LLM/Tavily)


@app.get("/api/compliance/demo/scenarios")
async def compliance_demo_scenarios():
    """列出 manifest 内可用 sample batch · 前端形态切换 toggle 用."""
    try:
        from agent_compliance.demo_loader import (
            DemoBatchError,
            list_scenarios,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"demo_loader import failed: {e}"}},
        ) from e
    try:
        return {"scenarios": list_scenarios()}
    except DemoBatchError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": e.code, "message": str(e)}},
        ) from e


@app.post("/api/compliance/demo/run")
async def compliance_demo_run(
    req: ComplianceDemoRunRequest,
    _user: dict = Depends(require_action("compliance", "invoke")),
):
    """演示路径 · 用 sample batch (compliance-kb manifest) **真跑后端 pipeline**.

    PM 2026-05-10 真意 reframe verbatim:
      "演示不是一键切换 · 把本地 mock 数据真实上传 · 通过真实后端代码跑一遍 · 给出结果"

    与 `/policy_scan` 区别:
      - `/policy_scan`: 上游真上传 policy_doc + business_docs (用户自传)
      - `/demo/run`:    后端从 manifest 读 sample → 走相同 engine (input_source=sample_batch)
    数据来源 (data_source) 由 scan_engine.build_compli_provider 真实判定 (LLM/Tavily 是否在线),
    不再硬编 MOCK_FORCED · 真接 = LIVE · 真降级 = MOCK_FALLBACK · 用户显式 force_mock = MOCK_FORCED.
    """
    try:
        from agent_compliance.demo_loader import (
            DemoBatchError,
            load_scenario,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"demo_loader import failed: {e}"}},
        ) from e

    def gen():
        try:
            batch = load_scenario(req.scenario_id or "online_loan")
        except DemoBatchError as e:
            yield encode_event(make_error(str(e), code=e.code))
            return

        extras = {
            "scenario_id": batch.scenario_id,
            "scenario_label": batch.label,
            "input_source": "sample_batch",
            "business_doc_sources": batch.business_doc_sources,
        }

        yield from _run_scan_engine_stream(
            policy_doc=batch.policy_doc,
            business_docs=batch.business_docs,
            policy_meta=batch.policy_meta,
            force_mock=bool(req.force_mock),
            extras=extras,
            endpoint="/api/compliance/demo/run",
        )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# POST /api/compliance/matrix_check — N×M 矩阵 (sync)
# ---------------------------------------------------------------------------


class MatrixCheckRequest(BaseModel):
    policies: list = []              # 政策原文 list[str] · 或已结构化 list[dict] (mixed allowed)
    business_lines: list = []        # 业务记录 list[str|dict]
    use_llm: bool = True             # 是否调 LLM (slow path) · 默认 True


@app.post("/api/compliance/matrix_check")
async def compliance_matrix_check(
    req: MatrixCheckRequest,
    _user: dict = Depends(require_action("compliance", "invoke")),
):
    """sync N×M 矩阵比对 · 不持久化 · 不流式 · 单次返结果.

    Auth (ALL IN Phase B.1 fix · per Q-052 #8 与 policy_scan/policy_diff 一致):
      - compliance_officer/admin → 200 · rm/credit_officer/risk_manager → 403 · 无 cookie → 401
    """
    if not req.policies:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "policies 不能为空",
                              "details": {"field": "policies"}}},
        )

    try:
        from agent_compliance.scan_engine import (
            build_llm_json_caller,
            extract_events_from_business_docs,
            extract_rules_from_policy_text,
            matrix_check,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"scan_engine import failed: {e}"}},
        ) from e

    llm_json = build_llm_json_caller() if req.use_llm else None

    # 政策可以是已结构化的 rule list · 也可以是 raw policy text
    rules: list[dict] = []
    for idx, pol in enumerate(req.policies):
        if isinstance(pol, dict):
            rules.append({
                "rule_id": str(pol.get("rule_id") or f"POL-{idx+1:03d}"),
                "article": str(pol.get("article") or ""),
                "category": str(pol.get("category") or "其他"),
                "condition": str(pol.get("condition") or ""),
                "threshold": pol.get("threshold") or {},
                "severity_hint": str(pol.get("severity_hint") or "major").lower(),
            })
        elif isinstance(pol, str):
            rules.extend(extract_rules_from_policy_text(pol, llm_json_caller=llm_json))

    events = extract_events_from_business_docs(req.business_lines, llm_json_caller=llm_json)

    matrix_result = matrix_check(rules, events, llm_json_caller=llm_json)
    cleaned, hits = _qc_scrub_dict(to_jsonable(matrix_result))
    resp = dict(cleaned)
    resp["llm_used"] = bool(req.use_llm and llm_json is not None)
    if hits:
        resp["_qc_placeholder_hits"] = hits
    return resp


# ---------------------------------------------------------------------------
# GET /api/compliance/scan — 取持久化扫描 (latest 或 by scan_id)
# ---------------------------------------------------------------------------


@app.get("/api/compliance/scan")
async def compliance_get_scan(scan_id: str = ""):
    try:
        from agent_compliance.scan_engine import (
            ScanResultNotFoundError,
            load_scan_result,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"scan_engine import failed: {e}"}},
        ) from e

    try:
        return load_scan_result(scan_id=scan_id.strip())
    except ScanResultNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "SCAN_NOT_FOUND",
                              "message": str(e),
                              "details": {"scan_id": scan_id}}},
        ) from e


# ---------------------------------------------------------------------------
# POST /api/compliance/export_docx — 修订意见书 Word (改/补/强 分类)
# ---------------------------------------------------------------------------


class ExportDocxRequest(BaseModel):
    scan_id: str = ""
    title: str = "合规修订意见书"


@app.post("/api/compliance/export_docx")
async def compliance_export_docx(
    req: ExportDocxRequest,
    _user: dict = Depends(require_action("compliance", "export")),
):
    """从 persisted scan 渲染修订意见书 .docx (本地 python-docx · 禁海外 API).

    Body: {scan_id, title?}
    Response: docx · Content-Disposition attachment · UTF-8 RFC 5987 中文文件名
    """
    try:
        from agent_compliance.scan_engine import (
            ScanResultNotFoundError,
            load_scan_result,
        )
        from agent_compliance.word_export import (
            build_revision_docx,
            build_revision_filename,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"export deps import failed: {e}"}},
        ) from e

    try:
        payload = load_scan_result(scan_id=(req.scan_id or "").strip())
    except ScanResultNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "SCAN_NOT_FOUND",
                              "message": str(e),
                              "details": {"scan_id": req.scan_id}}},
        ) from e

    try:
        data = build_revision_docx(payload, title=req.title or "合规修订意见书")
        filename = build_revision_filename(payload)
    except (RuntimeError, ValueError, OSError, AttributeError) as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"docx render failed: {type(e).__name__}: {e}"}},
        ) from e

    encoded = quote(filename)
    return Response(
        content=data,
        media_type=("application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "Cache-Control": "no-store",
        },
    )
