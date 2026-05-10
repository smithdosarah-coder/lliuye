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
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Tiered data sources bootstrap (feat/tiered-search); fail-safe on missing deps
try:
    from shared.sources import bootstrap as _sources_bootstrap; _sources_bootstrap()
except Exception:
    pass

# D.5 shared/kb_scan scanner registry bootstrap
try:
    from shared.kb_scan import bootstrap_scanners as _kb_bootstrap; _kb_bootstrap()
except Exception:
    pass

# Stage E.2 · Sentry init (env DSN · 缺 silent skip · 必须在 add_middleware 前)
try:
    from monitoring_service.sentry_init import init_sentry as _init_sentry
    _init_sentry()
except Exception:  # noqa: BLE001
    pass

app = FastAPI(title="Zhongan Credit AI — Portal API", version="2.2")

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


# ---------------------------------------------------------------------------
# Tier 0.1 · Production startup fail-fast check (PM 5/7 拍板 · Codex R2 加)
# ---------------------------------------------------------------------------
try:
    from shared.production_check import run_startup_checks
    _STARTUP_REPORT = run_startup_checks()  # production raise · dev warn
except RuntimeError as _e:
    print(f"[api_server] PRODUCTION STARTUP FAILED: {_e}", file=sys.stderr)
    raise  # production 模式 fail fast 抛
except ImportError as _e:
    print(f"[api_server] production_check unavailable: {_e}", file=sys.stderr)


@app.get("/api/_/health")
def health_check():
    """Tier 0.1 · 健康检查 endpoint · 暴露 startup check 结果."""
    try:
        from shared.production_check import run_startup_checks
        return run_startup_checks(raise_on_fail=False)
    except (ImportError, AttributeError) as e:
        return {"mode": "unknown", "ok": False, "error": str(e)}


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
# Auth + RBAC · Stage D.1 · 2026-04-28 · onboarding W-D1-A2-auth-rbac-backend
# Spec: docs/contracts/auth-protocol.md v1.0 (`4e8310b` Stage A.4)
# 模块: auth_service/{users,jwt_util,rbac,dependencies}.py
# ---------------------------------------------------------------------------

from auth_service.dependencies import COOKIE_NAME, require_user  # noqa: E402
from auth_service.jwt_util import JWT_EXP_HOURS, JWTError, issue, verify  # noqa: E402
from auth_service.rbac import access_for, demo_mode_visible  # noqa: E402
from auth_service.users import authenticate, get_user_public  # noqa: E402

# Cookie strategy (per auth-protocol.md §5)
_COOKIE_MAX_AGE = JWT_EXP_HOURS * 3600
_COOKIE_SECURE = os.environ.get("AUTH_COOKIE_SECURE", "").lower() in ("1", "true", "yes")
_COOKIE_SAMESITE = "lax"


class LoginRequest(BaseModel):
    user_id: str
    password: str


