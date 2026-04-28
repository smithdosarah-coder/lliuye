# -*- coding: utf-8 -*-
"""FastAPI 总线 — 装载所有 Agent 路由模块，对外暴露统一 API。

设计原则（chore/l0-infra 重构后）：
- 本文件不写 Agent 业务路由，只做 mounting + cross-cutting concerns（health / feedback / CORS）
- 每个 Agent 自己 own `agent_*/api.py`，定义独立 FastAPI app
- 本文件通过 routes 合并模式装载，单进程单端口

装载的 Agent 路由：
  - agent_report.api     → /api/report/*     (Agent6, 最成熟)
  - agent_credit.api     → /api/credit/*     (Agent3)
  - agent_channel.api    → /api/channel/*    (Agent1)
  - agent_compliance.api → /api/compliance/* (Agent5)
  - agent_alert.api      → /api/alert/*      (Agent4, Phase 2 接入 · Task C)
  - agent_riskctrl.api   → /api/riskctrl/*   (Agent2, Phase 2 接入 · Task C)

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

from fastapi import FastAPI, HTTPException, Header, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Tiered data sources bootstrap (feat/tiered-search); fail-safe on missing deps
try:
    from shared.sources import bootstrap as _sources_bootstrap; _sources_bootstrap()
except Exception:
    pass

app = FastAPI(title="Zhongan Credit AI — Portal API", version="2.2")

# Stage E.2 · Sentry init (env DSN · 缺 silent skip · 必须在 add_middleware 前)
try:
    from monitoring_service.sentry_init import init_sentry as _init_sentry
    _init_sentry()
except Exception:  # noqa: BLE001
    pass

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
    return {"status": "ok", "version": "2.2"}


# ---------------------------------------------------------------------------
# Stage E.2 · Monitoring endpoints (Prometheus /metrics + extended /health)
# ---------------------------------------------------------------------------

try:
    from monitoring_service.health import run_extended_health
    from monitoring_service.metrics import (
        install_metrics_middleware as _install_metrics,
        metrics_response as _metrics_response,
    )
    _install_metrics(app)
    _MONITORING_OK = True
except ImportError as _e:
    _MONITORING_OK = False
    print(f"[portal] monitoring_service unavailable: {_e}", file=sys.stderr)


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus exposition format · text/plain · 不可用时返 stub 提示."""
    if not _MONITORING_OK:
        from fastapi.responses import Response as _R
        return _R(content=b"# monitoring_service unavailable\n",
                  media_type="text/plain; charset=utf-8")
    return _metrics_response()


@app.get("/health/extended")
async def extended_health(ping: int = 0, timeout: float = 5.0):
    """Component-level health check (Stage E.2 · onboarding W-E2-A3).

    Query:
      ping=1: 真打 DeepSeek + Tavily (默认 0 · 省 quota)
      timeout=N: 单 ping 超时 (默认 5s)
    """
    if not _MONITORING_OK:
        return {"status": "degraded", "reason": "monitoring_service unavailable",
                "components": []}
    return await run_extended_health(
        app=app,
        ping_external=bool(int(ping or 0)),
        timeout_s=float(timeout or 5.0),
    )


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
_mount_agent_routes("agent_alert.api", "Agent4 Alert")
_mount_agent_routes("agent_riskctrl.api", "Agent2 RiskCtrl")


# ---------------------------------------------------------------------------
# IM dispatch send · 客户经理 / 审贷员 / 合规官 IM 协作 (2026-04-27 #5 实装)
# ---------------------------------------------------------------------------

class ImSendRequest(BaseModel):
    message: str
    thread_id: str = ""
    customer_id: str = ""
    target_agent: str = ""  # "" / "channel" / "credit" / "alert" / "compli" / "report" / "riskctrl"


