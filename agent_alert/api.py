# -*- coding: utf-8 -*-
"""agent_alert.api — Agent4 贷中预警 FastAPI 路由模块。

端点：
  POST /api/alert/scan          — 流式跑批量扫描 (SSE) · 完成后持久化
  POST /api/alert/demo/run      — Demo fixture 模式 (worker-A4-alert) · 不读 KB / 不调 LLM
  POST /api/alert/export_docx   — 命中清单 Word 报告本地导出 (W-FIX2 修 bug #6)
  GET  /api/alert/hitlist       — 取持久化红/黄/绿榜单 (latest 或 by session_id)
  GET  /api/alert/drill/{cid}   — 取单客户 drill detail + LLM 处置建议
  GET  /api/alert/health        — 健康探针

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- /scan SSE 业务逻辑走 agent_alert.scan_engine.run_scan_and_persist
  (Stage C onboarding W-C3-A3 · KB_DEMO 解锁 + Tavily 401 fallback)
- import 失败时 SSE 仍能 yield error 事件，前端不崩
- 输出前过 shared.qc.placeholder_guard (Task B 软降级模式)
- SSE done event 共形 envelope (worker-A4-alert · per docs/audit/A4-alert-draft.md §3
  + shared.sse_envelope.make_done) · 含 totals + hit_list (red/yellow/green) +
  top_cases + dispositions + kb_state · 前端 normalizeAlertSession 注入 liveData
- LLM caller 走 shared.llm_caller.make_text_caller · 替代直 LLMClient init
  (Cat 7 fix · per CLAUDE.md §3.6 · 自动 fallback chain + audit)

字段契约：见 docs/contracts/field-naming.md + docs/audit/A4-alert-draft.md
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402
from shared.sse_envelope import (  # noqa: E402
    DATA_SOURCE_LIVE,
    DATA_SOURCE_MOCK,
    DATA_SOURCE_MOCK_FALLBACK,
    DATA_SOURCE_MOCK_FORCED,
    encode_event,
    make_done,
    make_error_from_exception,
    make_stage,
)

from agent_alert.output_validator import soft_clean as _qc_scrub  # noqa: E402

# Stage W-FIX2 · audit log SSE-aware finally hook (silent fail if unavailable)
try:
    from audit_service.stream_helpers import audit_stream_event  # noqa: E402
except ImportError:
    def audit_stream_event(*_args, **_kwargs):  # type: ignore[no-redef]
        pass

app = FastAPI(title="Agent4 Alert Radar API", version="3.3")


@app.get("/api/alert/health")
async def alert_health():
    """Agent4 sub-app 健康探针 (与 portal /health 平级, 用于精细化故障定位)。"""
    return {"status": "ok", "agent": "agent_alert"}


class AlertScanRequest(BaseModel):
    scenario_key: str = ""               # e.g. "micro_credit_100"; 空 → 默认场景
    uploaded_files: list[str] | None = None
    provider: str | None = None
    api_key: str | None = None
    force_mock: bool = False             # 强制走 mock_pool · 不尝试 Tavily


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


class AlertDemoRunRequest(BaseModel):
    """Demo fixture run · 走 data/mock/workspace/alert/scenarios/<key>.json。

    与 /api/alert/scan 共形 done envelope · 但 mode=mock_forced · 不读 KB / 不调 LLM。
    """
    scenario_key: str = "baseline_100"


# ============================================================================
# stage 名映射 + done envelope builder
# ============================================================================


def _stage_for_event(evt: dict[str, Any]) -> str:
    """启发式: 把 agent yield evt → 5 stage 名 (kb_load / external_scan /
    internal_match / cross / summary).

    前端只需 ascending stage hint 来推 progress bar · 绝对精度不重要。
    """
    et = evt.get("type", "")
    if et == "tool_result":
        tool = (evt.get("tool") or "").lower()
        if "kb" in tool:
            return "kb_load"
        if "search" in tool or "provider" in tool:
            return "external_scan"
        if "disposit" in tool:
            return "summary"
    if et == "hit":
        return "cross"
    if et in ("hitlist", "session"):
        return "summary"
    if et == "thinking":
        msg = str(evt.get("content", ""))
        if "知识库" in msg or "装载" in msg:
            return "kb_load"
        if "搜索数据源" in msg or "搜索" in msg:
            return "external_scan"
        if "批量扫描" in msg:
            return "internal_match"
        if "处置" in msg:
            return "summary"
    return "scan"


def _hit_target_payload(hit: Any) -> dict:
    """读 HitItem.target.payload · 容忍 dict / pydantic obj 两种形态."""
    target = getattr(hit, "target", None) if not isinstance(hit, dict) else hit.get("target")
    if target is None:
        return {}
    payload = getattr(target, "payload", None) if not isinstance(target, dict) else target.get("payload")
    return payload or {}


def _grade_value(level: Any) -> str:
    """Risk level → red/yellow/green (snake) · 容忍 enum / str."""
    if hasattr(level, "value"):
        return str(level.value).lower()
    return str(level).lower()


def _to_compact_hit(hit: Any) -> dict:
    """HitItem → 前端 hit_list bucket 单条 (含 risk_level snake)."""
    payload = _hit_target_payload(hit)
    matched = list(getattr(hit, "matched_rules", None) or [])
    reasons = list(getattr(hit, "reasons", None) or [])
    return {
        "client_id": getattr(hit, "hit_id", None) or (hit.get("hit_id") if isinstance(hit, dict) else "") or "",
        "company_name": payload.get("company_name", ""),
        "amount": payload.get("credit_balance", "") or payload.get("amount", ""),
        "risk_level": _grade_value(getattr(hit, "level", None) if not isinstance(hit, dict) else hit.get("level")),
        "score": float(getattr(hit, "score", 0.0) if not isinstance(hit, dict) else hit.get("score", 0.0)),
        "matched_rules": matched,
        "reasons": reasons,
    }


def _to_top_case(hit: Any) -> dict:
    """HitItem → 前端 topCases 单条 (含 client_id + risk_level snake + triggers)."""
    payload = _hit_target_payload(hit)
    reasons = list(getattr(hit, "reasons", None) or [])
    matched = list(getattr(hit, "matched_rules", None) or [])
    triggers = (reasons or matched)[:4]
    return {
        "id": getattr(hit, "hit_id", None) or (hit.get("hit_id") if isinstance(hit, dict) else ""),
        "client_id": getattr(hit, "hit_id", None) or (hit.get("hit_id") if isinstance(hit, dict) else ""),
        "customer": payload.get("company_name", ""),
        "amount": payload.get("credit_balance", "") or payload.get("amount", ""),
        "risk_level": _grade_value(getattr(hit, "level", None) if not isinstance(hit, dict) else hit.get("level")),
        "triggers": triggers,
        "advice": "",
        "lastUpdate": "刚刚",
    }


def _serialize_dispositions(dispositions: Any) -> dict:
    """dict[str, DispositionPlan] → dict[client_id, advice_text]."""
    if not dispositions:
        return {}
    out: dict[str, str] = {}
    for name, plan in dispositions.items():
        if hasattr(plan, "model_dump"):
            d = plan.model_dump(mode="json")
        elif isinstance(plan, dict):
            d = plan
        else:
            d = {"advice": str(plan)}
        out[name] = str(d.get("advice", "") or d.get("content", "") or d.get("recommendation", ""))
    return out


def _build_done_envelope(
    *,
    hit_list: Any,
    dispositions: Any,
    session_id: str,
    scenario_key: str,
    mode_label: str,
    kb_summary: str,
) -> dict[str, Any]:
    """Build SSE done envelope · per docs/audit/A4-alert-draft.md §3.

    Frontend normalizeAlertSession 消费此结构 · 注入 liveData · 5 panel 切 live。

    Args:
        hit_list: HitList obj | None
        dispositions: dict[company_name, DispositionPlan]
        session_id: persisted session id ("" 表持久化失败)
        scenario_key: req.scenario_key 透传
        mode_label: build_alert_provider 给的 ("web_live" / "tavily_disabled" / ...)
        kb_summary: load_kb 输出摘要 · → kb_state
    """
    # data_source 映射 mode_label → 5 enum
    if mode_label == "web_live":
        data_source = DATA_SOURCE_LIVE
    elif mode_label == "demo_forced":
        data_source = DATA_SOURCE_MOCK_FORCED
    elif mode_label.startswith("web_fallback_"):
        data_source = DATA_SOURCE_MOCK_FALLBACK
    else:
        data_source = DATA_SOURCE_MOCK

    if hit_list is None:
        return make_done(
            data_source=data_source,
            session_id=session_id,
            metrics={"red": 0, "yellow": 0, "green": 0, "total": 0},
            summary="扫描未产出 hit_list (KB 未装载或样本为空)",
            scenario_key=scenario_key,
            kb_state=kb_summary,
            mode=mode_label,
        )

    hits = list(getattr(hit_list, "hits", None) or [])
    by_grade: dict[str, list[dict]] = {"red": [], "yellow": [], "green": []}
    for h in hits:
        bucket = _grade_value(getattr(h, "level", None))
        if bucket in by_grade:
            by_grade[bucket].append(_to_compact_hit(h))

    sorted_hits = sorted(
        hits,
        key=lambda h: float(getattr(h, "score", 0.0) or 0.0),
        reverse=True,
    )
    top_cases = [_to_top_case(h) for h in sorted_hits[:10]]

    red_count = int(getattr(hit_list, "red_count", 0))
    yellow_count = int(getattr(hit_list, "yellow_count", 0))
    green_count = int(getattr(hit_list, "green_count", 0))
    total_scanned = int(getattr(hit_list, "total_scanned", red_count + yellow_count + green_count))

    summary = (
        f"扫描 {total_scanned} 户 · "
        f"红 {red_count} / 黄 {yellow_count} / 绿 {green_count}"
    )

    return make_done(
        panels={
            "hit_list": by_grade,
            "top_cases": top_cases,
            "dispositions": _serialize_dispositions(dispositions),
        },
        metrics={
            "red": red_count,
            "yellow": yellow_count,
            "green": green_count,
            "total_scanned": total_scanned,
        },
        data_source=data_source,
        session_id=session_id,
        summary=summary,
        scenario_key=scenario_key,
        kb_state=kb_summary,
        mode=mode_label,
        totals={"red": red_count, "yellow": yellow_count, "green": green_count},
    )


# ============================================================================
# Streaming generator
# ============================================================================


def _alert_event_stream(req: AlertScanRequest):
    """生成器 — yield SSE-encoded lines · try/except/finally 内部记 audit (bug #11 修).

    走 scan_engine.run_scan_and_persist · 含 Tavily 401 fallback (Q-040) +
    持久化到 data/alert/sessions/{session_id}.json + latest pointer。

    cat 4 fix (worker-A4-alert): 末尾 yield 共形 done envelope (panels/metrics/data_source)。
    cat 7 fix: LLM caller 走 shared.llm_caller (本 stream 不直 init LLMClient)。
    """
    t0 = time.time()
    err: str | None = None

    captured_hit_list: Any = None
    captured_dispositions: Any = None
    captured_session_id: str = ""
    captured_mode: str = ""
    captured_kb_summary: str = ""

    try:
        try:
            from agent_alert.scan_engine import run_scan_and_persist
        except ImportError as e:
            err = f"ImportError: {e}"
            yield encode_event(make_error_from_exception(e, code="SCAN_ENGINE_IMPORT_FAILED"))
            return

        try:
            for evt in run_scan_and_persist(
                scenario_key=req.scenario_key or "",
                uploaded_files=req.uploaded_files,
                api_key=req.api_key or "dummy",
                provider=req.provider or "deepseek",
                force_mock=bool(req.force_mock),
            ):
                # 捕获 raw refs (在 jsonable 转换前 · 保留 HitList obj)
                etype = evt.get("type", "") if isinstance(evt, dict) else ""
                if etype == "hitlist":
                    captured_hit_list = evt.get("hitlist")
                    captured_dispositions = evt.get("dispositions")
                elif etype == "session":
                    captured_session_id = str(evt.get("session_id", ""))
                    captured_mode = str(evt.get("mode", ""))
                elif etype == "tool_result" and (evt.get("tool") or "").lower() == "load_kb":
                    captured_kb_summary = str(evt.get("result", ""))

                payload = to_jsonable(evt)
                cleaned, hits = _qc_scrub(payload)
                stage_name = _stage_for_event(evt if isinstance(evt, dict) else {})
                wrap: dict[str, Any] = make_stage(
                    stage_name,
                    "running",
                    payload=cleaned,
                )
                if hits:
                    wrap["_qc_placeholder_hits"] = hits
                yield encode_event(wrap)

            # final stage tag (frontend stepIdx → 4 / summary)
            yield encode_event(make_stage("summary", "done", message="扫描完成 · 准备 done envelope"))

            # done envelope · 共形 (panels + metrics + data_source + session_id)
            done_evt = _build_done_envelope(
                hit_list=captured_hit_list,
                dispositions=captured_dispositions,
                session_id=captured_session_id,
                scenario_key=req.scenario_key or "",
                mode_label=captured_mode,
                kb_summary=captured_kb_summary,
            )
            yield encode_event(done_evt)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            err = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            yield encode_event(make_error_from_exception(e))
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
    """贷中预警批量扫描 SSE — 装载 KB → 双路交叉 → 进度/命中事件 → 处置建议汇总 → 持久化.

    QC blocker (CLAUDE.md §8): 每条 SSE payload 前置走 placeholder_guard,
    占位符残留软降级标"未能自动填写"并在事件挂 _qc_placeholder_hits 元数据。

    完成后写 data/alert/sessions/{session_id}.json + 更新 latest pointer ·
    后续 GET /api/alert/hitlist · GET /api/alert/drill/{cid} 消费同一份产物。

    Done envelope (worker-A4-alert · 2026-04-29): 共形 panels + metrics + data_source ·
    panels = {hit_list, top_cases, dispositions} · 前端 normalizeAlertSession 注入 liveData。
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


# ============================================================================
# POST /api/alert/demo/run — Demo fixture mode (worker-A4-alert · 2026-04-29)
# ============================================================================


SCENARIOS_DIR = PROJECT_ROOT / "data" / "mock" / "workspace" / "alert" / "scenarios"


def _load_scenario_fixture(scenario_key: str) -> dict[str, Any]:
    """从 data/mock/workspace/alert/scenarios/<key>.json 读 fixture。

    反 5 原则 #5 环境边界: fixture 是稳态 internal context · 不替 Agent
    做"本该外搜"的工作 · 故 fixture 不含答案字段 (难度档 / 风险评级是 Agent
    自己根据规则算 · 这里只给原始命中 + 元信息)。
    """
    import json as _json
    safe_key = (scenario_key or "baseline_100").strip()
    if not safe_key.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail=f"invalid scenario_key={safe_key!r}")
    path = SCENARIOS_DIR / f"{safe_key}.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"scenario fixture not found: {safe_key}")
    return _json.loads(path.read_text(encoding="utf-8"))


