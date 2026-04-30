# -*- coding: utf-8 -*-
"""agent_report.api — FastAPI + SSE 后端 · v16 主管线 wrapper.

端点:
  POST /api/report/v16/fill     — v16 主管线 SSE (Stage C.1 · classifier→generator→QC)
  POST /api/report/demo/run     — 纯 mock SSE 演示流 · scenario_id (easy/medium/hard) · Phase A worker-A4 (2026-04-29)
  POST /api/report/upload       — multipart 上传材料 + 解析摘要 (Stage C.1)
  POST /api/report/refine       — session_id 外因续跑(stub,只重跑 external_factor)
  POST /api/report/refine_section — section_id LLM 重写指定章节 (Stage C.1)
  POST /api/report/export_docx  — 从 session 数据渲染 .docx (Stage C.1)
  POST /api/report/export_pdf   — 从 session 数据渲染 .pdf (Phase A worker-A4 · prd-evidence-frozen G-10)
  GET  /api/report/downloads/{report_id}            — alias to latest session docx (Stage C.1)
  GET  /api/report/downloads/{session_id}/{filename}— UUID 白名单下载
  GET  /api/report/downloads/v16/{filename}         — v16 真路径产物
  GET  /api/report/preset/{key}                     — 预置 fixture
  GET  /health  /  GET /api/report/health           — 健康检查 + LLM 状态灯

事件契约(与前端 v16 约定 · Phase A worker-A4 align · audit cat 4 fix):
  event: stage   — {stage, progress, message, pipeline?}
  event: section — {section: {id, title, content}}
  event: done    — {session_id, report_id, pipeline:"v16", sections, qc, stats, pending_questions,
                    profile, data_source, mock_pipeline}
  event: error   — {stage, message, code?}

端口:8002(agent_credit 在 8001)
"""
from __future__ import annotations

import asyncio
import json
import os
import queue
import re
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_report.enterprise_profile import EnterpriseProfile, PendingQuestion  # noqa: E402
from agent_report.session_store import store, audit_log, hash_input  # noqa: E402
from agent_report import mock_fixtures  # noqa: E402

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

# Tiered data sources bootstrap (feat/tiered-search); fail-safe on missing deps
try:
    from shared.sources import bootstrap as _sources_bootstrap; _sources_bootstrap()  # noqa: E402
except Exception:
    pass