# 6 Agent 角色 system prompt (2026-04-27 · 加 @agent 路由支持 + archive 内 ConversationPanel 真接)
_AGENT_SYSTEMS = {
    "channel": "你是 Agent1 获客 (Scout) · 根据客户经理描述生成获客线索 / look-alike 推荐。回复 1-3 句·不编造数字 / 客户名 · 没有依据时显式说「需要查询」。",
    "report": "你是 Agent6 报告 · 辅助客户经理 / 审贷员处理材料 → 报告生成。回复 1-3 句·不编造内容。",
    "credit": "你是 Agent3 授信 · 辅助审贷员评分 / 红线判定。回复 1-3 句·不编造决策结果。",
    "alert": "你是 Agent4 预警 · 分析在贷客户行为信号 + 红/黄/绿榜单。回复 1-3 句·不编造预警事件。",
    "compli": "你是 Agent5 合规 · 解析新政策与业务制度冲突点。回复 1-3 句·不编造政策条款。",
    "riskctrl": "你是 Agent2 风控 · 辅助策略经理写 DSL + 回测。回复 1-3 句·不编造样本数。",
}
_AGENT_TO_ID = {
    "channel": "agent_channel",
    "report": "agent_report",
    "credit": "agent_credit",
    "alert": "agent_alert",
    "compli": "agent_compliance",
    "riskctrl": "agent_riskctrl",
}
_DEFAULT_SYSTEM = (
    "你是信贷 AI 助手·在客户经理 / 审贷员 / 合规官的协作 IM 工作台。"
    "回复简短·直接·1-3 句。"
    "涉及信贷决策时建议用户调相应 Agent (Agent1 获客 / Agent3 授信 / Agent4 预警 / Agent5 合规 / Agent6 报告)。"
    "不编造数字 / 政策 / 客户资料 · 没有依据时显式说「需要查询」。"
)


