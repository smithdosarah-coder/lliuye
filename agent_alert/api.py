# -*- coding: utf-8 -*-
"""agent_alert.api — Agent4 贷中预警 FastAPI 路由模块。

端点：
  POST /api/alert/scan  — 流式跑批量扫描 (SSE)

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- 业务逻辑全在 agent_alert.agent.AlertRadarAgent.process_message
- import 失败时 SSE 仍能 yield error 事件，前端不崩
- 输出前过 shared.qc.placeholder_guard (Task B 软降级模式)

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402

from agent_alert.output_validator import soft_clean as _qc_scrub  # noqa: E402

app = FastAPI(title="Agent4 Alert Radar API", version="3.1")


@app.get("/api/alert/health")
async def alert_health():
    """Agent4 sub-app 健康探针 (与 portal /health 平级, 用于精细化故障定位)。"""
    return {"status": "ok", "agent": "agent_alert"}


class AlertScanRequest(BaseModel):
    scenario_key: str = ""               # e.g. "micro_credit_100"; 空 → 默认场景
    uploaded_files: list[str] | None = None
    provider: str | None = None
    api_key: str | None = None


def _alert_event_stream(req: AlertScanRequest):
    """生成器 — yield SSE-encoded lines."""
    try:
        from agent_alert.agent import AlertRadarAgent
    except ImportError as e:
        yield sse_encode({"event": "error", "message": f"agent import failed: {e}"})
        return

    try:
        agent = AlertRadarAgent(
            api_key=req.api_key or "dummy",
            model_provider=req.provider or "deepseek",
        )
        for evt in agent.process_message(
            user_message=req.scenario_key,
            uploaded_files=req.uploaded_files,
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
async def alert_scan(req: AlertScanRequest):
    """贷中预警批量扫描 SSE — 装载 KB → 双路交叉 → 进度/命中事件 → 处置建议汇总。

    QC blocker (CLAUDE.md §8): 每条 SSE payload 前置走 placeholder_guard,
    占位符残留软降级标"未能自动填写"并在事件挂 _qc_placeholder_hits 元数据。
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