def _alert_demo_event_stream(req: AlertDemoRunRequest):
    """Demo SSE 流 · 5 stage 节拍 + done envelope (mock_forced)。

    与 /api/alert/scan 共形 envelope shape · 但不读 KB / 不调 LLM / 不持久化。
    用于 worker-A4-alert Playwright smoke + 客户走访演示。
    """
    try:
        fixture = _load_scenario_fixture(req.scenario_key)
    except HTTPException:
        raise
    except (RuntimeError, ValueError, OSError, AttributeError, KeyError) as e:
        yield encode_event(make_error_from_exception(e, code="FIXTURE_LOAD_FAILED"))
        return

    stages = ["kb_load", "external_scan", "internal_match", "cross", "summary"]
    for stage in stages:
        yield encode_event(make_stage(stage, "done", message=f"demo · {stage} · fixture={req.scenario_key}"))
        time.sleep(0.25)

    done_evt = make_done(
        panels={
            "hit_list": fixture.get("hit_list", {}),
            "top_cases": fixture.get("top_cases", []),
            "dispositions": fixture.get("dispositions", {}),
        },
        metrics=fixture.get("metrics", {}),
        data_source=DATA_SOURCE_MOCK_FORCED,
        session_id=f"demo-{req.scenario_key}",
        summary=fixture.get("summary", ""),
        scenario_key=req.scenario_key,
        kb_state=fixture.get("kb_state", "demo · 不读 KB"),
        mode="demo_forced",
        totals=fixture.get("totals", {}),
        industry_distribution=fixture.get("industry_distribution", []),
        signal_heatmap=fixture.get("signal_heatmap", []),
        reach_rate=fixture.get("reach_rate", []),
    )
    yield encode_event(done_evt)