# ---------------------------------------------------------------------------
# FastAPI 初始化
# ---------------------------------------------------------------------------
app = FastAPI(title="Credit Report Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)
SESSIONS_DIR = OUTPUTS_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR = OUTPUTS_DIR  # 历史 docx(mock fallback 用)
TEMPLATE_DEFAULT = PROJECT_ROOT / "templates_cache" / "福建普惠授信申报及审查审批意见表2025新版.docx"

# session 目录 TTL(分钟)—— 过期连材料+docx 一起清
SESSION_DIR_TTL_MINUTES = 30


def _cleanup_expired_sessions() -> None:
    """清理 outputs/sessions/ 下超过 TTL 的子目录。惰性调用。"""
    import shutil
    if not SESSIONS_DIR.exists():
        return
    cutoff = time.time() - SESSION_DIR_TTL_MINUTES * 60
    for sub in SESSIONS_DIR.iterdir():
        try:
            if sub.is_dir() and sub.stat().st_mtime < cutoff:
                shutil.rmtree(sub, ignore_errors=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# SSE 工具
# ---------------------------------------------------------------------------
def _sse(event: str, data: dict) -> str:
    """按 SSE 协议编码事件."""
    body = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {body}\n\n"


# 5 段阶段常量
STAGE_INGEST = "ingest"
STAGE_EXTRACT = "extract"
STAGE_INFER = "infer"
STAGE_WRITE = "write"
STAGE_AUDIT = "audit"
STAGE_ORDER = [STAGE_INGEST, STAGE_EXTRACT, STAGE_INFER, STAGE_WRITE, STAGE_AUDIT]


# ---------------------------------------------------------------------------
# 阶段映射 — 把 form_filler 的内部日志归类到 5 段
# ---------------------------------------------------------------------------
def map_log_to_stage(msg: str) -> Optional[str]:
    """把 form_filler._log 的内部消息归类到 5 段,返回 None 表示不切阶段."""
    m = str(msg or "")
    # ingest: 材料加载 + KB + 锚点抽取
    if any(k in m for k in ("材料加载", "材料KB", "材料全文索引", "企业画像锚点")):
        return STAGE_INGEST
    # extract: 财务事实库 + 结构化预填
    if any(k in m for k in ("财务事实库", "KB预填", "truth_fill", "结构化预填")):
        return STAGE_EXTRACT
    # infer: 模板语义分析 + 扫描字段
    if any(k in m for k in ("模板语义", "扫描模版", "分析模板", "逐节生成模式")):
        return STAGE_INFER
    # write: 节生成 / LLM 调用
    if any(k in m for k in ("生成段落", "Section", "Phase1", "Phase2", "Phase3", "节生成", "节改写")):
        return STAGE_WRITE
    # audit: 校验 / affiliate / numeric / sanitize
    if any(k in m for k in ("校验", "validator", "sanitize", "affiliate", "affiliateguard", "清理")):
        return STAGE_AUDIT
    return None


# ---------------------------------------------------------------------------
# Mock 模式
# ---------------------------------------------------------------------------
async def _mock_stream(preset: str, business_line: Optional[str] = None) -> AsyncIterator[str]:
    """Mock 模式 SSE 事件流.

    串行推 5 个 stage 事件(每个 500ms),最后发 done。
    business_line 会写入 enterprise_profile.business_line(供下游 Agent 消费)。
    """
    messages = {
        STAGE_INGEST: "材料上传解析中...",
        STAGE_EXTRACT: "结构化数据抽取中...",
        STAGE_INFER: "企业画像与财务指标推断中...",
        STAGE_WRITE: "报告章节生成中...",
        STAGE_AUDIT: "数值校验与合规复核中...",
    }
    total = len(STAGE_ORDER)
    for idx, stage in enumerate(STAGE_ORDER):
        progress = round((idx + 1) / total, 2)
        yield _sse("stage", {
            "stage": stage,
            "progress": progress,
            "message": messages[stage],
        })
        await asyncio.sleep(0.5)

    # 组装 done payload
    profile_dict = mock_fixtures.load_preset_profile(preset)
    if business_line and not profile_dict.get("business_line"):
        profile_dict["business_line"] = business_line
    enterprise = EnterpriseProfile(**_coerce_profile(profile_dict))
    pending = mock_fixtures.sample_pending_questions(preset)

    # Mock 模式 docx_url 不再可用 (legacy 下载端点已下架 · batch 4 cleanup)
    report_docx_url = None

    # mock 场景也推几节 section,让前端看到内容
    chapters = profile_dict.get("chapters") or {}
    mock_sections = []
    for i, (k, v) in enumerate(chapters.items()):
        if not v:
            continue
        sec = {
            "id": k,
            "title": _chapter_title(k),
            "content": str(v),
        }
        mock_sections.append(sec)
        yield _sse("section", {"section": sec})
        await asyncio.sleep(0.2)

    session_id = store.create({
        "mode": "mock",
        "preset": preset,
        "enterprise_profile": enterprise.model_dump(),
        "pending_questions": pending,
        "report_docx_path": str(fallback_docx) if fallback_docx else None,
    })

    done_payload = {
        "profile": enterprise.model_dump(),
        "sections": mock_sections,
        "pending_questions": pending,
        "downstream_handoff": mock_fixtures.downstream_handoff(preset),
        "stats": {
            "total_fields": 492,
            "auto_filled": 460,
            "unfilled": 32,
        },
        "docx_url": report_docx_url,
    }
    yield _sse("done", {
        "session_id": session_id,
        "report_docx_url": report_docx_url,
        "enterprise_profile": enterprise.model_dump(),
        "pending_questions": pending,
        "downstream_handoff": mock_fixtures.downstream_handoff(preset),
        # v16 payload:前端 applyEvent 读 evt.payload.* (audit cat 4 align · Phase A worker-A4)
        "payload": done_payload,
    })


_CHAPTER_TITLES = {
    "chapter_1_background": "一、企业背景",
    "chapter_2_operation": "二、经营情况",
    "chapter_3_finance": "三、财务分析",
    "chapter_4_conclusion": "四、审批意见",
}


def _chapter_title(key: str) -> str:
    return _CHAPTER_TITLES.get(key, key)


def _coerce_profile(d: dict) -> dict:
    """fixture dict -> EnterpriseProfile 构造参数(补字段默认值)."""
    out = dict(d)
    out.setdefault("generated_at", datetime.now().isoformat(timespec="seconds"))
    out.setdefault("source_materials", [])
    return out


# ---------------------------------------------------------------------------
# 真 Pipeline 模式
# ---------------------------------------------------------------------------
def _build_llm_caller():
    """构造 LLM caller · 走 shared/llm_caller fallback chain (DeepSeek 主 + DashScope 备).

    Phase A worker-A4 (2026-04-29) · audit cat 7-5 fix:
    替代历史裸 OpenAI(base_url=...) 实现 (caller 4 of 4) · 改用 shared.llm_caller.make_text_caller
    保持 (system, user) -> str 签名不变 · 失败返 "" · refine_section 里的调用点不需改。

    fallback chain 命中第一个有 key 的 provider · 全部 key 缺失时 ProviderUnavailableError ·
    make_text_caller 已 catch 返 "" · 与历史 stub 行为对齐 · 流程不崩。
    """
    from shared.llm_caller import make_text_caller
    return make_text_caller(
        agent_id="report",
        endpoint="/api/report/refine_section",
    )


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# 业务线 → 预置资源映射 (v16 align · audit cat 4 fix · Phase A worker-A4)
# ---------------------------------------------------------------------------
BUSINESS_LINE_TO_PRESET = {
    "corporate": "dingsheng_trade",
    "inclusive": "zhangsan_restaurant",
    "reserved": "dingsheng_trade",  # 预留位,暂复用对公
}

BUSINESS_LINE_TEMPLATE_NAMES = {
    "corporate": "对公授信申报表-标准版.docx",
    "inclusive": "普惠授信申报书-标准版.docx",
    "reserved": "预留模板",
}


@app.get("/api/report/health")
async def report_health():
    """前端状态灯调用:检查 LLM 是否已配置.

    安全:只返回布尔,绝不暴露 key 内容。
    """
    key = os.environ.get("DEEPSEEK_API_KEY") or ""
    return {
        "status": "ok",
        "llm_connected": bool(key.strip()),
        "version": "0.1.0",
    }


class RefineAnswer(BaseModel):
    id: str
    value: Any


class RefineRequest(BaseModel):
    session_id: str
    answers: list[RefineAnswer] = []


@app.post("/api/report/refine")
async def report_refine(req: RefineRequest, request: Request):
    """基于 session_id 的外因续跑.

    当前版本为 stub:
      - 从 session_store 取回原 enterprise_profile
      - 推送 write/audit 两个阶段事件(只重跑 external_factor 相关 section)
      - done 事件回传相同 session_id 与(可能更新后的) enterprise_profile
    真正的 section 重跑由 V14-C Agent 负责接入 section_generator。
    """
    # 审计上下文 — DoD L2-12
    _audit_t0 = time.time()
    _audit_user = (request.headers.get("x-user-id") or "mock_wangzhe")
    _audit_input = hash_input({
        "endpoint": "/api/report/refine",
        "session_id": req.session_id,
        "answer_ids": [a.id for a in (req.answers or [])],
    })

    def _emit_audit(status: str) -> None:
        audit_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_id": _audit_user,
            "endpoint": "/api/report/refine",
            "input_hash": _audit_input,
            "output_status": status,
            "latency_ms": int((time.time() - _audit_t0) * 1000),
        })

    sess = store.get(req.session_id)
    if sess is None:
        _emit_audit("error")
        raise HTTPException(404, f"session {req.session_id} 不存在或已过期")

    async def gen():
        status = "ok"
        try:
            async for evt in _refine_stream(req, sess):
                yield evt
        except Exception:
            status = "error"
            raise
        finally:
            _emit_audit(status)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


