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


def _policy_scan_event_stream(req: CompliancePolicyScanRequest):
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
            policy_doc=req.policy_doc or "",
            business_docs=req.business_docs or [],
            policy_meta=req.policy_meta,
            force_mock=bool(req.force_mock),
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
            done_evt = _build_compliance_done_envelope(
                scan_id=last_scan_id,
                payload=full_payload,
                duration_seconds=_time.time() - t_start,
            )
            yield encode_event(done_evt)
        else:
            yield encode_event(make_error(
                "scan event 未发出 · run_policy_scan_and_persist 未持久化",
                code="SCAN_PERSIST_MISSING",
            ))
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        traceback.print_exc()
        yield encode_event(make_error_from_exception(e, code="SCAN_RUNTIME_ERROR"))


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
# POST /api/compliance/demo/run · Phase A worker-A4-compli (2026-04-29)
#   纯 mock SSE · 不调 LLM/Tavily · 从 data/mock/workspace/compliance/scenarios/<id>.json 读
#   用途: 演示模式 / Playwright smoke / 客户走访稳定 demo 路径
#   反 5 原则 §3.5 难度分层: online_loan / aml / data_protect 三档 (per spec §6.2)
# ============================================================================


import json as _json  # noqa: E402

_COMPLI_SCENARIO_DIR = PROJECT_ROOT / "data" / "mock" / "workspace" / "compliance" / "scenarios"
_COMPLI_ALLOWED_SCENARIOS = {"online_loan", "aml", "data_protect"}


class ComplianceDemoRunRequest(BaseModel):
    scenario_id: str = "online_loan"  # "online_loan" | "aml" | "data_protect"


@app.post("/api/compliance/demo/run")
async def compliance_demo_run(
    req: ComplianceDemoRunRequest,
    _user: dict = Depends(require_action("compliance", "demo")),
):
    """纯 mock SSE 演示流 · 不依赖 Tavily / LLM · 视觉与 live 一致 (4 stage 流 + done envelope).

    Per agent-compli-spec §6.2 + sse-envelope §3.1 · done event panels 4 keys
    (violations / matrix / events / recommendations) 同共形.
    """
    import time as _time

    def gen():
        scenario_id = req.scenario_id or "online_loan"
        if scenario_id not in _COMPLI_ALLOWED_SCENARIOS:
            yield encode_event(make_error(
                f"unknown scenario_id: {scenario_id} "
                f"(allowed: {'/'.join(sorted(_COMPLI_ALLOWED_SCENARIOS))})",
                code="DEMO_SCENARIO_INVALID",
            ))
            return
        path = _COMPLI_SCENARIO_DIR / f"{scenario_id}.json"
        if not path.exists():
            yield encode_event(make_error(
                f"scenario file not found: {path.name}",
                code="DEMO_SCENARIO_MISSING",
            ))
            return
        try:
            data = _json.loads(path.read_text("utf-8"))
        except (_json.JSONDecodeError, OSError) as e:
            yield encode_event(make_error(
                f"scenario load failed: {type(e).__name__}: {e}",
                code="DEMO_SCENARIO_LOAD",
            ))
            return

        # 4 阶段 (per scan_engine.run_policy_scan_and_persist)
        stages = ["rule_extract", "event_extract", "matrix_match", "revision_generate"]
        stage_msgs = data.get("stage_messages", {}) or {}
        for stage_name in stages:
            yield encode_event(make_stage(
                stage_name, "running",
                message=stage_msgs.get(stage_name, f"{stage_name}..."),
            ))
            _time.sleep(0.18)
            yield encode_event(make_stage(stage_name, "done"))

        violations = data.get("violations", []) or []
        recommendations = data.get("recommendations") or _aggregate_recommendations(violations)

        yield encode_event(make_done(
            panels={
                "violations": violations,
                "matrix": data.get("matrix", []) or [],
                "events": data.get("events", []) or [],
                "recommendations": recommendations,
            },
            metrics=data.get("metrics", {}) or {},
            data_source=DATA_SOURCE_MOCK_FORCED,
            session_id=f"demo_{scenario_id}_{int(_time.time())}",
            rules_preview=(data.get("rules_preview") or data.get("rules") or [])[:5],
            events_preview=(data.get("events_preview") or data.get("events") or [])[:5],
            policy_meta=data.get("policy_meta", {}) or {},
            scenario_id=scenario_id,
        ))

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
