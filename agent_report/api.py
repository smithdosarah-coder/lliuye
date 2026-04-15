# -*- coding: utf-8 -*-
"""agent_report.api — FastAPI + SSE 后端,封装 V13 form-fill pipeline.

端点:
  POST /api/report/fill     — 流式推送 5 阶段 + done,可带 mock=1 走预置场景
  POST /api/report/refine   — 基于 session_id 的外因续跑(stub,只重跑 external_factor section)
  GET  /downloads/<file>    — 下载生成的 docx
  GET  /health              — 健康检查

事件契约(与前端 V14-B 约定):
  event: stage   — {stage, progress, message}
  event: done    — {session_id, report_docx_url, enterprise_profile, pending_questions, downstream_handoff}
  event: error   — {stage, message}

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
from agent_report.session_store import store  # noqa: E402
from agent_report import mock_fixtures  # noqa: E402


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

    # Mock 模式沿用历史 docx(在 outputs 根目录,/downloads/{fname} 老端点兜底)
    fallback_docx = mock_fixtures.fallback_docx_path(OUTPUTS_DIR)
    report_docx_url = (
        f"/api/report/downloads/legacy/{fallback_docx.name}" if fallback_docx else None
    )

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
        # V14 payload:前端 applyEvent 读 evt.payload.*
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
    """构造 DeepSeek LLM caller,照抄 test_full_pipeline.py.

    若未配置 DEEPSEEK_API_KEY,返回 stub(直接返回空字符串),让流程不崩。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        def stub(system_prompt: str, user_prompt: str) -> str:
            return ""
        return stub

    try:
        from openai import OpenAI
    except ImportError:
        def stub(system_prompt: str, user_prompt: str) -> str:
            return ""
        return stub

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    def caller(system_prompt: str, user_prompt: str) -> str:
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=8192,
                temperature=0.3,
                timeout=120,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"[LLM error] {e}")
            return ""

    return caller


def _load_uploaded_materials(upload_paths: list[Path]) -> tuple[dict, dict]:
    """把上传的文件读成 (file_contents, file_path_map),沿用 tools._read_single_file."""
    try:
        from tools import _read_single_file  # type: ignore
    except Exception as e:
        print(f"[ingest] _read_single_file import 失败: {e}")
        _read_single_file = None

    file_contents: dict[str, str] = {}
    file_path_map: dict[str, str] = {}
    exts = {".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"}
    for p in upload_paths:
        if p.suffix.lower() not in exts:
            continue
        if _read_single_file is None:
            continue
        try:
            content = _read_single_file(str(p))
            if content:
                file_contents[p.name] = content
                file_path_map[p.name] = str(p)
        except Exception as e:
            print(f"[ingest] 读取 {p.name} 失败: {e}")
    return file_contents, file_path_map


def _build_enterprise_profile_from_run(agent, output_path: str,
                                       source_files: list[str]) -> EnterpriseProfile:
    """从 FormFillAgent.run() 产物回构 EnterpriseProfile.

    主要消费:
      - agent.kb (material_kb 产物)
      - agent._truth_financial_data (truth_fill 产物)
      - material_anchor(若可用)
    字段不齐全时全部降级为 None / 空字符串。
    """
    facts = (getattr(agent, "kb", None) or {}).get("facts", {}) or {}
    truth_fin = getattr(agent, "_truth_financial_data", None) or {}

    # 选最新年份数据
    annual = [k for k in truth_fin.keys() if re.fullmatch(r"20\d{2}", str(k or ""))]
    annual.sort()
    latest = annual[-1] if annual else None
    prev = annual[-2] if len(annual) >= 2 else None

    def _num(d: dict, *keys) -> Optional[float]:
        for k in keys:
            v = d.get(k)
            if v is None:
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
        return None

    latest_d = truth_fin.get(latest, {}) if latest else {}
    prev_d = truth_fin.get(prev, {}) if prev else {}

    fa = {
        "revenue_latest": _num(latest_d, "营业收入", "revenue", "主营业务收入"),
        "revenue_prev": _num(prev_d, "营业收入", "revenue", "主营业务收入"),
        "net_profit_latest": _num(latest_d, "净利润", "net_profit"),
        "net_profit_prev": _num(prev_d, "净利润", "net_profit"),
        "total_assets": _num(latest_d, "资产总计", "total_assets"),
        "total_liabilities": _num(latest_d, "负债合计", "total_liabilities"),
        "net_assets": _num(latest_d, "所有者权益", "net_assets"),
        "accounts_receivable": _num(latest_d, "应收账款", "accounts_receivable"),
        "inventory": _num(latest_d, "存货", "inventory"),
        "operating_cash_flow": _num(latest_d, "经营活动现金流量净额", "operating_cash_flow"),
        "short_term_borrowing": _num(latest_d, "短期借款", "short_term_borrowing"),
        "ebitda": _num(latest_d, "EBITDA", "ebitda"),
        "period": f"{latest}年度" if latest else None,
    }

    company_name = (facts.get("company_name") or "未知企业").strip() or "未知企业"
    pid = "report_" + re.sub(r"[^0-9A-Za-z_]+", "_", company_name)[:32] + "_" + str(int(time.time()))

    profile = EnterpriseProfile(
        profile_id=pid,
        company_name=company_name,
        unified_credit_code=facts.get("unified_credit_code"),
        industry=facts.get("industry"),
        establishment_date=facts.get("establishment_date"),
        registered_capital=facts.get("registered_capital"),
        employee_count=None,
        region=facts.get("region"),
        main_business=facts.get("main_business") or facts.get("business"),
        controller_name=facts.get("controller_name"),
        controller_share_pct=facts.get("controller_share_pct"),
        financial_anchors=fa,  # type: ignore[arg-type]
        source_materials=source_files,
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )
    return profile


