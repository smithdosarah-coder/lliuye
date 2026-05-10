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
    # BE1 Sprint 3 · RM 辖区 (e.g. "华东" / "上海") · 给候选证据评分 region 维度用
    # 空则 region 维度走 default low · 不破 candidate metadata 4 字段
    rm_region: str = ""


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
                    rm_region=req.rm_region,
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
# POST /api/channel/demo/run · Phase B.2 真意 reframe (PM 2026-05-10)
#
# PM 真意 (verbatim 02:00 AM):
#   "我要的演示不是一键切换 · 而是把本地的 mock 数据真实上传 · 通过真实后端代码
#   跑一遍 · 最后给出结果"
#
# 演示 = 上传 sample (channel-kb 营销倾向 docx) → 真后端 pipeline → 真返结果
# 内部 mock = data/mock/channel-kb/marketing-preferences/*.docx (= "上传的 sample")
# 外部源    = 真 Tavily + 真 LLM + 8 源 (force_mock=False · 不再 yield fixture event)
# 旧版废:   data/mock/workspace/channel/scenarios/<id>.json (反 §3.5 5 原则 · 答案给嘴边)
#
# scenario_id 现在只决定从 marketing-preferences seed query list 里取第几条 ·
# 不再决定结果 · 结果由 Tavily/LLM 真跑产生
# ============================================================================


class ChannelDemoRunRequest(BaseModel):
    scenario_id: str = "medium"  # "easy" | "medium" | "hard" — 选 seed query idx
    rm_region: str = "华东"      # 给 evidence_scorer region 维度评分用


@app.post("/api/channel/demo/run")
async def channel_demo_run(
    req: ChannelDemoRunRequest,
    _user: dict = Depends(require_action("channel", "invoke")),
):
    """Phase B.2 真后端演示流 · 走 channel-kb marketing-preferences docx 派生 seed query
    → run_channel_search_stream (real Tavily + real LLM + 8 源 + evidence scorer) → 真返结果.

    与 /api/channel/run 的区别:
      - /api/channel/run        前端 query 框输入文本 · 用户驱动
      - /api/channel/demo/run   后端从 channel-kb 派生 seed query · 一键示例

    硬线 (per dispatch §不可 GO):
      - 不 yield fixture event · 不读 data/mock/workspace/channel/scenarios/*.json
      - 不 silent fallback fake · TAVILY_API_KEY 缺时 typed banner (live-fallback-banner-spec §1.5)
      - mock 只 mock 输入 (channel-kb docx) · 不 mock 结果 (候选/评分/匹配理由)
    """
    from shared.sse_envelope import encode_event, make_error
    from agent_channel.realtime_stream import run_channel_search_stream
    from agent_channel.seed_query_builder import (
        build_queries,
        parse_marketing_preferences,
    )

    _KB_PATH = PROJECT_ROOT / "data" / "mock" / "channel-kb" / "marketing-preferences"

    def gen():
        scenario_id = (req.scenario_id or "medium").strip()
        if scenario_id not in {"easy", "medium", "hard"}:
            yield encode_event(make_error(
                f"unknown scenario_id: {scenario_id} (allowed: easy/medium/hard)",
                code="DEMO_SCENARIO_INVALID",
            ))
            return

        # 1) Sample input · 从 channel-kb 真读 marketing-preferences (= "上传的 sample")
        if not _KB_PATH.is_dir():
            yield encode_event(make_error(
                f"channel-kb marketing-preferences 目录不存在 · path={_KB_PATH}",
                code="DEMO_KB_MISSING",
            ))
            return

        bundles = parse_marketing_preferences(str(_KB_PATH))
        queries = build_queries(bundles, max_total=6) if bundles else []
        if not queries:
            yield encode_event(make_error(
                "channel-kb marketing-preferences 解析失败 · 无可用 seed query",
                code="DEMO_KB_EMPTY",
            ))
            return

        # 2) 按 scenario_id 选 seed query
        idx_map = {
            "easy":   0,
            "medium": min(2, len(queries) - 1),
            "hard":   min(4, len(queries) - 1),
        }
        seed_query = queries[idx_map[scenario_id]]

        # 3) 透出 demo 上下文 (前端 banner 显 sample 来源 · 演示透明)
        sample_files = [Path(b.source_doc).name for b in bundles[:5]]
        tavily_ok = bool(os.environ.get("TAVILY_API_KEY"))
        yield sse_encode({
            "event": "demo_context",
            "scenario_id": scenario_id,
            "sample_source": "data/mock/channel-kb/marketing-preferences",
            "sample_files": sample_files,
            "derived_seed_query": seed_query,
            "tavily_configured": tavily_ok,
            "pipeline": "run_channel_search_stream (real)",
        })

        # 4) 不 silent fallback · TAVILY 缺立即 typed banner · 用户感知
        if not tavily_ok:
            yield sse_encode({
                "event": "error",
                "stage": "search",
                "code": "TAVILY_KEY_MISSING_FOR_DEMO",
                "message": (
                    "TAVILY_API_KEY 未配置 · 真后端演示需 Tavily 实搜 · "
                    "请联系运维配置 · 或切到 /api/channel/run 走 mock 池 (force_mock=true)"
                ),
            })
            return

        # 5) 真跑 backend pipeline (Tavily + LLM + 8 源 + 评分 + 证据)
        # 错误降级 (per dispatch §5): NotImplementedError / API key missing / Tavily down
        # 走 typed banner · 不 silent fallback fake · run_channel_search_stream 内部已 catch
        # (RuntimeError/ValueError/TypeError/OSError/AttributeError/KeyError) · 这里额外 catch
        # NotImplementedError (build_search_provider demo_mode=False · 缺 Tavily key 时 raise)
        try:
            for evt in run_channel_search_stream(
                query=seed_query,
                provider="deepseek",
                api_key="",  # 走 env DEEPSEEK_API_KEY
                top_n=8,
                force_mock=False,
                rm_region=req.rm_region or "华东",
            ):
                yield sse_encode(_qc_clean_event(
                    {k: to_jsonable(v) for k, v in evt.items()}
                ))
        except NotImplementedError as e:
            # 触发源: agent_channel.agent.build_search_provider(demo_mode=False) 无 Tavily 时
            # 上抛 NotImplementedError · 走 typed banner · 不 silent
            yield sse_encode({
                "event": "error",
                "stage": "pipeline",
                "code": "BACKEND_NOT_IMPLEMENTED",
                "message": (
                    f"后端搜索器未配置可用 provider · {type(e).__name__}: {e} · "
                    "请联系运维补全 Tavily/akshare 配置"
                ),
            })

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