async def _refine_stream(req: "RefineRequest", sess: dict) -> AsyncIterator[str]:
    """外因续跑 SSE 流(模块级),供 /api/report/refine 的 gen() 包装调用。"""
    # 模拟"只重跑外因相关 section"
    yield _sse("stage", {"stage": STAGE_WRITE, "progress": 0.5,
                         "message": f"基于 {len(req.answers)} 条外因答案重写相关 section..."})
    await asyncio.sleep(0.3)
    yield _sse("stage", {"stage": STAGE_AUDIT, "progress": 1.0,
                         "message": "校验完成"})

    profile = sess.get("enterprise_profile") or {}
    pending = sess.get("pending_questions") or []
    # 标记已回答的问题
    answered_ids = {a.id for a in req.answers}
    remaining = [q for q in pending if q.get("id") not in answered_ids]

    store.update(req.session_id, {
        "pending_questions": remaining,
        "last_refine_answers": [a.model_dump() for a in req.answers],
    })

    # legacy /downloads/{fname} 端点已下架 (batch 4 cleanup);refine 路径若需暴露
    # docx 链接,改走 /api/report/downloads/{session_id}/{filename} 或 v16 路径。
    report_url = None

    yield _sse("done", {
        "session_id": req.session_id,
        "report_docx_url": report_url,
        "enterprise_profile": profile,
        "pending_questions": remaining,
        "downstream_handoff": mock_fixtures.downstream_handoff(
            (profile.get("profile_id") or "dingsheng_trade")),
    })


@app.get("/api/report/downloads/{session_id}/{filename}")
async def download_session(session_id: str, filename: str):
    """下载某 session 生成的 docx.

    安全:
      - session_id 必须是 UUID 格式,filename 只取 basename
      - 最终路径必须在 SESSIONS_DIR 下(防目录穿越)
    """
    # session_id 白名单:只允 UUID4 (hex + dash)
    if not re.fullmatch(r"[0-9a-fA-F\-]{8,64}", session_id):
        raise HTTPException(400, "非法 session_id")
    safe_name = os.path.basename(filename)
    sess_dir = (SESSIONS_DIR / session_id).resolve()
    # 确保在 SESSIONS_DIR 下
    try:
        sess_dir.relative_to(SESSIONS_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "非法路径")
    target = sess_dir / safe_name
    if not target.is_file():
        raise HTTPException(404, f"文件不存在: session={session_id}, file={safe_name}")
    return FileResponse(
        path=str(target),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_name,
    )


@app.get("/api/report/preset/{key}")
async def preset_profile(key: str):
    """返回预置 fixture 的 EnterpriseProfile(只读),用于跨 Agent 预填 fallback.

    安全:只返回内嵌 stub,不会读外部敏感数据。
    """
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", key)[:64]
    profile_dict = mock_fixtures.load_preset_profile(safe)
    if not profile_dict:
        raise HTTPException(404, f"preset 不存在: {safe}")
    try:
        ent = EnterpriseProfile(**_coerce_profile(profile_dict))
        return {"preset": safe, "enterprise_profile": ent.model_dump()}
    except Exception as e:
        # fallback:直接返回 dict
        return {"preset": safe, "enterprise_profile": profile_dict, "warning": str(e)}


