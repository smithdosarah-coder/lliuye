# -*- coding: utf-8 -*-
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402

app = FastAPI(title="Agent3 Credit Decision API", version="3.1")


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


def _decision_event_stream(req: DecisionRequest):
    """生成器 — yield SSE-encoded lines."""
    try:
        from agent_credit.agent import CreditDecisionAgent
    except Exception as e:
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
            yield sse_encode({
                "event": "stage",
                "stage": stage,
                "payload": to_jsonable(payload),
            })

        yield sse_encode({"event": "done"})
    except Exception as e:
        traceback.print_exc()
        yield sse_encode({
            "event": "error",
            "message": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-2000:],
        })


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
