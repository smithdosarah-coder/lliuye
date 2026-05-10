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
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_service.dependencies import require_action  # noqa: E402
from shared.api_utils import sse_encode, to_jsonable  # noqa: E402
from shared.sse_envelope import (  # noqa: E402
    DATA_SOURCE_LIVE,
    DATA_SOURCE_MOCK,
    DATA_SOURCE_MOCK_FALLBACK,
    DATA_SOURCE_MOCK_FORCED,
    encode_event,
    make_done,
    make_error,
    make_error_from_exception,
    make_stage,
)

from agent_alert.output_validator import soft_clean as _qc_scrub  # noqa: E402

# ALL IN Phase B step 5 (2026-05-09): per candidate-identity-contract v1.1 §3 ·
# alert.id 按 client_entity_key 派生 (uscc_X / name_md5 / cand_X) · 防 PM 痛点
# "左右气泡不联动" 真根因 (后端 candidate 没 id → 前端 find 命中错误).
from shared.entity_resolver import ensure_list_unique_ids, resolve_entity  # noqa: E402

# ALL IN Phase B.2 step 10 (2026-05-10): cross-agent decision ledger 上链 ·
# per CLAUDE.md §3.7.5 + docs/contracts/decision-ledger.md v1.0.
# alert default retention=short (90d) · severity=red 升 standard (5y) ·
# subject_id 必 hash · jurisdiction default HQ · failure silent-fail.
try:
    from shared.decision_ledger import (  # noqa: E402
        RETENTION_STANDARD,
        hash_subject_id,
        record_decision,
    )
    _LEDGER_AVAILABLE = True
except ImportError:
    _LEDGER_AVAILABLE = False
    def record_decision(**_kwargs):  # type: ignore[no-redef]
        return ""
    def hash_subject_id(_v):  # type: ignore[no-redef]
        return None
    RETENTION_STANDARD = "standard"  # type: ignore[assignment]


def _ensure_alert_emit_ids(
    by_grade: dict[str, list[dict]],
    top_cases: list[dict],
    *,
    name_field_compact: str = "company_name",
    name_field_top: str = "customer",
    uscc_field: str = "uscc",
) -> None:
    """ALL IN Phase B step 5 · in-place 给 hit_list buckets + top_cases 加 id 字段.

    每个 list 内独立 unique (red / yellow / green / top_cases 4 条 list).
    USCC 不在 emitted dict 时 (后端未带 uscc 字段) · 派生 fallback 走 name_md5 (confidence 0.5).
    """
    for grade in ("red", "yellow", "green"):
        bucket = by_grade.get(grade) or []
        if bucket:
            ensure_list_unique_ids(
                bucket,
                name_field=name_field_compact,
                uscc_field=uscc_field,
            )
    if top_cases:
        ensure_list_unique_ids(
            top_cases,
            name_field=name_field_top,
            uscc_field=uscc_field,
        )

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


class AlertBatchScanRequest(BaseModel):
    """BE9.1 (Phase B Sprint 2 · 2026-05-04): 跨多 scenario 批量扫描请求.

    一次扫多客户场景 · 内 streaming 进度 · 产出聚合 hitlist + per-scenario breakdown ·
    给 BE9.2 alert clustering 做前置 (≥ 3 客户共同 pattern 跨 scenario detect)。

    红线 (per CLAUDE.md §3.7.1): max_total_customers ≤ 50000 (与 Agent2 MAX_ROWS 同
    口径 · banking 客户不会一次扫 5 万 · 这是 abuse 防御不是 quota)。
    """
    scenarios: list[str] = []                # 1+ scenario key (KB 已知 demo_data/agent_alert/<key>)
    client_ids: list[str] = []               # 可选 filter · 空 = scenario 内全扫
    force_mock: bool = True                  # 默认 mock · live 路径要 caller 显式开
    provider: str | None = None
    api_key: str | None = None
    max_total_customers: int = 50000         # CLAUDE.md §3.7.1 active rule 上限


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
    """HitItem → 前端 hit_list bucket 单条 (V2 · per A6 schema · `tier` red/yellow/green).

    ALL IN Phase B step 5: 加 uscc 字段 (来自 target.payload.unified_credit_code) ·
    供下游 ensure_list_unique_ids 派生 entity-key based id (uscc_X · confidence 1.0).
    """
    payload = _hit_target_payload(hit)
    matched = list(getattr(hit, "matched_rules", None) or [])
    reasons = list(getattr(hit, "reasons", None) or [])
    return {
        "client_id": getattr(hit, "hit_id", None) or (hit.get("hit_id") if isinstance(hit, dict) else "") or "",
        "company_name": payload.get("company_name", ""),
        "uscc": payload.get("unified_credit_code", "") or payload.get("uscc", ""),
        "amount": payload.get("credit_balance", "") or payload.get("amount", ""),
        "tier": _grade_value(getattr(hit, "level", None) if not isinstance(hit, dict) else hit.get("level")),
        "score": float(getattr(hit, "score", 0.0) if not isinstance(hit, dict) else hit.get("score", 0.0)),
        "matched_rules": matched,
        "reasons": reasons,
    }