# ============================================================================
# GET /api/channel/personal_insight/{candidate_id} — Phase B Sprint 3 BE12 (2026-05-05)
# 候选客户/候选企业个人画像 · 后端 only · 不改 frontend layout (B5 owns layout)
# 实施 status: 真业务实装 (V2-FIX 2026-05-05) · 走 shared/personal_profile.redact
#   (PII hash) + shared/sources Router (pbc_gov 政策扫) + 本地 PEP/sanction stub
#   (OFAC 真集成留 Phase C) + shared/llm_caller.LLMCaller (LLM grounded talking_points
#   · 8 段 system prompt · A1 spec landed 自动 pickup) + 端到端 latency_ms.
#   stub=true query param 保留作 schema 验证路径.
# 消费者: B7 BE13 4 维度评价 (个人画像 35% / 产品适配 25% / 合规+话术 20% / PII+latency 20%)
# ============================================================================


@app.get("/api/channel/personal_insight/{candidate_id}")
async def channel_personal_insight(
    candidate_id: str,
    industry: str = "",
    role: str = "",
    risk_appetite: str = "",
    decision_path: str = "",
    age: int = 0,
    education: str = "",
    industry_yr: int = 0,
    name: str = "",
    stub: bool = False,
):
    """GET /api/channel/personal_insight/{candidate_id} — BE12 真业务实装.

    走 shared/personal_profile.redact (PII hash) + shared/sources Router (pbc_gov 政策扫
    + 本地 PEP/sanction 关键词 stub · 真 OFAC 集成留 Phase C) + shared/llm_caller
    (LLM grounded talking_points · 8 段 system prompt · A1 spec landed 自动 pickup)
    + 端到端 latency_ms 测量.

    Response payload schema (per BACKEND-DEEP-WORK-V2-1-FINAL.md:54-59):
    {
        candidate_id, person_features, product_fit, compliance_check,
        talking_points, pii_redacted, latency_ms
    }

    Query params (可选 · 用于派生 person_features 与合规扫):
        industry         · 候选企业行业 · 给 pbc_gov policy keyword
        role             · 决策角色
        risk_appetite    · "保守" / "稳健" / "激进"
        decision_path    · "单点决策" / "委员会"
        age / education / industry_yr / name · PII (将 hash · 不存原文)
        stub=true        · 测试模式 · 不调 LLM/源 · 返 stub payload
    """
    cid = (candidate_id or "").strip()
    if not cid:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": "candidate_id 不能为空",
                              "details": {"field": "candidate_id"}}},
        )

    try:
        from agent_channel.personal_insight import (
            build_personal_insight,
            build_personal_insight_stub,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"personal_insight module unavailable: {e}"}},
        ) from e

    if stub:
        return build_personal_insight_stub(cid)

    person_features: dict = {}
    for k, v in (
        ("role", role),
        ("risk_appetite", risk_appetite),
        ("decision_path", decision_path),
        ("education", education),
        ("name", name),
    ):
        if v:
            person_features[k] = v
    if age:
        person_features["age"] = int(age)
    if industry_yr:
        person_features["industry_yr"] = int(industry_yr)

    return build_personal_insight(
        cid,
        person_features=person_features or None,
        candidate_industry=industry,
    )


