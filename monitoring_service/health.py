# -*- coding: utf-8 -*-
"""Extended health check (Stage E.2 · onboarding W-E2-A3).

按 onboarding · 验各 component:
- DeepSeek API ping (chat with "ok" 返 ok) · 缺 key skip · 失败标 down
- Tavily API ping (1 query 验 401 / quota) · 缺 key skip
- sqlite DB (audit + im threads) · stat + integrity check
- 6 Agent endpoint (HEAD ping local 进程内 · 不真打外部)

设计:
- 单 endpoint /health/extended · 同步执行所有 check (并发 < 5s · 超时 fail-fast)
- 总状态 status: ok / degraded / down · 任一 critical down → status=down
- 不调真外部 API 是 default · 显式 ping=true 才打 (省 quota)
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Component check 抽象
# ---------------------------------------------------------------------------


def _ok(component: str, **extras: Any) -> dict[str, Any]:
    return {"component": component, "status": "ok", **extras}


def _degraded(component: str, reason: str, **extras: Any) -> dict[str, Any]:
    return {"component": component, "status": "degraded", "reason": reason, **extras}


def _down(component: str, reason: str, **extras: Any) -> dict[str, Any]:
    return {"component": component, "status": "down", "reason": reason, **extras}


def _skipped(component: str, reason: str) -> dict[str, Any]:
    return {"component": component, "status": "skipped", "reason": reason}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_sentry() -> dict[str, Any]:
    """Sentry init 状态 · 不打远端."""
    try:
        from monitoring_service.sentry_init import get_init_status
        s = get_init_status()
    except ImportError:
        return _skipped("sentry", "module unavailable")
    if not s.get("available"):
        return _skipped("sentry", "sentry_sdk not installed")
    if not s.get("dsn_present"):
        return _skipped("sentry", "SENTRY_DSN not set")
    if s.get("initialized"):
        return _ok("sentry", environment=s.get("environment", ""))
    return _degraded("sentry", s.get("skip_reason", "init failed"))


def check_metrics() -> dict[str, Any]:
    """Prometheus init 状态 · 不打远端."""
    try:
        from monitoring_service.metrics import is_prometheus_available
    except ImportError:
        return _skipped("metrics", "module unavailable")
    if is_prometheus_available():
        return _ok("metrics", exporter="prometheus_client")
    return _skipped("metrics", "prometheus_client not installed (NoOp mode)")


def check_sqlite_audit() -> dict[str, Any]:
    """audit log dir 是否存在 + 可写."""
    audit_dir = PROJECT_ROOT / "data" / "audit"
    if not audit_dir.exists():
        return _degraded("sqlite_audit", "data/audit dir missing", path=str(audit_dir))
    try:
        # 验 dir 可写 (touch + remove)
        probe = audit_dir / ".healthcheck.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        return _down("sqlite_audit", f"not writable: {e}", path=str(audit_dir))
    # 数文件统计
    files = list(audit_dir.glob("*.jsonl"))
    return _ok("sqlite_audit", path=str(audit_dir), audit_files=len(files))


def check_sqlite_im() -> dict[str, Any]:
    """im_service threads.db 验 schema."""
    db_path = PROJECT_ROOT / "data" / "im" / "threads.db"
    if not db_path.exists():
        return _degraded(
            "sqlite_im", "threads.db 不在 (尚未跑过 im_service)",
            path=str(db_path),
        )
    try:
        conn = sqlite3.connect(str(db_path), timeout=2.0)
        try:
            cur = conn.execute("PRAGMA integrity_check")
            row = cur.fetchone()
            integrity = row[0] if row else "unknown"
            tables_cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = sorted(r[0] for r in tables_cur.fetchall())
        finally:
            conn.close()
    except sqlite3.Error as e:
        return _down("sqlite_im", f"sqlite error: {e}", path=str(db_path))
    if integrity != "ok":
        return _down("sqlite_im", f"integrity check: {integrity}",
                     path=str(db_path), tables=tables)
    return _ok("sqlite_im", path=str(db_path), tables=tables, integrity=integrity)


def check_compliance_storage() -> dict[str, Any]:
    """data/compliance + data/alert sessions dir."""
    info: dict[str, Any] = {"compliance_sessions": 0, "alert_sessions": 0}
    compli_dir = PROJECT_ROOT / "data" / "compliance" / "sessions"
    alert_dir = PROJECT_ROOT / "data" / "alert" / "sessions"
    if compli_dir.exists():
        info["compliance_sessions"] = len(list(compli_dir.glob("*.json")))
    if alert_dir.exists():
        info["alert_sessions"] = len(list(alert_dir.glob("*.json")))
    return _ok("storage", **info)


async def check_deepseek_ping(*, timeout_s: float = 5.0) -> dict[str, Any]:
    """打 DeepSeek API · 缺 key 跳过 · 失败标 down · 真消耗 1 LLM call."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return _skipped("llm_deepseek", "DEEPSEEK_API_KEY not set")
    try:
        from llm import LLMClient  # type: ignore[import]
    except ImportError as e:
        return _down("llm_deepseek", f"llm module import failed: {e}")

    def _sync_ping() -> tuple[bool, str, float]:
        t0 = time.perf_counter()
        try:
            client = LLMClient(provider="deepseek", api_key=api_key)
            reply = client.simple_chat(
                "你是健康检查 bot · 只回复 'ok' 一个词",
                "回复 ok",
                temperature=0.0,
            )
            ok = bool(reply and "ok" in reply.lower())
            return ok, (reply or "")[:80], time.perf_counter() - t0
        except Exception as e:  # noqa: BLE001
            return False, f"{type(e).__name__}: {e}", time.perf_counter() - t0

    try:
        ok, reply, dur = await asyncio.wait_for(
            asyncio.to_thread(_sync_ping), timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        return _down("llm_deepseek", f"ping timeout > {timeout_s}s")
    if ok:
        return _ok("llm_deepseek", reply_snippet=reply, duration_s=round(dur, 3))
    return _down("llm_deepseek", reply or "no reply", duration_s=round(dur, 3))


async def check_tavily_ping(*, timeout_s: float = 5.0) -> dict[str, Any]:
    """打 Tavily 1 query · 缺 key skip · 401 标 down · 失败标 degraded."""
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return _skipped("external_tavily", "TAVILY_API_KEY not set")

    def _sync_ping() -> tuple[bool, str, float, Optional[int]]:
        t0 = time.perf_counter()
        try:
            from shared.kb_scan.tavily_client import TavilyClient  # type: ignore[import]
        except ImportError as e:
            return False, f"tavily_client import failed: {e}", 0.0, None
        try:
            client = TavilyClient(api_key=api_key)
            raw = client.search("健康检查", max_results=1, search_depth="basic")
            ok = isinstance(raw, dict) or (isinstance(raw, list) and len(raw) >= 0)
            return ok, "ok" if ok else "unexpected response", time.perf_counter() - t0, 200
        except Exception as e:  # noqa: BLE001
            etype = type(e).__name__
            status = None
            msg = str(e)
            if "401" in msg or "unauthorized" in msg.lower():
                status = 401
            return False, f"{etype}: {msg[:120]}", time.perf_counter() - t0, status

    try:
        ok, reply, dur, status = await asyncio.wait_for(
            asyncio.to_thread(_sync_ping), timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        return _down("external_tavily", f"ping timeout > {timeout_s}s")
    if ok:
        return _ok("external_tavily", message=reply, duration_s=round(dur, 3))
    if status == 401:
        return _down("external_tavily", f"401 unauthorized: {reply}",
                     duration_s=round(dur, 3))
    return _degraded("external_tavily", reply, duration_s=round(dur, 3))


def check_agent_routes(app: Any) -> dict[str, Any]:
    """6 Agent endpoint 是否注册到 FastAPI app."""
    expected = {
        "agent_channel": ["/api/channel/scenarios", "/api/channel/run"],
        "agent_credit": ["/api/credit/decision", "/api/credit/presets/{segment}"],
        "agent_report": ["/api/report/health"],
        "agent_compliance": ["/api/compliance/policy_scan", "/api/compliance/health"],
        "agent_alert": ["/api/alert/scan", "/api/alert/health"],
        "agent_riskctrl": ["/api/riskctrl/dsl_gen", "/api/riskctrl/health"],
    }
    if app is None:
        return _degraded("agents", "FastAPI app reference missing")
    routes = {getattr(r, "path", "") for r in app.routes if hasattr(r, "path")}
    coverage: dict[str, Any] = {}
    overall_ok = True
    for agent, paths in expected.items():
        # at least 1 path matched
        matched = [p for p in paths if p in routes]
        coverage[agent] = {
            "expected": paths,
            "matched": matched,
            "ok": len(matched) > 0,
        }
        if not matched:
            overall_ok = False
    if overall_ok:
        return _ok("agents", coverage=coverage)
    return _degraded("agents", "some agents missing routes", coverage=coverage)


# ---------------------------------------------------------------------------
# Aggregator · /health/extended endpoint
# ---------------------------------------------------------------------------


SEVERITY_RANK = {"ok": 0, "skipped": 0, "degraded": 1, "down": 2}


def _aggregate_status(checks: list[dict[str, Any]]) -> str:
    """worst component status · ok < degraded < down."""
    worst = "ok"
    for c in checks:
        s = c.get("status", "ok")
        if SEVERITY_RANK.get(s, 0) > SEVERITY_RANK.get(worst, 0):
            worst = s
    if worst == "down":
        return "down"
    if worst == "degraded":
        return "degraded"
    return "ok"


async def run_extended_health(
    app: Any = None,
    *,
    ping_external: bool = False,
    timeout_s: float = 5.0,
) -> dict[str, Any]:
    """主 entrypoint · /health/extended endpoint 调用.

    Args:
        app: FastAPI app (用于 agent route 检查)
        ping_external: True 才打 DeepSeek + Tavily (省 quota · default false)
        timeout_s: 单 ping 超时
    """
    started = time.perf_counter()

    # 同步 checks
    sync_checks: list[dict[str, Any]] = [
        check_sentry(),
        check_metrics(),
        check_sqlite_audit(),
        check_sqlite_im(),
        check_compliance_storage(),
        check_agent_routes(app),
    ]

    # 异步 external ping (可选)
    if ping_external:
        async_results = await asyncio.gather(
            check_deepseek_ping(timeout_s=timeout_s),
            check_tavily_ping(timeout_s=timeout_s),
            return_exceptions=True,
        )
        for r in async_results:
            if isinstance(r, BaseException):
                sync_checks.append(_down("external_ping", f"{type(r).__name__}: {r}"))
            else:
                sync_checks.append(r)
    else:
        # 标 skipped 让前端知道有这俩 component (但默认未 ping)
        sync_checks.append(_skipped("llm_deepseek", "external ping disabled (?ping=1 to enable)"))
        sync_checks.append(_skipped("external_tavily", "external ping disabled (?ping=1 to enable)"))

    overall = _aggregate_status(sync_checks)
    return {
        "status": overall,
        "duration_s": round(time.perf_counter() - started, 3),
        "ping_external": ping_external,
        "components": sync_checks,
        "summary": {
            "total": len(sync_checks),
            "ok": sum(1 for c in sync_checks if c.get("status") == "ok"),
            "degraded": sum(1 for c in sync_checks if c.get("status") == "degraded"),
            "down": sum(1 for c in sync_checks if c.get("status") == "down"),
            "skipped": sum(1 for c in sync_checks if c.get("status") == "skipped"),
        },
    }
