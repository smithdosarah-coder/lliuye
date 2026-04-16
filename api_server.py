# -*- coding: utf-8 -*-
"""FastAPI wrapper — expose all agent capabilities to the Next.js frontend.

Endpoints:
  GET  /api/presets/{segment}            — list preset profiles
  POST /api/credit/decision (SSE)        — run Agent3 pipeline, stream events
  POST /api/channel/run (SSE)            — run Agent1 look-alike search stream
  POST /api/feedback                     — 数据飞轮第 3 环：审贷员修改反馈沉淀
  GET  /api/feedback/stats               — 反馈统计（按 Agent / 按日）
  GET  /health                           — liveness probe

Run:
  py api_server.py           # dev (port 8000)
  uvicorn api_server:app ...

Design notes:
- One process, all agents. Portability > ceremony.
- SSE for streaming (simpler than websockets, works across proxies).
- Mock-friendly: if agent import fails, serve canned responses so the UI can
  still render — useful for pure front-end iteration.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Tiered data sources (feat/tiered-search) — fail-safe; missing deps just skipped.
try:
    from shared.sources import bootstrap as _sources_bootstrap; _sources_bootstrap()
except Exception:
    pass

app = FastAPI(title="Zhongan Credit AI — Portal API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001",
                   "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    # 允许 cloudflared / ngrok 演示隧道（正则匹配）
    allow_origin_regex=r"https://.*\.(trycloudflare\.com|ngrok-free\.app|ngrok\.app|ngrok\.io)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses / pydantic / sets / custom to JSON-safe."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, BaseModel):
        return _to_jsonable(obj.model_dump())
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return _to_jsonable(obj.to_dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return _to_jsonable({k: v for k, v in obj.__dict__.items()
                             if not k.startswith("_")})
    return str(obj)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0"}


# ---------------------------------------------------------------------------
# Agent3 — Credit Decision
# ---------------------------------------------------------------------------

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
        presets = _list_preset_profiles(segment)
        return {"segment": segment, "presets": presets}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"load presets failed: {e}")


def _decision_event_stream(req: DecisionRequest):
    """生成器 — yield SSE-encoded lines."""
    try:
        from agent_credit.agent import CreditDecisionAgent
    except Exception as e:
        yield _sse({"event": "error", "message": f"agent import failed: {e}"})
        return

    def sse_event(evt: dict) -> str:
        return f"data: {json.dumps(evt, ensure_ascii=False, default=str)}\n\n"

    try:
        agent = CreditDecisionAgent(
            api_key=req.api_key or "dummy",
            model_provider=req.provider or "deepseek",
        )
        profile = agent.load_preset_profile(req.preset_name, req.segment)  # type: ignore

        yield sse_event({
            "event": "profile_loaded",
            "profile": _to_jsonable(profile),
        })

        for stage, payload in agent.run_decision_stream(profile, req.segment):  # type: ignore
            evt = {
                "event": "stage",
                "stage": stage,
                "payload": _to_jsonable(payload),
            }
            yield sse_event(evt)

        yield sse_event({"event": "done"})
    except Exception as e:
        traceback.print_exc()
        yield sse_event({
            "event": "error",
            "message": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-2000:],
        })


def _sse(evt: dict) -> str:
    return f"data: {json.dumps(evt, ensure_ascii=False, default=str)}\n\n"


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


# ---------------------------------------------------------------------------
# Agent1 — Channel / Look-alike  (stub; to be fleshed out)
# ---------------------------------------------------------------------------

@app.get("/api/channel/scenarios")
async def list_channel_scenarios():
    try:
        from agent_channel.app_demo import SCENARIOS  # type: ignore
        return {"scenarios": [
            {"key": k, "name": v.get("name"), "desc": v.get("desc")}
            for k, v in SCENARIOS.items()
        ]}
    except Exception:
        # Fallback — list from demo_data directory
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
    # True → 前端显式切 DEMO MODE，后端跳过 Tavily，直接走 mock 池，
    # 并在 data_source 字段标记 "mock_forced"（区别于 key 缺失时的 mock_fallback）
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
            yield _sse({
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
                safe = {k: _to_jsonable(v) for k, v in evt.items()}
                yield _sse(safe)
        except Exception as e:
            traceback.print_exc()
            yield _sse({
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


# ---------------------------------------------------------------------------
# Data Flywheel — feedback ingestion (第 3 环：动态经验)
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    agent: str                    # "channel" / "credit" / "alert" / "compliance" / "report" / "riskctrl"
    session_id: str
    original_output: dict         # Agent 原始输出
    user_correction: dict         # 审贷员修改后的结果
    correction_reason: str = ""   # 可选：修改原因，便于后续提取 few-shot 时加权
    user_id: str | None = None    # 可选：哪位审贷员


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """接收审贷员对 Agent 输出的修改反馈，按日 JSONL 沉淀。

    写入路径：data/feedback/YYYY-MM-DD.jsonl
    后续由离线脚本消费：提取 few-shot 示例注入 prompts.py（数据飞轮第 4 环）。
    """
    allowed = {"channel", "credit", "alert", "compliance", "report", "riskctrl"}
    if req.agent not in allowed:
        raise HTTPException(400, f"agent must be one of {sorted(allowed)}")

    date = datetime.now().strftime("%Y-%m-%d")
    path = PROJECT_ROOT / "data" / "feedback" / f"{date}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now().isoformat(),
        "agent": req.agent,
        "session_id": req.session_id,
        "user_id": req.user_id,
        "original_output": req.original_output,
        "user_correction": req.user_correction,
        "correction_reason": req.correction_reason,
    }
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(500, f"write feedback failed: {e}")

    return {"status": "ok", "path": str(path.relative_to(PROJECT_ROOT))}


@app.get("/api/feedback/stats")
async def feedback_stats():
    """反馈沉淀统计 — 每个 Agent 累计条数，用于判断何时 refresh few-shot。"""
    feedback_dir = PROJECT_ROOT / "data" / "feedback"
    if not feedback_dir.exists():
        return {"total": 0, "by_agent": {}, "by_date": {}}

    by_agent: dict[str, int] = {}
    by_date: dict[str, int] = {}
    total = 0
    for jsonl in feedback_dir.glob("*.jsonl"):
        date = jsonl.stem
        by_date.setdefault(date, 0)
        try:
            with jsonl.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        agent = rec.get("agent", "unknown")
                        by_agent[agent] = by_agent.get(agent, 0) + 1
                        by_date[date] += 1
                        total += 1
                    except Exception:
                        continue
        except Exception:
            continue
    return {"total": total, "by_agent": by_agent, "by_date": by_date}


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="127.0.0.1", port=port, reload=False)