def _run_real_pipeline(upload_paths: list[Path],
                       template_path: Path,
                       session_dir: Path,
                       emit: "queue.Queue[str]",
                       business_line: Optional[str] = None) -> None:
    """在工作线程里真跑 V13 pipeline,把 stage/done/error 事件推进 emit 队列.

    session_dir:所有本次运行产物(材料副本 / docx)都落在该目录下,30min TTL 统一清。
    """
    # 未配置 LLM key 时立即返回明确错误,别让用户等 10 分钟
    if not os.environ.get("DEEPSEEK_API_KEY"):
        emit.put(_sse("error", {"stage": STAGE_INGEST,
                                "message": "后端未配置 DEEPSEEK_API_KEY,真模式不可用。请切换 Mock 演示或联系 IT 配置。"}))
        emit.put("__END__")
        return

    try:
        from form_filler import FormFillAgent  # type: ignore
    except Exception as e:
        emit.put(_sse("error", {"stage": STAGE_INGEST,
                                "message": f"form_filler import 失败: {e}"}))
        emit.put("__END__")
        return

    emit.put(_sse("stage", {"stage": STAGE_INGEST, "progress": 0.05,
                            "message": "准备材料..."}))

    file_contents, file_path_map = _load_uploaded_materials(upload_paths)
    if not file_contents:
        emit.put(_sse("error", {"stage": STAGE_INGEST,
                                "message": "未成功读取任何材料,请检查上传文件格式(支持 docx/pdf/xlsx/txt)"}))
        emit.put("__END__")
        return

    llm_caller = _build_llm_caller()
    agent = FormFillAgent(llm_caller, file_contents, file_path_map=file_path_map)

    output_path = str(session_dir / f"report_{int(time.time())}.docx")

    # progress_cb 把内部日志归类到 5 段并发事件
    seen_stages: set[str] = set()
    stage_count = [0]

    def progress_cb(msg: str) -> None:
        try:
            stage = map_log_to_stage(msg)
            if stage:
                if stage not in seen_stages:
                    seen_stages.add(stage)
                    stage_count[0] += 1
                progress = min(0.95, stage_count[0] / len(STAGE_ORDER))
                emit.put(_sse("stage", {
                    "stage": stage,
                    "progress": round(progress, 2),
                    "message": str(msg)[:200],
                }))
        except Exception:
            pass

    try:
        result_path = agent.run(str(template_path), output_path, progress_cb)
    except Exception as e:
        traceback.print_exc()
        emit.put(_sse("error", {"stage": STAGE_WRITE,
                                "message": f"pipeline 执行失败: {e}"}))
        emit.put("__END__")
        return

    # 最后补一条 audit 完成
    emit.put(_sse("stage", {"stage": STAGE_AUDIT, "progress": 1.0,
                            "message": "生成完成"}))

    try:
        profile = _build_enterprise_profile_from_run(
            agent, result_path, list(file_contents.keys()))
        if business_line:
            profile.business_line = business_line  # type: ignore[assignment]
    except Exception as e:
        traceback.print_exc()
        emit.put(_sse("error", {"stage": STAGE_AUDIT,
                                "message": f"EnterpriseProfile 构造失败: {e}"}))
        emit.put("__END__")
        return

    # Pending questions:V14-C 未接入前返回 stub
    pending = mock_fixtures.sample_pending_questions("dingsheng_trade")

    session_id = store.create({
        "mode": "real",
        "enterprise_profile": profile.model_dump(),
        "pending_questions": pending,
        "report_docx_path": str(result_path),
        "upload_paths": [str(p) for p in upload_paths],
    })

    fname = os.path.basename(result_path)
    docx_url = f"/api/report/downloads/{session_id}/{fname}"
    # 把 docx 拷贝到 session_id 为目录(而非 session_dir 名,因它是 upload-时随机前缀)
    import shutil
    final_sess_dir = SESSIONS_DIR / session_id
    final_sess_dir.mkdir(parents=True, exist_ok=True)
    try:
        dst = final_sess_dir / fname
        if Path(result_path).resolve() != dst.resolve():
            shutil.copy2(result_path, dst)
    except Exception as e:
        print(f"[session copy] 失败: {e}")

    # 更新 session 里的 docx 路径为 final dir,方便后续下载端点查找
    store.update(session_id, {"report_docx_path": str(final_sess_dir / fname)})

    # 构造给前端的 sections(尽力从 agent / profile.chapters 回构)
    sections = []
    try:
        chapters_d = profile.chapters.model_dump() if hasattr(profile.chapters, "model_dump") else dict(profile.chapters or {})
    except Exception:
        chapters_d = {}
    for k, v in chapters_d.items():
        if v:
            sections.append({"id": k, "title": _chapter_title(k), "content": str(v)})
    # 补:从 section_generator 跑过的产物里拿(若 agent 保留)
    sec_cache = getattr(agent, "_generated_sections", None)
    if isinstance(sec_cache, list) and sec_cache:
        for s in sec_cache:
            if isinstance(s, dict) and s.get("content"):
                sections.append({
                    "id": s.get("id") or s.get("section_id") or f"sec_{len(sections)}",
                    "title": s.get("title") or s.get("section_title") or "段落",
                    "content": s.get("content") or "",
                })

    # FormFillAgent 实际字段:self.stats = {"total_sections", "filled", "errors"},
    # self.pending_tags = [...] 是未填字段清单
    agent_stats = getattr(agent, "stats", {}) or {}
    pending_tags = getattr(agent, "pending_tags", []) or []
    filled = int(agent_stats.get("filled", 0))
    unfilled = len(pending_tags)
    total_fields = int(agent_stats.get("total_sections", 0)) or (filled + unfilled)
    stats = {
        "total_fields": total_fields,
        "auto_filled": filled,
        "unfilled": unfilled,
    }

    done_payload = {
        "profile": profile.model_dump(),
        "sections": sections,
        "pending_questions": pending,
        "downstream_handoff": mock_fixtures.downstream_handoff(profile.profile_id),
        "stats": stats,
        "docx_url": docx_url,
    }

    emit.put(_sse("done", {
        "session_id": session_id,
        "report_docx_url": docx_url,
        "enterprise_profile": profile.model_dump(),
        "pending_questions": pending,
        "downstream_handoff": mock_fixtures.downstream_handoff(profile.profile_id),
        "payload": done_payload,
    }))
    emit.put("__END__")