@app.post("/api/alert/demo/run")
async def alert_demo_run(req: AlertDemoRunRequest):
    """Demo fixture mode (worker-A4-alert · 2026-04-29).

    与 /api/alert/scan 共形 done envelope shape · mode=mock_forced ·
    不读 KB / 不调 LLM / 不持久化 · 适合 Playwright smoke + 客户走访演示。

    Body: {scenario_key: "baseline_100" | "manuf_policy_event" | "judicial_news_dual"}
    """
    def gen():
        yield from _alert_demo_event_stream(req)
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ============================================================================
# POST /api/alert/export_docx — W-FIX2 bug #6 · 命中清单 Word 导出
# ============================================================================


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


# ============================================================================
# GET /api/alert/hitlist — 拉持久化红/黄/绿榜单 (Stage C · onboarding W-C3-A3)
# ============================================================================


@app.get("/api/alert/hitlist")
async def alert_hitlist(session_id: str = ""):
    """返回最新（或指定 session_id 的）扫描结果.

    Response:
      {session_id, generated_at, scenario_key, mode, hit_list: HitList, dispositions}
    404: 尚无任何扫描记录 / session_id 不存在
    """
    try:
        from agent_alert.scan_engine import HitListNotFoundError, load_hitlist
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"scan_engine import failed: {e}"}},
        ) from e

    try:
        return load_hitlist(session_id=session_id.strip())
    except HitListNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "HITLIST_NOT_FOUND",
                              "message": str(e),
                              "details": {"session_id": session_id}}},
        ) from e


