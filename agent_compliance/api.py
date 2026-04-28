# -*- coding: utf-8 -*-
"""agent_compliance.api — Agent5 合规雷达 FastAPI 路由模块。

端点：
  GET  /api/compliance/policy_scan   — 主动从 gov.cn / pbc / flk_npc 拉最新政策候选
                                       (Tavily 政策发现 · 前端轮询 / 看新政策列表)
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
- 既有 GET /policy_scan + ComplianceRadarAgent.process_message 路径不动 (向后兼容)
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402
from shared.qc import mark_unfilled, scan as scan_placeholders  # noqa: E402

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


def _qc_scrub_policies(policies: list) -> tuple[list, list[str]]:
    """对每条 policy item 的字符串字段做占位符清洗。"""
    hits: list[str] = []
    cleaned: list = []
    for p in policies or []:
        if isinstance(p, dict):
            new: dict = {}
            for k, v in p.items():
                if isinstance(v, str):
                    local = scan_placeholders(v)
                    if local:
                        hits.extend(h.kind for h in local)
                        new[k] = mark_unfilled(v)
                        continue
                new[k] = v
            cleaned.append(new)
        else:
            cleaned.append(p)
    return cleaned, hits


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
# GET /api/compliance/policy_scan — 既有 · Tavily 政策发现
# ---------------------------------------------------------------------------


@app.get("/api/compliance/policy_scan")
@audit_llm_call(agent_id="compliance", endpoint="/api/compliance/policy_scan", model="deepseek-chat")
async def compliance_policy_scan_get(query: str = "", limit: int = 10):
    """主动从政策源拉最新候选清单。失败优雅降级返回空 list + error，前端不崩。

    QC blocker (CLAUDE.md §8): 输出前过 placeholder_guard, 占位符残留软降级
    为"未能自动填写"标记并在响应中带 ``_qc_placeholder_hits`` 元数据。
    """
    try:
        from agent_compliance.agent import ComplianceRadarAgent
        agent = ComplianceRadarAgent()
        cleaned, hits = _qc_scrub_policies(agent.scan_external_policies(query, limit))
        resp: dict = {"policies": cleaned}
        if hits:
            resp["_qc_placeholder_hits"] = hits
        return resp
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        return {"policies": [], "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# POST /api/compliance/policy_scan — 新 · 政策事件触发巡检 SSE (Stage C.4)
# ---------------------------------------------------------------------------


class CompliancePolicyScanRequest(BaseModel):
    policy_doc: str                  # 监管政策原文 (text)
    business_docs: list = []         # 业务记录 list[str|dict]
    policy_meta: dict | None = None  # 可选 metadata (title / source_url / fetched_at)
    force_mock: bool = False         # 强制走 mock 政策库 · 不尝试 Tavily


def _policy_scan_event_stream(req: CompliancePolicyScanRequest):
    try:
        from agent_compliance.scan_engine import run_policy_scan_and_persist
    except ImportError as e:
        yield sse_encode({"event": "error", "message": f"scan_engine import failed: {e}"})
        return

    try:
        for evt in run_policy_scan_and_persist(
            policy_doc=req.policy_doc or "",
            business_docs=req.business_docs or [],
            policy_meta=req.policy_meta,
            force_mock=bool(req.force_mock),
        ):
            payload = to_jsonable(evt)
            cleaned, hits = _qc_scrub_dict(payload)
            wrap = {"event": "stage", "payload": cleaned}
            if hits:
                wrap["_qc_placeholder_hits"] = hits
            yield sse_encode(wrap)

        yield sse_encode({"event": "done"})
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        traceback.print_exc()
        yield sse_encode({
            "event": "error",
            "message": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-2000:],
        })


@app.post("/api/compliance/policy_scan")
async def compliance_policy_scan_post(req: CompliancePolicyScanRequest):
    """政策事件触发巡检 SSE — 4 阶段 (抽规则 → 抽事件 → N×M 矩阵 → 改/补/强 修订).

    完成后写 data/compliance/sessions/{scan_id}.json + latest pointer ·
    后续 GET /api/compliance/scan + POST /api/compliance/export_docx 消费同份产物。
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


# ---------------------------------------------------------------------------
# POST /api/compliance/matrix_check — N×M 矩阵 (sync)
# ---------------------------------------------------------------------------


class MatrixCheckRequest(BaseModel):
    policies: list = []              # 政策原文 list[str] · 或已结构化 list[dict] (mixed allowed)
    business_lines: list = []        # 业务记录 list[str|dict]
    use_llm: bool = True             # 是否调 LLM (slow path) · 默认 True


@app.post("/api/compliance/matrix_check")
async def compliance_matrix_check(req: MatrixCheckRequest):
    """sync N×M 矩阵比对 · 不持久化 · 不流式 · 单次返结果."""
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
async def compliance_export_docx(req: ExportDocxRequest):
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