@app.post("/api/im/send")
async def im_send(req: ImSendRequest):
    """IM 对话 · DeepSeek + agent routing (target_agent 选不同 system prompt)。

    单 turn · 无 thread persistence · 无 SSE。后续扩 history + SSE + workflow。
    archive 内 ConversationPanel 通过 target_agent="channel/report/..." 调对应 agent prompt。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise HTTPException(503, "DEEPSEEK_API_KEY 未配置 · IM 后端不可用")
    if not req.message.strip():
        raise HTTPException(400, "message 不能为空")
    try:
        from llm import LLMClient
        llm = LLMClient(provider="deepseek", api_key=api_key)
        if req.target_agent and req.target_agent in _AGENT_SYSTEMS:
            system = _AGENT_SYSTEMS[req.target_agent]
            agent_id = _AGENT_TO_ID[req.target_agent]
        else:
            system = _DEFAULT_SYSTEM
            agent_id = "agent_report"
        reply = llm.simple_chat(system, req.message, temperature=0.4)
        return {
            "reply": (reply or "").strip(),
            "agent": agent_id,
            "target_agent": req.target_agent,
            "thread_id": req.thread_id,
        }
    except (RuntimeError, ValueError, OSError, AttributeError) as e:
        raise HTTPException(500, f"IM call failed: {type(e).__name__}: {e}") from e


# ============================================================================
# IM Stage D.2 + D.3 · Thread DB + WebSocket + REST
# 按 docs/contracts/im-protocol.md v1.0
# ============================================================================

from im_service import threads as _im_threads  # noqa: E402
from im_service.auth import TokenInvalidError, decode_token as _im_decode_token  # noqa: E402
from im_service.schemas import (  # noqa: E402
    CreateThreadRequest,
    ImMessage,
    SendMessageRequest,
    SendMessageResponse,
)
from im_service.websocket import im_websocket_endpoint, manager as _im_ws_manager  # noqa: E402

_im_threads.init_schema()


def _resolve_im_user(authorization: str | None, token_q: str | None) -> str:
    """从 Authorization 头 (Bearer ...) 或 ?token query 解析 user_id.

    auth 优先级: Authorization Bearer > query token · 失败抛 401。
    生产 (D.1 land 后) 走真 JWT · 当前 demo 路径接受 demo-<user_id>。
    """
    raw = ""
    if authorization:
        if authorization.lower().startswith("bearer "):
            raw = authorization[7:].strip()
        else:
            raw = authorization.strip()
    elif token_q:
        raw = token_q.strip()

    if not raw:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "MISSING_TOKEN",
                              "message": "请先登录 · 缺 token"}},
        )
    try:
        return _im_decode_token(raw)
    except TokenInvalidError as e:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "TOKEN_INVALID", "message": str(e)}},
        ) from e


@app.get("/api/im/threads")
async def im_list_threads(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """列 currentUser 在 participants 里的 thread (按 last_message_at desc)."""
    user_id = _resolve_im_user(authorization, token)
    items = _im_threads.list_threads_for_user(user_id)
    return {"user_id": user_id, "threads": items}


@app.get("/api/im/threads/{thread_id}/messages")
async def im_list_messages(
    thread_id: str,
    before: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """历史消息 paginated · before 是 created_at cursor (ASC) · 限 currentUser 在 thread."""
    user_id = _resolve_im_user(authorization, token)
    if not _im_threads.thread_has_participant(thread_id, user_id):
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "NOT_IN_THREAD",
                              "message": f"user {user_id} not in thread {thread_id}"}},
        )
    msgs = _im_threads.list_messages(thread_id, before=before, limit=limit)
    return {"thread_id": thread_id, "messages": msgs, "limit": limit, "before": before}


@app.post("/api/im/threads")
async def im_create_thread(
    req: CreateThreadRequest,
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """创建 thread · currentUser 自动加入 participants."""
    user_id = _resolve_im_user(authorization, token)
    parts = list({user_id, *(req.participants or [])})
    try:
        thread = _im_threads.create_thread(
            title=req.title or "新会话",
            participants=parts,
            kind=req.kind,
            customer_id=req.customer_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED", "message": str(e)}},
        ) from e
    return thread


@app.post("/api/im/threads/{thread_id}/read")
async def im_mark_thread_read(
    thread_id: str,
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """标记 thread 已读 · currentUser 必须在 participants."""
    user_id = _resolve_im_user(authorization, token)
    try:
        return _im_threads.mark_thread_read(thread_id, user_id)
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "THREAD_NOT_FOUND", "message": str(e)}},
        ) from e
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "NOT_IN_THREAD", "message": str(e)}},
        ) from e


@app.post("/api/im/messages")
async def im_send_message(
    req: SendMessageRequest,
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """新 send 端点 · 持久化 + WebSocket broadcast · 替代 /api/im/send (后者保留向后兼容)."""
    user_id = _resolve_im_user(authorization, token)
    if not _im_threads.thread_has_participant(req.thread_id, user_id):
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "NOT_IN_THREAD",
                              "message": f"user {user_id} not in thread {req.thread_id}"}},
        )
    try:
        msg = _im_threads.insert_message(
            thread_id=req.thread_id,
            from_id=user_id,
            kind=req.kind or "text",
            content=req.content or "",
            refs=req.refs,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INSERT_FAILED", "message": str(e)}},
        ) from e

    # WebSocket broadcast (异步 · 不阻塞 REST 响应)
    try:
        await _im_ws_manager.broadcast_to_thread(
            req.thread_id,
            {"type": "message", "thread_id": req.thread_id, "message": msg},
        )
    except (RuntimeError, ConnectionError, json.JSONDecodeError):
        # broadcast 失败不阻断写入 · client 重连 resync 即可补
        pass

    return SendMessageResponse(message=ImMessage(**msg), ack="stored").model_dump()


@app.websocket("/ws/im")
async def im_websocket(websocket: WebSocket, token: str = Query(default="")):
    """WebSocket 入口 · query param token=<jwt> · 业务逻辑全在 im_service.websocket."""
    await im_websocket_endpoint(websocket, token=token)


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="127.0.0.1", port=port, reload=False)
