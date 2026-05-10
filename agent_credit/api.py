# -*- coding: utf-8 -*-
"""agent_credit.api — Agent3 授信决策 FastAPI 路由模块 (Stage C v4.0).

端点 (v4.0 · 2026-04-28 · onboarding W-C2-A2-agent-credit-backend-complete):
  GET  /api/credit/presets/{segment}    — 列出 preset_name (corporate/retail)
  POST /api/credit/decision             — SSE 流式 · body {stage_tab, report_json?, materials?, preset_name?, mock?}
  POST /api/credit/export_docx          — body {decision_id?} or {advice?} · 决策建议书 docx
  GET  /api/credit/handoff/demo/{segment} — Agent6→Agent3 handoff 样本

设计:
  - v4.0 stage_tab 含 3 板块: corporate / small_business / retail
    · backend ScoringModel 仅 corporate/retail · small_business → corporate (segment_subtype 标记)
  - report_json 可选 · 优先于 preset_name · 落地走现有 CreditDecisionAgent.run_decision_stream
  - mock=true 路径返 fixture SSE events · 不调 LLM (curl/无 key 环境 demo 友好)
  - decision_id in-memory cache (advice payload) · 30 min TTL · demo 级 (生产走 sqlite)

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

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_service.dependencies import require_action  # noqa: E402
from auth_service.rbac import can_action  # noqa: E402
from shared.api_utils import sse_encode, to_jsonable  # noqa: E402
from shared.entity_resolver import ensure_list_unique_ids  # noqa: E402
from shared.qc import mark_unfilled, scan as scan_placeholders  # noqa: E402

# Stage E.1 · audit log decorator (silent fail if audit_service unavailable)
try:
    from audit_service.decorators import audit_llm_call  # noqa: E402
except ImportError:
    def audit_llm_call(**_kwargs):  # type: ignore[no-redef]
        def _passthrough(fn):
            return fn
        return _passthrough

# Stage W-FIX2 · SSE-aware audit hook (latency to generator end · 修 bug #11)
try:
    from audit_service.stream_helpers import audit_stream_event  # noqa: E402
except ImportError:
    def audit_stream_event(*_args, **_kwargs):  # type: ignore[no-redef]
        pass

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


def _build_data_sources_panel(
    *,
    rule_hits: list | None,
    case_matches: list | None,
    scoring: dict | None,
    advice: dict | None,
    timestamp: str,
) -> dict[str, Any]:
    """ALL IN Phase B step 4 (2026-05-09) · per AGENT_IDENTITY-credit step 4 + EvidenceDrawer
    + KT §3.6 红线 #3 无证据 claim · 反 silent decision 无源.

    返 DataSourcesPanel shape (per CreditSession.dataSources frontend type)
    描述本次决策实际使用的 4 evidence 类源 · trust display + 反假分根据。
    """
    has_rules = bool(rule_hits)
    has_cases = bool(case_matches)
    has_scoring = bool(scoring)
    has_advice = bool(advice)
    active_count = sum([has_rules, has_cases, has_scoring, has_advice])
    return {
        "summary": f"{active_count} 项已接入 · 3 deterministic + 1 LLM",
        "updated": timestamp,
        "sources": [
            {
                "id": "scoring_model",
                "name": "四维评分模型 (确定性)",
                "desc": "财 / 行 / 经 / 担 · Python 计算 · 不让 LLM 现场算",
                "status": "online" if has_scoring else "offline",
            },
            {
                "id": "rule_engine_v2",
                "name": "红线规则引擎 v2 (确定性)",
                "desc": "对公 30 条 / 普惠 20 条 / 对私 20 条 · 阈值规则 + 豁免条件",
                "status": "online" if has_rules else "offline",
            },
            {
                "id": "case_retriever",
                "name": "历史案例库 (确定性)",
                "desc": "Top 5 相似案例 · 相似度 ≥ 0.75 · 同业对标参考",
                "status": "online" if has_cases else "offline",
            },
            {
                "id": "advisor_llm",
                "name": "LLM 决策建议生成器",
                "desc": "PIPL fallback chain · deepseek 主 + dashscope 备 · 全境内合规",
                "status": "online" if has_advice else "offline",
            },
        ],
    }


def _build_done_envelope(
    *,
    stage_tab: str,
    source: str,
    preset_name: str | None,
    profile: dict | None,
    scoring: dict | None,
    rule_hits: list | None,
    case_matches: list | None,
    advice: dict | None,
    decision_id: str | None,
    decision_graph: dict | None = None,
    ledger: dict | None = None,
) -> dict[str, Any]:
    """Cat 4 fix (Phase A worker-A4-credit · 2026-04-29) · done event 完整 envelope.

    A3 ChannelWorkspace done event 已含完整 panel 数据 (per workspace-state-protocol §4)。
    Credit done 之前空 payload (mock path L387 + live path L465) · 前端无法 hydrate。
    本 helper 把 4 stage 关键 payload + segment/preset_name/source/decision_id 一次性灌入。

    前端 normalize 后整体注入 setLiveData → 5 panel 单点派生 · 不再分 stage 累积本地 state。

    BE2 (Phase B-3 · 2026-05-01): 新增 `decision_graph` 字段 · null 兼容旧前端。
    BE7 (Phase B-3 · 2026-05-01): 新增 `ledger` 字段。
    ALL IN Phase B step 4 (2026-05-09): 新增 `data_sources` 字段 (4 evidence 类源 trust display)。
    Schema: docs/contracts/agent-credit-decision-graph.md v1.0
    """
    return {
        "event": "done",
        "stage_tab": stage_tab,
        "source": source,                    # "mock" | "preset" | "report_json"
        "preset_name": preset_name,
        "decision_id": decision_id,
        "profile": profile,                  # profile_loaded payload
        "scoring": scoring,                  # scoring_done payload (composite + sub_scores + grade)
        "rule_hits": rule_hits or [],        # rule_done payload (red lines list)
        "case_matches": case_matches or [],  # case_done payload (Top 5 similar)
        "advice": advice,                    # advising_done payload (decision/amount/term/rate/reason)
        "decision_graph": decision_graph,    # BE2 audit-grade evidence graph (null when absent)
        "ledger": ledger,                    # BE7 ledger persist result {decision_id, persisted, error?} (null when absent)
        "data_sources": _build_data_sources_panel(  # ALL IN step 4 · 4 evidence 类源 trust display
            rule_hits=rule_hits,
            case_matches=case_matches,
            scoring=scoring,
            advice=advice,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        ),
    }


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
# Stage C v4.0 · 3 stage_tab 评分维度 + 红线规则元数据 (内部消费 · decision SSE 用)
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


@app.get("/api/credit/presets/{segment}")
async def list_credit_presets(segment: str):
    """列出指定 segment 下的 preset_name (来自 mock_data/{seg}_profiles/)."""
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
# Agent6 → Agent3 handoff endpoints (Phase A worker-A4-credit · 2026-04-29)
#   per agent-credit-spec §5.2 + agent-handoff-schemas §2 · cat 0 北极星核心
#   Phase A fallback: 后端从 demo_data/agent_credit/*.json 读 (无真 Agent6 archive)
#   Phase B 转: data/handoff/report_to_credit/<report_id>.json 真接 Agent6 v16 pipeline 输出
# ============================================================================


_AGENT6_ARCHIVE_DIR = PROJECT_ROOT / "data" / "handoff" / "report_to_credit"


def _build_session_meta(path: Path, source: str) -> dict[str, Any]:
    """从 ReportJSON 文件推 session_id + meta · 双源:
       - source="demo" · path 在 demo_data/agent_credit/ · session_id 加 "demo_" 前缀 (与 handoff_from_report sid.startswith('demo_') 路径吻合)
       - source="archive" · path 在 data/handoff/report_to_credit/ · session_id 用 stem (真 Agent6 v16 archive 命名 · 通常含 timestamp)
    """
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if source == "archive":
        sid = path.stem  # 真 Agent6 archive · sid 即 stem
        # segment 推断: report_json 含 business_line · 或 stage_tab fallback (per agent-handoff-schemas §2.3)
        seg_raw = (d.get("business_line") or d.get("stage_tab") or "").lower()
        if "retail" in seg_raw or "personal" in seg_raw:
            seg = "retail"
        elif "small" in seg_raw or "sme" in seg_raw or "普惠" in d.get("business_line", ""):
            seg = "small_business"
        else:
            seg = "corporate"
    else:  # demo
        sid = f"demo_{path.stem}"
        seg = "retail" if path.name.startswith("retail_") else "corporate"
    preset = d.get("preset_name", path.stem)
    return {
        "session_id": sid,
        "report_id": d.get("profile_id", path.stem),
        "company_name": d.get("company_name", "(unknown)"),
        "segment": seg,
        "preset_name": preset,
        "industry": d.get("industry"),
        "established_date": d.get("establishment_date"),
        "generated_at": (d.get("_handoff_meta") or {}).get("generated_at", ""),
        "status": "done",
        "source": source,                 # "demo" | "archive" · 前端可显源标
        "source_file": path.name,
    }


@app.get("/api/credit/reports/sessions")
async def list_credit_reports(
    status: str = "done",
    user: dict = Depends(require_action("credit", "invoke")),
):
    """列出 Agent6 已生成的报告 session list (供 EmptyState onPrimary 选 handoff 源)。

    Phase B.1 fix #2 · 假 live root cause:
      - 旧: 默认双源扫描 · archive (Agent6 真产物) + demo_data (Phase A fallback) · 用户看见 4 sample 误认 production
      - 新: 默认仅扫 archive · 仅 user.demoModeAvailable=true 时附加 demo_data
      - 反 KT §3.6 红线 #1 假 live · 演示报告不能混入生产 list 让客户经理误用

    Source path:
      - source="archive" · `data/handoff/report_to_credit/*.json` (Agent6 v16 pipeline 真产物 · report worker 写本 worker 读)
      - source="demo"    · `demo_data/agent_credit/*.json` (4 sample · 仅 demoModeAvailable 解锁)
    """
    if status not in ("done", "all"):
        raise HTTPException(400, "status must be 'done' or 'all'")
    sessions: list[dict[str, Any]] = []
    # Phase B.1 fix #2 (codex re-review 抓) · JWT payload 没 demoModeAvailable 字段
    # 改用 demo_mode_visible(user) helper · 动态 check env DEMO_MODE_VISIBLE + role
    from auth_service.rbac import demo_mode_visible as _demo_visible
    demo_unlocked = _demo_visible(user)

    # 先扫真 Agent6 archive · 真 session 优先 (sort: 时间倒序 · 最新报告排首)
    if _AGENT6_ARCHIVE_DIR.exists():
        archive_paths = sorted(_AGENT6_ARCHIVE_DIR.glob("*.json"), reverse=True)
        for path in archive_paths:
            meta = _build_session_meta(path, "archive")
            if meta:
                sessions.append(meta)

    # Phase B.1 fix #2 · demo_data 仅 demoModeAvailable=true 才附加 (反假 live · 默认生产 only)
    if demo_unlocked and _HANDOFF_DIR.exists():
        for path in sorted(_HANDOFF_DIR.glob("*.json")):
            meta = _build_session_meta(path, "demo")
            if meta:
                sessions.append(meta)

    archive_count = sum(1 for s in sessions if s.get("source") == "archive")
    demo_count = sum(1 for s in sessions if s.get("source") == "demo")
    return {
        "sessions": sessions,
        "count": len(sessions),
        "archive_count": archive_count,
        "demo_count": demo_count,
        "demo_unlocked": demo_unlocked,
        "source": "archive_only" if not demo_unlocked else "archive_plus_demo",
        "archive_dir": str(_AGENT6_ARCHIVE_DIR.relative_to(PROJECT_ROOT)),
        "demo_dir": str(_HANDOFF_DIR.relative_to(PROJECT_ROOT)) if demo_unlocked else None,
    }


class HandoffFromReportRequest(BaseModel):
    session_id: str = Field(..., description="Agent6 report session_id (从 /reports/sessions 拉)")


@app.post("/api/credit/handoff/from_report")
async def handoff_from_report(
    req: HandoffFromReportRequest,
    user: dict = Depends(require_action("credit", "handoff")),
):
    """Agent6→Agent3 handoff · Cat 0 北极星核心: EmptyState onPrimary 真消费 ReportJSON。

    返 enterprise_profile + ready_for_decision flag · 前端注入 /api/credit/decision body。

    Phase B.1 fix #3 · 改默认读 Agent6 真产物 archive (report worker 写本 worker 读):
      - 默认路径: data/handoff/report_to_credit/<sid>.json
      - Demo 路径: 仅 user.demoModeAvailable=true 时 sid 可用 "demo_" 前缀解锁 demo_data/agent_credit/<stem>.json
      - 反 KT §3.6 红线 #1 假 live · 默认生产路径 only · demo 显式解锁
    """
    sid = req.session_id
    if not sid:
        raise HTTPException(400, detail={
            "error": {"code": "VALIDATION_FAILED", "message": "session_id required"}
        })

    # Phase B.1 fix #2 (codex re-review 抓 · 第 2 处) · 同 line 433 · JWT 没 demoModeAvailable
    # 改用 demo_mode_visible(user) helper · 动态 check env DEMO_MODE_VISIBLE + role
    from auth_service.rbac import demo_mode_visible as _demo_visible
    demo_unlocked = _demo_visible(user)
    is_demo_sid = sid.startswith("demo_")

    if is_demo_sid:
        # Phase B.1 fix #3 · demo 路径仅 demoModeAvailable 解锁
        if not demo_unlocked:
            raise HTTPException(403, detail={
                "error": {
                    "code": "DEMO_LOCKED",
                    "message": (
                        "demo session_id 不允许 (per Phase B.1 fix #3) · "
                        "需 demoModeAvailable=true 解锁 (从 /api/auth/me payload 读)"
                    ),
                    "details": {"sid": sid, "demoModeAvailable": False},
                }
            })
        stem = sid[len("demo_"):]
        path = _HANDOFF_DIR / f"{stem}.json"
        if not path.exists():
            raise HTTPException(404, detail={
                "error": {"code": "REPORT_NOT_FOUND",
                          "message": f"demo report not found: {stem}.json",
                          "available": [p.stem for p in _HANDOFF_DIR.glob("*.json")]}
            })
    else:
        # 默认路径 · Agent6 真产物 archive (data/handoff/report_to_credit/<sid>.json)
        archive = _AGENT6_ARCHIVE_DIR / f"{sid}.json"
        if not archive.exists():
            raise HTTPException(404, detail={
                "error": {"code": "REPORT_NOT_FOUND",
                          "message": (
                              f"Agent6 archive not found: {sid}.json · "
                              "report worker 应已写本路径 · 检查 /archive/report 是否完成尽调"
                          ),
                          "details": {
                              "expected_path": str(archive.relative_to(PROJECT_ROOT)),
                          }}
            })
        path = archive

    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(500, detail={
            "error": {"code": "REPORT_LOAD_FAILED",
                      "message": f"{type(e).__name__}: {e}"}
        }) from e

    # 关键字段缺失检查 (per agent-handoff-schemas §2.5 缺失降级)
    has_financial = bool((report.get("financial_anchors") or {}).get("revenue_latest"))
    has_company = bool(report.get("company_name"))

    return {
        "session_id": sid,
        "report_id": report.get("profile_id", sid),
        "company_name": report.get("company_name"),
        "industry": report.get("industry"),
        "generated_at": (report.get("_handoff_meta") or {}).get("generated_at", ""),
        "preset_name": report.get("preset_name"),
        "enterprise_profile": report,   # 全量 ReportJSON · 注入 /decision body.report_json
        "ready_for_decision": has_company and has_financial,
        "missing_fields": [
            *(["company_name"] if not has_company else []),
            *(["financial_anchors.revenue_latest"] if not has_financial else []),
        ],
        "warning": None if (has_company and has_financial) else
                   "关键字段缺失 · 评分将用保守 fallback (per agent-handoff-schemas §2.5)",
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
    """返 fixture SSE events · 各 stage_tab 略有差异化数值.

    Cat 4 fix (Phase A worker-A4-credit · 2026-04-29):
    末 done event 改为 _build_done_envelope() 完整 payload (segment/profile/scoring/
    rule_hits/case_matches/advice) · 与 live path 对称 · 前端 normalize 整体注入。
    """
    seg_dim = _STAGE_DIMENSIONS[stage_tab]
    is_retail = stage_tab == "retail"
    score_max = 850 if is_retail else 100
    composite = 730 if is_retail else (72 if stage_tab == "corporate" else 68)

    profile_payload = {
        "profile_id": f"mock_{stage_tab}_001",
        "company_name": "(mock) 鼎盛商贸有限公司"
                        if stage_tab != "retail" else "(mock) 张三 · 个体户",
        "stage_tab": stage_tab,
    }
    feature_done_payload = {
        "financial.debt_ratio": 0.42 if not is_retail else None,
        "operational.years_established": 5.3 if not is_retail else None,
        "retail.monthly_income_yuan": 18000 if is_retail else None,
        "_count": 60 if not is_retail else 22,
    }
    scoring_done_payload = {
        "composite_score": composite,
        "score_max": score_max,
        "risk_grade": "B" if not is_retail else "良好",
        "sub_scores": {
            d["axis_id"]: int(composite * 0.92 + i * 3)
            for i, d in enumerate(seg_dim["scoring_dimensions"])
        },
    }
    rule_done_payload = ensure_list_unique_ids(
        [
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
        # ALL IN Phase B step 5 · per candidate-identity-contract v1.1 §4 · 后端 emit 必经 helper
        name_field="rule_name",
        uscc_field="",
    )
    case_done_payload = ensure_list_unique_ids(
        [
            {
                "case_id": f"case_{stage_tab[:4]}_022",
                "company_name": "启明软件" if not is_retail else "李四",
                "similarity": 0.92,
                "decision": "批",
                "approved_amount": 400 if not is_retail else 50,
            },
        ],
        # ALL IN Phase B step 5 · per candidate-identity-contract v1.1 §4
        name_field="company_name",
        uscc_field="",
    )
    advising_done_payload = {
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
    }

    events: list[dict[str, Any]] = [
        {"event": "profile_loaded", "profile": profile_payload},
        {"event": "stage", "stage": "feature_extracting", "payload": None},
        {"event": "stage", "stage": "feature_done", "payload": feature_done_payload},
        {"event": "stage", "stage": "scoring", "payload": None},
        {"event": "stage", "stage": "scoring_done", "payload": scoring_done_payload},
        {"event": "stage", "stage": "rule_checking", "payload": None},
        {"event": "stage", "stage": "rule_done", "payload": rule_done_payload},
        {"event": "stage", "stage": "case_retrieving", "payload": None},
        {"event": "stage", "stage": "case_done", "payload": case_done_payload},
        {"event": "stage", "stage": "advising", "payload": None},
        {"event": "stage", "stage": "advising_done", "payload": advising_done_payload},
        _build_done_envelope(
            stage_tab=stage_tab,
            source="mock",
            preset_name=None,
            profile=profile_payload,
            scoring=scoring_done_payload,
            rule_hits=rule_done_payload,
            case_matches=case_done_payload,
            advice=advising_done_payload,
            decision_id=None,
            decision_graph=None,  # in-memory fixture · scenario fixtures (demo/run) carry real graph
            ledger=None,          # in-memory fixture skips ledger persist (no real decision_id needed)
        ),
    ]
    return events


def _decision_event_stream_v4(req: DecisionRequestV4):
    """SSE generator · 真 LLM 路径走 CreditDecisionAgent · mock 路径走 fixture.

    W-FIX2 修 bug #11: try/finally 内部记 audit · latency 含真实 stream 时延。
    """
    t0 = time.time()
    err: str | None = None
    try:
        if req.mock:
            # mock 模式 · fixture events
            for evt in _mock_decision_events(req.stage_tab):
                yield sse_encode(evt)
            return

        # 真 LLM 路径
        segment = _stage_to_segment(req.stage_tab)
        try:
            try:
                from agent_credit.agent import CreditDecisionAgent
            except ImportError as e:
                err = f"ImportError: {e}"
                # Phase B.2 step 5 · typed error banner (反 silent fallback fake)
                yield sse_encode({
                    "event": "error",
                    "code": "IMPORT_ERROR",
                    "message": f"CreditDecisionAgent 模块导入失败 · {e} · 联系运维",
                    "raw": err[:200],
                })
                return

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

            # Cat 4 fix (Phase A worker-A4-credit · 2026-04-29)
            # 串流时 capture 4 个关键 stage payload · done event 一次性灌完整 envelope
            # BE2 (Phase B-3 · 2026-05-01): 新增 capture graph_done payload
            # BE7 (Phase B-3 · 2026-05-01): 新增 capture ledger_done payload
            last_scoring: dict | None = None
            last_rules: list | None = None
            last_cases: list | None = None
            last_advice: dict | None = None
            last_graph: dict | None = None
            last_ledger: dict | None = None
            for stage, payload in agent.run_decision_stream(profile, segment):  # type: ignore
                cleaned, hits = _qc_scrub(to_jsonable(payload))
                if stage == "scoring_done" and isinstance(cleaned, dict):
                    last_scoring = cleaned
                elif stage == "rule_done" and isinstance(cleaned, list):
                    # ALL IN Phase B step 5 (2026-05-09) · ensure unique id per candidate-identity-contract v1.1 §4
                    last_rules = ensure_list_unique_ids(
                        cleaned, name_field="rule_name", uscc_field="",
                    )
                elif stage == "case_done" and isinstance(cleaned, list):
                    # ALL IN Phase B step 5 · ensure unique id (case_id 已 unique · helper 在缺失时兜底)
                    last_cases = ensure_list_unique_ids(
                        cleaned, name_field="company_name", uscc_field="",
                    )
                elif stage == "advising_done" and isinstance(cleaned, dict):
                    last_advice = cleaned
                elif stage == "graph_done" and isinstance(cleaned, dict):
                    last_graph = cleaned
                elif stage == "ledger_done" and isinstance(cleaned, dict):
                    last_ledger = cleaned
                evt = {"event": "stage", "stage": stage, "payload": cleaned}
                if hits:
                    evt["_qc_placeholder_hits"] = hits
                yield sse_encode(evt)

            # 缓存 advice for export_docx · 返 decision_id
            decision_id: str | None = None
            if last_advice:
                decision_id = _cache_advice(last_advice)
                yield sse_encode({
                    "event": "decision_cached",
                    "decision_id": decision_id,
                    "ttl_sec": _DECISION_TTL_SEC,
                })

            # done envelope (cat 4) · 与 mock path 对称 · 前端 normalize 整体注入 sessionData
            yield sse_encode(_build_done_envelope(
                stage_tab=req.stage_tab,
                source="report_json" if req.report_json else (
                    "preset" if req.preset_name else "unknown"
                ),
                preset_name=req.preset_name,
                profile=profile_payload if isinstance(profile_payload, dict) else None,
                scoring=last_scoring,
                rule_hits=last_rules,
                case_matches=last_cases,
                advice=last_advice,
                decision_id=decision_id,
                decision_graph=last_graph,
                ledger=last_ledger,
            ))
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            err_str = f"{type(e).__name__}: {e}"
            err = err_str
            traceback.print_exc()  # stderr log only · 不给 client (security · 不 leak 文件路径)

            # Phase B.2 step 5 · typed error banner 分类 (per onboarding "NotImplementedError / API key
            # missing / Tavily down 显 typed banner · 不 silent · 不 fallback fake")
            err_lower = err_str.lower()
            if any(k in err_lower for k in ("401", "unauthorized", "authentication", "api key", "api_key")):
                code = "LLM_KEY_MISSING"
                friendly = (
                    "LLM 密钥未配置或失效 (DEEPSEEK_API_KEY / DASHSCOPE_API_KEY) · "
                    "联系运维补 key · 反假 live 不切 fallback fake"
                )
            elif any(k in err_lower for k in ("rate limit", "429", "quota")):
                code = "LLM_RATE_LIMITED"
                friendly = "LLM 调用配额已满 · 稍后重试 · 反假 live 不切 fallback fake"
            elif any(k in err_lower for k in ("all providers failed", "fallback chain", "no provider")):
                code = "LLM_FALLBACK_EXHAUSTED"
                friendly = (
                    "LLM 主+备 provider 全降级 (deepseek + dashscope · PIPL 境内 fallback) · "
                    "检查 LLM 服务可用性 · 反假 live 不切 fallback fake"
                )
            elif isinstance(e, ImportError):
                code = "IMPORT_ERROR"
                friendly = f"模块导入失败 · {e} · 联系运维"
            elif isinstance(e, NotImplementedError):
                # NotImplementedError 不可在 demo/run 路径出现 (反不可 GO 条件 #5)
                code = "NOT_IMPLEMENTED"
                friendly = f"功能未实装 · {e} · 反不可 GO 条件 #5 · 主 CLI fix-forward"
            else:
                code = "INTERNAL_ERROR"
                friendly = f"内部错误 · {type(e).__name__}: {str(e)[:200]}"

            yield sse_encode({
                "event": "error",
                "code": code,
                "message": friendly,
                "raw": err_str[:200],  # dev debug 用 · 非 stack trace
            })
    finally:
        # bug #11 fix · audit 写在 generator 末尾 · latency 含全 stream 真实延迟
        audit_stream_event(
            agent_id="credit",
            endpoint="/api/credit/decision",
            model=req.provider or "deepseek-chat",
            t0=t0,
            error=err,
        )


@app.post("/api/credit/decision")
async def credit_decision_v4(
    req: DecisionRequestV4,
    user: dict = Depends(require_action("credit", "invoke")),
):
    """v4.0 SSE · stage_tab 3 板块 + report_json/preset_name 双源 + mock fallback.

    Audit (W-FIX2 修 bug #11): generator finally 内调 audit_stream_event ·
    latency 含真实 stream 时延 · 不再用 @audit_llm_call decorator
    (decorator 在 route function return StreamingResponse 即记 · 失真)。

    Auth (B5 sub-PR 2 · 2026-05-05 · per Q-052 #8): require_action("credit", "invoke")
    enforce row-level/action gate · credit_officer/risk_manager/admin 可调 · RM read-only 403.

    Phase B.1 fix #5 · 双控 demo gate (per PM 2026-05-09):
      - 默认 invoke 路径 (mock=False) · require_action("credit", "invoke") 已 OK
      - mock=True 路径 · 额外 require credit:demo action 或 user.demoModeAvailable=true
      - 反 KT §3.6 红线 #1 假 live · 普通用户不能误触 mock fixture 路径
    """
    # Phase B.1 fix #5 · mock 路径双控
    # Phase B.1 fix #2 (codex re-review 抓) · can_action("demo") 现已含 env+role 双控 · 删 demoModeAvailable OR (redundant + buggy)
    if req.mock:
        if not can_action(user.get("role", ""), "credit", "demo"):
            raise HTTPException(403, detail={
                "error": {
                    "code": "DEMO_ACCESS_DENIED",
                    "message": (
                        "mock=true 演示路径需 credit:demo action (env DEMO_MODE_VISIBLE=1 + role admin/demo_user) · "
                        "默认 invoke 路径走 mock=false (per PM Phase B.1 #5)"
                    ),
                    "details": {
                        "role": user.get("role"),
                    },
                }
            })

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
# POST /api/credit/demo/run · Phase B.2 真后端跑改造 (PM 2026-05-10 真意 reframe)
#   旧: 读 data/mock/workspace/credit/scenarios/<id>.json yield fixture · 不调 LLM
#   新: 接受 sample_id (内置 ReportJSON sample) · 真调 LLM/scoring/rule/case/ledger 全 pipeline
#   Refs: docs/onboarding/B2-phase-b2-dispatch.md "演示=上传 sample 跑真后端"
#   反不可 GO 条件 #1 (yield fixture_event) + 红线 #1 假 live + #2 假分
#
# Sample 来源:
#   demo_data/agent_credit/<sample_id>.json (Agent6 → Agent3 handoff JSON · v4 ReportJSON shape)
#   credit 是下游 agent · 不直接吃原始材料 (DP001_龙峰精工/ 是 Agent6 域) · 真"sample 输入"形态 = ReportJSON
# ============================================================================


# v4 ReportJSON shape sample (含 business_line + financial_anchors · 可喂 _decision_event_stream_v4)
# manufacturing_eval / trade_eval 是 v1 scenario shape · 不在本 demo/run scope (走 /decision · 历史 path)
_DEMO_SAMPLE_DIR = PROJECT_ROOT / "demo_data" / "agent_credit"
_DEMO_SAMPLE_ALLOWLIST: tuple[str, ...] = (
    "corp_dingsheng_trade",   # 对公 · 鼎盛商贸 (建材批发 · 关联交易高 · 现金流负)
    "retail_lisi_education",  # 对私 · 李四 (教育行业 · FICO 式)
)


class CreditDemoRunRequest(BaseModel):
    sample_id: str = Field(
        default="corp_dingsheng_trade",
        description=(
            "内置 ReportJSON sample 文件名 (无 .json) · "
            "allowlist: corp_dingsheng_trade | retail_lisi_education · "
            "demo_data/agent_credit/ 下 v4 ReportJSON shape sample · "
            "PM 真意: 演示=上传 sample 跑真后端 · 不是 yield fixture (per docs/onboarding/B2-phase-b2-dispatch.md)"
        ),
    )


def _load_demo_report_json(sample_id: str) -> dict:
    """加载内置 ReportJSON sample · 喂 _decision_event_stream_v4 (真 LLM 路径).

    Raises:
        HTTPException 400 · sample_id 不在 allowlist
        HTTPException 404 · sample 文件缺失
        HTTPException 500 · JSON 解析失败
    """
    if sample_id not in _DEMO_SAMPLE_ALLOWLIST:
        raise HTTPException(400, detail={
            "error": {
                "code": "SAMPLE_NOT_ALLOWED",
                "message": (
                    f"sample_id 不在 allowlist · 收到 {sample_id!r} · "
                    "manufacturing_eval/trade_eval 是 v1 scenario shape (input_message+preset_data) · "
                    "走 /api/credit/decision 历史 path · 不入 demo/run 真后端 pipeline"
                ),
                "details": {"allowlist": list(_DEMO_SAMPLE_ALLOWLIST)},
            }
        })

    path = _DEMO_SAMPLE_DIR / f"{sample_id}.json"
    if not path.exists():
        raise HTTPException(404, detail={
            "error": {
                "code": "SAMPLE_NOT_FOUND",
                "message": f"sample file not found: {sample_id}.json",
                "details": {
                    "expected_path": str(path.relative_to(PROJECT_ROOT)),
                    "available": sorted(p.stem for p in _DEMO_SAMPLE_DIR.glob("*.json")),
                },
            }
        })

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(500, detail={
            "error": {
                "code": "SAMPLE_LOAD_FAILED",
                "message": f"{type(e).__name__}: {e}",
                "details": {"path": str(path.relative_to(PROJECT_ROOT))},
            }
        }) from e


def _infer_stage_tab_from_report(report: dict) -> StageTab:
    """从 ReportJSON business_line 推 stage_tab (per agent-handoff-schemas §2.3)."""
    bl = (report.get("business_line") or report.get("stage_tab") or "").lower()
    if "retail" in bl or "personal" in bl:
        return "retail"
    if "small" in bl or "sme" in bl:
        return "small_business"
    return "corporate"


@app.post("/api/credit/demo/run")
async def credit_demo_run(
    req: CreditDemoRunRequest,
    _user: dict = Depends(require_action("credit", "invoke")),
):
    """演示入口 · 内置 sample → 真后端 pipeline (LLM/scoring/rule/case/ledger 全真).

    PM 2026-05-10 真意 reframe: 演示 ≠ ModePill 切假 · 演示 = 上传 sample 跑真后端.
    本 endpoint 复用 /api/credit/decision 真路径 (_decision_event_stream_v4 mock=False) ·
    输入来自内置 ReportJSON sample (而非用户上传 + Agent6 handoff) · LLM / 评分 / 红线 /
    案例召回 / decision_graph / ledger 全部真跑 · 与 /decision 行为一致。

    错误降级 (Step 5 onboarding): LLM key 缺失 / Tavily down / NotImplementedError →
    _decision_event_stream_v4 内部 yield typed error event · 前端 LiveFailError → fail-visible banner.
    不 silent fallback fake 数据.
    """
    report = _load_demo_report_json(req.sample_id)
    stage_tab = _infer_stage_tab_from_report(report)

    real_req = DecisionRequestV4(
        stage_tab=stage_tab,
        report_json=report,
        materials=None,
        preset_name=None,
        appetite_config=None,
        provider=None,
        api_key=None,
        mock=False,  # 真路径 · 不走 fixture
    )

    def gen():
        yield from _decision_event_stream_v4(real_req)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "X-Credit-Demo-Sample": req.sample_id,
            "X-Credit-Demo-Path": "real_backend_pipeline",
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
async def export_decision_docx(
    req: ExportDocxRequest,
    _user: dict = Depends(require_action("credit", "export")),
):
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