@app.post("/api/auth/login")
async def auth_login(req: LoginRequest, response: Response):
    """Auth login · bcrypt verify + 签 JWT + Set-Cookie httpOnly.

    Body: { user_id, password }
    Returns: { token, user, roles } on success · 401 on bad creds.
    Set-Cookie: zhongan_auth=<jwt>; HttpOnly; SameSite=Lax; Max-Age=86400
                Secure 仅 production (AUTH_COOKIE_SECURE=true).
    """
    if not req.user_id or not req.password:
        raise HTTPException(
            400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "user_id 和 password 必填"}},
        )
    user = authenticate(req.user_id, req.password)
    if user is None:
        raise HTTPException(
            401,
            detail={"error": {"code": "AUTH_FAILED", "message": "账号或密码错误"}},
        )
    token = issue(user["id"], user["role"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite=_COOKIE_SAMESITE,
        secure=_COOKIE_SECURE,
        path="/",
    )
    return {
        "token": token,
        "user": user,
        "roles": [user["role"]],
        "accessibleAgents": access_for(user["role"]),
    }


@app.get("/api/auth/me")
async def auth_me(payload=Depends(require_user)):
    """Auth me · 解 cookie → 返当前 user + roles + accessibleAgents.

    401 if no cookie / invalid / expired (走 require_user dependency 标准化).
    """
    user_id = payload.get("sub", "")
    user = get_user_public(user_id)
    if not user:
        raise HTTPException(
            401,
            detail={"error": {"code": "AUTH_USER_NOT_FOUND",
                              "message": f"token sub 不在 USERS: {user_id}"}},
        )
    return {
        "user": user,
        "roles": [user["role"]],
        "accessibleAgents": access_for(user["role"]),
        # Phase A.6 (2026-05-09) · demo_mode 双控 · per cross-agent-feedback-protocol
        # adjacent · env DEMO_MODE_VISIBLE=1 AND role in {admin, demo_user} 才 True
        # 默认 production env=0 安全 · 不暴露 demo 入口
        "demoModeAvailable": demo_mode_visible(user),
    }


@app.post("/api/auth/logout")
async def auth_logout(response: Response, zhongan_auth: str | None = Cookie(default=None)):
    """Auth logout · 清 cookie · 200 ok.

    幂等 · 即使无 cookie 也返 ok (防客户端反复点 logout 翻 401).
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=_COOKIE_SAMESITE,
        secure=_COOKIE_SECURE,
    )
    return {"ok": True, "had_cookie": bool(zhongan_auth)}


# ---------------------------------------------------------------------------
# Stage E.1 · LLM Audit Log (银保监合规留痕 · admin /api/audit/llm_calls)
# ---------------------------------------------------------------------------
try:
    from audit_service.api import register_audit_routes
    register_audit_routes(app)
except ImportError as _audit_import_err:
    print(f"[api_server] audit_service unavailable: {_audit_import_err}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Phase B-3 BE7 · Cross-agent decision ledger (银保监 jurisdiction-scoped audit)
# Distinct from audit_service.LLMCall — see docs/contracts/decision-ledger.md
# ---------------------------------------------------------------------------
try:
    from ledger_service.api import register_ledger_routes
    register_ledger_routes(app)
except ImportError as _ledger_import_err:
    print(f"[api_server] ledger_service unavailable: {_ledger_import_err}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Phase C Track A+B · 客户画像 (A1) + 决策 (A2) + 人工确认 (A3) + 血缘 (B1+B2)
# 跨 Agent 端到端流程 · 用 CRM contract 15 字段 schema 严格校验
# ---------------------------------------------------------------------------
try:
    from shared.customer_aggregator import aggregate_customer_profile, list_customers
    from shared.ai_decision import build_decision
    from shared.decision_review import submit_review, get_reviews, get_decision_status
    from shared.data_lineage import get_lineage_store
    # Tier 0.2 · API envelope (PM 5/7 拍板) · 4 critical endpoint 用 envelope
    from shared.api_envelope import envelope_ok, envelope_error, envelope_degraded

    # === A1 客户画像聚合 ===
    @app.get("/api/customer/list")
    def customer_list(rm: Optional[str] = Query(None, description="RM 工号过滤")):
        """列出客户 · 可选 RM 过滤. Tier 0.2 envelope."""
        return envelope_ok(data={"items": list_customers(rm_id=rm)})

    @app.get("/api/customer/{customer_id}/profile")
    def customer_profile(customer_id: str):
        """聚合客户画像 · CRM 15 字段 + 跨 Agent 历史. Tier 0.2 envelope."""
        result = aggregate_customer_profile(customer_id)
        if result is None:
            return envelope_error(
                category="validation",
                origin="data",
                message=f"客户 {customer_id} 不存在",
            )
        # consent 检查 · 未授权返 degraded (业务可见但 banner)
        consent = result.get("customer", {}).get("consent_status")
        if consent != "granted":
            return envelope_degraded(
                data=result,
                reason=f"customer-consent-{consent}",
                origin="business",
            )
        return envelope_ok(data=result)

    # === A2 AI 决策建议 ===
    class DecisionBuildRequest(BaseModel):
        customer_id: str
        intent: str = "ai_advice_proactive"

    @app.post("/api/decision/build")
    def decision_build(req: DecisionBuildRequest):
        """端到端 AI 决策 · Tier 0.2 envelope + 0.3 honest metadata."""
        decision = build_decision(customer_id=req.customer_id, intent=req.intent)
        if decision.get("block"):
            return envelope_error(
                category="business_rule" if "PIPL" in (decision.get("block_reason") or "") else "validation",
                origin="business",
                message=decision.get("block_reason") or "决策受阻",
                details={"decision_id": decision.get("decision_id"), "customer_id": req.customer_id},
            )
        # Tier 0.3 · 当前 ai_decision 是 rule-fallback-no-llm (mock fallback) · 用 degraded 标
        is_llm = decision.get("metadata", {}).get("is_llm_grounded", False)
        if not is_llm:
            return envelope_degraded(
                data=decision,
                reason="llm-not-wired-rule-fallback",
                origin="llm",
            )
        return envelope_ok(data=decision)

    # === A3 人工确认工作台 ===
    class DecisionReviewRequest(BaseModel):
        decision_id: str
        reviewer: str
        action: str  # "accept" / "modify" / "reject"
        reason: str = ""
        modified_content: Optional[dict] = None

    @app.post("/api/decision/{decision_id}/review")
    def decision_review_submit(decision_id: str, req: DecisionReviewRequest):
        """RM 提交 review (accept/modify/reject) · 写 ledger + lineage + audit."""
        if req.decision_id != decision_id:
            raise HTTPException(status_code=400, detail="decision_id 路径与 body 不一致")
        result = submit_review(
            decision_id=req.decision_id,
            reviewer=req.reviewer,
            action=req.action,
            reason=req.reason,
            modified_content=req.modified_content,
        )
        if result.get("block"):
            raise HTTPException(status_code=400, detail=result.get("block_reason"))
        return result

    @app.get("/api/decision/{decision_id}/reviews")
    def decision_reviews_get(decision_id: str):
        """查询一笔决策的 review history."""
        return {
            "decision_id": decision_id,
            "status": get_decision_status(decision_id),
            "reviews": get_reviews(decision_id),
        }

    # === B2 血缘 UI 接口 (Tier 0.2 envelope) ===
    @app.get("/api/lineage/decision/{decision_id}")
    def lineage_by_decision(decision_id: str):
        """查询一笔决策的所有字段血缘 (B1 sqlite store)."""
        store = get_lineage_store()
        rows = store.query_by_decision(decision_id)
        return envelope_ok(data={
            "decision_id": decision_id,
            "lineage_count": len(rows),
            "records": rows,
        })

    @app.get("/api/lineage/field")
    def lineage_by_field(path: str = Query(..., description="字段路径")):
        """查询某字段路径的最近血缘."""
        store = get_lineage_store()
        rows = store.query_by_field(path, limit=50)
        return envelope_ok(data={
            "field_path": path,
            "lineage_count": len(rows),
            "records": rows,
        })

    @app.get("/api/lineage/stats")
    def lineage_stats():
        """全局血缘统计."""
        return envelope_ok(data=get_lineage_store().stats())

    # === A5 走访导出物 + C1 业务指标看板 ===
    from shared.walkthrough_export import build_walkthrough_docx, build_walkthrough_pdf
    from shared.business_metrics import compute_metrics
    from fastapi.responses import FileResponse

    class WalkthroughExportRequest(BaseModel):
        decision_id: str
        format: str = "docx"  # "docx" or "pdf"

    @app.post("/api/decision/{decision_id}/export")
    def decision_export(decision_id: str, req: WalkthroughExportRequest):
        """导出走访报告 word/pdf · 含 customer 画像 + 决策 + review history + lineage."""
        if req.decision_id != decision_id:
            raise HTTPException(status_code=400, detail="decision_id 路径与 body 不一致")
        if req.format == "docx":
            path = build_walkthrough_docx(decision_id)
        elif req.format == "pdf":
            path = build_walkthrough_pdf(decision_id)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {req.format}")
        if path is None:
            raise HTTPException(status_code=500, detail="导出失败 · 检查 python-docx / reportlab 安装")
        return FileResponse(str(path), filename=path.name)

    @app.get("/api/metrics/business")
    def metrics_business(
        days: int = Query(30, description="时间窗 · 默认 30 天"),
        rm: Optional[str] = Query(None, description="RM 工号过滤"),
    ):
        """业务指标看板 · 5 指标 (Tier 0.2 envelope · 数据源内存 · 标 degraded)."""
        m = compute_metrics(date_range_days=days, rm_id=rm)
        # 现 review_events 是内存 store · 重启丢 · 标 degraded
        return envelope_degraded(
            data=m,
            reason="metrics-source-in-memory",
            origin="persistence",
        )

    print("[api_server] Phase C Track A+B+C routes mounted (A1/A2/A3/A5/B1/B2/C1)", file=sys.stderr)
except ImportError as _phasec_import_err:
    print(f"[api_server] Phase C Track A+B unavailable: {_phasec_import_err}", file=sys.stderr)


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
    rating: int | None = None     # 1-5 满意度 (Sprint 2 决策 1 · None=未评分)


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """接收审贷员对 Agent 输出的修改反馈，按日 JSONL 沉淀 + 写 audit log。

    1. 写入路径：data/feedback/YYYY-MM-DD.jsonl（数据飞轮第 3 环 · 离线脚本消费）
    2. 同时记一条 audit_service.LLMCall · endpoint=/api/feedback ·
       admin 通过 GET /api/audit/llm_calls?endpoint=/api/feedback 可查 modify 流水
       (Phase B BE10 · 银保监合规留痕 · 不重 A/B 平台)
    """
    allowed = {"channel", "credit", "alert", "compliance", "report", "riskctrl"}
    if req.agent not in allowed:
        raise HTTPException(400, f"agent must be one of {sorted(allowed)}")

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    path = PROJECT_ROOT / "data" / "feedback" / f"{date}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    if req.rating is not None and not (1 <= req.rating <= 5):
        raise HTTPException(400, "rating must be 1-5 or null")

    record = {
        "timestamp": now.isoformat(),
        "agent": req.agent,
        "session_id": req.session_id,
        "user_id": req.user_id,
        "original_output": req.original_output,
        "user_correction": req.user_correction,
        "correction_reason": req.correction_reason,
        "rating": req.rating,
    }
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        raise HTTPException(500, f"write feedback failed: {e}") from e

    # Audit modify trail · silent fail · 不阻断主流程 (审贷员反馈不能因 audit 故障丢)
    try:
        from audit_service.recorder import LLMCall, default_recorder
        original_json = json.dumps(req.original_output, ensure_ascii=False)
        correction_json = json.dumps(req.user_correction, ensure_ascii=False)
        default_recorder().record(LLMCall(
            ts=now.isoformat(timespec="seconds"),
            user_id=req.user_id,
            agent_id=req.agent,
            endpoint="/api/feedback",
            model="user-feedback",
            prompt=original_json,
            response=correction_json,
            error=req.correction_reason or None,
        ))
    except Exception as audit_err:  # noqa: BLE001
        print(f"[api_server] audit modify record failed: {audit_err}", file=sys.stderr)

    return {"status": "ok", "path": str(path.relative_to(PROJECT_ROOT))}


def _resolve_admin_dep():
    """lazy admin dep · auth_service 缺时返 stub (本地 dev / 未 cherry-pick · 复用
    audit_service.api 模式)."""
    try:
        from auth_service.dependencies import require_user as _require
        return _require
    except ImportError:
        async def _stub() -> dict:
            return {"sub": "anonymous", "role": "admin"}
        return _stub


def _check_admin_role(user: dict) -> None:
    role = (user or {}).get("role", "")
    if role != "admin":
        raise HTTPException(
            403,
            detail={
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": "feedback admin requires admin role",
                    "details": {"role": role},
                },
            },
        )


_FEEDBACK_ADMIN_DEP = _resolve_admin_dep()


@app.get("/api/feedback")
async def feedback_admin_list(
    user: dict = Depends(_FEEDBACK_ADMIN_DEP),
    agent_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="ISO date · 默认无下界"),
    date_to: str | None = Query(default=None, description="ISO date · 默认无上界"),
    rating: str | None = Query(default=None, description="CSV · 4,5"),
    user_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None, description="last id 'date:lineno'"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Admin filter list · Sprint 2 决策 1 · 4 filter + cursor pagination."""
    _check_admin_role(user)
    from feedback_admin import query_feedback
    try:
        return query_feedback(
            PROJECT_ROOT / "data" / "feedback",
            agent_id=agent_id,
            date_from=date_from,
            date_to=date_to,
            rating=rating,
            user_id=user_id,
            cursor=cursor,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/feedback/export")
async def feedback_admin_export(
    user: dict = Depends(_FEEDBACK_ADMIN_DEP),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    agents: str | None = Query(default=None, description="CSV agent ids · 默认全部"),
):
    """Admin export zip · per-agent 1 jsonl · application/zip · 流式不内存爆."""
    _check_admin_role(user)
    from fastapi.responses import Response
    from feedback_admin import build_export_zip
    agent_list = [a.strip() for a in agents.split(",") if a.strip()] if agents else None
    try:
        zip_bytes = build_export_zip(
            PROJECT_ROOT / "data" / "feedback",
            date_from=date_from,
            date_to=date_to,
            agents=agent_list,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    df_label = (date_from or "all")[:10]
    dt_label = (date_to or "all")[:10]
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="feedback_{df_label}_to_{dt_label}.zip"'
            ),
        },
    )


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
    target_agent: str = ""  # "" / "channel" / "credit" / "alert" / "compliance" / "report" / "riskctrl"