# ============================================================================
# Stage C.1 · 新增端点 (master plan §C.1 · gap #6 + gap #12 闭环)
#   - POST /api/report/upload        — multipart 上传材料 + 解析摘要
#   - POST /api/report/v16/fill      — v16 主管线 SSE wrapper
#   - POST /api/report/refine_section — section_id LLM 重写章节
#   - POST /api/report/export_docx   — session → docx 本地渲染
#   - GET  /api/report/downloads/{report_id}   — alias 最近一份 docx
#   - GET  /api/report/downloads/v16/{filename}— v16 真路径产物下载
# ============================================================================


# ---------------------------------------------------------------------------
# POST /api/report/upload — Stage C.1 multipart 上传 + 解析摘要
# ---------------------------------------------------------------------------

@app.post("/api/report/upload")
async def report_upload(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    business_line: str = Query("corporate"),
):
    """multipart 上传 1+ 材料文件 · 持久化到 ``data/kb/report/{report_id}/`` ·
    返 ``{report_id, file_summary}`` 供 fill 阶段引用同一 report_id 跳过重传。

    解耦上传与 fill: 与 ``/api/report/fill`` 一把梭相比 · 此端点仅持久 + 元数据 ·
    LLM 不在此调用 (empty-state-design-protocol §3 · user trigger 与 LLM 调用解耦)。
    """
    if not files:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "至少上传一个材料文件",
                              "details": {"field": "files"}}},
        )
    from agent_report.upload import (  # noqa: E402
        make_report_id, persist_files,
    )

    # 读出全部 bytes (多 file → list[(name, bytes)])
    payload: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        payload.append((f.filename or "upload.bin", content))

    report_id = make_report_id()
    summaries = persist_files(report_id, payload)

    # 审计 · 同 fill 风格
    _audit_t0 = time.time()
    _audit_user = (request.headers.get("x-user-id") or "mock_wangzhe")
    _audit_input = hash_input({
        "endpoint": "/api/report/upload",
        "report_id": report_id,
        "file_count": len(files),
        "business_line": business_line,
    })
    audit_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_id": _audit_user,
        "endpoint": "/api/report/upload",
        "input_hash": _audit_input,
        "output_status": "ok",
        "latency_ms": int((time.time() - _audit_t0) * 1000),
    })

    total_chars = sum(s.get("parsed_chars", 0) for s in summaries)
    return {
        "report_id": report_id,
        "session_id": report_id,
        "business_line": business_line,
        "file_summary": summaries,
        "total_files": len(summaries),
        "total_parsed_chars": total_chars,
    }


# ---------------------------------------------------------------------------
# POST /api/report/v16/fill — Stage C.1 v16 主管线 SSE wrapper
# ---------------------------------------------------------------------------

class V16FillRequest(BaseModel):
    report_id: str = ""           # = session_id · 关联 upload 产物 (可选)
    source_docx: str = "samples/经纬测绘_对公成稿A.docx"  # 模板 docx 路径(项目相对)
    material_dir: str = ""        # 材料目录 · 空时按 report_id 自动指向 upload dir
    classified_json: str = ""     # 默认走 outputs/v16_llm_classified.json
    business_line: str = "corporate"
    mock: bool = False            # explicit mock = true → 走 mock_v16_stream