async def _real_stream(upload_paths: list[Path],
                       template_path: Path,
                       session_dir: Path,
                       business_line: Optional[str] = None) -> AsyncIterator[str]:
    """真 pipeline 的 SSE 流:开工作线程跑 pipeline,主协程从队列消费事件."""
    emit: "queue.Queue[str]" = queue.Queue()
    worker = threading.Thread(
        target=_run_real_pipeline,
        args=(upload_paths, template_path, session_dir, emit, business_line),
        daemon=True,
    )
    worker.start()

    while True:
        # 阻塞获取时用 run_in_executor 避免卡住事件循环
        try:
            item = await asyncio.get_event_loop().run_in_executor(
                None, emit.get, True, 0.5)
        except queue.Empty:
            # 轮询 worker 是否还活着
            if not worker.is_alive():
                break
            continue
        if item == "__END__":
            break
        yield item


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# 业务线 → 预置资源映射 (V14-D)
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


@app.post("/api/report/fill")
async def report_fill(
    request: Request,
    mock: int = Query(0),
    preset: str = Query("dingsheng_trade"),
    business_line: str = Query("corporate"),
    files: list[UploadFile] = File(default=[]),
    template_file: Optional[UploadFile] = File(default=None),
):
    """生成信贷报告.

    - mock=1 走预置 fixture,5 段假进度+done
    - mock=0 走真 pipeline,需要上传材料文件(files)
    - business_line:普惠 inclusive / 对公 corporate / 预留 reserved
    - template_file:客户自传的申报书模板;不传则用业务线对应的内置默认
    """
    # business_line 决定 mock preset(若未显式传 preset 或与 business_line 冲突)
    effective_preset = preset
    if business_line in BUSINESS_LINE_TO_PRESET and preset == "dingsheng_trade":
        # 只有在 preset 仍是默认值时才按业务线覆盖,避免显式传 preset 被吞
        effective_preset = BUSINESS_LINE_TO_PRESET[business_line]

    if mock == 1:
        async def gen():
            async for evt in _mock_stream(effective_preset, business_line):
                yield evt
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache",
                                          "X-Accel-Buffering": "no"})

    # 真 pipeline:先把上传文件落盘到 session 目录(outputs/sessions/<random>)
    if not files:
        raise HTTPException(400, "真模式需要上传至少一个材料文件")

    # 预创建 session 工作目录(30min TTL 清理)
    _cleanup_expired_sessions()
    session_dir = Path(tempfile.mkdtemp(prefix="work_", dir=str(SESSIONS_DIR)))

    saved: list[Path] = []
    for f in files:
        safe_name = os.path.basename(f.filename or "upload.bin")
        dst = session_dir / safe_name
        with dst.open("wb") as out:
            out.write(await f.read())
        saved.append(dst)

    # 模板:优先用前端上传的,否则用业务线默认
    template: Path = TEMPLATE_DEFAULT
    if template_file is not None and template_file.filename:
        tpl_name = os.path.basename(template_file.filename)
        tpl_dst = session_dir / f"_template_{tpl_name}"
        with tpl_dst.open("wb") as out:
            out.write(await template_file.read())
        template = tpl_dst
    if not template.exists():
        raise HTTPException(500, f"默认模板不存在: {template}")

    async def gen():
        async for evt in _real_stream(saved, template, session_dir, business_line):
            yield evt
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