# 6 Agent 角色 system prompt (2026-04-27 · 加 @agent 路由支持 + archive 内 ConversationPanel 真接)
_AGENT_SYSTEMS = {
    "channel": "你是 Agent1 获客 (Scout) · 根据客户经理描述生成获客线索 / look-alike 推荐。回复 1-3 句·不编造数字 / 客户名 · 没有依据时显式说「需要查询」。",
    "report": "你是 Agent6 报告 · 辅助客户经理 / 审贷员处理材料 → 报告生成。回复 1-3 句·不编造内容。",
    "credit": "你是 Agent3 授信 · 辅助审贷员评分 / 红线判定。回复 1-3 句·不编造决策结果。",
    "alert": "你是 Agent4 预警 · 分析在贷客户行为信号 + 红/黄/绿榜单。回复 1-3 句·不编造预警事件。",
    "compliance": "你是 Agent5 合规 · 解析新政策与业务制度冲突点。回复 1-3 句·不编造政策条款。",
    "riskctrl": "你是 Agent2 风控 · 辅助风险经理写 DSL + 回测。回复 1-3 句·不编造样本数。",
}
_AGENT_TO_ID = {
    "channel": "agent_channel",
    "report": "agent_report",
    "credit": "agent_credit",
    "alert": "agent_alert",
    "compliance": "agent_compliance",
    "riskctrl": "agent_riskctrl",
}
_DEFAULT_SYSTEM = (
    "你是信贷 AI 助手·在客户经理 / 审贷员 / 合规官的协作 IM 工作台。"
    "回复简短·直接·1-3 句。"
    "涉及信贷决策时建议用户调相应 Agent (Agent1 获客 / Agent3 授信 / Agent4 预警 / Agent5 合规 / Agent6 报告)。"
    "不编造数字 / 政策 / 客户资料 · 没有依据时显式说「需要查询」。"
)


