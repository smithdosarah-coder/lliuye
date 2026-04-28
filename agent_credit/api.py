# -*- coding: utf-8 -*-
"""agent_credit.api — Agent3 授信决策 FastAPI 路由模块 (Stage C v4.0).

端点 (v4.0 · 2026-04-28 · onboarding W-C2-A2-agent-credit-backend-complete):
  GET  /api/credit/presets              — 返 3 stage_tab 评分维度 + 红线 (无 path 版)
  GET  /api/credit/presets/{segment}    — [legacy] 列出 preset_name (corporate/retail)
  POST /api/credit/decision             — SSE 流式 · body {stage_tab, report_json?, materials?, preset_name?, mock?}
  POST /api/credit/decision_legacy      — [legacy] body {segment, preset_name} (preset-only)
  POST /api/credit/export_docx          — body {decision_id?} or {advice?} · 决策建议书 docx
  GET  /api/credit/handoff/demo/{segment} — Agent6→Agent3 handoff 样本

设计:
  - v4.0 stage_tab 含 3 板块: corporate / small_business / retail
    · backend ScoringModel 仅 corporate/retail · small_business → corporate (segment_subtype 标记)
  - report_json 可选 · 优先于 preset_name · 落地走现有 CreditDecisionAgent.run_decision_stream
  - mock=true 路径返 fixture SSE events · 不调 LLM (curl/无 key 环境 demo 友好)
  - decision_id in-memory cache (advice payload) · 30 min TTL · demo 级 (生产走 sqlite)
  - 老 endpoint 保留 _legacy 后缀 · 不 break Stage A/B 已有调用

Boundary 守 (Stage C onboarding):
  - 改: 本文件
  - 加: agent_credit/word_export.py (thin wrapper) + agent_credit/tests/*.py 5 file
  - 不动: financial_analyzer.py / decision_engine.py / agent.py / decision_letter_docx.py / web/*

字段契约: 见 docs/contracts/field-naming.md + docs/contracts/agent-credit-spec.md §5
"""
from __future__ import annotations

import json
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402
from shared.qc import mark_unfilled, scan as scan_placeholders  # noqa: E402

app = FastAPI(title="Agent3 Credit Decision API", version="4.0")

_HANDOFF_DIR = PROJECT_ROOT / "demo_data" / "agent_credit"


# ============================================================================
# 内部 helpers
# ============================================================================


# stage_tab → segment mapping (backend ScoringModel 只 binary)
StageTab = Literal["corporate", "small_business", "retail"]
_STAGE_TO_SEGMENT: dict[str, str] = {
    "corporate": "corporate",
    "small_business": "corporate",  # 小微走对公评分 + 抵押弱化 (业务 mapping)
    "retail": "retail",
}


def _stage_to_segment(stage_tab: str) -> str:
    if stage_tab not in _STAGE_TO_SEGMENT:
        raise HTTPException(
            400,
            f"stage_tab 必须 ∈ {tuple(_STAGE_TO_SEGMENT)} · 收到 {stage_tab!r}",
        )
    return _STAGE_TO_SEGMENT[stage_tab]


def _qc_scrub(payload):
    """递归把字符串字段里的占位符替换为"未能自动填写"; 返回 (清洗后, 命中类型列表)."""
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


# in-memory decision_id cache (TTL 30 min · demo 级 · 生产走 sqlite)
_DECISION_CACHE: dict[str, dict[str, Any]] = {}
_DECISION_TTL_SEC = 1800


def _cache_advice(advice: dict[str, Any]) -> str:
    decision_id = "dec_" + uuid.uuid4().hex[:12]
    _DECISION_CACHE[decision_id] = {"advice": advice, "ts": time.time()}
    # GC: 清过期
    cutoff = time.time() - _DECISION_TTL_SEC
    for k in list(_DECISION_CACHE):
        if _DECISION_CACHE[k]["ts"] < cutoff:
            del _DECISION_CACHE[k]
    return decision_id


def _get_cached_advice(decision_id: str) -> dict[str, Any] | None:
    rec = _DECISION_CACHE.get(decision_id)
    if not rec:
        return None
    if time.time() - rec["ts"] > _DECISION_TTL_SEC:
        del _DECISION_CACHE[decision_id]
        return None
    return rec["advice"]


# ============================================================================
# Stage C v4.0 · GET /api/credit/presets (no path · 返 3 stage_tab 维度 + 红线)
# ============================================================================


