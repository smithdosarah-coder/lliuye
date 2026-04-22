# -*- coding: utf-8 -*-
"""FastAPI 总线 — 装载所有 Agent 路由模块，对外暴露统一 API。

设计原则（chore/l0-infra 重构后）：
- 本文件不写 Agent 业务路由，只做 mounting + cross-cutting concerns（health / feedback / CORS）
- 每个 Agent 自己 own `agent_*/api.py`，定义独立 FastAPI app
- 本文件通过 routes 合并模式装载，单进程单端口

装载的 Agent 路由：
  - agent_report.api  → /api/report/*  (Agent6, 最成熟)
  - agent_credit.api  → /api/credit/*  (Agent3)
  - agent_channel.api → /api/channel/* (Agent1)
  - agent_compliance.api → /api/compliance/* (Agent5)
  TODO Phase 2: agent_alert.api / agent_riskctrl.api

跨切关注点（留在本文件）：
  - /health 总健康检查
  - /api/feedback + /api/feedback/stats 数据飞轮第 3 环（跨 Agent 通用）
  - CORS middleware（demo.liuye.me / cloudflared / ngrok 隧道）

Run:
  py scripts/start_uvicorn.py     # 带 .env 自动加载 + key 校验的 wrapper(推荐)
  uvicorn api_server:app --port 8000     # 裸跑(env 需提前手动 export)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Tiered data sources bootstrap (feat/tiered-search); fail-safe on missing deps
try:
    from shared.sources import bootstrap as _sources_bootstrap; _sources_bootstrap()
except Exception:
    pass

app = FastAPI(title="Zhongan Credit AI — Portal API", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3001",
        "http://127.0.0.1:3000", "http://127.0.0.1:3001",
        "https://demo.liuye.me", "https://api.liuye.me",
    ],
    allow_origin_regex=r"https://.*\.(trycloudflare\.com|ngrok-free\.app|ngrok\.app|ngrok\.io|liuye\.me)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.1"}


# ---------------------------------------------------------------------------
# Data Flywheel — feedback ingestion (第 3 环：动态经验)
# 跨 Agent 通用，留在 portal 而非单 Agent
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    agent: str                    # "channel" / "credit" / "alert" / "compliance" / "report" / "riskctrl"
    session_id: str
    original_output: dict
    user_correction: dict
    correction_reason: str = ""
    user_id: str | None = None


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
    except OSError as e:
        raise HTTPException(500, f"write feedback failed: {e}") from e

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
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
    return {"total": total, "by_agent": by_agent, "by_date": by_date}


# ---------------------------------------------------------------------------
# 装载各 Agent 路由模块
# 单进程单端口，cloudflared 无需路径分流。冲突路径（/health）保留 portal 的。
# ---------------------------------------------------------------------------

def _mount_agent_routes(module_path: str, label: str) -> None:
    """从 agent_*/api.py 导入 app 并把 routes 合并到 portal app。"""
    try:
        mod = __import__(module_path, fromlist=["app"])
        sub_app = mod.app
    except Exception as e:
        print(f"[portal] {label} routes NOT mounted: {type(e).__name__}: {e}",
              file=sys.stderr)
        return

    existing = {
        (r.path, tuple(sorted(getattr(r, "methods", None) or [])))
        for r in app.routes if hasattr(r, "path")
    }
    mounted = 0
    for route in sub_app.routes:
        if not hasattr(route, "path"):
            continue
        key = (route.path, tuple(sorted(getattr(route, "methods", None) or [])))
        if key in existing:
            continue
        app.routes.append(route)
        existing.add(key)
        mounted += 1
    print(f"[portal] {label}: mounted {mounted} routes from {module_path}",
          file=sys.stderr)


_mount_agent_routes("agent_report.api", "Agent6 Report")
_mount_agent_routes("agent_credit.api", "Agent3 Credit")
_mount_agent_routes("agent_channel.api", "Agent1 Channel")
_mount_agent_routes("agent_compliance.api", "Agent5 Compliance")
# TODO Phase 2: _mount_agent_routes("agent_alert.api", "Agent4 Alert")
# TODO Phase 2: _mount_agent_routes("agent_riskctrl.api", "Agent2 RiskCtrl")


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="127.0.0.1", port=port, reload=False)