@app.post("/api/report/v16/fill")
async def report_v16_fill(req: V16FillRequest, request: Request):
    """v16 主管线 SSE · classifier (复用) → generator → QC gate.

    自动选 mock / real (依 ``DEEPSEEK_API_KEY`` + classifier 产物存在与否) ·
    显式 ``mock=true`` 强制走 mock(empty-state-design-protocol §5 demo).

    Audit (W-FIX2 修 bug #11): 移除 @audit_llm_call decorator (decorator 在 route
    return StreamingResponse 即记 latency · 失真) · 改在 gen() finally 内调
    audit_stream_event · latency 含真实 SSE 流时延。
    内部 _emit_audit (写 session_store) 不动。
    """
    from agent_report.upload import upload_dir  # noqa: E402
    from agent_report.v16_runner import fill_stream  # noqa: E402

    # report_id 兜底
    report_id = (req.report_id or "").strip() or str(int(time.time()))

    source_docx = (PROJECT_ROOT / req.source_docx).resolve()
    classified_json = (
        Path(req.classified_json).resolve() if req.classified_json
        else (PROJECT_ROOT / "outputs" / "v16_llm_classified.json").resolve()
    )
    if req.material_dir:
        material_dir = Path(req.material_dir).resolve()
    elif req.report_id:
        material_dir = upload_dir(req.report_id).resolve()
    else:
        material_dir = (PROJECT_ROOT / "samples").resolve()

    output_dir = (PROJECT_ROOT / "outputs").resolve()

    # 审计上下文
    _audit_t0 = time.time()
    _audit_user = (request.headers.get("x-user-id") or "mock_wangzhe")
    _audit_input = hash_input({
        "endpoint": "/api/report/v16/fill",
        "report_id": report_id,
        "source": req.source_docx,
        "material": str(material_dir),
        "mock": bool(req.mock),
    })

    def _emit_audit(status: str) -> None:
        audit_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_id": _audit_user,
            "endpoint": "/api/report/v16/fill",
            "input_hash": _audit_input,
            "output_status": status,
            "latency_ms": int((time.time() - _audit_t0) * 1000),
        })

    async def gen():
        status = "ok"
        err: str | None = None
        # Codex Part 2 Area A fix: live mode (mock=False) 必须有 DEEPSEEK_API_KEY · 否则 SSE 错误事件早失败 (不 silent fallback)
        # Phase A worker-A4: shared.llm_caller fallback chain 容多个 provider · 但 v16 主管线
        # 现仍走 DeepSeek (v16_runner.fill_stream 内部硬编) · 此处 key 检查保留为 v16 早失败闸门
        if not bool(req.mock) and not os.environ.get("DEEPSEEK_API_KEY"):
            status = "error"
            err = "DEEPSEEK_KEY_MISSING"
            yield _sse("error", {
                "stage": "ingest",
                "message": "DEEPSEEK_API_KEY 未配置 · 真模式不可用 · 请联系运维配置或切到 demo 模式",
                "code": "DEEPSEEK_KEY_MISSING",
            })
            _emit_audit(status)
            audit_stream_event(
                agent_id="report",
                endpoint="/api/report/v16/fill",
                model="deepseek-chat",
                t0=_audit_t0,
                user_id=_audit_user,
                error=err,
            )
            return
        try:
            async for evt in fill_stream(
                report_id=report_id,
                source_docx=source_docx,
                material_dir=material_dir,
                classified_json=classified_json,
                output_dir=output_dir,
                explicit_mock=bool(req.mock),
            ):
                yield evt
        except Exception as e:
            status = "error"
            err = f"{type(e).__name__}: {e}"
            raise
        finally:
            _emit_audit(status)
            # W-FIX2 修 bug #11: SSE-aware audit (latency 含全流) · 替代 decorator
            audit_stream_event(
                agent_id="report",
                endpoint="/api/report/v16/fill",
                model="deepseek-chat",
                t0=_audit_t0,
                user_id=_audit_user,
                error=err,
            )

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /api/report/refine_section — Stage C.1 · LLM 重写指定章节
# ---------------------------------------------------------------------------

class RefineSectionRequest(BaseModel):
    session_id: str
    section_id: str             # chapter_1_background / 2_operation / 3_finance / 4_conclusion
    user_edit: str              # 用户输入 · 引导 LLM 重写
    target_word_count: int = 1500


@app.post("/api/report/refine_section")
async def report_refine_section(req: RefineSectionRequest, request: Request):
    """LLM 重写指定 section · 用户给 ``user_edit`` 引导(增删改方向).

    返回:
      {section: {id, title, content}, session_id, status}
    """
    sess = store.get(req.session_id)
    if sess is None:
        raise HTTPException(404, f"session {req.session_id} 不存在或已过期")

    sections = []
    payload_sec = sess.get("done_payload", {}).get("sections")
    if isinstance(payload_sec, list):
        sections = payload_sec
    target_idx = next(
        (i for i, s in enumerate(sections) if s.get("id") == req.section_id),
        None,
    )

    # 找到原文本
    old_content = ""
    old_title = _chapter_title(req.section_id)
    if target_idx is not None:
        old_content = sections[target_idx].get("content") or ""
        old_title = sections[target_idx].get("title") or old_title

    # 审计上下文
    _audit_t0 = time.time()
    _audit_user = (request.headers.get("x-user-id") or "mock_wangzhe")
    _audit_input = hash_input({
        "endpoint": "/api/report/refine_section",
        "session_id": req.session_id,
        "section_id": req.section_id,
    })

    # LLM 调用 · Codex Decision 6 fix: 无 key 显式 503 不静默 demo (与 /api/report/fill line 427-431 一致)
    has_key = bool(os.environ.get("DEEPSEEK_API_KEY"))
    if not has_key:
        raise HTTPException(
            status_code=503,
            detail="DEEPSEEK_API_KEY 未配置 · 真改写不可用 · 请联系运维配置或回退到原章节",
        )

    llm_caller = _build_llm_caller()
    new_content = ""
    if old_content:
        system = (
            "你是信贷调查报告重写助手。基于客户经理的指引,把原段落改写得更准确、"
            "更完整,但不得编造数字 / 名称 / 资质 / 任何无原始证据的事实。"
            "保持段落语气专业。直接输出新段落正文。"
        )
        user = (
            f"原章节:{old_title}\n"
            f"原文本:\n{old_content}\n\n"
            f"客户经理指引:\n{req.user_edit}\n\n"
            f"目标字数:约 {req.target_word_count} 字。请重写此段。"
        )
        try:
            new_content = (llm_caller(system, user) or "").strip()
        except Exception as e:  # noqa: BLE001 — LLM 失败显式 503 不 fallback
            raise HTTPException(
                status_code=503,
                detail=f"LLM 调用失败 · {type(e).__name__}: {e}",
            ) from e

    if not new_content:
        # 仅当 LLM 返空内容时 fallback (老文本 + 客户经理指引拼接 · 不冒用 LLM 名义)
        new_content = (
            (old_content or "")
            + "\n\n[客户经理指引补充]\n"
            + req.user_edit
        )

    new_section = {
        "id": req.section_id,
        "title": old_title,
        "content": new_content,
        "status": "done",
        "word_count": len(new_content),
        "refined_at": datetime.now().isoformat(timespec="seconds"),
    }

    # 写回 session
    if target_idx is not None:
        sections[target_idx] = new_section
    else:
        sections.append(new_section)
    new_payload = dict(sess.get("done_payload") or {})
    new_payload["sections"] = sections
    store.update(req.session_id, {
        "done_payload": new_payload,
        "last_refined_section": req.section_id,
    })

    audit_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_id": _audit_user,
        "endpoint": "/api/report/refine_section",
        "input_hash": _audit_input,
        "output_status": "ok",
        "latency_ms": int((time.time() - _audit_t0) * 1000),
    })

    return {
        "session_id": req.session_id,
        "report_id": req.session_id,
        "section": new_section,
        "status": "ok",
        "llm_used": bool(has_key),
    }


