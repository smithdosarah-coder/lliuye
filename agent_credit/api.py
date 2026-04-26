"""agent_credit.api — Agent3 授信决策 FastAPI 路由模块。

端点：
  GET  /api/credit/presets/{segment}    — 列出预置画像 (corporate / retail)
  POST /api/credit/decision             — 流式跑授信决策 pipeline (SSE)

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- 业务逻辑全在 agent_credit.agent.CreditDecisionAgent，本模块只做 HTTP 包装
- import 失败时 SSE 仍能 yield error 事件，前端不崩

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import json
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

app = FastAPI(title="Agent3 Credit Decision API", version="3.1")

_HANDOFF_DIR = PROJECT_ROOT / "demo_data" / "agent_credit"


def _qc_scrub(payload):
    """递归把字符串字段里的占位符替换为"未能自动填写"; 返回 (清洗后, 命中类型列表)。"""
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


class DecisionRequest(BaseModel):
    segment: str       # "corporate" | "retail"
    preset_name: str
    provider: str | None = None
    api_key: str | None = None


@app.get("/api/credit/presets/{segment}")
async def list_credit_presets(segment: str):
    if segment not in ("corporate", "retail"):
        raise HTTPException(400, "segment must be corporate or retail")
    try:
        from agent_credit.agent import _list_preset_profiles
        return {"segment": segment, "presets": _list_preset_profiles(segment)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"load presets failed: {e}") from e


@app.get("/api/credit/handoff/demo/{segment}")
async def get_handoff_demo(segment: str):
    """返回 demo_data/agent_credit/ 下 Agent6→Agent3 handoff 样本画像。

    响应：{ segment, profile, preset_name }。前端 HandoffButton 消费后
    写入 sessionStorage.enterprise_profile 触发现有 applyProfile 流程。
    """
    if segment not in ("corporate", "retail"):
        raise HTTPException(400, detail={
            "error": {"code": "VALIDATION_FAILED",
                      "message": "segment must be corporate or retail",
                      "details": {"field": "segment", "got": segment}}
        })
    prefix = "corp_" if segment == "corporate" else "retail_"
    if not _HANDOFF_DIR.exists():
        raise HTTPException(404, detail={
            "error": {"code": "NOT_FOUND",
                      "message": f"handoff demo dir missing: {_HANDOFF_DIR}"}
        })
    candidates = sorted(_HANDOFF_DIR.glob(f"{prefix}*.json"))
    if not candidates:
        raise HTTPException(404, detail={
            "error": {"code": "NOT_FOUND",
                      "message": f"no handoff demo for segment={segment}"}
        })
    try:
        profile = json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail={
            "error": {"code": "INTERNAL_ERROR",
                      "message": f"load handoff demo failed: {e}"}
        }) from e
    return {
        "segment": segment,
        "profile": profile,
        "preset_name": profile.get("preset_name", ""),
        "source_file": candidates[0].name,
    }


def _decision_event_stream(req: DecisionRequest):
    """生成器 — yield SSE-encoded lines."""
    try:
        from agent_credit.agent import CreditDecisionAgent
    except ImportError as e:
        yield sse_encode({"event": "error", "message": f"agent import failed: {e}"})
        return

    try:
        agent = CreditDecisionAgent(
            api_key=req.api_key or "dummy",
            model_provider=req.provider or "deepseek",
        )
        profile = agent.load_preset_profile(req.preset_name, req.segment)  # type: ignore
        yield sse_encode({"event": "profile_loaded", "profile": to_jsonable(profile)})

        for stage, payload in agent.run_decision_stream(profile, req.segment):  # type: ignore
            cleaned, hits = _qc_scrub(to_jsonable(payload))
            evt = {
                "event": "stage",
                "stage": stage,
                "payload": cleaned,
            }
            if hits:
                evt["_qc_placeholder_hits"] = hits
            yield sse_encode(evt)

        yield sse_encode({"event": "done"})
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        traceback.print_exc()
        yield sse_encode({
            "event": "error",
            "message": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-2000:],
        })


class ExportDocxRequest(BaseModel):
    advice: dict


@app.post("/api/credit/export_docx")
async def export_decision_docx(req: ExportDocxRequest):
    """本地 python-docx 渲染决策意见书。

    监管底线：禁用海外 API，全部本地计算；仅消费前端回传的 advice dict。
    响应：application/vnd.openxmlformats-officedocument.wordprocessingml.document
    """
    advice = req.advice or {}
    if not advice.get("subject_name") and not advice.get("decision"):
        raise HTTPException(400, detail={
            "error": {"code": "VALIDATION_FAILED",
                      "message": "advice payload empty or missing subject_name/decision",
                      "details": {"keys": list(advice.keys())}}
        })
    try:
        from agent_credit.decision_letter_docx import build_filename, export
        data = export(advice)
        filename = build_filename(advice)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail={
            "error": {"code": "INTERNAL_ERROR",
                      "message": f"docx render failed: {e}"}
        }) from e

    # RFC 5987 中文文件名
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


@app.post("/api/credit/decision")
async def credit_decision(req: DecisionRequest):
    def gen():
        yield from _decision_event_stream(req)
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