@app.post("/api/im/send")
async def im_send(
    req: ImSendRequest,
    zhongan_auth: str | None = Cookie(default=None),  # noqa: ARG001 · W-FIX2: 兼容 cookie auth, legacy 路径不强制
):
    """IM 对话 · DeepSeek + agent routing (target_agent 选不同 system prompt)。

    单 turn · 无 thread persistence · 无 SSE。后续扩 history + SSE + workflow。
    archive 内 ConversationPanel 通过 target_agent="channel/report/..." 调对应 agent prompt。

    W-FIX2-A2: legacy endpoint · 接 zhongan_auth cookie param 让 frontend `credentials:"include"`
    一致 · 但当前 LLM 单 turn 不依赖 user_id · 所以不强制鉴权 (后续 deprecate 后改走 /api/im/messages)。
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
from im_service.auth import (  # noqa: E402
    TokenInvalidError,
    decode_jwt_cookie as _im_decode_jwt_cookie,
    decode_token as _im_decode_token,
)
from im_service.schemas import (  # noqa: E402
    CreateThreadRequest,
    ImMessage,
    SendMessageRequest,
    SendMessageResponse,
)
from im_service.websocket import im_websocket_endpoint, manager as _im_ws_manager  # noqa: E402

_im_threads.init_schema()


def _resolve_im_user(
    zhongan_auth: str | None,
    authorization: str | None,
    token_q: str | None,
) -> str:
    """解析 IM 当前 user_id · 三 source 优先级 (per W-FIX2-A2-im-cookie-auth):

      1. **cookie zhongan_auth** (D.1 httpOnly · 生产路径): 走 auth_service.jwt_util.verify
      2. **Authorization Bearer** (legacy / demo 兼容): demo-<user_id> 或真 JWT
      3. **?token=<...>** query (legacy / WS): 同上

    任一成功立即返 · 全失败抛 401。bug #8 根因: frontend 之前读
    `auth_token` cookie 但 D.1 真 cookie 名 `zhongan_auth` (httpOnly · JS 不可读)
    · 现 backend 优先吃 cookie · frontend 走 `credentials: "include"` 让 browser 自动带。
    """
    cookie_uid = _im_decode_jwt_cookie(zhongan_auth)
    if cookie_uid:
        return cookie_uid

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
                              "message": "请先登录 · 缺 cookie / token"}},
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
    zhongan_auth: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """列 currentUser 在 participants 里的 thread (按 last_message_at desc)."""
    user_id = _resolve_im_user(zhongan_auth, authorization, token)
    items = _im_threads.list_threads_for_user(user_id)
    return {"user_id": user_id, "threads": items}


@app.get("/api/im/threads/{thread_id}/messages")
async def im_list_messages(
    thread_id: str,
    before: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    zhongan_auth: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """历史消息 paginated · before 是 created_at cursor (ASC) · 限 currentUser 在 thread."""
    user_id = _resolve_im_user(zhongan_auth, authorization, token)
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
    zhongan_auth: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """创建 thread · currentUser 自动加入 participants."""
    user_id = _resolve_im_user(zhongan_auth, authorization, token)
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
    zhongan_auth: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """标记 thread 已读 · currentUser 必须在 participants."""
    user_id = _resolve_im_user(zhongan_auth, authorization, token)
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
    zhongan_auth: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
):
    """新 send 端点 · 持久化 + WebSocket broadcast · 替代 /api/im/send (后者保留向后兼容)."""
    user_id = _resolve_im_user(zhongan_auth, authorization, token)
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
    """WebSocket 入口 · 优先 zhongan_auth cookie (W-FIX2-A2 · 浏览器 same-origin 自动带)
    · 失败回退 query param token=<jwt> (legacy / 非 same-origin 客户端)。
    业务逻辑全在 im_service.websocket。
    """
    # 浏览器 same-origin WebSocket 自动带 cookie · starlette 通过 websocket.cookies 暴露
    cookie_token = ""
    try:
        cookie_token = websocket.cookies.get("zhongan_auth", "") or ""
    except (AttributeError, TypeError):
        cookie_token = ""
    await im_websocket_endpoint(websocket, token=token, cookie_token=cookie_token)


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_server:app", host="127.0.0.1", port=port, reload=False)
