# -*- coding: utf-8 -*-
"""agent_channel.api — Agent1 全渠道获客 FastAPI 路由模块。

端点：
  GET  /api/channel/scenarios   — 列出预置场景元数据
  POST /api/channel/run         — 流式跑 look-alike 搜索 (SSE)

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- 业务逻辑全在 agent_channel.realtime_stream.run_channel_search_stream
- mock=true 强制 demo 模式，断网可演示

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import json
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

app = FastAPI(title="Agent1 Channel Lookalike API", version="4.0")


@app.get("/api/channel/scenarios")
async def list_channel_scenarios():
    try:
        from agent_channel.app_demo import SCENARIOS  # type: ignore
        return {"scenarios": [
            {"key": k, "name": v.get("name"), "desc": v.get("desc")}
            for k, v in SCENARIOS.items()
        ]}
    except Exception:
        scen_dir = PROJECT_ROOT / "demo_data" / "agent_channel" / "scenarios"
        if not scen_dir.exists():
            return {"scenarios": []}
        items = []
        for sub in scen_dir.iterdir():
            meta = sub / "scenario.json"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                    items.append({
                        "key": sub.name,
                        "name": data.get("name", sub.name),
                        "desc": data.get("description", ""),
                    })
                except Exception:
                    items.append({"key": sub.name, "name": sub.name, "desc": ""})
        return {"scenarios": items}


class ChannelRunRequest(BaseModel):
    query: str
    provider: str = "deepseek"
    api_key: str = ""
    top_n: int = 8
    # True → 前端显式切 DEMO MODE，后端跳过 Tavily，直接走 mock 池
    mock: bool = False


@app.post("/api/channel/run")
async def channel_run(req: ChannelRunRequest):
    """全渠道获客真实搜索流 SSE — 5 阶段事件推送 + 最终候选清单。

    无 TAVILY_API_KEY 自动降级到 mock_fallback。
    """
    def gen():
        try:
            from agent_channel.realtime_stream import run_channel_search_stream
        except Exception as e:
            yield sse_encode({
                "event": "error",
                "message": f"import failed: {e}",
                "traceback": traceback.format_exc(),
            })
            return
        try:
            for evt in run_channel_search_stream(
                query=req.query,
                provider=req.provider,
                api_key=req.api_key,
                top_n=req.top_n,
                force_mock=req.mock,
            ):
                yield sse_encode({k: to_jsonable(v) for k, v in evt.items()})
        except Exception as e:
            traceback.print_exc()
            yield sse_encode({
                "event": "error",
                "message": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc()[-2000:],
            })

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
