# -*- coding: utf-8 -*-
"""agent_alert.api — Agent4 贷中预警 FastAPI 路由模块。

端点：
  POST /api/alert/scan          — 流式跑批量扫描 (SSE) · 完成后持久化
  GET  /api/alert/hitlist       — 取持久化红/黄/绿榜单 (latest 或 by session_id)
  GET  /api/alert/drill/{cid}   — 取单客户 drill detail + LLM 处置建议
  GET  /api/alert/health        — 健康探针

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- /scan SSE 业务逻辑走 agent_alert.scan_engine.run_scan_and_persist
  (Stage C onboarding W-C3-A3 · KB_DEMO 解锁 + Tavily 401 fallback)
- import 失败时 SSE 仍能 yield error 事件，前端不崩
- 输出前过 shared.qc.placeholder_guard (Task B 软降级模式)

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402

from agent_alert.output_validator import soft_clean as _qc_scrub  # noqa: E402

# Stage E.1 · audit log decorator (silent fail if audit_service unavailable)
try:
    from audit_service.decorators import audit_llm_call  # noqa: E402
except ImportError:
    def audit_llm_call(**_kwargs):  # type: ignore[no-redef]
        def _passthrough(fn):
            return fn
        return _passthrough

app = FastAPI(title="Agent4 Alert Radar API", version="3.2")


@app.get("/api/alert/health")
async def alert_health():
    """Agent4 sub-app 健康探针 (与 portal /health 平级, 用于精细化故障定位)。"""
    return {"status": "ok", "agent": "agent_alert"}


class AlertScanRequest(BaseModel):
    scenario_key: str = ""               # e.g. "micro_credit_100"; 空 → 默认场景
    uploaded_files: list[str] | None = None
    provider: str | None = None
    api_key: str | None = None
    force_mock: bool = False             # 强制走 mock_pool · 不尝试 Tavily


def _alert_event_stream(req: AlertScanRequest):
    """生成器 — yield SSE-encoded lines.

    走 scan_engine.run_scan_and_persist · 含 Tavily 401 fallback (Q-040) +
    持久化到 data/alert/sessions/{session_id}.json + latest pointer。
    """
    try:
        from agent_alert.scan_engine import run_scan_and_persist
    except ImportError as e:
        yield sse_encode({"event": "error", "message": f"scan_engine import failed: {e}"})
        return

    try:
        for evt in run_scan_and_persist(
            scenario_key=req.scenario_key or "",
            uploaded_files=req.uploaded_files,
            api_key=req.api_key or "dummy",
            provider=req.provider or "deepseek",
            force_mock=bool(req.force_mock),
        ):
            payload = to_jsonable(evt)
            cleaned, hits = _qc_scrub(payload)
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


@app.post("/api/alert/scan")
@audit_llm_call(agent_id="alert", endpoint="/api/alert/scan", model="deepseek-chat")
async def alert_scan(req: AlertScanRequest):
    """贷中预警批量扫描 SSE — 装载 KB → 双路交叉 → 进度/命中事件 → 处置建议汇总 → 持久化.

    QC blocker (CLAUDE.md §8): 每条 SSE payload 前置走 placeholder_guard,
    占位符残留软降级标"未能自动填写"并在事件挂 _qc_placeholder_hits 元数据。

    完成后写 data/alert/sessions/{session_id}.json + 更新 latest pointer ·
    后续 GET /api/alert/hitlist · GET /api/alert/drill/{cid} 消费同一份产物。
    """
    def gen():
        yield from _alert_event_stream(req)
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
# GET /api/alert/hitlist — 拉持久化红/黄/绿榜单 (Stage C · onboarding W-C3-A3)
# ============================================================================


@app.get("/api/alert/hitlist")
async def alert_hitlist(session_id: str = ""):
    """返回最新（或指定 session_id 的）扫描结果.

    Response:
      {session_id, generated_at, scenario_key, mode, hit_list: HitList, dispositions}
    404: 尚无任何扫描记录 / session_id 不存在
    """
    try:
        from agent_alert.scan_engine import HitListNotFoundError, load_hitlist
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"scan_engine import failed: {e}"}},
        ) from e

    try:
        return load_hitlist(session_id=session_id.strip())
    except HitListNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "HITLIST_NOT_FOUND",
                              "message": str(e),
                              "details": {"session_id": session_id}}},
        ) from e


# ============================================================================
# GET /api/alert/drill/{client_id} — 单客户 drill detail (Stage C · onboarding W-C3-A3)
# ============================================================================


@app.get("/api/alert/drill/{client_id}")
async def alert_drill(client_id: str, session_id: str = ""):
    """返回单客户 drill detail · 含 信号 timeline + 处置建议 (LLM 优先 / 模板兜底).

    Response:
      {client_id, company_name, level, score, matched_rules, reasons,
       signal_timeline, disposition, disposition_source}
    404: client_id 不在当前 hitlist
    """
    try:
        from agent_alert.scan_engine import (
            ClientNotFoundError,
            HitListNotFoundError,
            build_drill_payload,
            load_hitlist,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"scan_engine import failed: {e}"}},
        ) from e

    try:
        payload = load_hitlist(session_id=session_id.strip())
    except HitListNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "HITLIST_NOT_FOUND",
                              "message": str(e)}},
        ) from e

    # 优先用真 LLM caller (DEEPSEEK_API_KEY 配置时) · 无则走模板兜底
    llm_caller = _build_simple_llm_caller()

    try:
        return build_drill_payload(payload, client_id, llm_caller=llm_caller)
    except ClientNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "CLIENT_NOT_FOUND",
                              "message": str(e),
                              "details": {"client_id": client_id}}},
        ) from e


def _build_simple_llm_caller():
    """构造 (system, user) -> str caller · 无 key 返 None 让 build_drill 走模板."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from llm import LLMClient
        client = LLMClient(provider="deepseek", api_key=api_key)
        def caller(system: str, user: str) -> str:
            return (client.simple_chat(system, user, temperature=0.3) or "").strip()
        return caller
    except (ImportError, RuntimeError, ValueError, OSError):
        return None