# ---------------------------------------------------------------------------
# POST /api/report/export_docx — Stage C.1 · session → docx 本地渲染
# ---------------------------------------------------------------------------

class ExportDocxRequest(BaseModel):
    session_id: str = ""        # 取 session 的 sections / profile
    report_id: str = ""         # session_id 别名
    # 直接传字段(不依赖 session · 用于 mock 路径)
    profile: dict | None = None
    sections: list[dict] | None = None
    pending_questions: list[dict] | None = None
    stats: dict | None = None
    qc: dict | None = None
    business_line: str = "corporate"
    client_manager: str = ""


@app.post("/api/report/export_docx")
async def report_export_docx(req: ExportDocxRequest, request: Request):
    """从 session 数据(或直接 payload)渲 .docx · 返 attachment 下载."""
    from urllib.parse import quote
    from agent_report.word_export import build_filename, export

    sid = (req.session_id or req.report_id or "").strip()
    payload: dict[str, Any] = {
        "report_id": sid,
        "session_id": sid,
        "business_line": req.business_line,
        "client_manager": req.client_manager,
    }

    # 优先从 session 取 sections / profile / pending
    if sid:
        sess = store.get(sid)
        if sess:
            done_payload = sess.get("done_payload") or {}
            ep = sess.get("enterprise_profile") or done_payload.get("profile") or {}
            payload["profile"] = ep
            payload["sections"] = done_payload.get("sections") or []
            payload["pending_questions"] = sess.get("pending_questions") or []
            payload["stats"] = done_payload.get("stats") or {}

    # 显式 payload 字段覆盖 session
    if req.profile is not None:
        payload["profile"] = req.profile
    if req.sections is not None:
        payload["sections"] = req.sections
    if req.pending_questions is not None:
        payload["pending_questions"] = req.pending_questions
    if req.stats is not None:
        payload["stats"] = req.stats
    if req.qc is not None:
        payload["qc"] = req.qc

    if not payload.get("sections") and not payload.get("profile"):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "需 session_id (含 sections) 或显式 profile/sections",
                              "details": {"field": "session_id|sections"}}},
        )

    # 审计
    _audit_t0 = time.time()
    _audit_user = (request.headers.get("x-user-id") or "mock_wangzhe")
    _audit_input = hash_input({
        "endpoint": "/api/report/export_docx",
        "session_id": sid,
        "section_count": len(payload.get("sections") or []),
    })

    try:
        data = export(payload)
        filename = build_filename(payload)
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError) as e:
        audit_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_id": _audit_user,
            "endpoint": "/api/report/export_docx",
            "input_hash": _audit_input,
            "output_status": "error",
            "latency_ms": int((time.time() - _audit_t0) * 1000),
        })
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"docx 渲染失败: {type(e).__name__}: {e}"}},
        ) from e

    audit_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_id": _audit_user,
        "endpoint": "/api/report/export_docx",
        "input_hash": _audit_input,
        "output_status": "ok",
        "latency_ms": int((time.time() - _audit_t0) * 1000),
    })

    filename_ascii = re.sub(r"[^A-Za-z0-9._-]+", "_", filename) or "agent6_report.docx"
    from fastapi.responses import Response  # 局部 import 避顶部冲突
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
            "X-Agent6-Export-Type": "docx",
            "X-Agent6-Export-Sections": str(len(payload.get("sections") or [])),
        },
    )


# ---------------------------------------------------------------------------
# GET /api/report/downloads/{report_id}  alias — 取最新 session docx
# ---------------------------------------------------------------------------

@app.get("/api/report/downloads/{report_id}")
async def download_report_alias(report_id: str):
    """报告 alias 端点 · 从 session 找 ``report_docx_path`` 直返."""
    if not re.fullmatch(r"[0-9a-fA-F\-]{8,64}", report_id):
        raise HTTPException(400, "非法 report_id")
    sess = store.get(report_id)
    if sess is None:
        raise HTTPException(404, f"session {report_id} 不存在或已过期")
    docx_path = sess.get("report_docx_path")
    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(404, f"session {report_id} 暂无 docx 产物 · 请先 fill 或 export")
    fname = os.path.basename(docx_path)
    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=fname,
    )