_STAGE_DIMENSIONS: dict[str, dict[str, Any]] = {
    "corporate": {
        "stage_tab": "corporate",
        "label": "对公授信",
        "amount_range_wan": [50, 5000],
        "scoring_dimensions": [
            {"name": "经营财务", "weight": 0.35, "axis_id": "financial"},
            {"name": "行业前景", "weight": 0.15, "axis_id": "industry"},
            {"name": "经营管理", "weight": 0.25, "axis_id": "operational"},
            {"name": "担保条件", "weight": 0.25, "axis_id": "guarantee"},
        ],
        "risk_grades": [
            {"grade": "A", "min_score": 80, "decision": "建议批准"},
            {"grade": "B", "min_score": 65, "decision": "建议有条件批准"},
            {"grade": "C", "min_score": 50, "decision": "建议人工复核"},
            {"grade": "D", "min_score": 0, "decision": "建议拒绝"},
        ],
        "red_line_count": 30,
        "amount_methods": ["营收法", "净资产法", "现金流法", "担保法"],
    },
    "small_business": {
        "stage_tab": "small_business",
        "label": "普惠 / 小微",
        "amount_range_wan": [10, 500],
        "scoring_dimensions": [
            {"name": "经营财务", "weight": 0.30, "axis_id": "financial"},
            {"name": "行业前景", "weight": 0.10, "axis_id": "industry"},
            {"name": "经营管理", "weight": 0.30, "axis_id": "operational"},
            {"name": "抵押 / 担保", "weight": 0.30, "axis_id": "guarantee"},
        ],
        "risk_grades": [
            {"grade": "A", "min_score": 75, "decision": "建议批准"},
            {"grade": "B", "min_score": 60, "decision": "建议有条件批准"},
            {"grade": "C", "min_score": 45, "decision": "建议人工复核"},
            {"grade": "D", "min_score": 0, "decision": "建议拒绝"},
        ],
        "red_line_count": 20,
        "amount_methods": ["营收法", "现金流法", "担保法"],
        "note": "小微继承对公评分模型 · 但抵押权重提升 · 行业权重弱化 · 阈值放宽 5 分",
    },
    "retail": {
        "stage_tab": "retail",
        "label": "对私 / 零售",
        "amount_range_wan": [5, 500],
        "scoring_dimensions": [
            {"name": "偿债能力", "weight": 0.30, "axis_id": "ability"},
            {"name": "还款意愿", "weight": 0.25, "axis_id": "willingness"},
            {"name": "工作稳定", "weight": 0.25, "axis_id": "stability"},
            {"name": "抵押 / 担保", "weight": 0.20, "axis_id": "collateral"},
        ],
        "risk_grades": [
            {"grade": "优",  "min_score": 800, "decision": "建议批准"},
            {"grade": "中优", "min_score": 760, "decision": "建议批准"},
            {"grade": "良好", "min_score": 700, "decision": "建议有条件批准"},
            {"grade": "边界", "min_score": 680, "decision": "建议人工复核"},
            {"grade": "拒",  "min_score": 0,   "decision": "建议拒绝"},
        ],
        "red_line_count": 20,
        "amount_methods": ["评分档上限", "抵押 70% LTV", "月收入×20"],
    },
}


@app.get("/api/credit/presets")
async def list_credit_presets_all():
    """返 3 stage_tab 评分维度 + 红线规则元数据 (前端 RiskAppetiteDrawer 消费)."""
    return {"stages": list(_STAGE_DIMENSIONS.values())}


@app.get("/api/credit/presets/{segment}")
async def list_credit_presets(segment: str):
    """[legacy] 列出指定 segment 下的 preset_name (来自 mock_data/{seg}_profiles/)."""
    if segment not in ("corporate", "retail"):
        raise HTTPException(400, "segment must be corporate or retail")
    try:
        from agent_credit.agent import _list_preset_profiles
        return {"segment": segment, "presets": _list_preset_profiles(segment)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"load presets failed: {e}") from e


# ============================================================================
# GET /api/credit/handoff/demo/{segment} (preserved · Stage C 不动)
# ============================================================================


@app.get("/api/credit/handoff/demo/{segment}")
async def get_handoff_demo(segment: str):
    """返 demo_data/agent_credit/ 下 Agent6→Agent3 handoff 样本画像."""
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


# ============================================================================
# POST /api/credit/decision — Stage C v4.0 (SSE)
# body: { stage_tab, report_json?, materials?, preset_name?, provider?, api_key?, mock? }
# ============================================================================


class DecisionRequestV4(BaseModel):
    stage_tab: str = Field(
        ..., description="corporate | small_business | retail · 板块 tab"
    )
    report_json: dict | None = Field(
        default=None, description="(可选) Agent6 ReportJSON · 优先于 preset_name"
    )
    materials: list[dict] | None = Field(
        default=None, description="(可选) 客户提交材料元数据列表"
    )
    preset_name: str | None = Field(
        default=None, description="(可选) preset profile 名 · report_json 缺失时 fallback"
    )
    appetite_config: dict | None = Field(
        default=None, description="(可选) 风险偏好配置覆盖默认"
    )
    provider: str | None = None
    api_key: str | None = None
    mock: bool = Field(
        default=False,
        description="true → 返 fixture SSE events · 不调 LLM (无 key demo 友好)",
    )


