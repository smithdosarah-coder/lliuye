# -*- coding: utf-8 -*-
"""agent_alert.api — Agent4 贷中预警 FastAPI 路由模块。

端点：
  POST /api/alert/scan         — 流式跑批量扫描 (SSE)
  POST /api/alert/export_docx  — 命中清单 Word 报告本地导出 (W-FIX2 修 bug #6)

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- 业务逻辑全在 agent_alert.agent.AlertRadarAgent.process_message
- import 失败时 SSE 仍能 yield error 事件，前端不崩
- 输出前过 shared.qc.placeholder_guard (Task B 软降级模式)
- SSE audit (W-FIX2 修 bug #11): generator try/finally 调 audit_stream_event,
  decorator 不再包 SSE route (latency 失真) · sync route 仍可用 decorator

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402

from agent_alert.output_validator import soft_clean as _qc_scrub  # noqa: E402

# Stage W-FIX2 · audit log SSE-aware finally hook (silent fail if unavailable)
try:
    from audit_service.stream_helpers import audit_stream_event  # noqa: E402
except ImportError:
    def audit_stream_event(*_args, **_kwargs):  # type: ignore[no-redef]
        pass

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


class AlertExportDocxRequest(BaseModel):
    """W-FIX2 bug #6 · 命中清单 Word 导出请求.

    形态对齐 frontend AlertWorkspace 命中清单 + 顶 case · session 元信息可选。
    """
    session_id: str = ""
    summary: str = ""
    cases: list[dict] = []
    scan_range: str = ""
    client_manager: str = ""
    stage: str = ""
    totals: dict | None = None


def _alert_event_stream(req: AlertScanRequest):
    """生成器 — yield SSE-encoded lines · try/except/finally 内部记 audit (bug #11 修)。"""
    t0 = time.time()
    err: str | None = None
    try:
        try:
            from agent_alert.agent import AlertRadarAgent
        except ImportError as e:
            err = f"ImportError: {e}"
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
            err = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            yield sse_encode({
                "event": "error",
                "message": err,
                "traceback": traceback.format_exc()[-2000:],
            })
    finally:
        # bug #11 fix · audit 写在 generator 末尾 · latency 含全 stream 真实延迟
        audit_stream_event(
            agent_id="alert",
            endpoint="/api/alert/scan",
            model=req.provider or "deepseek-chat",
            t0=t0,
            error=err,
        )


@app.post("/api/alert/scan")
async def alert_scan(req: AlertScanRequest):
    """贷中预警批量扫描 SSE — 装载 KB → 双路交叉 → 进度/命中事件 → 处置建议汇总。

    QC blocker (CLAUDE.md §8): 每条 SSE payload 前置走 placeholder_guard,
    占位符残留软降级标"未能自动填写"并在事件挂 _qc_placeholder_hits 元数据。

    Audit (W-FIX2 bug #11 修): generator finally 内调 audit_stream_event ·
    latency 含真实 LLM 调用时延 · 不再用 @audit_llm_call decorator
    (decorator 在 route function return StreamingResponse 即记 · 失真)。
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


@app.post("/api/alert/export_docx")
async def alert_export_docx(req: AlertExportDocxRequest):
    """W-FIX2 bug #6 修 · 命中清单 Word 报告本地导出.

    监管底线: 渲染全 BytesIO 本地完成 · 禁海外 API · attachment 下载.
    RFC 6266 ``filename*=UTF-8''<encoded>`` 兼容中文文件名。

    Failure: payload 非法 / docx 渲染异常 · 抛 HTTP 500 · frontend 应 catch
    设 setExportError + UI banner 显 (不静默 console-only)。
    """
    try:
        from agent_alert.word_export import build_filename, export_hitlist_docx
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"word_export module import failed: {e}",
        ) from e

    try:
        out_path_str = export_hitlist_docx(
            session_id=req.session_id or "",
            summary=req.summary or "",
            cases=list(req.cases or []),
            scan_range=req.scan_range or "",
            client_manager=req.client_manager or "",
            stage=req.stage or "",
            totals=req.totals or {},
        )
    except (RuntimeError, ValueError, TypeError, OSError) as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {e}",
        ) from e

    out_path = Path(out_path_str)
    if not out_path.exists():
        raise HTTPException(
            status_code=500,
            detail="docx generation succeeded but file missing on disk",
        )

    filename = build_filename({"session_id": req.session_id or ""})
    return FileResponse(
        path=str(out_path),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        filename=filename,
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(filename)}"
            ),
        },
    )