# ---------------------------------------------------------------------------
# GET /api/report/downloads/v16/{filename} — v16 真路径产物下载
# ---------------------------------------------------------------------------

@app.get("/api/report/downloads/v16/{filename}")
async def download_v16_output(filename: str):
    """v16 主管线产物下载 · ``outputs/{filename}_v16.docx`` 取."""
    safe = os.path.basename(filename)
    target = (PROJECT_ROOT / "outputs" / safe).resolve()
    try:
        target.relative_to((PROJECT_ROOT / "outputs").resolve())
    except ValueError:
        raise HTTPException(400, "非法路径") from None
    if not target.is_file():
        raise HTTPException(404, f"v16 产物不存在: {safe}")
    return FileResponse(
        path=str(target),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe,
    )


# ============================================================================
# POST /api/report/demo/run · Phase A worker-A4 (2026-04-29)
#   纯 mock SSE · 不调 LLM · 从 data/mock/workspace/report/scenarios/<id>.json 读
#   用途: 演示模式 / Playwright smoke / 客户走访稳定 demo 路径
#   反 5 原则 §3.5 难度分层: easy / medium / hard 三档
#   契约: 与 /api/report/v16/fill done event 同形 (sections + qc + stats + profile)
# ============================================================================


class ReportDemoRunRequest(BaseModel):
    scenario_id: str = "medium"  # "easy" | "medium" | "hard"


_REPORT_SCENARIO_DIR = PROJECT_ROOT / "data" / "mock" / "workspace" / "report" / "scenarios"


@app.post("/api/report/demo/run")
async def report_demo_run(req: ReportDemoRunRequest):
    """纯 mock SSE 演示流 · 不依赖 DEEPSEEK_API_KEY / v16 主管线 · 视觉与 live 一致.

    与 /api/report/v16/fill 共形 (event 名 stage / section / done / error · payload key
    sections / qc / stats / profile / pending_questions · data_source=mock_forced).
    Phase A worker-A4 · audit cat 4 align (event v16 同名) · 5 原则 §3.5 难度分层.
    """
    if req.scenario_id not in {"easy", "medium", "hard"}:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "DEMO_SCENARIO_INVALID",
                              "message": f"unknown scenario_id: {req.scenario_id} (allowed: easy/medium/hard)"}},
        )
    path = _REPORT_SCENARIO_DIR / f"{req.scenario_id}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "DEMO_SCENARIO_MISSING",
                              "message": f"scenario file not found: {path.name}"}},
        )
    try:
        data = json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "DEMO_SCENARIO_LOAD",
                              "message": f"scenario load failed: {type(e).__name__}: {e}"}},
        ) from e

    async def gen():
        stage_msgs = data.get("stage_messages") or {}
        total = len(STAGE_ORDER)
        for idx, stage in enumerate(STAGE_ORDER):
            progress = round((idx + 1) / total, 2)
            yield _sse("stage", {
                "stage": stage,
                "progress": progress,
                "message": stage_msgs.get(stage, f"{stage}..."),
                "pipeline": "v16",
            })
            await asyncio.sleep(0.2)

        sections = data.get("sections") or []
        for sec in sections:
            yield _sse("section", {"section": sec})
            await asyncio.sleep(0.15)

        session_id = f"demo_report_{req.scenario_id}_{int(time.time())}"
        done_payload: dict[str, Any] = {
            "event": "done",
            "data_source": "mock_forced",
            "pipeline": "v16",
            "mock_pipeline": True,
            "session_id": session_id,
            "report_id": session_id,
            "sections": sections,
            "profile": data.get("profile") or {},
            "stats": data.get("stats") or {},
            "qc": data.get("qc") or {"passed": True, "score": 88, "fatal_fail": False, "halluc_count": 0},
            "pending_questions": data.get("pending_questions") or [],
        }
        # 持久 session 让后续 export 能命中 (与 v16 fill_stream 一致)
        store.create({
            "mode": "demo",
            "scenario_id": req.scenario_id,
            "done_payload": done_payload,
            "enterprise_profile": done_payload["profile"],
            "pending_questions": done_payload["pending_questions"],
        })
        yield _sse("done", done_payload)

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
# POST /api/report/export_pdf · Phase A worker-A4 (2026-04-29)
#   prd-evidence-frozen G-10 · export_pdf 真接 (前端 toolbar PDF 按钮 wire)
#   实现: reportlab 直接渲 sections (不经过 .docx → .pdf 的 LibreOffice 链路 · 避部署依赖)
# ============================================================================


