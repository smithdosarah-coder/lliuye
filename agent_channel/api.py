# -*- coding: utf-8 -*-
"""agent_channel.api — Agent1 全渠道获客 FastAPI 路由模块。

端点：
  GET  /api/channel/scenarios    — 列出预置场景元数据
  POST /api/channel/run          — 流式跑 look-alike 搜索 (SSE)
  POST /api/channel/export_xlsx  — 候选企业清单导出为 xlsx（本地 openpyxl，禁止境外 API）
  POST /api/channel/export_docx  — 候选线索 Word 报告导出（本地 python-docx · §B.7）
  POST /api/channel/handoff      — 移交选中候选给 Agent3 授信决策引擎

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- 业务逻辑全在 agent_channel.realtime_stream.run_channel_search_stream
- mock=true 强制 demo 模式，断网可演示

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import traceback
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_service.dependencies import require_action  # noqa: E402
from shared.api_utils import sse_encode, to_jsonable  # noqa: E402
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

app = FastAPI(title="Agent1 Channel Lookalike API", version="4.0")


def _qc_clean_event(evt: dict) -> dict:
    """SSE 流出口侧的占位符闸门 (CLAUDE.md §8 第 1 条)。

    对事件中的字符串字段做 placeholder scan, 命中则:
      - 用 ``mark_unfilled`` 把残留替换为"未能自动填写", 保前端可见
      - 在事件上挂 ``_qc_placeholder_hits`` 元数据, 便于 UI/log 显式提示
    不抛异常以免单条事件污染导致整个 SSE 流断, 这是 *软降级*; 调用方若想
    *硬阻断* 改 ``shared.qc.assert_clean`` 即可。
    """
    cleaned: dict = {}
    hits_total: list[str] = []
    for k, v in evt.items():
        if isinstance(v, str):
            hits = scan_placeholders(v)
            if hits:
                hits_total.extend(h.kind for h in hits)
                cleaned[k] = mark_unfilled(v)
                continue
        cleaned[k] = v
    if hits_total:
        cleaned["_qc_placeholder_hits"] = hits_total
    return cleaned


@app.get("/api/channel/scenarios")
async def list_channel_scenarios():
    try:
        from agent_channel.app_demo import SCENARIOS  # type: ignore
        return {"scenarios": [
            {"key": k, "name": v.get("name"), "desc": v.get("desc")}
            for k, v in SCENARIOS.items()
        ]}
    except (ImportError, ModuleNotFoundError, AttributeError, KeyError, TypeError):
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
                except (OSError, json.JSONDecodeError, ValueError, TypeError):
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
async def channel_run(
    req: ChannelRunRequest,
    _user: dict = Depends(require_action("channel", "invoke")),
):
    """全渠道获客真实搜索流 SSE — 5 阶段事件推送 + 最终候选清单。

    无 TAVILY_API_KEY 自动降级到 mock_fallback。

    Audit (W-FIX2 修 bug #11): generator finally 内调 audit_stream_event ·
    latency 含真实 LLM 调用时延 · 不再用 @audit_llm_call decorator
    (decorator 在 route function return StreamingResponse 即记 · 失真)。

    Auth (B5 sub-PR 2 · 2026-05-05 · per Q-052 #8): require_action("channel", "invoke")
    enforce row-level/action gate · RM/admin 可调 · 其他角色 403.
    """
    def gen():
        t0 = time.time()
        err: str | None = None
        # Codex Part 2 Area A fix: live mode (mock=False) 必须有 TAVILY_API_KEY · 否则 SSE 错误事件早失败 (不 silent mock_fallback · live-fallback-banner-spec §1.5)
        if not req.mock and not os.environ.get("TAVILY_API_KEY"):
            err = "TAVILY_KEY_MISSING"
            yield sse_encode({
                "event": "error",
                "stage": "search",
                "message": "TAVILY_API_KEY 未配置 · 真搜不可用 · 请联系运维配置或切到 demo 模式",
                "code": "TAVILY_KEY_MISSING",
            })
            return
        try:
            try:
                from agent_channel.realtime_stream import run_channel_search_stream
            except (ImportError, ModuleNotFoundError, AttributeError) as e:
                err = f"{type(e).__name__}: {e}"
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
                    # QC blocker: 占位符残留软降级为"未能自动填写"
                    yield sse_encode(_qc_clean_event(
                        {k: to_jsonable(v) for k, v in evt.items()}
                    ))
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
                err = f"{type(e).__name__}: {e}"
                traceback.print_exc()
                yield sse_encode({
                    "event": "error",
                    "message": err,
                    "traceback": traceback.format_exc()[-2000:],
                })
        finally:
            audit_stream_event(
                agent_id="channel",
                endpoint="/api/channel/run",
                model=req.provider or "deepseek-chat",
                t0=t0,
                error=err,
            )

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
# POST /api/channel/demo/run · Phase A worker-A3 (2026-04-29)
#   纯 mock SSE · 不调 LLM/Tavily · 从 data/mock/workspace/channel/scenarios/<id>.json 读
#   用途: 演示模式 / Playwright smoke / 客户走访稳定 demo 路径
#   反 5 原则 §3.5 难度分层: easy / medium / hard 三档
# ============================================================================


class ChannelDemoRunRequest(BaseModel):
    scenario_id: str = "medium"  # "easy" | "medium" | "hard"


_SCENARIO_DIR = PROJECT_ROOT / "data" / "mock" / "workspace" / "channel" / "scenarios"


@app.post("/api/channel/demo/run")
async def channel_demo_run(req: ChannelDemoRunRequest):
    """纯 mock SSE 演示流 · 不依赖 Tavily / LLM · 视觉与 live 一致 (stage 流 + done envelope).

    Per workspace-state-protocol §4 + sse-envelope §3.1 · done event panels 7 keys 同共形.
    """
    from shared.sse_envelope import (
        DATA_SOURCE_MOCK_FORCED,
        encode_event,
        make_done,
        make_error,
        make_stage,
    )
    import time as _time

    def gen():
        scenario_id = req.scenario_id or "medium"
        if scenario_id not in {"easy", "medium", "hard"}:
            yield encode_event(make_error(
                f"unknown scenario_id: {scenario_id} (allowed: easy/medium/hard)",
                code="DEMO_SCENARIO_INVALID",
            ))
            return
        path = _SCENARIO_DIR / f"{scenario_id}.json"
        if not path.exists():
            yield encode_event(make_error(
                f"scenario file not found: {path.name}",
                code="DEMO_SCENARIO_MISSING",
            ))
            return
        try:
            data = json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            yield encode_event(make_error(
                f"scenario load failed: {type(e).__name__}: {e}",
                code="DEMO_SCENARIO_LOAD",
            ))
            return

        stages = ["parse", "signal_scan", "aggregate", "enrich", "pitch", "rank"]
        stage_msgs = data.get("stage_messages", {})
        for stage_name in stages:
            yield encode_event(make_stage(
                stage_name, "running",
                message=stage_msgs.get(stage_name, f"{stage_name}..."),
            ))
            _time.sleep(0.25)
            yield encode_event(make_stage(stage_name, "done"))

        yield encode_event(make_done(
            panels={
                "candidates":              data.get("candidates", []),
                "signals":                 data.get("signals", []),
                "radar":                   data.get("radar", []),
                "funnel":                  data.get("funnel", []),
                "match_dimensions":        data.get("match_dimensions", []),
                "product_recommendations": data.get("product_recommendations", []),
                "pitch_scripts":           data.get("pitch_scripts", []),
                # V3 fix · CHANNEL_PANEL_KEYS 8 key · scenario JSON 可选 conversation 字段 ·
                # 缺则 [] · 前端 normalizeBackendDone 兜底 tplFallback.conversation
                "conversation":            data.get("conversation", []),
            },
            metrics=data.get("metrics", {}),
            data_source=DATA_SOURCE_MOCK_FORCED,
            session_id=f"demo_{scenario_id}_{int(_time.time())}",
        ))

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
# POST /api/channel/export_xlsx
# 本地 openpyxl 生成候选企业 xlsx，不走境外 API（合规见 data_classification/agent1.md）
# 表头字段严格按 docs/contracts/field-naming.md（snake_case + _yuan 后缀 + business_line 枚举）
# ============================================================================


class ChannelExportRequest(BaseModel):
    session_id: str = ""
    candidates: list[dict]
    business_line: str = "corporate"  # 导出场景默认，单候选可在 dict 内 override


# 导出列顺序与字段映射（表头 → candidate/EnterpriseProfile 取值路径）
_EXPORT_COLUMNS: list[tuple[str, str]] = [
    ("enterprise_name", "company_name"),              # ← EnterpriseProfile.company_name
    ("unified_social_credit_code", "uscc"),            # ← candidate.uscc / EP.unified_credit_code
    ("business_line", "business_line"),
    ("match_score", "match_score"),
    ("signal_count", "signal_count"),
    ("signal_types", "signal_types"),
    ("approved_amount_yuan", "approved_amount_yuan"),
    ("source_urls", "source_urls"),
    ("region", "region"),
    ("industry", "industry"),
    ("recommended_products", "recommended_products"),
    ("data_sources", "data_sources"),
]


@app.post("/api/channel/export_xlsx")
async def channel_export_xlsx(
    req: ChannelExportRequest,
    _user: dict = Depends(require_action("channel", "export")),
):
    """将候选企业清单导出为 xlsx（本地生成，禁止境外传输）。

    输入 candidates 是 /api/channel/run done 事件的 candidates 数组（带 camelCase 字段）。
    通过 CandidateProfile 做规范化，再按 field-naming.md 的 snake_case 表头落盘。
    """
    if not req.candidates:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "candidates must not be empty",
                    "details": {"field": "candidates"},
                }
            },
        )

    try:
        from openpyxl import Workbook

        from agent_channel.candidate_profile import CandidateProfile
    except Exception as e:  # noqa: BLE001 — import error surfaces to client
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"export deps unavailable: {e}",
                }
            },
        ) from e

    wb = Workbook()
    ws = wb.active
    ws.title = "candidates"
    ws.append([col for col, _ in _EXPORT_COLUMNS])

    for raw in req.candidates:
        profile = CandidateProfile.from_candidate_dict(
            raw, session_id=req.session_id, business_line=req.business_line,  # type: ignore[arg-type]
        )
        ep = profile.enterprise_profile
        row_values: list[str | int] = []
        for header, _ in _EXPORT_COLUMNS:
            row_values.append(_pick_export_value(header, profile, ep))
        ws.append(row_values)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"agent1_candidates_{req.session_id or 'export'}.xlsx"
    return Response(
        content=buf.read(),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Agent1-Export-Rows": str(len(req.candidates)),
        },
    )


# ============================================================================
# POST /api/channel/export_docx — Word 报告导出（master plan §B.7 · gap #12）
# 本地 python-docx 渲染，不走境外 API（合规见 data_classification/agent1.md）
# 内容契约：见 agent_channel/export_docx.py 模块 docstring
# ============================================================================


class ChannelExportDocxRequest(BaseModel):
    session_id: str = ""
    ideal_profile: dict | None = None
    candidates: list[dict]
    business_line: str = "corporate"
    client_manager: str = ""
    query: str = ""


@app.post("/api/channel/export_docx")
async def channel_export_docx(
    req: ChannelExportDocxRequest,
    _user: dict = Depends(require_action("channel", "export")),
):
    """生成 Agent1 候选线索 Word 报告并作为 attachment 返回。

    内容含: 客户经理 + 日期 / IdealProfile 12 维卡 / TopN 候选概览表 /
    每候选明细 (radar 8 维表 + 信号 timeline + 匹配维度 + Top3 产品 + 切入话术)。
    """
    if not req.candidates:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "candidates must not be empty",
                    "details": {"field": "candidates"},
                }
            },
        )

    try:
        from agent_channel.export_docx import build_filename, export
    except Exception as e:  # noqa: BLE001 — surface deps issue
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"export_docx deps unavailable: {e}",
                }
            },
        ) from e

    payload = req.model_dump()
    try:
        data = export(payload)
        filename = build_filename(payload)
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError) as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"docx render failed: {type(e).__name__}: {e}",
                }
            },
        ) from e

    # RFC 6266 · 中文文件名 ASCII 兜底 + UTF-8 编码段
    from urllib.parse import quote
    filename_ascii = re.sub(r"[^A-Za-z0-9._-]+", "_", filename) or "agent1_export.docx"
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename_ascii}"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "X-Agent1-Export-Candidates": str(len(req.candidates)),
            "X-Agent1-Export-Type": "docx",
        },
    )


# ============================================================================
# POST /api/channel/handoff — 移交候选到 Agent3 授信决策引擎
# 契约见 docs/contracts/channel_to_credit_handoff.md
# ============================================================================

_UUID_V4_RE = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$"
)
_HANDOFF_ROOT = PROJECT_ROOT / "data" / "handoff" / "channel_to_credit"


class ChannelHandoffRequest(BaseModel):
    session_id: str = ""  # 空串时服务端自动生成 UUID v4
    candidates: list[dict]
    business_line: str = "corporate"


@app.post("/api/channel/handoff")
async def channel_handoff(
    req: ChannelHandoffRequest,
    _user: dict = Depends(require_action("channel", "handoff")),
):
    """将候选企业 dict 转为 CandidateProfile，按契约写入本地 handoff JSON。

    返回各 profile_id + 相对路径，供 Agent3 按 profile_id 拉取。
    """
    if not req.candidates:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "candidates must not be empty",
                    "details": {"field": "candidates"},
                }
            },
        )

    session_id = req.session_id.strip() or str(uuid.uuid4())
    if not _UUID_V4_RE.match(session_id):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "session_id must be UUID v4 (per field-naming.md §4)",
                    "details": {"field": "session_id", "got": session_id},
                }
            },
        )

    from agent_channel.candidate_profile import CandidateProfile

    session_dir = _HANDOFF_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    profile_ids: list[str] = []
    relative_paths: list[str] = []
    for raw in req.candidates:
        profile = CandidateProfile.from_candidate_dict(
            raw, session_id=session_id, business_line=req.business_line,  # type: ignore[arg-type]
        )
        out_path = session_dir / f"{profile.profile_id}.json"
        out_path.write_text(
            json.dumps(profile.to_handoff_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        profile_ids.append(profile.profile_id)
        relative_paths.append(
            f"data/handoff/channel_to_credit/{session_id}/{profile.profile_id}.json"
        )

    return {
        "session_id": session_id,
        "profile_ids": profile_ids,
        "paths": relative_paths,
        "count": len(profile_ids),
        "schema_version": "1.0",
    }


def _pick_export_value(header, profile, ep) -> str | int:
    """按表头取值，统一序列化 list/None。"""
    # EnterpriseProfile 字段
    if header == "enterprise_name":
        return ep.company_name or ""
    if header == "unified_social_credit_code":
        return ep.unified_credit_code or ""
    if header == "region":
        return ep.region or ""
    if header == "industry":
        return ep.industry or ""

    # CandidateProfile 字段
    if header == "business_line":
        return profile.business_line
    if header == "match_score":
        return int(profile.match_score)
    if header == "signal_count":
        return int(profile.signal_count)
    if header == "signal_types":
        return ", ".join(profile.signal_types)
    if header == "approved_amount_yuan":
        return int(profile.approved_amount_yuan)
    if header == "source_urls":
        return "\n".join(profile.source_urls)
    if header == "recommended_products":
        return ", ".join(profile.recommended_products)
    if header == "data_sources":
        return ", ".join(profile.data_sources)
    return ""


# ============================================================================
# POST /api/channel/upload_kb — Stage B.6 backend KB upload
# 3 类 KB 文件 (customer_list / policy / industry_guide) · xlsx/pdf/docx ≤ 50MB
# 解析 + 持久化 (data/channel_kb/{kb_id}.json) + 返摘要
# 业务实现: agent_channel/kb_upload.py · 本端点仅 wire FastAPI multipart → handler
# ============================================================================


@app.post("/api/channel/upload_kb")
async def channel_upload_kb(
    kb_type: str = Form(...),
    file: UploadFile = File(...),
):
    """Channel KB 文件上传端点 · multipart/form-data.

    Field:
      kb_type: "customer_list" | "policy" | "industry_guide"
      file:    xlsx | xls | pdf | docx (single file · ≤ 50MB)

    Returns: { kb_id, kb_type, source_filename, summary_text, n_rows? | n_pages? | n_paragraphs? }
    Errors:  400 (kb_type 非法 / extension 不支持 / 内容损坏 / 空) · 413 (>50MB)
    """
    from agent_channel.kb_upload import handle_upload
    return await handle_upload(kb_type, file)


# ============================================================================
# POST /api/channel/profile — 12 维 IdealProfile LLM 抽取 (master plan §B.6b · onboarding W-B-A3)
# 消费 A2 worker 写出的 data/channel_kb/{kb_id}.json
# ============================================================================


class ChannelProfileRequest(BaseModel):
    kb_id: str
    kb_type: str = "customer_list"  # "customer_list" | "policy" | "industry_guide"


@app.post("/api/channel/profile")
async def channel_profile(req: ChannelProfileRequest):
    """从 A2 上传的 KB blob 抽 12 维 IdealProfile.

    错误处理:
      - kb_id 不存在 → 404
      - LLM 超时 → 504
      - LLM 其他失败 → 200 + 降级空 profile + reasoning_text 标原因
    """
    kb_id = (req.kb_id or "").strip()
    if not kb_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "kb_id 不能为空",
                    "details": {"field": "kb_id"},
                }
            },
        )

    try:
        from agent_channel.ideal_profile import (
            extract_ideal_profile,
            load_kb_blob,
            KBNotFoundError,
            LLMTimeoutError,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"ideal_profile module unavailable: {e}",
                }
            },
        ) from e

    try:
        blob = load_kb_blob(kb_id)
    except KBNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "KB_NOT_FOUND",
                    "message": str(e),
                    "details": {"kb_id": kb_id},
                }
            },
        ) from e

    try:
        result = extract_ideal_profile(blob, kb_type=req.kb_type)
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail={
                "error": {
                    "code": "LLM_TIMEOUT",
                    "message": str(e),
                    "details": {"kb_id": kb_id},
                }
            },
        ) from e
    except (RuntimeError, ValueError, TypeError) as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"extract_ideal_profile failed: {type(e).__name__}: {e}",
                }
            },
        ) from e

    return result.model_dump()