class RefineAnswer(BaseModel):
    id: str
    value: Any


class RefineRequest(BaseModel):
    session_id: str
    answers: list[RefineAnswer] = []


@app.post("/api/report/refine")
async def report_refine(req: RefineRequest):
    """基于 session_id 的外因续跑.

    当前版本为 stub:
      - 从 session_store 取回原 enterprise_profile
      - 推送 write/audit 两个阶段事件(只重跑 external_factor 相关 section)
      - done 事件回传相同 session_id 与(可能更新后的) enterprise_profile
    真正的 section 重跑由 V14-C Agent 负责接入 section_generator。
    """
    sess = store.get(req.session_id)
    if sess is None:
        raise HTTPException(404, f"session {req.session_id} 不存在或已过期")

    async def gen():
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

        report_url = None
        docx_path = sess.get("report_docx_path")
        if docx_path and os.path.exists(docx_path):
            report_url = f"/downloads/{os.path.basename(docx_path)}"

        yield _sse("done", {
            "session_id": req.session_id,
            "report_docx_url": report_url,
            "enterprise_profile": profile,
            "pending_questions": remaining,
            "downstream_handoff": mock_fixtures.downstream_handoff(
                (profile.get("profile_id") or "dingsheng_trade")),
        })

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/downloads/{fname}")
async def download_legacy(fname: str):
    """兼容老接口:直接从 outputs 根目录下载."""
    safe = os.path.basename(fname)
    target = DOWNLOAD_DIR / safe
    if not target.is_file():
        raise HTTPException(404, f"文件不存在: {safe}")
    return FileResponse(
        path=str(target),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe,
    )


@app.get("/api/report/downloads/legacy/{fname}")
async def download_mock_fallback(fname: str):
    """Mock 模式历史 docx 下载(从 outputs 根目录取)."""
    safe = os.path.basename(fname)
    target = DOWNLOAD_DIR / safe
    if not target.is_file():
        raise HTTPException(404, f"文件不存在: {safe}")
    return FileResponse(
        path=str(target),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe,
    )


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


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8002))
    uvicorn.run("agent_report.api:app", host="127.0.0.1", port=port, reload=False)