@app.post("/api/report/export_pdf")
async def report_export_pdf(req: ExportDocxRequest, request: Request):
    """从 session 数据(或显式 payload)渲 .pdf · 返 attachment 下载.

    与 /api/report/export_docx 共用 ExportDocxRequest schema · 同源异格输出 · 给客户的
    "导出 PDF" toolbar 按钮真接 (G-10 闭环) · 分享链接 / 版本时光机仍 Phase B.

    实现: reportlab platypus · 简体中文需嵌字体 · 失败回退英文 helvetica + 中文转拼音兜底
    (PDF 是分发格式 · 不要求精排 · 银行可读即可 · 精排走 docx 路径).
    """
    from urllib.parse import quote
    from io import BytesIO

    sid = (req.session_id or req.report_id or "").strip()
    payload: dict[str, Any] = {
        "report_id": sid,
        "session_id": sid,
        "business_line": req.business_line,
        "client_manager": req.client_manager,
    }

    if sid:
        sess = store.get(sid)
        if sess:
            done_payload = sess.get("done_payload") or {}
            ep = sess.get("enterprise_profile") or done_payload.get("profile") or {}
            payload["profile"] = ep
            payload["sections"] = done_payload.get("sections") or []
            payload["pending_questions"] = sess.get("pending_questions") or []
            payload["stats"] = done_payload.get("stats") or {}

    if req.profile is not None:
        payload["profile"] = req.profile
    if req.sections is not None:
        payload["sections"] = req.sections
    if req.pending_questions is not None:
        payload["pending_questions"] = req.pending_questions
    if req.stats is not None:
        payload["stats"] = req.stats
    if req.qc is not None:
        payload["qc"] = req.qc

    if not payload.get("sections") and not payload.get("profile"):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "需 session_id (含 sections) 或显式 profile/sections",
                              "details": {"field": "session_id|sections"}}},
        )

    _audit_t0 = time.time()
    _audit_user = (request.headers.get("x-user-id") or "mock_wangzhe")
    _audit_input = hash_input({
        "endpoint": "/api/report/export_pdf",
        "session_id": sid,
        "section_count": len(payload.get("sections") or []),
    })

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        )
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    except ImportError as e:
        audit_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_id": _audit_user,
            "endpoint": "/api/report/export_pdf",
            "input_hash": _audit_input,
            "output_status": "error",
            "latency_ms": int((time.time() - _audit_t0) * 1000),
        })
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"reportlab unavailable: {e}"}},
        ) from e

    # 中文字体注册 · STSong-Light 是 reportlab 内置 CJK CID 字体 · 不需外部 ttf
    cn_font = "Helvetica"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        cn_font = "STSong-Light"
    except Exception:
        pass

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1cn", parent=styles["Heading1"], fontName=cn_font, fontSize=18, leading=24)
    h2 = ParagraphStyle("h2cn", parent=styles["Heading2"], fontName=cn_font, fontSize=14, leading=20)
    body = ParagraphStyle("bodycn", parent=styles["BodyText"], fontName=cn_font, fontSize=11, leading=18)
    foot = ParagraphStyle("footcn", parent=styles["Italic"], fontName=cn_font, fontSize=9, textColor="#666666")

    flow: list[Any] = []
    profile = payload.get("profile") or {}
    title = profile.get("company_name") or sid or "授信调查报告"
    flow.append(Paragraph(f"{title} · 授信调查报告", h1))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(
        f"业务线: {payload.get('business_line', '-')} · 客户经理: {payload.get('client_manager', '-')} · 生成时间: {datetime.now().isoformat(timespec='minutes')}",
        body,
    ))
    flow.append(Spacer(1, 18))

    for sec in (payload.get("sections") or []):
        sec_title = sec.get("title") or sec.get("id") or "(未命名章节)"
        sec_content = sec.get("content") or "(暂无内容)"
        flow.append(Paragraph(sec_title, h2))
        flow.append(Spacer(1, 6))
        # paragraph 不接受单 \n · 转 <br/>
        safe = (
            str(sec_content)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )
        flow.append(Paragraph(safe, body))
        flow.append(Spacer(1, 14))

    flow.append(Spacer(1, 18))
    flow.append(Paragraph(
        "— 以上为 AI 协作预览稿 · 未经人工终审不得作为正式决策依据 —", foot,
    ))

    try:
        doc.build(flow)
    except Exception as e:
        audit_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_id": _audit_user,
            "endpoint": "/api/report/export_pdf",
            "input_hash": _audit_input,
            "output_status": "error",
            "latency_ms": int((time.time() - _audit_t0) * 1000),
        })
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"pdf 渲染失败: {type(e).__name__}: {e}"}},
        ) from e

    data = buf.getvalue()
    safe_company = re.sub(r"[^\w.-]+", "_", str(title))[:40] or "agent6_report"
    filename = f"{safe_company}_授信调查报告.pdf"
    filename_ascii = re.sub(r"[^A-Za-z0-9._-]+", "_", filename) or "agent6_report.pdf"

    audit_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_id": _audit_user,
        "endpoint": "/api/report/export_pdf",
        "input_hash": _audit_input,
        "output_status": "ok",
        "latency_ms": int((time.time() - _audit_t0) * 1000),
    })

    from fastapi.responses import Response
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename_ascii}"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "X-Agent6-Export-Type": "pdf",
            "X-Agent6-Export-Sections": str(len(payload.get("sections") or [])),
        },
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run("agent_report.api:app", host="127.0.0.1", port=port, reload=False)