# ============================================================================
# GET /api/alert/drill/{client_id} — 单客户 drill detail (Stage C · onboarding W-C3-A3)
# ============================================================================


@app.get("/api/alert/drill/{client_id}")
async def alert_drill(client_id: str, session_id: str = ""):
    """返回单客户 drill detail · 含 信号 timeline + 处置建议 (LLM 优先 / 模板兜底).

    Response:
      {client_id, company_name, level, score, matched_rules, reasons,
       signal_timeline, disposition, disposition_source}
    404: client_id 不在当前 hitlist
    """
    try:
        from agent_alert.scan_engine import (
            ClientNotFoundError,
            HitListNotFoundError,
            build_drill_payload,
            load_hitlist,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"scan_engine import failed: {e}"}},
        ) from e

    try:
        payload = load_hitlist(session_id=session_id.strip())
    except HitListNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "HITLIST_NOT_FOUND",
                              "message": str(e)}},
        ) from e

    # cat 7 fix (worker-A4-alert): LLM caller 走 shared.llm_caller · 替代直 LLMClient init
    llm_caller = _build_drill_llm_caller()

    try:
        return build_drill_payload(payload, client_id, llm_caller=llm_caller)
    except ClientNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "CLIENT_NOT_FOUND",
                              "message": str(e),
                              "details": {"client_id": client_id}}},
        ) from e


def _build_drill_llm_caller():
    """构造 (system, user) -> str caller · 走 shared.llm_caller.make_text_caller.

    cat 7 fix (worker-A4-alert · 2026-04-29 · per CLAUDE.md §3.6):
    - 自动 fallback chain (deepseek → dashscope · PIPL 境内优先)
    - 自动 audit log (region 字段 · 跨境调用可追溯)
    - 失败返 "" (与现有 build_drill_payload 兜底逻辑一致)

    无 DEEPSEEK_API_KEY 时 caller 仍可用 · 但 chat 内部抛 ProviderUnavailableError
    被 make_text_caller closure catch 返 "" · build_drill_payload 走模板兜底。
    """
    try:
        from shared.llm_caller import make_text_caller
    except ImportError:
        return None

    return make_text_caller(
        agent_id="alert",
        endpoint="/api/alert/drill",
        temperature=0.3,
    )