def _to_top_case(hit: Any) -> dict:
    """HitItem → 前端 topCases 单条 (V2 · per A6 schema · `tier` red/yellow/green + triggers).

    ALL IN Phase B step 5: 加 uscc 字段 · id 字段下游 ensure_list_unique_ids 重写
    (现 hit_id-based id 不是 entity-key 派生 · 不满足 candidate-identity-contract v1.1 §2).
    """
    payload = _hit_target_payload(hit)
    reasons = list(getattr(hit, "reasons", None) or [])
    matched = list(getattr(hit, "matched_rules", None) or [])
    triggers = (reasons or matched)[:4]
    return {
        # id 字段由 _ensure_alert_emit_ids 派生 (uscc_X / name_md5 / cand_X) · 不再用 hit_id
        "client_id": getattr(hit, "hit_id", None) or (hit.get("hit_id") if isinstance(hit, dict) else ""),
        "customer": payload.get("company_name", ""),
        "uscc": payload.get("unified_credit_code", "") or payload.get("uscc", ""),
        "amount": payload.get("credit_balance", "") or payload.get("amount", ""),
        "tier": _grade_value(getattr(hit, "level", None) if not isinstance(hit, dict) else hit.get("level")),
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


def _resolve_fallback_banner(mode_label: str) -> dict[str, Any] | None:
    """BE5 (Phase B Sprint 2 · 2026-05-04): provider degrade → banner metadata.

    把 mode_label 映射成机器+人话双层 banner payload · frontend 按
    docs/contracts/live-fallback-banner-spec.md §2 渲染顶部 banner。

    Returns:
        None: live mode (无 banner) / demo_forced (mock_forced banner 由前端 mock-banner 处理)
        dict: {source, reason, severity, message, hint, retried}
              · source: "Tavily" / "Search" 等 (人话)
              · reason: machine-readable code (key_missing / web_fallback_* / disabled / ...)
              · severity: "info" | "warn" | "error"
              · message: 用户可见中文 (banner 显)
              · hint: 下一步引导 (per CLAUDE.md 反馈引导行动 § 交互设计原则)
              · retried: bool (是否已尝试 + 自动降级)

    Note:
        live-fallback-banner-spec §1: 不允许静默 swap mock + 假装成功 · 任何
        fallback 必显示 · 不区分 frontend / backend · 此函数是 backend SSOT。
    """
    if mode_label == "web_live":
        return None  # 真接通 · 无 banner

    if mode_label == "demo_forced":
        # 用户显式 force_mock=True · 这是预期路径 · 但仍透明告知 (per spec §1)
        return {
            "source": "Mock Demo",
            "reason": "demo_forced",
            "severity": "info",
            "message": "演示模式 · 当前显示 mock 演示数据 (用户显式触发)",
            "hint": "切真实输入 / 取消 force_mock → 切回 live · 见 dropdown 切换",
            "retried": False,
        }

    # ALL IN Phase B.2 (PM 2026-05-10 reframe): 3 fallback 路径不再返合成 mock 结果 ·
    # 改用 NullSearchProvider (返 []) · 仅内部规则真跑 · banner 必明示 trust model 降级.
    if mode_label == "tavily_disabled":
        return {
            "source": "Tavily",
            "reason": "tavily_disabled",
            "severity": "warn",
            "message": "Tavily 外部搜索已禁用 (ALERT_USE_TAVILY=0) · 仅内部规则命中 · 外部源 0 hit",
            "hint": "管理员设置 ALERT_USE_TAVILY=1 + TAVILY_API_KEY 可切真实外部搜索",
            "retried": False,
        }

    if mode_label == "tavily_key_missing":
        return {
            "source": "Tavily",
            "reason": "tavily_key_missing",
            "severity": "warn",
            "message": "Tavily API Key 未配置 · 仅内部规则命中 · 外部源 0 hit (不返合成 mock 结果)",
            "hint": "设置 TAVILY_API_KEY 环境变量后重启服务 → 切真实外部源",
            "retried": False,
        }

    if mode_label.startswith("web_fallback_"):
        # web 路径异常 · NullSearchProvider 替代 · 仅内部规则真跑 · banner error
        err_type = mode_label.replace("web_fallback_", "", 1)
        return {
            "source": "Tavily",
            "reason": mode_label,
            "severity": "error",
            "message": f"外部搜索调用失败 ({err_type}) · 仅内部规则命中 · 外部源 0 hit",
            "hint": "可点[重试] · 或检查 Tavily Key / 网络后重启服务",
            "retried": True,
        }

    # 兜底: 未识别 mode_label → 标注 unknown 但仍透明 (避免静默 mock fallback)
    return {
        "source": "Unknown",
        "reason": f"unknown_mode_{mode_label or 'empty'}",
        "severity": "warn",
        "message": f"扫描模式 '{mode_label or '(空)'}' 不在已知映射 · 当前数据来源不明",
        "hint": "检查 build_alert_provider 配置 + 联系管理员",
        "retried": False,
    }


def _record_alert_decisions_to_ledger(
    *,
    hit_list: Any,
    dispositions: Any,
    session_id: str,
    scenario_key: str,
    mode_label: str,
    endpoint: str,
) -> int:
    """ALL IN Phase B.2 step 10 (2026-05-10) · per CLAUDE.md §3.7.5.

    把每个红/黄客户的预警决策上链 decision_ledger · 1 cluster 1 entry.

    Spec (per docs/contracts/decision-ledger.md + CLAUDE.md §3.7.5 alert 行):
    - retention default = "short" (90d · alert routine 预警)
    - severity == "red" → 升 "standard" (5y · 银保监 archive)
    - subject_id 必 hash (16-hex prefix · 防 PII 入库)
    - jurisdiction default "HQ" (env LIUYE_LEDGER_JURISDICTION 可覆盖)
    - failure silent-fail (decision flow 不破)

    Returns:
        int · 成功上链的 entry 数 (失败也返已成功的 count)
    """
    if not _LEDGER_AVAILABLE or hit_list is None:
        return 0

    written = 0
    hits = list(getattr(hit_list, "hits", None) or [])
    dispo_map = dispositions or {}

    for hit in hits:
        try:
            level_val = getattr(hit, "level", None)
            level_str = (level_val.value if hasattr(level_val, "value") else str(level_val)).lower()
            # 仅红/黄上链 (绿不算预警决策 · routine 不消耗 retention quota)
            if level_str not in ("red", "yellow"):
                continue

            target = getattr(hit, "target", None)
            payload = getattr(target, "payload", {}) if target else {}
            if isinstance(payload, dict):
                company_name = str(payload.get("company_name") or "")
                uscc = str(payload.get("unified_credit_code") or payload.get("uscc") or "")
            else:
                company_name = ""
                uscc = ""
            if not company_name:
                continue

            entity = resolve_entity(name=company_name, uscc=uscc)
            entity_handle = entity.uscc or entity.name_normalized or company_name
            subject_hash = hash_subject_id(entity_handle) or None

            disposition_plan = dispo_map.get(company_name)
            if hasattr(disposition_plan, "model_dump"):
                disposition_serialized = disposition_plan.model_dump(mode="json")
            elif isinstance(disposition_plan, dict):
                disposition_serialized = dict(disposition_plan)
            else:
                disposition_serialized = {"advice": str(disposition_plan or "")}

            evidences = getattr(hit, "evidences", None) or []
            evidence_chain = [
                {
                    "source": getattr(ev, "source", "") if not isinstance(ev, dict) else ev.get("source", ""),
                    "snippet": (getattr(ev, "snippet", "") if not isinstance(ev, dict) else ev.get("snippet", ""))[:200],
                    "url": getattr(ev, "url", "") if not isinstance(ev, dict) else ev.get("url", ""),
                }
                for ev in evidences[:10]
            ]

            input_payload = {
                "scenario_key": scenario_key,
                "session_id": session_id,
                "provider_mode": mode_label,
                "company_name": company_name,
            }
            output_payload = {
                "level": level_str,
                "score": float(getattr(hit, "score", 0.0) or 0.0),
                "matched_rules": list(getattr(hit, "matched_rules", []) or []),
                "reasons": list(getattr(hit, "reasons", []) or [])[:8],
                "disposition": disposition_serialized,
            }

            retention = RETENTION_STANDARD if level_str == "red" else None  # None → 走 alert default "short"
            record_decision(
                agent_id="alert",
                endpoint=endpoint,
                input_payload=input_payload,
                output_payload=output_payload,
                evidence_chain=evidence_chain,
                jurisdiction=None,  # resolve_jurisdiction 自动 env or HQ
                retention_class=retention,
                subject_name=company_name,
                subject_id=subject_hash,
            )
            written += 1
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
            # silent-fail per CLAUDE.md §3.7.5: ledger 不破 disposition flow
            continue
    return written


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

    BE5 (2026-05-04): done envelope 加 `fallback` 字段 (per
    live-fallback-banner-spec.md) · provider degrade 时 frontend 按机器+人话
    渲染顶部 banner · 不加新 SSE event 名 (per sse-envelope §1.5 forward-compat 安全)。

    Args:
        hit_list: HitList obj | None
        dispositions: dict[company_name, DispositionPlan]
        session_id: persisted session id ("" 表持久化失败)
        scenario_key: req.scenario_key 透传
        mode_label: build_alert_provider 给的 ("web_live" / "tavily_disabled" / ...)
        kb_summary: load_kb 输出摘要 · → kb_state
    """
    # data_source 映射 mode_label → 5 enum
    # ALL IN Phase B.2 (PM 2026-05-10 reframe): 3 fallback 路径用 NullSearchProvider ·
    # 即"主路径 fail · 系统降级运行" (mock_fallback 语义) · 不是"用户主动选演示" (mock).
    # 旧 tavily_disabled / tavily_key_missing → DATA_SOURCE_MOCK 是误用 (那暗示用户主动选).
    if mode_label == "web_live":
        data_source = DATA_SOURCE_LIVE
    elif mode_label == "demo_forced":
        data_source = DATA_SOURCE_MOCK_FORCED
    elif mode_label.startswith("web_fallback_"):
        data_source = DATA_SOURCE_MOCK_FALLBACK
    elif mode_label in ("tavily_disabled", "tavily_key_missing"):
        # B.2 reframe: 系统侧降级 (Null external · internal-only) · 用户必感知
        data_source = DATA_SOURCE_MOCK_FALLBACK
    else:
        data_source = DATA_SOURCE_MOCK

    fallback_banner = _resolve_fallback_banner(mode_label)

    if hit_list is None:
        done = make_done(
            data_source=data_source,
            session_id=session_id,
            metrics={"red": 0, "yellow": 0, "green": 0, "total": 0},
            summary="扫描未产出 hit_list (KB 未装载或样本为空)",
            scenario_key=scenario_key,
            kb_state=kb_summary,
            mode=mode_label,
        )
        if fallback_banner:
            done["fallback"] = fallback_banner
        return done

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

    # ALL IN Phase B step 5 · per candidate-identity-contract v1.1 §3 alert.id 派生
    _ensure_alert_emit_ids(by_grade, top_cases)

    red_count = int(getattr(hit_list, "red_count", 0))
    yellow_count = int(getattr(hit_list, "yellow_count", 0))
    green_count = int(getattr(hit_list, "green_count", 0))
    total_scanned = int(getattr(hit_list, "total_scanned", red_count + yellow_count + green_count))

    summary = (
        f"扫描 {total_scanned} 户 · "
        f"红 {red_count} / 黄 {yellow_count} / 绿 {green_count}"
    )

    done = make_done(
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
    if fallback_banner:
        done["fallback"] = fallback_banner
    return done


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
            # ALL IN Phase B.2 step 10 · 上链 decision_ledger (silent-fail · 不破 flow)
            ledger_written = _record_alert_decisions_to_ledger(
                hit_list=captured_hit_list,
                dispositions=captured_dispositions,
                session_id=captured_session_id,
                scenario_key=req.scenario_key or "",
                mode_label=captured_mode,
                endpoint="/api/alert/scan",
            )
            done_evt["ledger_entries_written"] = ledger_written
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
async def alert_scan(
    req: AlertScanRequest,
    _user: dict = Depends(require_action("alert", "invoke")),
):
    """贷中预警批量扫描 SSE — 装载 KB → 双路交叉 → 进度/命中事件 → 处置建议汇总 → 持久化.

    QC blocker (CLAUDE.md §8): 每条 SSE payload 前置走 placeholder_guard,
    占位符残留软降级标"未能自动填写"并在事件挂 _qc_placeholder_hits 元数据。

    完成后写 data/alert/sessions/{session_id}.json + 更新 latest pointer ·
    后续 GET /api/alert/hitlist · GET /api/alert/drill/{cid} 消费同一份产物。

    Done envelope (worker-A4-alert · 2026-04-29): 共形 panels + metrics + data_source ·
    panels = {hit_list, top_cases, dispositions} · 前端 normalizeAlertSession 注入 liveData。

    Auth (B5 sub-PR 2 · 2026-05-05 · per Q-052 #8): require_action("alert", "invoke")
    enforce row-level/action gate · risk_manager/admin 可调 · RM/credit_officer/compliance_officer read-only 403.
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
# POST /api/alert/demo/run — ALL IN Phase B.2 (PM 2026-05-10 真意 reframe)
# ============================================================================
#
# OLD (Phase A · 2026-04-29 · REVERTED):
#   读 data/mock/workspace/alert/scenarios/<key>.json fixture · yield 5 stage 假节拍
#   + 假 done envelope (mode=mock_forced) · 不读 KB / 不调 LLM / 不持久化.
#
# NEW (Phase B.2 · 2026-05-10 · per dispatch §A 主活):
#   "演示 = 上传 sample → 真 backend pipeline → 真返结果" verbatim PM 真意.
#   demo 输入 = data/mock/alert-pool/clients.csv (180 户在贷客户池 · 优质 batch ·
#   per dispatch §3.5 表 alert 行内部 mock).
#   backend pipeline = scan_engine.run_scan_and_persist · 与 /api/alert/scan 同 ·
#   force_mock=False · Tavily 真接 · 真 LLM disposition · 真持久化 · 真上链 ledger.
#   mock 只能 mock 输入 · 不能 mock 结果.
# ============================================================================


ALERT_POOL_DIR = PROJECT_ROOT / "data" / "mock" / "alert-pool"
ALERT_POOL_CLIENTS_CSV = ALERT_POOL_DIR / "clients.csv"


def _alert_demo_event_stream(req: AlertDemoRunRequest):
    """ALL IN Phase B.2 demo stream · 真跑 backend pipeline (per PM 真意 reframe).

    输入: data/mock/alert-pool/clients.csv (180 户) 作为 uploaded_files ·
        通过 AlertKnowledgeBase.from_uploads → 真 KB 装载.
    pipeline: scan_engine.run_scan_and_persist · 同 /api/alert/scan ·
        Tavily 真接 (force_mock=False) · 真 cross_matcher · 真 LLM disposition ·
        真 persist_hitlist · 真 decision_ledger 上链 (per CLAUDE.md §3.7.5).
    输出: SSE 共形 envelope · mode=web_live | tavily_key_missing | web_fallback_X
        (与 /api/alert/scan 完全相同的 mode label · 透明 banner).

    红线 (per dispatch §不可 GO 条件):
      - 不 yield fixture event (fixture 路径已删)
      - 不 silent fallback fake 数据 (走 build_alert_provider banner 路径)
      - 评分真 LLM 算 (走 disposition.py · 不静态)
    """
    t0 = time.time()
    err: str | None = None

    if not ALERT_POOL_CLIENTS_CSV.is_file():
        yield encode_event(make_error(
            message=f"alert-pool batch missing: {ALERT_POOL_CLIENTS_CSV} not found",
            code="DEMO_BATCH_NOT_FOUND",
        ))
        return

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

        # Stage banner: demo input batch loaded
        yield encode_event(make_stage(
            "kb_load",
            "running",
            message=f"加载 demo batch · alert-pool · 客户池 {ALERT_POOL_CLIENTS_CSV.name}",
        ))

        try:
            for evt in run_scan_and_persist(
                scenario_key=req.scenario_key or "alert-pool",
                uploaded_files=[str(ALERT_POOL_CLIENTS_CSV)],
                api_key=os.environ.get("DEEPSEEK_API_KEY", "dummy"),
                provider="deepseek",
                force_mock=False,  # backend 真跑 · 不退 mock 路径
                use_alert_pool_fixture=True,  # B.2.3 · audit-grade fixture · cross_matcher 真命中
            ):
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

            yield encode_event(make_stage(
                "summary",
                "done",
                message="扫描完成 · alert-pool 真 backend pipeline (Tavily + LLM + ledger)",
            ))

            done_evt = _build_done_envelope(
                hit_list=captured_hit_list,
                dispositions=captured_dispositions,
                session_id=captured_session_id,
                scenario_key=req.scenario_key or "alert-pool",
                mode_label=captured_mode,
                kb_summary=captured_kb_summary,
            )
            # ALL IN Phase B.2 step 10 · 上链 decision_ledger · demo 也真上链
            # (per dispatch reframe "结果不能 mock" · 真后端跑 → 真 ledger).
            ledger_written = _record_alert_decisions_to_ledger(
                hit_list=captured_hit_list,
                dispositions=captured_dispositions,
                session_id=captured_session_id,
                scenario_key=req.scenario_key or "alert-pool",
                mode_label=captured_mode,
                endpoint="/api/alert/demo/run",
            )
            done_evt["ledger_entries_written"] = ledger_written
            # demo 模式 banner · 透明告知输入来源 (per CLAUDE.md 反馈引导行动)
            # 仅当 backend 没产 fallback banner (即 Tavily 真接通) 时加 demo-input banner
            if done_evt.get("fallback") is None:
                done_evt["fallback"] = {
                    "source": "Demo Input",
                    "reason": "alert_pool_batch",
                    "severity": "info",
                    "message": "演示模式 · 输入 alert-pool 180 户在贷客户池 · backend 真跑双路扫 + LLM 处置",
                    "hint": "线上场景把 clients.csv 替换为银行真实在贷客户名录即可 · backend 路径不变",
                    "retried": False,
                }
            yield encode_event(done_evt)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            err = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            yield encode_event(make_error_from_exception(e, code="DEMO_RUN_FAILED"))
    finally:
        audit_stream_event(
            agent_id="alert",
            endpoint="/api/alert/demo/run",
            model="deepseek-chat",
            t0=t0,
            error=err,
        )


@app.post("/api/alert/demo/run")
async def alert_demo_run(
    req: AlertDemoRunRequest,
    _user: dict = Depends(require_action("alert", "invoke")),
):
    """ALL IN Phase B.2 demo mode (2026-05-10 · PM 真意 reframe).

    PM verbatim 真意 (02:00 AM):
      "我要的演示不是一键切换 · 而是把本地的 mock 数据真实上传 ·
       通过真实后端代码跑一遍 · 最后给出结果"

    Demo input: data/mock/alert-pool/clients.csv (180 户在贷客户池 · 优质 batch ·
      per dispatch §3.5 alert 行 · 已就位 commit cf7e4b1).
    Backend: scan_engine.run_scan_and_persist · 同 /api/alert/scan · 真 KB 真 Tavily
      真 LLM disposition 真 persist 真 ledger.
    SSE envelope: 共形 panels + metrics + data_source + fallback banner.

    Auth (Phase B.1 fix · 2026-05-09): require_action("alert", "invoke") ·
      与 /api/alert/scan + /api/alert/batch_scan 一致.

    Body: {scenario_key: str = ""} (legacy field · 透传到 captured_kb_summary 标签 ·
      不再控制 fixture 路径 · fixture 路径已废)
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
# POST /api/alert/batch_scan — BE9.1 跨 scenario 批量扫描 + 聚合
# ============================================================================


def _alert_batch_event_stream(req: AlertBatchScanRequest):
    """BE9.1 (Phase B Sprint 2 · 2026-05-04): 多 scenario 批量扫描 SSE 流.

    形态:
    - 接 scenarios (1+) · 顺序跑每个 scenario · 内 streaming per-client tick
    - 可选 client_ids filter (跨 scenario 都按同一 client_id list 过)
    - aggregate done event 含: 全聚合 hit_list (red/yellow/green) + per_scenario breakdown
    - mode=batch · data_source 与最严 fallback 对齐 (任一 scenario fallback → 整体 mock_fallback)

    红线:
    - max_total_customers ≤ 50000 (per CLAUDE.md §3.7.1) · 防 abuse
    - LLM 调用经 shared/llm_caller (复用 run_scan_and_persist 内逻辑 · 不裸 init)
    - 不破 4 步 pipeline · 每 scenario 走 run_scan_and_persist (含 fallback chain)

    后续 (BE9.2):
    - alert_clusterer 消费 aggregate hits · jaccard ≥ 0.7 跨客户聚合
    - cluster pattern → Agent4→Agent2 §6.4 handoff
    """
    if not req.scenarios:
        yield encode_event(make_error(
            "scenarios 列表不能为空 · 至少给 1 个 scenario_key",
            code="EMPTY_SCENARIOS",
        ))
        return

    try:
        from agent_alert.scan_engine import run_scan_and_persist
    except ImportError as e:
        yield encode_event(make_error_from_exception(e, code="SCAN_ENGINE_IMPORT_FAILED"))
        return

    aggregate_hits: list[dict] = []
    per_scenario_breakdown: dict[str, dict] = {}
    fallback_modes: list[str] = []
    total_scanned = 0
    client_id_filter = set(req.client_ids or [])

    yield encode_event(make_stage(
        "batch_init",
        "running",
        message=(
            f"批量扫描启动 · scenarios={len(req.scenarios)} · "
            f"filter={len(client_id_filter)} client_ids · max={req.max_total_customers}"
        ),
        scenarios=list(req.scenarios),
    ))

    for scenario_idx, scenario_key in enumerate(req.scenarios, start=1):
        if total_scanned >= req.max_total_customers:
            yield encode_event(make_stage(
                "batch_capped",
                "warn",
                message=(
                    f"已扫 {total_scanned} 户 · 达到 max_total_customers={req.max_total_customers} "
                    f"· 余 {len(req.scenarios) - scenario_idx + 1} scenarios 跳过"
                ),
                scenario_key=scenario_key,
            ))
            break

        scenario_hits: list[dict] = []
        scenario_red = scenario_yellow = scenario_green = 0
        scenario_mode = ""
        scenario_session_id = ""
        scenario_total = 0

        yield encode_event(make_stage(
            "scenario_start",
            "running",
            message=f"开始扫 scenario={scenario_key} ({scenario_idx}/{len(req.scenarios)})",
            scenario_key=scenario_key,
        ))

        try:
            for evt in run_scan_and_persist(
                scenario_key=scenario_key,
                api_key=req.api_key or "dummy",
                provider=req.provider or "deepseek",
                force_mock=bool(req.force_mock),
            ):
                etype = evt.get("type", "") if isinstance(evt, dict) else ""

                if etype == "hit":
                    hit_obj = evt.get("hit")
                    if hit_obj is None:
                        continue
                    # client_id filter (跨 scenario 通用)
                    target_id = (
                        getattr(hit_obj, "hit_id", None)
                        or (getattr(hit_obj, "target", None) and getattr(hit_obj.target, "target_id", None))
                        or ""
                    )
                    if client_id_filter and target_id not in client_id_filter:
                        continue
                    scenario_total += 1
                    if total_scanned + scenario_total > req.max_total_customers:
                        # 超 cap 则 break 当前 scenario
                        scenario_total -= 1
                        break
                    compact = _to_compact_hit(hit_obj)
                    extras = getattr(hit_obj, "extras", None) or {}
                    compact["signal_kinds"] = list(extras.get("signal_kinds") or [])
                    compact["scenario_key"] = scenario_key
                    scenario_hits.append(compact)
                    bucket = compact.get("tier", "")
                    if bucket == "red":
                        scenario_red += 1
                    elif bucket == "yellow":
                        scenario_yellow += 1
                    elif bucket == "green":
                        scenario_green += 1

                    yield encode_event(make_stage(
                        "client_tick",
                        "running",
                        message=f"{scenario_key} · {compact.get('company_name', '')} · {bucket}",
                        scenario_key=scenario_key,
                        tier=bucket,
                    ))

                elif etype == "session":
                    scenario_session_id = str(evt.get("session_id", ""))
                    scenario_mode = str(evt.get("mode", ""))
                    if scenario_mode and scenario_mode != "web_live":
                        fallback_modes.append(scenario_mode)

        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
            yield encode_event(make_stage(
                "scenario_error",
                "error",
                message=f"{scenario_key} 扫描异常: {type(e).__name__}: {e}",
                scenario_key=scenario_key,
            ))
            per_scenario_breakdown[scenario_key] = {
                "session_id": "",
                "mode": "",
                "error": f"{type(e).__name__}: {e}",
                "red": 0, "yellow": 0, "green": 0, "total": 0,
            }
            continue

        aggregate_hits.extend(scenario_hits)
        total_scanned += scenario_total
        per_scenario_breakdown[scenario_key] = {
            "session_id": scenario_session_id,
            "mode": scenario_mode,
            "red": scenario_red,
            "yellow": scenario_yellow,
            "green": scenario_green,
            "total": scenario_total,
        }

        yield encode_event(make_stage(
            "scenario_done",
            "done",
            message=(
                f"{scenario_key} 完 · 红 {scenario_red} / 黄 {scenario_yellow} / 绿 {scenario_green} "
                f"· session={scenario_session_id} · mode={scenario_mode}"
            ),
            scenario_key=scenario_key,
            session_id=scenario_session_id,
        ))

    # aggregate done envelope
    by_grade: dict[str, list[dict]] = {"red": [], "yellow": [], "green": []}
    for h in aggregate_hits:
        bucket = h.get("tier", "")
        if bucket in by_grade:
            by_grade[bucket].append(h)

    sorted_hits = sorted(aggregate_hits, key=lambda h: float(h.get("score", 0.0) or 0.0), reverse=True)
    top_cases = []
    for h in sorted_hits[:20]:  # batch 给 20 (vs scan 10) · 跨 scenario 可见
        triggers = (h.get("reasons") or h.get("matched_rules") or [])[:4]
        top_cases.append({
            # ALL IN Phase B step 5 · 删旧 id=client_id · 由 _ensure_alert_emit_ids 派生
            "client_id": h.get("client_id", ""),
            "customer": h.get("company_name", ""),
            "uscc": h.get("uscc", "") or h.get("unified_credit_code", ""),
            "amount": h.get("amount", ""),
            "tier": h.get("tier", ""),
            "triggers": triggers,
            "scenario_key": h.get("scenario_key", ""),
            "lastUpdate": "刚刚",
        })

    # ALL IN Phase B step 5 · per candidate-identity-contract v1.1 §3 alert.id 派生
    _ensure_alert_emit_ids(by_grade, top_cases)

    red_total = sum(s.get("red", 0) for s in per_scenario_breakdown.values())
    yellow_total = sum(s.get("yellow", 0) for s in per_scenario_breakdown.values())
    green_total = sum(s.get("green", 0) for s in per_scenario_breakdown.values())

    # data_source 取最严 (任一 scenario fallback → mock_fallback / 全 live → live)
    if not fallback_modes:
        data_source = DATA_SOURCE_LIVE
    elif any(m.startswith("web_fallback_") for m in fallback_modes):
        data_source = DATA_SOURCE_MOCK_FALLBACK
    elif any(m == "demo_forced" for m in fallback_modes):
        data_source = DATA_SOURCE_MOCK_FORCED
    else:
        data_source = DATA_SOURCE_MOCK

    summary = (
        f"batch · 扫 {len(per_scenario_breakdown)} scenario · {total_scanned} 户 · "
        f"红 {red_total} / 黄 {yellow_total} / 绿 {green_total}"
    )

    done_evt = make_done(
        panels={
            "hit_list": by_grade,
            "top_cases": top_cases,
            "per_scenario": per_scenario_breakdown,
            "aggregate_hits": aggregate_hits,  # 给 BE9.2 alert_clusterer 消费
        },
        metrics={
            "red": red_total,
            "yellow": yellow_total,
            "green": green_total,
            "total_scanned": total_scanned,
            "scenarios_run": len(per_scenario_breakdown),
        },
        data_source=data_source,
        session_id=f"batch-{int(time.time())}",
        summary=summary,
        scenarios=list(req.scenarios),
        client_id_filter=list(client_id_filter),
        mode="batch",
        totals={"red": red_total, "yellow": yellow_total, "green": green_total},
    )
    # batch fallback banner (按最严 mode)
    worst_mode = next(
        (m for m in fallback_modes if m.startswith("web_fallback_")),
        next((m for m in fallback_modes if m), "web_live"),
    )
    fallback_banner = _resolve_fallback_banner(worst_mode)
    if fallback_banner:
        done_evt["fallback"] = fallback_banner
    yield encode_event(done_evt)


@app.post("/api/alert/batch_scan")
async def alert_batch_scan(
    req: AlertBatchScanRequest,
    _user: dict = Depends(require_action("alert", "invoke")),
):
    """BE9.1 (2026-05-04): 跨 scenario 批量扫描端点.

    Auth (Phase B.1 fix · 2026-05-09): require_action("alert", "invoke") ·
    与 /api/alert/scan 一致 · 防未授权用户触发跨 scenario 批量扫.

    输入 1+ scenario_key + 可选 client_ids filter · 顺序跑每个 scenario ·
    SSE 流 per-client tick + per-scenario aggregate · 最终 done event 含跨
    scenario 聚合 hit_list + per_scenario breakdown + aggregate_hits (给 BE9.2 消费).

    红线 (per CLAUDE.md §3.7.1): max_total_customers ≤ 50000 (默认 50000).

    Body:
    {
      "scenarios": ["baseline_100", "manuf_policy_event"],  // required 1+
      "client_ids": [],                                     // 可选 filter
      "force_mock": true,                                   // 默认 mock
      "max_total_customers": 50000
    }
    """
    def gen():
        yield from _alert_batch_event_stream(req)
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
# POST /api/alert/scan/replay/{scan_id} — BE5.5 历史 scan 重放
# ============================================================================


def _alert_replay_event_stream(scan_id: str):
    """BE5.5 (Phase B Sprint 2 · 2026-05-04): 历史 scan 重放 SSE 流.

    用途 (audit 需求):
    - 监管 / 内审复核某客户最初触发预警时的完整证据链
    - 客户经理回顾历史告警 · 对比当前扫描差异
    - 培训 / 演示用历史 case 重放 · 不消耗外部搜索 quota

    与 /api/alert/scan 共形 SSE shape · 但:
    - mode=replay · data_source=cached (per sse-envelope DATA_SOURCE_CACHED)
    - 不调 KB / 不调 LLM / 不调 SearchProvider
    - stage event 标 replay 节拍 (kb_load → external_scan → internal_match → cross → summary)
    - done envelope 复刻原 panels (hit_list/top_cases/dispositions) + replayed_at + original_generated_at

    Failure mode:
    - scan_id 不存在 → SSE error event (HITLIST_NOT_FOUND)
    - payload 格式异常 → SSE error event (REPLAY_PAYLOAD_INVALID)
    """
    try:
        from agent_alert.scan_engine import HitListNotFoundError, load_hitlist
    except ImportError as e:
        yield encode_event(make_error_from_exception(e, code="SCAN_ENGINE_IMPORT_FAILED"))
        return

    try:
        payload = load_hitlist(session_id=scan_id)
    except HitListNotFoundError as e:
        yield encode_event(make_error(str(e), code="HITLIST_NOT_FOUND"))
        return
    except (RuntimeError, ValueError, OSError, AttributeError, KeyError) as e:
        yield encode_event(make_error_from_exception(e, code="REPLAY_PAYLOAD_INVALID"))
        return

    # 5 stage 节拍 · 与 /scan 共形 stage 名 · 标 mode=replay
    stages = ["kb_load", "external_scan", "internal_match", "cross", "summary"]
    original_generated_at = str(payload.get("generated_at", ""))
    for stage in stages:
        yield encode_event(make_stage(
            stage,
            "done",
            message=f"replay · {stage} · session={scan_id} · original={original_generated_at}",
        ))
        time.sleep(0.05)  # 轻节拍 · 让前端有 stage flow 感觉 · 不假装真扫描

    # 复刻 done envelope panels
    hit_list_dict = payload.get("hit_list") or {}
    hits = hit_list_dict.get("hits") or []

    by_grade: dict[str, list[dict]] = {"red": [], "yellow": [], "green": []}
    for h in hits:
        level = (h.get("level") or "").lower()
        if level in by_grade:
            target_payload = (h.get("target") or {}).get("payload", {})
            by_grade[level].append({
                "client_id": h.get("hit_id", ""),
                "company_name": target_payload.get("company_name", ""),
                "uscc": target_payload.get("unified_credit_code", "") or target_payload.get("uscc", ""),
                "amount": target_payload.get("credit_balance", "") or target_payload.get("amount", ""),
                "tier": level,
                "score": float(h.get("score", 0.0) or 0.0),
                "matched_rules": h.get("matched_rules", []) or [],
                "reasons": h.get("reasons", []) or [],
            })

    sorted_hits = sorted(hits, key=lambda h: float(h.get("score", 0.0) or 0.0), reverse=True)
    top_cases = []
    for h in sorted_hits[:10]:
        target_payload = (h.get("target") or {}).get("payload", {})
        triggers = (h.get("reasons") or h.get("matched_rules") or [])[:4]
        top_cases.append({
            # ALL IN Phase B step 5 · 删旧 id=hit_id · 由 _ensure_alert_emit_ids 派生
            "client_id": h.get("hit_id", ""),
            "customer": target_payload.get("company_name", ""),
            "uscc": target_payload.get("unified_credit_code", "") or target_payload.get("uscc", ""),
            "amount": target_payload.get("credit_balance", "") or target_payload.get("amount", ""),
            "tier": (h.get("level") or "").lower(),
            "triggers": triggers,
            "advice": "",
            "lastUpdate": "历史 (replay)",
        })

    # ALL IN Phase B step 5 · per candidate-identity-contract v1.1 §3 alert.id 派生
    _ensure_alert_emit_ids(by_grade, top_cases)

    red_count = int(hit_list_dict.get("red_count", 0))
    yellow_count = int(hit_list_dict.get("yellow_count", 0))
    green_count = int(hit_list_dict.get("green_count", 0))
    total_scanned = int(hit_list_dict.get("total_scanned", red_count + yellow_count + green_count))

    summary = (
        f"replay · 重放 {scan_id} (生成于 {original_generated_at}) · "
        f"原扫描 {total_scanned} 户 · 红 {red_count} / 黄 {yellow_count} / 绿 {green_count}"
    )

    done_evt = make_done(
        panels={
            "hit_list": by_grade,
            "top_cases": top_cases,
            "dispositions": payload.get("dispositions") or {},
        },
        metrics={
            "red": red_count,
            "yellow": yellow_count,
            "green": green_count,
            "total_scanned": total_scanned,
        },
        # cached enum · sse-envelope DATA_SOURCE_CACHED · frontend 渲染 "历史重放" banner
        data_source="cached",
        session_id=scan_id,
        summary=summary,
        scenario_key=str(payload.get("scenario_key", "")),
        kb_state="replay · 不读 KB",
        mode="replay",
        original_mode=str(payload.get("mode", "")),
        original_generated_at=original_generated_at,
        replayed_at=datetime.now().isoformat(timespec="seconds"),
        totals={"red": red_count, "yellow": yellow_count, "green": green_count},
    )
    # replay 也有 banner · 透明告知"当前看的是历史" (per live-fallback-banner-spec §1)
    done_evt["fallback"] = {
        "source": "Replay",
        "reason": "scan_replay",
        "severity": "info",
        "message": f"历史扫描重放 · session={scan_id} · 生成于 {original_generated_at}",
        "hint": "如需最新数据 · 调 POST /api/alert/scan 重新扫描",
        "retried": False,
    }
    yield encode_event(done_evt)


@app.post("/api/alert/scan/replay/{scan_id}")
async def alert_scan_replay(
    scan_id: str,
    _user: dict = Depends(require_action("alert", "invoke")),
):
    """BE5.5 (2026-05-04): 历史 scan 重放端点 · audit 复核 / 培训 / 演示场景.

    Auth (Phase B.1 fix · 2026-05-09): require_action("alert", "invoke") ·
    与 /api/alert/scan 一致 · 防未授权用户重放历史 scan SSE.

    与 /api/alert/scan 共形 SSE 流形态 · 但:
    - mode=replay · data_source=cached
    - 不调 KB / 不调 LLM / 不调 SearchProvider · 100% 确定性回放
    - 复刻原 panels (hit_list/top_cases/dispositions) + replayed_at + original_generated_at
    - 错误 404 (HITLIST_NOT_FOUND) 走 SSE error event · frontend 显 banner

    Path param:
        scan_id: data/alert/sessions/<scan_id>.json 的文件名 (= persist_hitlist 返回的 session_id)
    """
    if not scan_id or not scan_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail=f"invalid scan_id={scan_id!r}")

    def gen():
        yield from _alert_replay_event_stream(scan_id)

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
async def alert_export_docx(
    req: AlertExportDocxRequest,
    _user: dict = Depends(require_action("alert", "export")),
):
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