# ============================================================================
# GET /api/channel/sources_health — Phase B Sprint 3 BE1 (2026-05-05)
# SearchProvider 健康检查 + UI banner payload (Tavily / akshare / QCC)
# 用途: 前端 banner 显示数据源 health · live-fallback-banner-spec §1.5
# ============================================================================


@app.get("/api/channel/sources_health")
async def channel_sources_health():
    """SearchProvider 健康检查 · 返各 provider 状态供前端 banner 显示.

    返 payload schema:
    {
        "providers": [
            {"name": "tavily", "configured": bool, "status": "ok"|"degraded"|"down", "reason": str},
            {"name": "akshare", ...},
            {"name": "qcc", ...}
        ],
        "live_search_available": bool,
        "fallback_chain_active": bool,
        "checked_at": ISO timestamp
    }
    """
    import datetime
    providers = []

    tavily_configured = bool(os.environ.get("TAVILY_API_KEY"))
    providers.append({
        "name": "tavily",
        "configured": tavily_configured,
        "status": "ok" if tavily_configured else "down",
        "reason": "" if tavily_configured else "TAVILY_API_KEY 未配置",
    })

    try:
        import akshare as _ak  # noqa: F401
        akshare_ok = True
    except ImportError:
        akshare_ok = False
    providers.append({
        "name": "akshare",
        "configured": akshare_ok,
        "status": "ok" if akshare_ok else "down",
        "reason": "" if akshare_ok else "akshare 未安装",
    })

    qcc_configured = bool(os.environ.get("QCC_API_KEY"))
    providers.append({
        "name": "qcc",
        "configured": qcc_configured,
        "status": "ok" if qcc_configured else "down",
        "reason": "" if qcc_configured else "QCC_API_KEY 未配置 (sub-PR 2 wire)",
    })

    live_available = any(p["status"] == "ok" for p in providers)

    return {
        "providers": providers,
        "live_search_available": live_available,
        "fallback_chain_active": not live_available,
        "checked_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


# ============================================================================
# POST /api/channel/conversion — Phase B Sprint 3 BE1 Step 4 (2026-05-05)
# RM 决策候选后追踪是否真成单 · 落 data/feedback/<rm_id>/<candidate_id>.jsonl
# 与 /api/feedback (Agent6 audit modify · worker-B1 BE10) 业务隔离
# 只追踪 Agent1 候选 → 实际成单 conversion 链路
# ============================================================================


class ChannelConversionRequest(BaseModel):
    candidate_id: str
    rm_id:        str
    stage:        str  # "contacted" | "quoted" | "approved" | "won" | "lost" | "on_hold"
    notes:        str = ""
    amount_yuan:  int = 0
    next_action:  str = ""
    metadata:     dict | None = None


@app.post("/api/channel/conversion")
async def channel_conversion(req: ChannelConversionRequest):
    """记录候选 → 成单 conversion 链 · 1 条 jsonl 行 append 到 candidate 文件.

    Returns:
        {path, rm_id, candidate_id, stage, timestamp}

    Errors:
        400 · candidate_id / rm_id / stage 校验失败 (含 path traversal 防护)
        500 · 文件 IO 失败
    """
    try:
        from agent_channel.conversion_tracker import (
            ConversionValidationError,
            record_conversion,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"conversion_tracker unavailable: {e}"}},
        ) from e

    payload = req.model_dump(exclude_none=True)
    try:
        result = record_conversion(payload)
    except ConversionValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALIDATION_FAILED",
                              "message": str(e)}},
        ) from e
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"conversion write failed: {e}"}},
        ) from e
    return result


@app.get("/api/channel/conversion/{rm_id}/{candidate_id}")
async def channel_conversion_list(rm_id: str, candidate_id: str):
    """读单候选的 conversion 链 · jsonl 行序 (插入序)."""
    try:
        from agent_channel.conversion_tracker import list_conversions
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR",
                              "message": f"conversion_tracker unavailable: {e}"}},
        ) from e
    events = list_conversions(rm_id, candidate_id)
    return {"rm_id": rm_id, "candidate_id": candidate_id, "events": events, "count": len(events)}
