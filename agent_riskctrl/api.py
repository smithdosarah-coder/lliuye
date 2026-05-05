# -*- coding: utf-8 -*-
"""agent_riskctrl.api — Agent2 风控策略运营 FastAPI 路由模块。

端点 (Phase A worker-A4 · 2026-04-29 · sse-envelope.md §1.5 + workspace-state-protocol §4):
  POST /api/riskctrl/dsl_gen          — SSE · 自然语言 → RuleSet JSON (LLM 真接 · stream)
  POST /api/riskctrl/backtest         — SSE · RuleSet + CSV → metrics JSON (KS / 通过率 / 坏账率)

设计:
- 独立 FastAPI app · api_server.py routes 合并装载
- 6 Agent SSE done envelope 共形 · 走 shared.sse_envelope.make_done · panel keys
  riskctrl 域投影 = (ruleset, ks, samples, rule_stats) · metrics 顶层 KPI
- mock=true 切预设 RuleSet · 不调 LLM · curl / 无 key 环境可演示
- 输出过 shared.qc.placeholder_guard (V2 后续接入 · 当前不阻塞)

字段契约: docs/contracts/field-naming.md + docs/contracts/sse-envelope.md
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Stage E.1 · audit log decorator (silent fail if audit_service unavailable)
try:
    from audit_service.decorators import audit_llm_call  # noqa: E402
except ImportError:
    def audit_llm_call(**_kwargs):  # type: ignore[no-redef]
        def _passthrough(fn):
            return fn
        return _passthrough

app = FastAPI(title="Agent2 Risk Control API", version="4.1")


@app.get("/api/riskctrl/health")
async def riskctrl_health():
    """Agent2 sub-app 健康探针 (与 portal /health 平级, 用于精细化故障定位)。"""
    return {"status": "ok", "agent": "agent_riskctrl"}


# ============================================================================
# Phase A worker-A4 · 2026-04-29 · SSE 化 + done envelope 共形
# 两端点 (dsl_gen / backtest) 走 StreamingResponse + shared.sse_envelope helper
# ============================================================================


# Mock RuleSet fixture (mock=true 路径 / 无 LLM key 环境)
_MOCK_DSL_RESPONSE: dict[str, Any] = {
    "rules": [
        {
            "rule_id": "R001",
            "name": "高负债率拒绝",
            "description": "负债率 > 80% 直接拒绝授信",
            "conditions": [
                {"field": "debt_ratio", "operator": ">", "value": 0.8}
            ],
            "action": "reject",
            "priority": 1,
        },
        {
            "rule_id": "R002",
            "name": "新成立企业人工审",
            "description": "成立年限 < 1 年转人工",
            "conditions": [
                {"field": "company_age_years", "operator": "<", "value": 1}
            ],
            "action": "manual_review",
            "priority": 5,
        },
    ],
    "description": "[mock] demo 默认策略 · 高负债拒 + 新企业转人工",
}


class DslGenRequest(BaseModel):
    """SSE dsl_gen body. Pydantic alias 同时接受前端旧名 rule_text + 后端规范名 strategy_intent."""

    # ConfigDict 允许 alias + field name 双向接受 (前端 v3.x 用 rule_text · A4 V2 后统一)
    model_config = ConfigDict(populate_by_name=True)

    strategy_intent: str = Field(
        ...,
        alias="rule_text",
        description="自然语言策略意图描述 (前端可传 rule_text · 后端统一为 strategy_intent)",
    )
    sample_csv_path: str | None = Field(
        default=None, description="(可选) 历史样本 CSV 路径 · 用于 LLM 对照字段"
    )
    mock: bool = Field(
        default=False,
        description="true → 返预设 RuleSet · 不调 LLM (无 key 环境可 demo)",
    )


def _sse_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }


@app.post("/api/riskctrl/dsl_gen")
@audit_llm_call(agent_id="riskctrl", endpoint="/api/riskctrl/dsl_gen", model="deepseek-chat")
async def riskctrl_dsl_gen(req: DslGenRequest):
    """自然语言 → RuleSet JSON · SSE stream · stage 流 + done envelope.

    Body:    { strategy_intent | rule_text, sample_csv_path?, mock? }
    LLM provider/api_key 不通过 body 传 · 一律走 env (PIPL fallback chain · CLAUDE.md §3.6).
    Stream:
        event: stage   {stage: parse_intent | build_prompt | validate_dsl, status}
        event: done    {ruleset, ruleset_id, source: llm|mock, csv_columns?, data_source}
        event: error   {message, code}
    """
    from shared.sse_envelope import (
        DATA_SOURCE_LIVE,
        DATA_SOURCE_MOCK_FORCED,
        encode_event,
        make_done,
        make_error,
        make_error_from_exception,
        make_stage,
    )

    def gen():
        # Imports moved inside generator to keep error path SSE-friendly
        try:
            from agent_riskctrl.prompts import SYSTEM_RULE_PARSER
            from agent_riskctrl.rule_engine import parse_natural_language_rules
        except (ImportError, ModuleNotFoundError) as e:
            yield encode_event(make_error_from_exception(e, code="IMPORT_FAILED"))
            return

        yield encode_event(make_stage("parse_intent", "running", message="解析策略意图..."))

        # 可选: 读 sample csv 抓字段 · 注入 LLM prompt 让规则字段名对齐
        csv_columns: list[str] | None = None
        data_context = ""
        if req.sample_csv_path:
            csv_path = Path(req.sample_csv_path)
            if not csv_path.is_absolute():
                csv_path = PROJECT_ROOT / req.sample_csv_path
            if csv_path.exists():
                try:
                    from agent_riskctrl.backtesting import load_csv_data
                    df = load_csv_data(str(csv_path))
                    csv_columns = [str(c) for c in df.columns]
                    data_context = (
                        f"\n\n参考数据字段:\n{', '.join(csv_columns)}\n"
                        f"前 3 行示例:\n{df.head(3).to_string(index=False)}"
                    )
                except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
                    data_context = f"\n\n[csv 加载失败: {type(e).__name__}: {e}]"

        yield encode_event(make_stage("parse_intent", "done"))

        user_prompt = f"请将以下策略意图转换为结构化规则:\n\n{req.strategy_intent}{data_context}"

        # mock 模式 (curl demo / 无 key) → 预设 RuleSet 不调 LLM
        if req.mock:
            yield encode_event(make_stage("build_prompt", "skipped", message="mock 模式 · 跳 LLM"))
            ruleset = parse_natural_language_rules(_MOCK_DSL_RESPONSE)
            ruleset_id = f"rs_mock_{abs(hash(req.strategy_intent)) % 10_000_000:07d}"
            yield encode_event(make_done(
                panels={
                    "ruleset": ruleset.model_dump(),
                    "ruleset_id": ruleset_id,
                    "csv_columns": csv_columns or [],
                },
                metrics={},
                data_source=DATA_SOURCE_MOCK_FORCED,
                session_id=ruleset_id,
                source="mock",
            ))
            return

        yield encode_event(make_stage("build_prompt", "running", message="组装 LLM prompt..."))

        # LLM 真接 · A4 caller 5 迁 shared.llm_caller (CLAUDE.md §3.6 PIPL fallback chain)
        # provider/api_key 不从 body 传 · 一律 env (DEFAULT_FALLBACK_CHAIN deepseek+dashscope)
        try:
            from shared.llm_caller import make_json_caller
            caller = make_json_caller(
                agent_id="riskctrl",
                endpoint="/api/riskctrl/dsl_gen",
                temperature=0.3,
            )
            yield encode_event(make_stage("build_prompt", "done"))
            yield encode_event(make_stage("call_llm", "running", message="调 LLM 生成 DSL..."))
            llm_json = caller(SYSTEM_RULE_PARSER, user_prompt)
        except (RuntimeError, ValueError, TypeError, OSError, KeyError, ImportError) as e:
            yield encode_event(make_error_from_exception(e, code="LLM_CALL_FAILED"))
            return

        if llm_json is None:
            yield encode_event(make_error(
                "LLM 调用失败 · fallback chain 全部不可用 · 请重试或检查 env LLM key",
                code="LLM_FALLBACK_EXHAUSTED",
            ))
            return

        yield encode_event(make_stage("call_llm", "done"))
        yield encode_event(make_stage("validate_dsl", "running", message="校验 DSL 结构..."))

        if not isinstance(llm_json, dict):
            llm_json = {"rules": llm_json} if isinstance(llm_json, list) else {}

        try:
            ruleset = parse_natural_language_rules(llm_json)
        except (ValueError, TypeError, KeyError) as e:
            yield encode_event(make_error_from_exception(e, code="DSL_PARSE_FAILED"))
            return

        if not ruleset.rules:
            yield encode_event(make_error(
                "LLM 返回未能解析出有效规则 · 请尝试更具体的策略意图描述",
                code="DSL_EMPTY_RULES",
            ))
            return

        yield encode_event(make_stage("validate_dsl", "done"))

        ruleset_id = f"rs_llm_{abs(hash(req.strategy_intent)) % 10_000_000:07d}"
        yield encode_event(make_done(
            panels={
                "ruleset": ruleset.model_dump(),
                "ruleset_id": ruleset_id,
                "csv_columns": csv_columns or [],
            },
            metrics={},
            data_source=DATA_SOURCE_LIVE,
            session_id=ruleset_id,
            source="llm",
        ))

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_sse_headers())


class BacktestRequest(BaseModel):
    """SSE backtest body."""

    ruleset: dict = Field(..., description="RuleSet model_dump 结构")
    csv_path: str = Field(..., description="历史样本 CSV 路径 (相对 PROJECT_ROOT or 绝对)")
    label_column: str | None = Field(
        default=None,
        description="坏账标签列名 · 默认自动探测 days_past_due / label_default / label",
    )
    bad_threshold: int = Field(
        default=30,
        description="days_past_due > 该值视作坏账 (默认 30)",
    )


def _ks_curve_points(y_true: list[int], y_pred: list[int], bins: int = 10) -> list[dict[str, Any]]:
    """11-point KS curve (bin 0..10) · TPR / FPR / KS @ 各分位 · 供前端 LineChart 消费.

    确定性计算 (per CLAUDE.md §3.1) · 不让 LLM 现场算.
    """
    import numpy as np  # local import to avoid module load cost on path miss
    if not y_true or len(y_true) != len(y_pred):
        return []
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    n_pos = float(yt.sum())
    n_neg = float(len(yt) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return []
    order = np.argsort(-yp)
    yt_sorted = yt[order]
    n = len(yt_sorted)
    points: list[dict[str, Any]] = []
    for i in range(bins + 1):
        cut = int(round(i * n / bins))
        if cut == 0:
            tpr = 0.0
            fpr = 0.0
        else:
            tpr = float(yt_sorted[:cut].sum() / n_pos)
            fpr = float((1 - yt_sorted[:cut]).sum() / n_neg)
        ks = round(abs(tpr - fpr), 3)
        points.append({"bin": i, "tpr": round(tpr, 3), "fpr": round(fpr, 3), "ks": ks})
    return points


@app.post("/api/riskctrl/backtest")
@audit_llm_call(agent_id="riskctrl", endpoint="/api/riskctrl/backtest", model="deterministic")
async def riskctrl_backtest(req: BacktestRequest):
    """RuleSet + CSV 历史数据 → metrics + KS curve + samples + rule_stats · SSE stream.

    Body: { ruleset, csv_path, label_column?, bad_threshold? }
    Stream:
        event: stage  {stage: load_csv | hit_rules | calc_ks, status}
        event: done   panels={ruleset, ks: {ksPeak, auc, passRate, badRate, points},
                               samples, rule_stats},
                       metrics={total_records, approved, rejected, manual_review,
                                approval_rate, bad_rate, ks_peak, label_column_used}
        event: error  {message, code}
    """
    from shared.sse_envelope import (
        DATA_SOURCE_LIVE,
        encode_event,
        make_done,
        make_error,
        make_error_from_exception,
        make_stage,
    )

    def gen():
        try:
            from agent_riskctrl.backtesting import load_csv_data, run_backtest
            from agent_riskctrl.metrics import calculate_auc, calculate_ks
            from agent_riskctrl.rule_engine import RuleSet
        except (ImportError, ModuleNotFoundError) as e:
            yield encode_event(make_error_from_exception(e, code="IMPORT_FAILED"))
            return

        # csv 路径解析
        csv_path = Path(req.csv_path)
        if not csv_path.is_absolute():
            csv_path = PROJECT_ROOT / req.csv_path
        if not csv_path.exists():
            yield encode_event(make_error(
                f"csv_path 不存在: {csv_path}",
                code="CSV_NOT_FOUND",
            ))
            return

        # ruleset 反序列化
        try:
            ruleset = RuleSet.model_validate(req.ruleset)
        except (ValueError, TypeError, KeyError) as e:
            yield encode_event(make_error_from_exception(e, code="RULESET_INVALID"))
            return
        if not ruleset.rules:
            yield encode_event(make_error("ruleset.rules 不能为空", code="RULESET_EMPTY"))
            return

        yield encode_event(make_stage("load_csv", "running", message="读 CSV 数据..."))
        try:
            df = load_csv_data(str(csv_path))
        except (OSError, ValueError) as e:
            yield encode_event(make_error_from_exception(e, code="CSV_LOAD_FAILED"))
            return
        yield encode_event(make_stage("load_csv", "done", count=int(len(df))))

        # label 列自动探测
        label_col = req.label_column
        if label_col is None:
            for cand in ("days_past_due", "label_default", "label"):
                if cand in df.columns:
                    label_col = cand
                    break

        yield encode_event(make_stage("hit_rules", "running", message="规则命中扫描..."))
        try:
            result = run_backtest(df, ruleset, label_column=label_col)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            yield encode_event(make_error_from_exception(e, code="BACKTEST_FAILED"))
            return
        yield encode_event(make_stage("hit_rules", "done"))

        # KS / AUC / bad_rate / curve (V2 fix · BE6.4 · AUC 实装 deterministic)
        bad_rate: float | None = None
        ks_peak: float | None = None
        auc_value: float | None = None
        ks_points: list[dict[str, Any]] = []

        yield encode_event(make_stage("calc_ks", "running", message="计算 KS / AUC / 通过率..."))
        if label_col and label_col in df.columns:
            try:
                if label_col == "days_past_due":
                    bad_mask = df[label_col].fillna(0).astype(float) > req.bad_threshold
                else:
                    bad_mask = df[label_col].fillna(0).astype(float) > 0.5
                bad_rate = round(float(bad_mask.mean()), 4)

                hit_results = result.metrics.get("hit_results", []) if result.metrics else []
                y_true = bad_mask.astype(int).tolist()
                y_pred = [
                    1 if r.get("action") in ("reject", "manual_review") else 0
                    for r in hit_results
                ]
                if len(y_true) == len(y_pred) and y_pred:
                    ks_peak = calculate_ks(y_true, y_pred)
                    auc_value = calculate_auc(y_true, y_pred)
                    ks_points = _ks_curve_points(y_true, y_pred, bins=10)
            except (TypeError, ValueError, KeyError):
                pass

        rule_stats_raw = (result.metrics or {}).get("rule_stats", [])
        # snake_case 透传 · 前端 normalize() 转 camelCase (sse-envelope §3 共形规则)
        rule_stats = [
            {
                "rule_id": r.get("rule_id") or r.get("ruleId"),
                "hit": r.get("hit", 0),
                "fp": r.get("fp", 0),
                "tn": r.get("tn", 0),
            }
            for r in rule_stats_raw
        ]

        # samples 三档 (pass / review / block) · 由 backtest 结果派生
        approved = int(result.approved)
        rejected = int(result.rejected)
        manual_review = int(result.manual_review)
        total = int(result.total_records) or (approved + rejected + manual_review) or 1
        samples = [
            {
                "key": "pass",
                "label": "通过",
                "count": approved,
                "pct": round(approved * 100.0 / total, 1),
                "bad_rate": round(((bad_rate or 0.0) * 100.0), 1),
            },
            {
                "key": "review",
                "label": "复核",
                "count": manual_review,
                "pct": round(manual_review * 100.0 / total, 1),
                "bad_rate": 0.0,  # 细分坏账率需 hit_results 三档区分 · V2 计算
            },
            {
                "key": "block",
                "label": "拒绝",
                "count": rejected,
                "pct": round(rejected * 100.0 / total, 1),
                "bad_rate": 0.0,
            },
        ]

        # KS 顶层 panel object · 前端直 setLiveData.ks
        # V2 fix (codex review critical 1): AUC 用 deterministic rank-based 实装
        # 替代 v1 hardcoded 0.0 · 见 metrics.calculate_auc (numpy · 不引 sklearn)
        ks_panel = {
            "ksPeak": ks_peak or 0.0,
            "auc": auc_value or 0.0,
            "passRate": round(approved * 100.0 / total, 1),
            "badRate": round((bad_rate or 0.0) * 100.0, 1),
            "points": ks_points,
        }

        yield encode_event(make_stage("calc_ks", "done"))

        # BE6.4 业务指标双轨 (业务方 demo 必备 · 行长汇报场景)
        # KS/AUC = 统计口径 · 通过率/坏账率/利润影响 = 业务口径 · 同 commit ship
        try:
            from agent_riskctrl.business_metrics import (
                calculate_business_metrics,
            )
            actual_avg_amt: float | None = None
            if "loan_amount_wan" in df.columns:
                try:
                    actual_avg_amt = float(df["loan_amount_wan"].mean())
                except (ValueError, TypeError):
                    actual_avg_amt = None
            business_panel = calculate_business_metrics(
                {
                    "total_records": result.total_records,
                    "approved": approved,
                    "rejected": rejected,
                    "manual_review": manual_review,
                    "approval_rate": result.approval_rate,
                },
                avg_loan_amount_wan_actual=actual_avg_amt,
                bad_rate=bad_rate,
            )
        except (ImportError, KeyError, ValueError, TypeError):
            business_panel = {}

        # BE6.3 collision report (静态 + 动态 dead-rule · 业务方 banner)
        try:
            from agent_riskctrl.rule_collision import analyze_collisions
            sample_records = df.head(500).to_dict(orient="records")
            collision_panel = analyze_collisions(
                ruleset, records=sample_records,
            ).to_dict()
        except (ImportError, KeyError, ValueError, TypeError):
            collision_panel = {}

        session_id = f"bt_{abs(hash(req.csv_path)) % 10_000_000:07d}"
        yield encode_event(make_done(
            panels={
                "ruleset": ruleset.model_dump(),
                "ks": ks_panel,
                "samples": samples,
                "rule_stats": rule_stats,
                "business_metrics": business_panel,  # BE6.4 业务口径
                "collision": collision_panel,        # BE6.3 互斥/遮蔽
            },
            metrics={
                "total_records": result.total_records,
                "approved": approved,
                "rejected": rejected,
                "manual_review": manual_review,
                "approval_rate": result.approval_rate,
                "bad_rate": bad_rate,
                "ks_peak": ks_peak,
                "label_column_used": label_col,
                # BE6.4 顶层 KPI · 业务方面板可直消费
                "profit_total_wan": business_panel.get("profit_total_wan"),
                "pass_rate": business_panel.get("pass_rate"),
                "reject_rate": business_panel.get("reject_rate"),
            },
            data_source=DATA_SOURCE_LIVE,
            session_id=session_id,
        ))

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_sse_headers())


# ============================================================================
# Phase A worker-A4 · 2026-04-29 · Export trio (docx / xlsx / pdf)
#   audit Cat 13 闭 · 与 worker-A6 export contract 共形
#   后端实装于 agent_riskctrl/exports.py · 不走境外 API · 本地渲染
# ============================================================================


class ExportRequest(BaseModel):
    """Export 三件套统一 body. ruleset_id 必传 (文件名后缀); 其余字段可选 ·
    缺则 build_*  内部用 placeholder. 前端 Step 8 wired 后会传 full panels."""

    ruleset_id: str = Field(..., description="ruleset 标识 · 文件名后缀")
    ruleset: dict | None = Field(default=None, description="RuleSet model_dump")
    ks: dict | None = Field(default=None, description="KS panel · {ksPeak, auc, passRate, badRate, points}")
    samples: list[dict] | None = Field(default=None, description="样本分档 · 3 档")
    rule_stats: list[dict] | None = Field(default=None, description="per-rule 命中明细")
    metrics: dict | None = Field(default=None, description="顶层 KPI metrics")


def _export_ctx_from_req(req: ExportRequest) -> dict[str, object]:
    return {
        "ruleset_id": req.ruleset_id,
        "ruleset": req.ruleset,
        "ks": req.ks,
        "samples": req.samples,
        "rule_stats": req.rule_stats,
        "metrics": req.metrics,
    }


def _export_response(data: bytes, ruleset_id: str, ext: str, mime: str) -> Response:
    from urllib.parse import quote

    from agent_riskctrl.exports import build_filename

    filename = build_filename(ruleset_id, ext)
    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "X-Riskctrl-Export-RulesetId": ruleset_id,
            "X-Riskctrl-Export-Type": ext,
        },
    )


@app.post("/api/riskctrl/export_docx")
async def riskctrl_export_docx(req: ExportRequest):
    """Word 报告导出 (回测稿) · 见 agent_riskctrl/exports.build_docx 内容契约."""
    try:
        from agent_riskctrl.exports import build_docx
        data = build_docx(_export_ctx_from_req(req))
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, ImportError) as e:
        raise HTTPException(
            500,
            detail={"error": {
                "code": "RENDER_FAILED",
                "message": f"docx render failed: {type(e).__name__}: {e}",
            }},
        ) from e
    return _export_response(
        data, req.ruleset_id, "docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/api/riskctrl/export_xlsx")
async def riskctrl_export_xlsx(req: ExportRequest):
    """Excel 规则明细导出 · 4 sheet (Rules / KS Points / Samples / RuleStats)."""
    try:
        from agent_riskctrl.exports import build_xlsx
        data = build_xlsx(_export_ctx_from_req(req))
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, ImportError) as e:
        raise HTTPException(
            500,
            detail={"error": {
                "code": "RENDER_FAILED",
                "message": f"xlsx render failed: {type(e).__name__}: {e}",
            }},
        ) from e
    return _export_response(
        data, req.ruleset_id, "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ============================================================================
# Phase A worker-A4 · 2026-04-29 · /api/riskctrl/demo/run · 纯 mock SSE 演示
#   物理隔离 endpoint · 不复用 _dsl_gen_stream / _backtest_stream
#   走 fixture · 反 5 原则 §3.5 难度分层 (credit_v15 / aml_kyc / fraud_high)
#   prod 端点失败时 banner 显式不 silent fallback (live-fallback-banner-spec §1.5)
# ============================================================================


class DemoRunRequest(BaseModel):
    scenario_id: str = Field(default="credit_v15", description="credit_v15 | aml_kyc | fraud_high")


@app.get("/api/riskctrl/demo/scenarios")
async def riskctrl_demo_scenarios():
    """枚举 demo scenarios (前端 dropdown 用)."""
    from agent_riskctrl.demo import list_scenarios
    return {"scenarios": list_scenarios()}


@app.post("/api/riskctrl/demo/run")
async def riskctrl_demo_run(req: DemoRunRequest):
    """纯 mock SSE 流 · 不调 LLM / 不读真 csv · 走 fixture json.

    Scenario 选 credit_v15 / aml_kyc / fraud_high · stages: load_csv → hit_rules → calc_ks ·
    done payload 与 prod backtest endpoint 共形 (panels.{ruleset, ks, samples, rule_stats}
    + metrics 顶层 KPI).
    """
    from shared.sse_envelope import (
        DATA_SOURCE_MOCK_FORCED,
        encode_event,
        make_done,
        make_error,
        make_stage,
    )
    import time as _time

    from agent_riskctrl.demo import VALID_SCENARIOS, load_scenario

    def gen():
        scenario_id = req.scenario_id or "credit_v15"
        if scenario_id not in VALID_SCENARIOS:
            yield encode_event(make_error(
                f"unknown scenario_id: {scenario_id} (allowed: {', '.join(VALID_SCENARIOS)})",
                code="DEMO_SCENARIO_INVALID",
            ))
            return
        try:
            data = load_scenario(scenario_id)
        except FileNotFoundError as e:
            yield encode_event(make_error(str(e), code="DEMO_SCENARIO_MISSING"))
            return
        except (json.JSONDecodeError, OSError) as e:
            yield encode_event(make_error(
                f"scenario load failed: {type(e).__name__}: {e}",
                code="DEMO_SCENARIO_LOAD",
            ))
            return

        stage_msgs = data.get("stage_messages", {}) or {}
        stages = ["load_csv", "hit_rules", "calc_ks"]
        for stage_name in stages:
            yield encode_event(make_stage(
                stage_name, "running",
                message=stage_msgs.get(stage_name, f"{stage_name}..."),
            ))
            _time.sleep(0.25)
            yield encode_event(make_stage(stage_name, "done"))

        yield encode_event(make_done(
            panels={
                "ruleset": data.get("ruleset", {}),
                "ks": data.get("ks", {}),
                "samples": data.get("samples", []),
                "rule_stats": data.get("rule_stats", []),
            },
            metrics=data.get("metrics", {}),
            data_source=DATA_SOURCE_MOCK_FORCED,
            session_id=data.get("session_id", f"demo_{scenario_id}"),
        ))

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_sse_headers())


@app.post("/api/riskctrl/export_pdf")
async def riskctrl_export_pdf(req: ExportRequest):
    """PDF 送审包 · 含规则明细 + 样本分布 + 审批栏 (留白)."""
    try:
        from agent_riskctrl.exports import build_pdf
        data = build_pdf(_export_ctx_from_req(req))
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError, ImportError) as e:
        raise HTTPException(
            500,
            detail={"error": {
                "code": "RENDER_FAILED",
                "message": f"pdf render failed: {type(e).__name__}: {e}",
            }},
        ) from e
    return _export_response(
        data, req.ruleset_id, "pdf",
        "application/pdf",
    )