# ----------------------------------------------------------------------------
# Mock SSE events (curl/无 key 路径)
# ----------------------------------------------------------------------------


def _mock_decision_events(stage_tab: str) -> list[dict[str, Any]]:
    """返 fixture SSE events · 各 stage_tab 略有差异化数值."""
    seg_dim = _STAGE_DIMENSIONS[stage_tab]
    is_retail = stage_tab == "retail"
    score_max = 850 if is_retail else 100
    composite = 730 if is_retail else (72 if stage_tab == "corporate" else 68)

    events: list[dict[str, Any]] = [
        {
            "event": "profile_loaded",
            "profile": {
                "profile_id": f"mock_{stage_tab}_001",
                "company_name": "(mock) 鼎盛商贸有限公司"
                                if stage_tab != "retail" else "(mock) 张三 · 个体户",
                "stage_tab": stage_tab,
            },
        },
        {"event": "stage", "stage": "feature_extracting", "payload": None},
        {
            "event": "stage", "stage": "feature_done",
            "payload": {
                "financial.debt_ratio": 0.42 if not is_retail else None,
                "operational.years_established": 5.3 if not is_retail else None,
                "retail.monthly_income_yuan": 18000 if is_retail else None,
                "_count": 60 if not is_retail else 22,
            },
        },
        {"event": "stage", "stage": "scoring", "payload": None},
        {
            "event": "stage", "stage": "scoring_done",
            "payload": {
                "composite_score": composite,
                "score_max": score_max,
                "risk_grade": "B" if not is_retail else "良好",
                "sub_scores": {
                    d["axis_id"]: int(composite * 0.92 + i * 3)
                    for i, d in enumerate(seg_dim["scoring_dimensions"])
                },
            },
        },
        {"event": "stage", "stage": "rule_checking", "payload": None},
        {
            "event": "stage", "stage": "rule_done",
            "payload": [
                {
                    "rule_id": f"{stage_tab[:4]}_rl_001",
                    "rule_name": "关联交易占比" if not is_retail else "近 12 月逾期次数",
                    "is_hard": False,
                    "can_waive": True,
                    "severity": "medium",
                    "actual_value": 0.32 if not is_retail else 1,
                    "threshold": 0.30 if not is_retail else 0,
                    "waiver_conditions": ["补充审计说明"] if not is_retail else ["逾期已结清证明"],
                },
            ],
        },
        {"event": "stage", "stage": "case_retrieving", "payload": None},
        {
            "event": "stage", "stage": "case_done",
            "payload": [
                {
                    "case_id": f"case_{stage_tab[:4]}_022",
                    "company_name": "启明软件" if not is_retail else "李四",
                    "similarity": 0.92,
                    "decision": "批",
                    "approved_amount": 400 if not is_retail else 50,
                },
            ],
        },
        {"event": "stage", "stage": "advising", "payload": None},
        {
            "event": "stage", "stage": "advising_done",
            "payload": {
                "decision": "有条件批准",
                "approved_amount": 300 if stage_tab == "corporate"
                                   else (80 if stage_tab == "small_business" else 30),
                "approved_term_months": 36 if not is_retail else 24,
                "interest_rate": 0.065 if stage_tab == "corporate"
                                  else (0.078 if stage_tab == "small_business" else 0.045),
                "rate_benchmark": "LPR+85BP" if stage_tab == "corporate"
                                  else ("LPR+200BP" if stage_tab == "small_business" else "LPR-10BP"),
                "risk_grade": "B" if not is_retail else "良好",
                "composite_score": composite,
                "conditions": ["关联交易审计说明", "季度应收账款账龄表"]
                              if not is_retail else ["户口本复印件", "近 6 月银行流水"],
                "decision_reason": (
                    f"[mock] {seg_dim['label']} 板块综合评分 {composite}/{score_max}，"
                    f"四维分布均衡 · 红线 1 条 (中等可豁免) · "
                    f"建议有条件批准 · 完整 LLM reasoning 走真接路径生成"
                ),
                "stage_tab": stage_tab,
            },
        },
        {"event": "done"},
    ]
    return events


