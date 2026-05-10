# -*- coding: utf-8 -*-
"""agent_report.v16_runner — Stage C.1 SSE wrapper for v16_pipeline.

设计目的:
  把项目根的 ``v16_pipeline.run_pipeline`` (sync 函数 · 返聚合 dict) 包成
  generator yield SSE 事件的形态 · 让 ``/api/report/fill`` 可以流式推 stage 进度。

5 阶段映射(per agent-report-spec.md §5.3):
  1. ingest   — 读上传材料 + 校验 classifier 产物
  2. extract  — classifier 复用(已存在的 v16_llm_classified.json)
  3. infer    — generator 装载 KB / facts / templates
  4. write    — generator 真跑 element-level 改写(主耗时)
  5. audit    — quality_scorer 9 维 QC

Mock 路径:
  无 ``classified_json`` / 无 DEEPSEEK_API_KEY 时切 mock · 走假 stage 进度 + 加载
  ``mock_fixtures`` 数据 · 与现有 _mock_stream 保持兼容 · empty-state-design-protocol
  §5 显式 demo 标记 (mock_pipeline=True 落 done payload)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, AsyncIterator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ALL IN Phase B step 5 + 6 · per candidate-identity-contract v1.1 §4.2 + entity-resolution-contract v1.1 §5
from shared.entity_resolver import ensure_list_unique_ids, resolve_entity  # noqa: E402

logger = logging.getLogger(__name__)

# 5 阶段(同 api.py STAGE_*)
STAGE_INGEST = "ingest"
STAGE_EXTRACT = "extract"
STAGE_INFER = "infer"
STAGE_WRITE = "write"
STAGE_AUDIT = "audit"
STAGE_ORDER = [STAGE_INGEST, STAGE_EXTRACT, STAGE_INFER, STAGE_WRITE, STAGE_AUDIT]


def _sse(event: str, data: dict) -> str:
    body = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {body}\n\n"


def _stage(stage: str, progress: float, message: str) -> str:
    return _sse("stage", {
        "stage": stage,
        "progress": round(progress, 2),
        "message": message,
        "pipeline": "v16",
    })


# ---------------------------------------------------------------------------
# Section extraction · 从 v16 输出 docx 抽 4 章 sections (V2 fix issue 2 · codex DISAGREE)
# ---------------------------------------------------------------------------

# 4 章模板锚点 · 与 mock_fixtures 同形 · 前端 PreviewPanel TOC 消费
_CHAPTER_HEADINGS: tuple[tuple[str, str, str], ...] = (
    ("chapter_1_background", "一、企业背景", "一、"),
    ("chapter_2_operation", "二、经营情况", "二、"),
    ("chapter_3_finance", "三、财务分析", "三、"),
    ("chapter_4_conclusion", "四、审批意见", "四、"),
)


def _extract_sections_from_docx(docx_path: Path) -> list[dict]:
    """从 v16 输出 docx 抽 4 章 sections · 按 ``一、/二、/三、/四、`` 中文章节锚分段.

    V2 fix issue 2 (codex DISAGREE): real_v16 done 必须含 top-level sections · 不让前端
    fallback 静态 REPORT_SESSION mock · 否则 5 panel hydrate 与 v16 真产物脱节.

    Returns:
        [{id, title, content, status, word_count}, ...] · 同 mock_v16_stream done.sections shape
        失败返 [] (caller 按 mock fallback)
    """
    if not docx_path or not Path(docx_path).is_file():
        return []
    try:
        from docx import Document
        doc = Document(str(docx_path))
    except Exception:
        return []
    paragraphs: list[str] = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            paragraphs.append(t)
    if not paragraphs:
        return []

    # 按 4 章锚点切段 · 命中第一个 "一、" / "二、" 即开新 section
    sections: list[dict] = []
    cur_idx = -1
    cur_lines: list[str] = []
    for line in paragraphs:
        matched = -1
        for i, (_id, _title, prefix) in enumerate(_CHAPTER_HEADINGS):
            if line.startswith(prefix) or line.startswith(_title[:2]):
                matched = i
                break
        if matched >= 0:
            # 关闭上一段
            if cur_idx >= 0 and cur_lines:
                _id, _title, _ = _CHAPTER_HEADINGS[cur_idx]
                content = "\n".join(cur_lines).strip()
                sections.append({
                    "id": _id,
                    "title": _title,
                    "content": content,
                    "status": "done" if content else "pending",
                    "word_count": len(content),
                })
            cur_idx = matched
            cur_lines = []
        elif cur_idx >= 0:
            cur_lines.append(line)
    # tail
    if cur_idx >= 0 and cur_lines:
        _id, _title, _ = _CHAPTER_HEADINGS[cur_idx]
        content = "\n".join(cur_lines).strip()
        sections.append({
            "id": _id,
            "title": _title,
            "content": content,
            "status": "done" if content else "pending",
            "word_count": len(content),
        })
    return sections


def _load_profile_for_real(report_id: str) -> dict:
    """real path 装载 profile · 优先用 report_id 命中 mock_fixtures 预置 (脱敏样本) ·
    否则返空 dict (前端 sessionData fallback REPORT_SESSION mock 兜底).

    V2 fix issue 2 · 真路径 done 需 top-level profile · 与 demo/run + mock_v16 同形.
    """
    try:
        from agent_report import mock_fixtures
        return dict(mock_fixtures.load_preset_profile(report_id) or {})
    except Exception:
        return {}


# ============================================================================
# Mock 路径(测试 + demo · 默认走 mock 不需 API key)
# ============================================================================

async def mock_v16_stream(
    *,
    report_id: str,
    source_docx: str = "samples/经纬测绘_对公成稿A.docx",
    pretend_pass: bool = True,
) -> AsyncIterator[str]:
    """v16 mock SSE 流 · 用于测试 + empty-state demo.

    输出 5 阶段假进度 + 1 个假 done payload。**不**真跑 v16_pipeline。
    empty-state-design-protocol 要求 demo 显式标 · done event 含 mock_pipeline=true。
    """
    messages = {
        STAGE_INGEST: "材料解析(mock) · 0 / 0 真材料",
        STAGE_EXTRACT: "v16_classifier 路由复用(mock 跳过 LLM)",
        STAGE_INFER: "v16_generator 加载 facts / KB(mock fixture)",
        STAGE_WRITE: "v16 element-level 改写(mock)",
        STAGE_AUDIT: "quality_scorer 9 维 QC(mock pass)",
    }
    n = len(STAGE_ORDER)
    for i, st in enumerate(STAGE_ORDER):
        yield _stage(st, (i + 1) / n, messages[st])
        await asyncio.sleep(0.15)

    # ALL IN Phase B step 6 · per entity-resolution-contract v1.1 §5 (report 必接入点):
    # 报告对象企业归一 · 防同企业多次写报告 + 跨 agent handoff 主键稳定
    # mock 路径用固定企业名 + USCC · 真路径 v16_generator 内部从材料抽 USCC 后 resolve_entity
    _mock_company_name = "测试样本有限公司"
    _mock_uscc = "91440300708461136T"  # 腾讯科技深圳 USCC (NECIPS 公开 · 算法 valid · per contract §4.4)
    entity_key = resolve_entity(name=_mock_company_name, uscc=_mock_uscc)
    profile = {
        "company_name": _mock_company_name,
        "uscc": _mock_uscc,
        "entity_key": {
            "uscc": entity_key.uscc,
            "name_normalized": entity_key.name_normalized,
            "confidence": entity_key.confidence,
        },
    }
    # mock done payload
    done = {
        "event": "done",
        "report_id": report_id,
        "session_id": report_id,
        "pipeline": "v16",
        "mock_pipeline": True,
        "source_docx": source_docx,
        "report_docx_url": None,
        "profile": profile,  # ALL IN step 6 · 含 entity_key 跨 agent handoff 主键
        "qc": {
            "passed": pretend_pass,
            "score": 86.5 if pretend_pass else 64.2,
            "fatal_fail": False,
            "halluc_count": 0,
        },
        "stats": {
            "handler": {"preserve": 120, "fill": 86, "rewrite": 12},
            "apply": {"keep": 120, "fill": 86, "clear": 0},
            "pending_count": 4,
        },
        "pending_questions": [
            {"id": "ext_1", "label": "外因 · 行业景气度",
             "recommended": "请补充近 6 个月行业关键变化",
             "source_ref": "材料 · 行业研究.docx p3"},
            {"id": "ext_2", "label": "外因 · 上下游集中度",
             "recommended": "前五大客户占比 / 前五大供应商占比",
             "source_ref": "材料 · 销售明细.xlsx Sheet1"},
        ],
        "sections": [
            {
                "id": "chapter_1_background",
                "title": "一、企业背景",
                "content": "（mock）测试样本有限公司成立于 2015 年 · 注册资本 5000 万 ...",
                "status": "done",
                "word_count": 1200,
            },
            {
                "id": "chapter_2_operation",
                "title": "二、经营情况",
                "content": "（mock）主营精密零部件 · 近 3 年营收稳定增长 ...",
                "status": "done",
                "word_count": 1500,
            },
            {
                "id": "chapter_3_finance",
                "title": "三、财务分析",
                "content": "（mock）资产负债率 45%（行业 P50 38%）· 流动比率 1.6 ...",
                "status": "done",
                "word_count": 2200,
            },
            {
                "id": "chapter_4_conclusion",
                "title": "四、审批意见",
                "content": "（待 Agent3 决策回写）",
                "status": "pending",
                "word_count": 0,
            },
        ],
        # ALL IN Phase B step 4 · per AGENT_IDENTITY-report.md §6 + shared/evidence_drawer.Evidence schema:
        # 字段级 evidence · 每 section 关联 1-2 条 source · 前端 EvidenceDrawer 消费 (mock 路径示范 · 真路径 v16_generator 内挂)
        "evidences": [
            {
                "evidence_id": "ev_mock_001",
                "claim_id": "chapter_1_background",
                "source": "uploaded_material:营业执照.pdf",
                "anchor": "page=1",
                "snippet": "测试样本有限公司 · 统一社会信用代码 91440300708461136T · 注册日期 2015-03",
                "source_tier": 2,  # Tier 2 政府监管(工商)
                "source_url": None,  # 内部上传材料无外链
                "evidence_date": "2015-03-15",
                "retrieved_at": "2026-05-09",
                "claim_type": "registry",
                "version": "v1",
                "content_hash": "mock_hash_001",
                "confidence": 1.0,
            },
            {
                "evidence_id": "ev_mock_002",
                "claim_id": "chapter_2_operation",
                "source": "uploaded_material:行业研究.docx",
                "anchor": "page=3§2",
                "snippet": "精密零部件行业 2024 年市场规模同比增长 12.4%",
                "source_tier": 3,  # Tier 3 行业
                "source_url": None,
                "evidence_date": "2024-Q4",
                "retrieved_at": "2026-05-09",
                "claim_type": "industry",
                "version": "v1",
                "content_hash": "mock_hash_002",
                "confidence": 0.85,
            },
            {
                "evidence_id": "ev_mock_003",
                "claim_id": "chapter_3_finance",
                "source": "uploaded_material:财务报表_2024.xlsx",
                "anchor": "Sheet1!B7",
                "snippet": "资产负债率 45.2% · 流动比率 1.62 · 速动比率 0.98",
                "source_tier": 1,  # Tier 1 内部权威(客户提交底稿)
                "source_url": None,
                "evidence_date": "2024-12-31",
                "retrieved_at": "2026-05-09",
                "claim_type": "financial",
                "version": "v1",
                "content_hash": "mock_hash_003",
                "confidence": 1.0,
            },
        ],
    }
    # ALL IN Phase B step 5 · per candidate-identity-contract v1.1 §4.2 (硬规) ·
    # sections / pending_questions / evidences 全经 helper · 防 regression placeholder
    ensure_list_unique_ids(done["sections"], name_field="title", uscc_field="", id_field="id")
    ensure_list_unique_ids(done["pending_questions"], name_field="label", uscc_field="", id_field="id")
    ensure_list_unique_ids(done["evidences"], name_field="source", uscc_field="", id_field="evidence_id")

    # ALL IN Phase B.1 fix · handoff 真产物 · per entity-resolution-contract v1.1 §5
    # report → credit 跨 agent handoff 主键 · 决策回写写盘 · 静态 ledger evidence
    # handoff_id 派自 entity_key (uscc anchored 优先 · name_normalized 兜底 · report_id 终极 fallback)
    try:
        _ek = profile.get("entity_key", {}) if isinstance(profile, dict) else {}
        handoff_id = (
            _ek.get("uscc")
            or (_ek.get("name_normalized") or "")[:12]
            or report_id
        )
        if handoff_id:
            handoff_dir = PROJECT_ROOT / "data" / "handoff" / "report_to_credit"
            handoff_dir.mkdir(parents=True, exist_ok=True)
            # 防 path traversal · 仅允字母数字 + 下划线
            import re as _re
            safe_id = _re.sub(r"[^a-zA-Z0-9_-]", "_", str(handoff_id))[:64]
            handoff_path = handoff_dir / f"{safe_id}.json"
            handoff_payload = {
                **done,
                "handoff_id": safe_id,
                "wrote_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "agent_from": "report",
                "agent_to": "credit",
            }
            handoff_path.write_text(
                json.dumps(handoff_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            done["handoff_path"] = str(handoff_path.relative_to(PROJECT_ROOT))
    except Exception as exc:
        # silent-fail · 不破 SSE 流 (per BE7 ledger 模式 · handoff 是观察层不是阻塞层)
        logger.warning("handoff write failed (silent): %s", exc)

    yield _sse("done", done)


# ============================================================================
# 真路径(后台 thread 跑 v16_pipeline · 主协程 yield 事件)
# ============================================================================

def _run_v16_in_thread(
    *,
    source_docx: Path,
    material_dir: Path,
    classified_json: Path,
    output_dir: Path,
    emit: "queue.Queue[str]",
) -> None:
    """工作线程 · 真跑 v16_pipeline.run_pipeline · 把 stage/done/error push 队列.

    阶段映射:
      run_pipeline 内部:classifier 已经预跑 → 我们 stage 1 (ingest) +
      stage 2 (extract) 是元数据准备 · stage 3 (infer) 在 generator 内部 ·
      stage 4 (write) 是 generator 主体耗时 · stage 5 (audit) 是 QC
    """
    try:
        # Step 1: ingest — 校验输入
        emit.put(_stage(STAGE_INGEST, 0.05, f"读模板 {source_docx.name}"))
        if not source_docx.exists():
            emit.put(_sse("error", {
                "stage": STAGE_INGEST,
                "message": f"模板 docx 不存在: {source_docx}",
                "pipeline": "v16",
            }))
            emit.put("__END__")
            return
        if not material_dir.exists():
            emit.put(_sse("error", {
                "stage": STAGE_INGEST,
                "message": f"材料目录不存在: {material_dir}",
                "pipeline": "v16",
            }))
            emit.put("__END__")
            return

        # Step 2: extract — 校验 classifier 产物
        emit.put(_stage(STAGE_EXTRACT, 0.18, "校验 v16_classifier 路由表"))
        if not classified_json.exists():
            emit.put(_sse("error", {
                "stage": STAGE_EXTRACT,
                "message": (
                    f"classifier 产物缺失: {classified_json}\n"
                    "请先运行 `py v16_classifier.py` 或上传分类结果。"
                ),
                "pipeline": "v16",
            }))
            emit.put("__END__")
            return

        # Step 3: infer — 装载 generator 依赖
        emit.put(_stage(STAGE_INFER, 0.30, "v16_generator 装载 KB / facts / templates"))

        # Step 4: write — 真跑 generate(主耗时 · 内部含 LLM 调用)
        emit.put(_stage(STAGE_WRITE, 0.45, "v16 element-level 改写(generator 跑中)"))
        try:
            from v16_pipeline import run_pipeline
        except ImportError as e:
            emit.put(_sse("error", {
                "stage": STAGE_WRITE,
                "message": f"v16_pipeline import 失败: {e}",
                "pipeline": "v16",
            }))
            emit.put("__END__")
            return

        try:
            summary = run_pipeline(
                source_docx=source_docx,
                material_dir=material_dir,
                classified_json=classified_json,
                output_dir=output_dir,
            )
        except (RuntimeError, ValueError, TypeError, OSError, KeyError) as e:
            traceback.print_exc()
            emit.put(_sse("error", {
                "stage": STAGE_WRITE,
                "message": f"v16_pipeline 执行失败: {type(e).__name__}: {e}",
                "pipeline": "v16",
            }))
            emit.put("__END__")
            return

        emit.put(_stage(STAGE_WRITE, 0.85, "generator 完成 · 产物落盘"))

        # Step 5: audit — QC 已经在 run_pipeline 内跑过 · 这里 stage 透传结果
        qc = summary.get("qc") or {}
        passed = qc.get("passed")
        score = qc.get("score")
        emit.put(_stage(
            STAGE_AUDIT, 1.0,
            f"QC {('通过' if passed else '阻断')} · 分 {score}",
        ))

        # done 事件 · 聚合 summary
        output_docx = summary.get("output_docx")
        pending_path = summary.get("pending_json")
        pending_questions: list[dict] = []
        if pending_path and Path(pending_path).is_file():
            try:
                raw = json.loads(Path(pending_path).read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    pending_questions = raw[:30]
                elif isinstance(raw, dict):
                    pending_questions = list(raw.values())[:30]
            except (OSError, ValueError, TypeError):
                pass

        report_docx_url = None
        if output_docx and Path(output_docx).is_file():
            # 与 api.py downloads 端点契合: /api/report/downloads/v16/{filename}
            report_docx_url = f"/api/report/downloads/v16/{Path(output_docx).name}"

        # V2 fix issue 2 (codex DISAGREE) · real done 加 top-level sections + profile + UUID session_id
        # 让前端 PreviewPanel/MaterialPanel/TimelinePanel 从真产物 hydrate · 不再 fallback 静态 mock
        sections = _extract_sections_from_docx(Path(output_docx)) if output_docx else []
        profile = _load_profile_for_real(str(source_docx.stem))

        # 持久 done_payload 进 SessionStore · UUID = session_id 契约 (refine_section / export 都靠它)
        # SessionStore 内部 RLock 线程安全 · 工作线程调用合法
        try:
            from agent_report.session_store import store as _store
            qc_payload = {
                "passed": qc.get("passed"),
                "score": qc.get("score"),
                "fatal_fail": qc.get("fatal_fail", False),
                "halluc_count": qc.get("hallucinations", 0),
            }
            stats_payload = {
                "handler": summary.get("handler_stats"),
                "apply": summary.get("apply_stats"),
                "pending_count": summary.get("pending_count"),
            }
            session_id = _store.create({
                "mode": "real_v16",
                "source_docx": str(source_docx),
                "enterprise_profile": profile,
                "pending_questions": pending_questions,
            })
        except Exception:
            # store 不可用时 fallback 用 stem · 至少前端 hydrate 不崩
            session_id = str(source_docx.stem)
            qc_payload = {
                "passed": qc.get("passed"),
                "score": qc.get("score"),
                "fatal_fail": qc.get("fatal_fail", False),
                "halluc_count": qc.get("hallucinations", 0),
            }
            stats_payload = {
                "handler": summary.get("handler_stats"),
                "apply": summary.get("apply_stats"),
                "pending_count": summary.get("pending_count"),
            }

        done_payload = {
            "report_id": session_id,
            "session_id": session_id,
            "pipeline": "v16",
            "mock_pipeline": False,
            "data_source": "live",
            "source_docx": str(source_docx),
            "report_docx_url": report_docx_url,
            "output_docx_path": output_docx,
            "sections": sections,
            "profile": profile,
            "qc": qc_payload,
            "stats": stats_payload,
            "pending_questions": pending_questions,
        }

        # ---- Phase B Sprint 1 BE3 · 注 material_gap_graph 字段 ----
        # real path Sprint 1: v16_summary 无显式 material status · build_graph_from_v16_summary
        # 返 None · 不破 done_payload 既有形态 (前端 sibling 字段 · 缺时 hide panel)
        # Phase B-3 fix-forward 后接 material_kb scan output 推断 missing/partial
        try:
            from agent_report.material_gap import build_graph_from_v16_summary
            _gap_graph = build_graph_from_v16_summary(
                summary, material_gap_inputs=None, report_id=session_id,
            )
            if _gap_graph is not None:
                done_payload["material_gap_graph"] = _gap_graph
        except Exception:
            # 计算失败不阻断 v16 真路径 · sibling 字段缺时前端 hide panel
            pass

        # done_payload 持久 (refine_section / export_docx / export_pdf 共消费)
        try:
            from agent_report.session_store import store as _store2
            _store2.update(session_id, {"done_payload": done_payload})
        except Exception:
            pass

        emit.put(_sse("done", done_payload))
    except Exception as e:  # noqa: BLE001 — last-resort crash guard
        traceback.print_exc()
        emit.put(_sse("error", {
            "stage": STAGE_WRITE,
            "message": f"v16_runner 内部错误: {type(e).__name__}: {e}",
            "pipeline": "v16",
        }))
    finally:
        emit.put("__END__")


async def real_v16_stream(
    *,
    source_docx: Path,
    material_dir: Path,
    classified_json: Path,
    output_dir: Path,
) -> AsyncIterator[str]:
    """真路径 SSE 流 · 启动后台线程 · 主协程从队列消费."""
    emit: "queue.Queue[str]" = queue.Queue()
    worker = threading.Thread(
        target=_run_v16_in_thread,
        kwargs=dict(
            source_docx=source_docx,
            material_dir=material_dir,
            classified_json=classified_json,
            output_dir=output_dir,
            emit=emit,
        ),
        daemon=True,
    )
    worker.start()

    while True:
        try:
            item = await asyncio.get_event_loop().run_in_executor(
                None, emit.get, True, 0.5,
            )
        except queue.Empty:
            if not worker.is_alive():
                break
            continue
        if item == "__END__":
            break
        yield item


# ============================================================================
# Decision: real or mock based on env + inputs
# ============================================================================

def should_use_mock_v16(
    *,
    classified_json: Path | None,
    has_dee_pseek_key: bool,
    explicit_mock: bool,
) -> tuple[bool, str]:
    """判断 v16 fill 应走 mock 还是 real · 返 (should_mock, reason).

    PM 2026-05-09 ALL IN 真产品 (per AGENT_IDENTITY-report.md §6 step 3 + 红线 1 假 live):
    silent mock fallback 全删 · 仅 explicit_mock=True 走 mock · 其他全 raise · 不假装真路径.
    """
    if explicit_mock:
        return True, "explicit_mock=true"
    if not has_dee_pseek_key:
        # 此处通常不到 (api.py /v16/fill 在 fill_stream 前已 fail-fast 503 拒 silent fallback) · 防御性 raise
        raise RuntimeError(
            "DEEPSEEK_API_KEY 未配置 · 真模式不可用 · 拒 silent mock fallback (红线 1)"
        )
    if classified_json is None or not classified_json.exists():
        raise RuntimeError(
            f"v16_llm_classified.json 不存在 ({classified_json}) · 请先跑 v16_classifier · 拒 silent mock fallback (红线 1)"
        )
    return False, "real_v16"


async def fill_stream(
    *,
    report_id: str,
    source_docx: Path,
    material_dir: Path,
    classified_json: Path,
    output_dir: Path,
    explicit_mock: bool = False,
) -> AsyncIterator[str]:
    """v16 fill 主入口 · 自动选 mock / real."""
    has_key = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
    use_mock, reason = should_use_mock_v16(
        classified_json=classified_json,
        has_dee_pseek_key=has_key,
        explicit_mock=explicit_mock,
    )
    if use_mock:
        logger.warning("[v16_runner] mock path: %s", reason)
        async for evt in mock_v16_stream(
            report_id=report_id,
            source_docx=str(source_docx),
        ):
            yield evt
    else:
        logger.warning("[v16_runner] real path · classified=%s", classified_json)
        async for evt in real_v16_stream(
            source_docx=source_docx,
            material_dir=material_dir,
            classified_json=classified_json,
            output_dir=output_dir,
        ):
            yield evt


__all__ = [
    "STAGE_AUDIT",
    "STAGE_EXTRACT",
    "STAGE_INFER",
    "STAGE_INGEST",
    "STAGE_ORDER",
    "STAGE_WRITE",
    "fill_stream",
    "mock_v16_stream",
    "real_v16_stream",
    "should_use_mock_v16",
]