def _decision_event_stream_v4(req: DecisionRequestV4):
    """SSE generator · 真 LLM 路径走 CreditDecisionAgent · mock 路径走 fixture."""
    if req.mock:
        # mock 模式 · fixture events
        for evt in _mock_decision_events(req.stage_tab):
            yield sse_encode(evt)
        return

    # 真 LLM 路径
    segment = _stage_to_segment(req.stage_tab)
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

        # 决定 profile 来源: report_json > preset_name
        profile: dict | None = None
        if req.report_json:
            from agent_credit.agent import _profile_from_report_json
            profile = _profile_from_report_json(req.report_json)
        elif req.preset_name:
            profile = agent.load_preset_profile(req.preset_name, segment)  # type: ignore
        else:
            yield sse_encode({
                "event": "error",
                "message": "必须提供 report_json 或 preset_name (空白启动 protocol)",
                "stage_tab": req.stage_tab,
            })
            return

        # 透传 stage_tab 给前端 (展示用 · 不影响 backend ScoringModel)
        profile_payload = to_jsonable(profile)
        if isinstance(profile_payload, dict):
            profile_payload["_stage_tab"] = req.stage_tab
        yield sse_encode({
            "event": "profile_loaded",
            "profile": profile_payload,
            "stage_tab": req.stage_tab,
        })

        last_advice: dict | None = None
        for stage, payload in agent.run_decision_stream(profile, segment):  # type: ignore
            cleaned, hits = _qc_scrub(to_jsonable(payload))
            if stage == "advising_done" and isinstance(cleaned, dict):
                last_advice = cleaned
            evt = {"event": "stage", "stage": stage, "payload": cleaned}
            if hits:
                evt["_qc_placeholder_hits"] = hits
            yield sse_encode(evt)

        # 缓存 advice for export_docx · 返 decision_id
        if last_advice:
            decision_id = _cache_advice(last_advice)
            yield sse_encode({
                "event": "decision_cached",
                "decision_id": decision_id,
                "ttl_sec": _DECISION_TTL_SEC,
            })

        yield sse_encode({"event": "done"})
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        traceback.print_exc()
        yield sse_encode({
            "event": "error",
            "message": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-2000:],
        })


@app.post("/api/credit/decision")
async def credit_decision_v4(req: DecisionRequestV4):
    """v4.0 SSE · stage_tab 3 板块 + report_json/preset_name 双源 + mock fallback."""
    # 提前校验 stage_tab (mock 路径也要)
    _stage_to_segment(req.stage_tab)

    def gen():
        yield from _decision_event_stream_v4(req)

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
# POST /api/credit/decision_legacy — preset-only · 保留 back-compat
# ============================================================================


class DecisionRequestLegacy(BaseModel):
    segment: str       # "corporate" | "retail"
    preset_name: str
    provider: str | None = None
    api_key: str | None = None


def _decision_event_stream_legacy(req: DecisionRequestLegacy):
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
            evt = {"event": "stage", "stage": stage, "payload": cleaned}
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


@app.post("/api/credit/decision_legacy")
async def credit_decision_legacy(req: DecisionRequestLegacy):
    """[legacy] preset-only · v3.1 兼容入口."""
    def gen():
        yield from _decision_event_stream_legacy(req)
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
# POST /api/credit/export_docx — Stage C v4.0
# body: { decision_id? } or { advice? } (二选一 · decision_id 优先)
# ============================================================================


class ExportDocxRequest(BaseModel):
    decision_id: str | None = Field(
        default=None,
        description="(优先) 由 /decision SSE event=decision_cached 返回的 id",
    )
    advice: dict | None = Field(
        default=None,
        description="(fallback) 完整 advice payload · decision_id 不可用时直接传",
    )


@app.post("/api/credit/export_docx")
async def export_decision_docx(req: ExportDocxRequest):
    """本地 python-docx 渲染决策建议书 · 接 decision_id (优先) 或 advice payload.

    监管底线: 禁海外 API · 全部本地计算.
    """
    advice: dict | None = None
    source: str = ""
    if req.decision_id:
        advice = _get_cached_advice(req.decision_id)
        if not advice:
            raise HTTPException(404, detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"decision_id 已过期或不存在: {req.decision_id}",
                    "ttl_sec": _DECISION_TTL_SEC,
                }
            })
        source = "cached"
    elif req.advice:
        advice = req.advice
        source = "passthrough"
    else:
        raise HTTPException(400, detail={
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "必须提供 decision_id 或 advice 二选一",
            }
        })

    if not advice.get("subject_name") and not advice.get("decision"):
        raise HTTPException(400, detail={
            "error": {"code": "VALIDATION_FAILED",
                      "message": "advice payload empty or missing subject_name/decision",
                      "details": {"keys": list(advice.keys()), "source": source}}
        })

    try:
        # 复用 word_export.py thin wrapper (转调 decision_letter_docx)
        from agent_credit.word_export import build_filename, export
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
            "X-Credit-Decision-Source": source,
        },
    )
