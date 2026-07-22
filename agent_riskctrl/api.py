# -*- coding: utf-8 -*-
"""agent_riskctrl.api — Agent2 风控策略运营 FastAPI 路由模块。

端点 (Phase A worker-A4 · 2026-04-29 · sse-envelope.md §1.5 + workspace-state-protocol §4):
  POST /api/riskctrl/dsl_gen          — SSE · 自然语言 → RuleSet JSON (LLM 真接 · stream)
  POST /api/riskctrl/backtest         — SSE · RuleSet + CSV → metrics JSON (KS / 通过率 / 坏账率)
  POST /api/riskctrl/dsl/deploy       — REST · 风险经理签字 DSL 上线 (BE7 ledger)
  POST /api/riskctrl/demo/run         — SSE · 物理隔离 fixture demo
  POST /api/riskctrl/export_{docx,xlsx,pdf}  — REST · 三件套导出

设计:
- 独立 FastAPI app · api_server.py routes 合并装载
- 6 Agent SSE done envelope 共形 · 走 shared.sse_envelope.make_done · panel keys
  riskctrl 域投影 = (ruleset, ks, samples, rule_stats) · metrics 顶层 KPI
- mock=true 切预设 RuleSet · 不调 LLM · curl / 无 key 环境可演示
- 输出过 shared.qc.placeholder_guard (V2 后续接入 · 当前不阻塞)

ALL IN Phase B step 3 demo_mode audit (2026-05-09):
  data_source 5 enum 决策树 (per shared.sse_envelope §):
  - dsl_gen mock=False (默认):
      LLM 成功 → DATA_SOURCE_LIVE
      LLM fail → make_error (不 silent fallback · code=LLM_FALLBACK_EXHAUSTED · 红线 #1 守住)
  - dsl_gen mock=True (显式 demo):
      → DATA_SOURCE_MOCK_FORCED + WARN log (audit 痕迹)
  - backtest:
      → DATA_SOURCE_LIVE (无 mock 模式 · 必走 deterministic Python 真算 KS/AUC)
  - demo/run (物理隔离 endpoint):
      → DATA_SOURCE_MOCK_FORCED (fixture 演示 · 不调 LLM/真 csv)
  - dsl/deploy (REST):
      ledger 写入 silent-fail per §3.7.5 失败隔离 · 决策本身仍生效
  无 silent mock fallback 路径 · 任何 LLM/source fail 必走 make_error +
  前端 banner-spec 显式 retry · 红线 #1 (假 live · silent fallback mock) 全栈守住.

字段契约: docs/contracts/field-naming.md + docs/contracts/sse-envelope.md
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any


def _deterministic_id(prefix: str, *parts: str) -> str:
    """ALL IN Phase B step 5 · ruleset_id / session_id 派生 helper.

    替代 hash(...) % 10_000_000 · Python hash() 跨进程不稳 (PYTHONHASHSEED randomization)
    + 碰撞概率高 (10M 桶 · 100 万 ruleset 时 ~5% 碰撞 per birthday paradox).

    sha256 前 12 hex (48 bit · 281 万亿桶 · 实际碰撞概率可忽略) · 跨进程稳定 ·
    同 input 必同 output · 防 ruleset_id flapping (同样的策略意图 + csv 应得同 id).

    Args:
        prefix: e.g. "rs_mock" / "rs_llm" / "bt"
        *parts: input strings to hash (e.g. strategy_intent, csv_path)

    Returns:
        f"{prefix}_{12-char hex}" e.g. "rs_llm_a3f9c8d12b4e"
    """
    blob = "\x00".join(str(p) for p in parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(blob).hexdigest()[:12]}"

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth_service.dependencies import require_action  # noqa: E402


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
async def riskctrl_dsl_gen(
    req: DslGenRequest,
    _user: dict = Depends(require_action("riskctrl", "invoke")),
):
    """自然语言 → RuleSet JSON · SSE stream · stage 流 + done envelope.

    Body:    { strategy_intent | rule_text, sample_csv_path?, mock? }
    LLM provider/api_key 不通过 body 传 · 一律走 env (PIPL fallback chain · CLAUDE.md §3.6).
    Stream:
        event: stage   {stage: parse_intent | build_prompt | validate_dsl, status}
        event: done    {ruleset, ruleset_id, source: llm|mock, csv_columns?, data_source}
        event: error   {message, code}

    Auth (B5 sub-PR 2 · 2026-05-05 · per Q-052 #8): require_action("riskctrl", "invoke")
    enforce row-level/action gate · risk_manager/admin 可调 · RM 不可调 (Q-052 #8 收窄).
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
            from shared.prompts.agent_helpers import build_riskctrl_ssot_prompt
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
            # ALL IN Phase B step 3 · audit 痕迹 · 显式 mock=True 调用必有 WARN log ·
            # 银保监审计可追溯 · 防 production 误开 mock 模式而无觉
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "DSL gen mock=True 显式触发 · DATA_SOURCE_MOCK_FORCED · intent=%s",
                req.strategy_intent[:80],
            )
            yield encode_event(make_stage("build_prompt", "skipped", message="mock 模式 · 跳 LLM"))
            ruleset = parse_natural_language_rules(_MOCK_DSL_RESPONSE)
            ruleset_id = _deterministic_id("rs_mock", req.strategy_intent)
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
            system_prompt = build_riskctrl_ssot_prompt(
                task_type="rule_parse",
                schema_hint=(
                    '{"rules": [{"rule_id", "name", "description", '
                    '"conditions": [{"field", "operator", "value"}], '
                    '"action": "approve/reject/manual_review", "priority": int}], "description"}'
                ),
            )
            llm_json = caller(system_prompt, user_prompt)
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

        ruleset_id = _deterministic_id("rs_llm", req.strategy_intent)
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
async def riskctrl_backtest(
    req: BacktestRequest,
    _user: dict = Depends(require_action("riskctrl", "invoke")),
):
    """RuleSet + CSV 历史数据 → metrics + KS curve + samples + rule_stats · SSE stream.

    Body: { ruleset, csv_path, label_column?, bad_threshold? }
    Stream:
        event: stage  {stage: load_csv | hit_rules | calc_ks, status}
        event: done   panels={ruleset, ks: {ksPeak, auc, passRate, badRate, points},
                               samples, rule_stats},
                       metrics={total_records, approved, rejected, manual_review,
                                approval_rate, bad_rate, ks_peak, label_column_used}
        event: error  {message, code}

    Auth (Phase B.1 fix · 2026-05-09 · per Q-052 #8): require_action("riskctrl", "invoke")
    enforce row-level/action gate · risk_manager/admin 可调 · RM 不可调 (per Q-052 #8 收窄)
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
        # 未命中任何规则 = 默认放行（银行语义，backtesting.approval_rate 同口径）——
        # 通过桶必须含 no_hit，否则三档不闭合（260721 生产实锤：通过 0% + 79% 样本消失）
        no_hit = int((result.metrics or {}).get("no_hit", 0))
        approved = int(result.approved) + no_hit
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

        # ALL IN Phase B step 4 · EvidenceDrawer wire (per RFC freshness-claim-loan-sample)
        # 用 evidence_pipeline 收集证据 · 用 shared.evidence_drawer 挂到 claim · 加 done panel
        # 失败隔离: drawer 写入失败不破 SSE stream (silent-fail)
        evidence_panel: dict[str, Any] = {}
        try:
            from agent_riskctrl.evidence_pipeline import (
                RiskctrlCommentaryContext,
                RiskctrlCommentaryPipeline,
            )
            from shared.evidence_drawer import default_drawer

            commentary_ctx = RiskctrlCommentaryContext(
                ruleset_name=getattr(ruleset, "name", "") or req.csv_path,
                metrics={
                    "ks": ks_peak,
                    "pass_rate": result.approval_rate,
                    "bad_rate": bad_rate,
                    "psi": None,  # PSI v2 后续接入
                },
                per_rule_fp=rule_stats,
            )
            pipeline = RiskctrlCommentaryPipeline()
            bundle = pipeline.collect(commentary_ctx)

            # Phase A.1 RFC ratify · 回测样本走 LOAN_SAMPLE ClaimType · 365d SLA
            drawer = default_drawer()
            session_id_for_claim = _deterministic_id("bt", req.csv_path)
            claim_id = f"riskctrl_backtest_{session_id_for_claim}"
            for ev_item in bundle.items:
                # source tier 按 source 区分: input/metrics_analyze=Tier 1 (内部权威) · backtest=Tier 1
                drawer.attach(
                    claim_id=claim_id,
                    source=f"riskctrl:{ev_item.source}:{ev_item.ref_id}",
                    anchor=ev_item.ref_id,
                    snippet=ev_item.snippet,
                    source_tier=1,  # 内部回测引擎 = Tier 1 内部权威
                    claim_type="loan_sample",  # Phase A.1 RFC ratify · 365d SLA
                    confidence=ev_item.confidence,
                    meta=ev_item.meta or {},
                )
            evidence_panel = drawer.to_drawer_payload(claim_id)
        except (ImportError, RuntimeError, ValueError, TypeError, KeyError, AttributeError):
            pass  # silent-fail · 不破 stream · 前端 fallback fixture

        session_id = _deterministic_id("bt", req.csv_path)

        # V2 fix (codex review major 1): 单次 backtest 决策上链 (retention=short
        # 90 天 · §3.7.5 alert 同档 · 银保监审计每次跑过的回测可追溯).
        # silent-fail 不破 stream · 见 ledger_integration.record_backtest_decision.
        try:
            from agent_riskctrl.ledger_integration import (
                record_backtest_decision,
            )
            record_backtest_decision(
                ruleset_id=session_id,
                csv_path=str(req.csv_path),
                metrics={
                    "total_records": result.total_records,
                    "approval_rate": result.approval_rate,
                    "bad_rate": bad_rate,
                    "ks_peak": ks_peak,
                    "auc": auc_value,
                },
                business_metrics=business_panel or None,
            )
        except (ImportError, RuntimeError, ValueError, TypeError):
            pass  # silent-fail per §3.7.5 失败隔离

        yield encode_event(make_done(
            panels={
                "ruleset": ruleset.model_dump(),
                "ks": ks_panel,
                "samples": samples,
                "rule_stats": rule_stats,
                "business_metrics": business_panel,  # BE6.4 业务口径
                "collision": collision_panel,        # BE6.3 互斥/遮蔽
                "evidence": evidence_panel,          # ALL IN step 4 · EvidenceDrawer payload
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
# V2 fix (codex review major 1) · BE7 ledger 接入 production endpoint
#   POST /api/riskctrl/dsl/deploy: 风险经理签字 DSL 上线决策 · 上链 jurisdiction=HQ
#   retention=standard (5y · §3.7.5) · 触发 Agent4 全量重扫 + Agent3 rubric 同步
# ============================================================================


class DslDeployRequest(BaseModel):
    """DSL 部署决策请求体."""

    ruleset_id: str = Field(..., description="策略 ID (来自 dsl_gen ruleset_id)")
    dsl_version: str = Field(..., description="语义化版本号 e.g. v1.2.0")
    rule_count: int = Field(..., description="规则条数")
    affected_segments: list[str] = Field(
        default_factory=list,
        description="影响的客群 segment list (科创/对公财务/普惠 等)",
    )
    backtest_summary: dict = Field(
        default_factory=dict,
        description="回测元信息 (KS/AUC/通过率/坏账率/利润/KS_improvement)",
    )
    approver_user_id: str | None = Field(
        default=None, description="签字人 user_id (None 时上链不带 reviewer)",
    )
    trigger_alert_rebuild: bool = Field(
        default=True,
        description="是否触 Agent4 全量重扫 (per handoff §6.5)",
    )
    trigger_credit_rubric_sync: bool = Field(
        default=True,
        description="是否触 Agent3 rubric 同步 (per handoff §6.6)",
    )


@app.post("/api/riskctrl/dsl/deploy")
@audit_llm_call(
    agent_id="riskctrl", endpoint="/api/riskctrl/dsl/deploy",
    model="deterministic",
)
async def riskctrl_dsl_deploy(
    req: DslDeployRequest,
    _user: dict = Depends(require_action("riskctrl", "approve")),
):
    """DSL 部署决策 (production caller for ledger_integration.record_dsl_deploy).

    流程:
      1. 验 approver_user_id (req body) 必 == _user["sub"] (JWT sub) · 防客户端伪造签字人
      2. 调 record_dsl_deploy 上链 (silent-fail · 不破 deploy 流程)
      3. 返 decision_id + handoff 触发标记
      4. (后续 Sprint 4) 真触 Agent4 rebuild_index endpoint + Agent3 rubric_sync

    Body: DslDeployRequest
    Returns: { decision_id, handoff_triggers: [], dsl_version, deployed_at }

    Auth (Phase B.1 fix · 2026-05-09 · 致命修复 · codex 抓到客户端可伪造 approver_user_id):
    - require_action("riskctrl", "approve") · 仅 risk_manager/admin role 可调 (per RBAC)
    - approver_user_id verify · 必与 JWT sub 匹配 · 防客户端 body 伪造签字人 (合规审计要求)
    """
    # Phase B.1 致命修复 · approver_user_id 必与 JWT sub 匹配 · 防伪造
    jwt_user_id = _user.get("sub")
    if req.approver_user_id is not None and req.approver_user_id != jwt_user_id:
        raise HTTPException(
            403,
            detail={"error": {
                "code": "APPROVER_MISMATCH",
                "message": (
                    f"approver_user_id (body) 必与 JWT sub 一致 · 防伪造签字人. "
                    f"body={req.approver_user_id!r} · jwt_sub={jwt_user_id!r}"
                ),
            }},
        )
    # body 未传 approver_user_id 时 · 自动用 JWT sub 填 (强约束 audit 痕迹)
    effective_approver = req.approver_user_id or jwt_user_id

    try:
        from agent_riskctrl.ledger_integration import record_dsl_deploy
        decision_id = record_dsl_deploy(
            ruleset_id=req.ruleset_id,
            dsl_version=req.dsl_version,
            rule_count=req.rule_count,
            affected_segments=req.affected_segments,
            backtest_summary=req.backtest_summary,
            approver_user_id=effective_approver,
            deploy_endpoint="/api/riskctrl/dsl/deploy",
        )
    except (RuntimeError, ValueError, TypeError, ImportError) as e:
        raise HTTPException(
            500,
            detail={"error": {
                "code": "LEDGER_WRITE_FAILED",
                "message": f"ledger 写入失败 (但决策本身仍生效): {type(e).__name__}: {e}",
            }},
        ) from e

    handoff_triggers: list[str] = []
    if req.trigger_alert_rebuild:
        handoff_triggers.append("§6.5 dsl_deployed → alert.scan_trigger")
    if req.trigger_credit_rubric_sync:
        handoff_triggers.append("§6.6 dsl_versioned → credit.rubric_sync")

    from datetime import datetime, timezone
    return {
        "decision_id": decision_id,
        "ruleset_id": req.ruleset_id,
        "dsl_version": req.dsl_version,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "handoff_triggers": handoff_triggers,
        "ledger_persisted": "import-failed" not in decision_id and "write-failed" not in decision_id,
    }


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
async def riskctrl_export_docx(
    req: ExportRequest,
    _user: dict = Depends(require_action("riskctrl", "export")),
):
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
async def riskctrl_export_xlsx(
    req: ExportRequest,
    _user: dict = Depends(require_action("riskctrl", "export")),
):
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
# Phase B.2 ALL IN reframe (2026-05-10) · /api/riskctrl/demo/run · 真后端 pipeline
#   PM 真意: 演示 = 用优质内部 mock 输入 (loans.csv) 跑真后端 (LLM + 确定性 backtest)
#   旧 fixture-based 实现 (Phase A worker-A4) 已废弃 · 违反反 5 原则 §3.5 (答案给嘴边)
#   新形态: seed_id → 真 dsl_gen (LLM) → 真 backtest (Python KS/AUC) → 真返结果
#   data_source = LIVE (后端 pipeline 真跑) · seed_id 标识输入来源 (mock 输入 != mock 结果)
# ============================================================================


class DemoRunRequest(BaseModel):
    """Phase B.2 demo run request · seed_id 选 demo 输入档 (输入 mock · 结果真跑)."""

    seed_id: str = Field(
        default="credit_v15",
        description="demo 输入档 ID · 见 GET /api/riskctrl/demo/seeds (credit_v15 | aml_kyc | fraud_high)",
    )
    # 旧字段 scenario_id 双兼 (向下兼容前端旧 client 直至 Phase B.2 ship)
    scenario_id: str | None = Field(
        default=None,
        description="(deprecated) 旧名 · 等价于 seed_id · 后端透传",
    )


@app.get("/api/riskctrl/demo/seeds")
async def riskctrl_demo_seeds():
    """枚举 demo input seed (前端 dropdown 用 · 仅输入字段 · 不含答案)."""
    from agent_riskctrl.demo import list_seeds
    return {"seeds": list_seeds()}


# Legacy alias · 旧前端 GET /api/riskctrl/demo/scenarios 调用兼容
@app.get("/api/riskctrl/demo/scenarios")
async def riskctrl_demo_scenarios_legacy():
    """[Deprecated · 改用 /api/riskctrl/demo/seeds] 旧 dropdown 形态 (key/label) 兼容."""
    from agent_riskctrl.demo import list_scenarios
    return {"scenarios": list_scenarios()}


@app.post("/api/riskctrl/demo/run")
@audit_llm_call(
    agent_id="riskctrl", endpoint="/api/riskctrl/demo/run", model="deepseek-chat",
)
async def riskctrl_demo_run(
    req: DemoRunRequest,
    _user: dict = Depends(require_action("riskctrl", "invoke")),
):
    """Phase B.2 真后端 demo · 用 demo seed 输入跑真 dsl_gen (LLM) + 真 backtest.

    流程:
      1. 解析 seed (strategy_intent + csv_path · 仅输入 · 无答案)
      2. 载 CSV (load_csv_data · MAX_ROWS=50000 上限)
      3. 调 LLM 生成 DSL (走 shared.llm_caller · PIPL fallback chain · 不 mock=true)
      4. 真 backtest (apply_ruleset + 确定性 KS/AUC · §3.1 不让 LLM 现场算)
      5. 决策上链 (silent-fail · §3.7.5 retention=short 90d)
      6. emit done envelope · data_source=LIVE · metrics.demo_seed_id 标识输入来源

    任何 LLM/CSV 失败 → typed make_error event · 不 silent fallback 假数据 (红线 #1).

    Auth (Phase B.1 fix · 2026-05-09 · per Q-052 #8): require_action("riskctrl", "invoke")
    enforce row-level/action gate · 即便 demo · 也防未授权 (防滥用作免费推理通道)
    """
    from shared.sse_envelope import (
        DATA_SOURCE_LIVE,
        encode_event,
        make_done,
        make_error,
        make_error_from_exception,
        make_stage,
    )

    from agent_riskctrl.demo import VALID_SEED_IDS, get_seed

    def gen():
        # seed 解析 · scenario_id (legacy) → seed_id (new)
        seed_id = req.seed_id or req.scenario_id or "credit_v15"
        if seed_id not in VALID_SEED_IDS:
            yield encode_event(make_error(
                f"unknown seed_id: {seed_id} (allowed: {', '.join(VALID_SEED_IDS)})",
                code="DEMO_SEED_INVALID",
            ))
            return
        seed = get_seed(seed_id)
        if seed is None:
            yield encode_event(make_error(
                f"seed lookup failed: {seed_id}",
                code="DEMO_SEED_MISSING",
            ))
            return

        # 延迟 import · 避免 module load cost on path miss
        try:
            from agent_riskctrl.backtesting import load_csv_data, run_backtest
            from agent_riskctrl.metrics import calculate_auc, calculate_ks
            from agent_riskctrl.rule_engine import RuleSet, parse_natural_language_rules
            from shared.llm_caller import make_json_caller
            from shared.prompts.agent_helpers import build_riskctrl_ssot_prompt
        except (ImportError, ModuleNotFoundError) as e:
            yield encode_event(make_error_from_exception(e, code="IMPORT_FAILED"))
            return

        # Stage 1 · load CSV (用 demo seed 的 csv_path · 真读 loans.csv)
        yield encode_event(make_stage(
            "load_csv", "running",
            message=f"载入 demo 样本 · {seed['csv_path']} (MAX_ROWS=50000)",
        ))
        csv_path = Path(seed["csv_path"])
        if not csv_path.is_absolute():
            csv_path = PROJECT_ROOT / seed["csv_path"]
        if not csv_path.exists():
            yield encode_event(make_error(
                f"demo seed CSV 不存在: {csv_path} · 检查 data/mock/agent2-samples/ 是否完整",
                code="CSV_NOT_FOUND",
            ))
            return
        try:
            df = load_csv_data(str(csv_path))
        except (OSError, ValueError) as e:
            yield encode_event(make_error_from_exception(e, code="CSV_LOAD_FAILED"))
            return
        yield encode_event(make_stage("load_csv", "done", count=int(len(df))))

        # Stage 2 · 调 LLM 生成 DSL (真路径 · 不 mock=true)
        yield encode_event(make_stage(
            "call_llm", "running",
            message=f"调 LLM 生成 DSL · 策略意图: {seed['label']}",
        ))
        csv_columns = [str(c) for c in df.columns]
        data_context = (
            f"\n\n参考数据字段:\n{', '.join(csv_columns)}\n"
            f"前 3 行示例:\n{df.head(3).to_string(index=False)}"
        )
        user_prompt = (
            f"请将以下策略意图转换为结构化规则:\n\n{seed['strategy_intent']}{data_context}"
        )
        try:
            caller = make_json_caller(
                agent_id="riskctrl",
                endpoint="/api/riskctrl/demo/run",
                temperature=0.3,
            )
            system_prompt = build_riskctrl_ssot_prompt(
                task_type="rule_parse",
                schema_hint=(
                    '{"rules": [{"rule_id", "name", "description", '
                    '"conditions": [{"field", "operator", "value"}], '
                    '"action": "approve/reject/manual_review", "priority": int}], "description"}'
                ),
            )
            llm_json = caller(system_prompt, user_prompt)
        except (RuntimeError, ValueError, TypeError, OSError, KeyError, ImportError) as e:
            yield encode_event(make_error_from_exception(e, code="LLM_CALL_FAILED"))
            return

        if llm_json is None:
            yield encode_event(make_error(
                "LLM 调用失败 · fallback chain 全部不可用 · 请检查 env LLM key (DEEPSEEK_API_KEY / DASHSCOPE_API_KEY) 后重试 · 不 silent fallback 假数据",
                code="LLM_FALLBACK_EXHAUSTED",
            ))
            return

        if not isinstance(llm_json, dict):
            llm_json = {"rules": llm_json} if isinstance(llm_json, list) else {}

        try:
            ruleset = parse_natural_language_rules(llm_json)
        except (ValueError, TypeError, KeyError) as e:
            yield encode_event(make_error_from_exception(e, code="DSL_PARSE_FAILED"))
            return

        if not ruleset.rules:
            yield encode_event(make_error(
                "LLM 返回未能解析出有效规则 · seed strategy_intent 可能需调整 · 不 silent fallback",
                code="DSL_EMPTY_RULES",
            ))
            return
        yield encode_event(make_stage("call_llm", "done", rule_count=len(ruleset.rules)))

        # Stage 3 · 真 backtest (apply_ruleset 走 rule_engine · 不让 LLM 算)
        yield encode_event(make_stage(
            "hit_rules", "running",
            message=f"真规则命中扫描 · {len(df)} 条样本 × {len(ruleset.rules)} 条规则",
        ))
        try:
            result = run_backtest(df, ruleset, label_column=None)  # auto-detect
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            yield encode_event(make_error_from_exception(e, code="BACKTEST_FAILED"))
            return
        yield encode_event(make_stage("hit_rules", "done"))

        # Stage 4 · KS / AUC (确定性 numpy · §3.1 不让 LLM 现场算)
        yield encode_event(make_stage(
            "calc_ks", "running",
            message="计算 KS / AUC / 通过率 (确定性 Python · 不让 LLM 估)",
        ))
        bad_rate: float | None = None
        ks_peak: float | None = None
        auc_value: float | None = None
        ks_points: list[dict[str, Any]] = []
        label_col: str | None = None
        for cand in ("days_past_due", "label_default", "label"):
            if cand in df.columns:
                label_col = cand
                break

        if label_col and label_col in df.columns:
            try:
                if label_col == "days_past_due":
                    bad_mask = df[label_col].fillna(0).astype(float) > 30  # default bad_threshold
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
        rule_stats = [
            {
                "rule_id": r.get("rule_id") or r.get("ruleId"),
                "hit": r.get("hit", 0),
                "fp": r.get("fp", 0),
                "tn": r.get("tn", 0),
            }
            for r in rule_stats_raw
        ]

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
                "bad_rate": 0.0,
            },
            {
                "key": "block",
                "label": "拒绝",
                "count": rejected,
                "pct": round(rejected * 100.0 / total, 1),
                "bad_rate": 0.0,
            },
        ]
        ks_panel = {
            "ksPeak": ks_peak or 0.0,
            "auc": auc_value or 0.0,
            "passRate": round(approved * 100.0 / total, 1),
            "badRate": round((bad_rate or 0.0) * 100.0, 1),
            "points": ks_points,
        }
        yield encode_event(make_stage("calc_ks", "done"))

        # 业务指标 (BE6.4) · silent-fail 不破 stream
        try:
            from agent_riskctrl.business_metrics import calculate_business_metrics
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

        # Collision report (BE6.3) · silent-fail
        try:
            from agent_riskctrl.rule_collision import analyze_collisions
            sample_records = df.head(500).to_dict(orient="records")
            collision_panel = analyze_collisions(ruleset, records=sample_records).to_dict()
        except (ImportError, KeyError, ValueError, TypeError):
            collision_panel = {}

        # 决策上链 (silent-fail · §3.7.5 retention=short 90d · alert 同档 · 银保监审计每次跑过的 demo 也可追溯)
        session_id = _deterministic_id("demo_bt", seed_id, seed["csv_path"])
        try:
            from agent_riskctrl.ledger_integration import record_backtest_decision
            record_backtest_decision(
                ruleset_id=session_id,
                csv_path=seed["csv_path"],
                metrics={
                    "total_records": result.total_records,
                    "approval_rate": result.approval_rate,
                    "bad_rate": bad_rate,
                    "ks_peak": ks_peak,
                    "auc": auc_value,
                    "demo_seed_id": seed_id,  # 上链标记 demo 来源 · 区分 prod backtest
                },
                business_metrics=business_panel or None,
            )
        except (ImportError, RuntimeError, ValueError, TypeError):
            pass

        yield encode_event(make_done(
            panels={
                "ruleset": ruleset.model_dump(),
                "ks": ks_panel,
                "samples": samples,
                "rule_stats": rule_stats,
                "business_metrics": business_panel,
                "collision": collision_panel,
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
                "profit_total_wan": business_panel.get("profit_total_wan"),
                "pass_rate": business_panel.get("pass_rate"),
                "reject_rate": business_panel.get("reject_rate"),
                "demo_seed_id": seed_id,
                "demo_seed_label": seed["label"],
                "demo_strategy_intent": seed["strategy_intent"],
            },
            data_source=DATA_SOURCE_LIVE,  # 真后端 pipeline · 不是 MOCK_FORCED
            session_id=session_id,
        ))

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_sse_headers())


# ============================================================================
# W1 Phase D (codex R3 R3.2 #3 ack · 2026-05-21) · 客户风险评级 endpoint
#
# 新业务方向 · 与旧 DSL `/dsl_gen` + `/backtest` 物理隔离 (backward compat 全保留)
# 输入: canonical (client_metadata + decision_context + credit_terms + material_facts)
# 输出: 7 维评分 + 评级 (低/中/高) + Top risks + 缓释 + 后审周期 + LLM reasoning
# 实现: in-process · agent_riskctrl.risk_assess_engine · 确定性出分 + LLM 写理由
# ============================================================================


class RiskAssessRequest(BaseModel):
    """客户风险评级请求 (W1 Phase D · codex R3 R3.2 #3).

    canonical signature: 含 ``client_metadata`` layer · 推荐
    backward compat: 老路径直接传 dict (无 client_metadata 层)· 会按 flat 自动归一
    """

    client_metadata: dict = Field(default_factory=dict, description="客户基础信息 (canonical 33 字段)")
    decision_context: dict | None = Field(
        default=None, description="credit Agent 决策上下文 (7 字段 · optional · 提升评分准确度)",
    )
    credit_terms: dict | None = Field(default=None, description="授信条件 (canonical 12 字段 · optional)")
    material_facts: dict | None = Field(
        default=None, description="物料事实 (canonical 23 字段 · optional)",
    )
    use_llm: bool = Field(default=True, description="是否调 LLM 写 reasoning · 默认 True · False 走模板兜底")


@app.post("/api/riskctrl/risk_assess")
@audit_llm_call(agent_id="riskctrl", endpoint="/api/riskctrl/risk_assess", model="deepseek-chat")
async def riskctrl_risk_assess(
    req: RiskAssessRequest,
    _user: dict = Depends(require_action("riskctrl", "invoke")),
):
    """客户风险评级 · 7 维加权 (deterministic) + LLM 写理由 · SSE stream.

    W1 Phase D (codex R3 R3.2 #3 user ack · 2026-05-21):

    - 新业务方向 · 与旧 ``/dsl_gen`` + ``/backtest`` DSL 业务并行 (backward compat 全保留)
    - 7 维 (信用/财务/交易/行业/担保/集中度/舆情司法) · 确定性加权 · LLM 不改分
    - 输出 grade=低/中/高 · review_cycle=12/6/3 月 · top_risks + mitigations + reasoning
    - LLM 缺 key / 失败 → 模板兜底 reasoning · data_source=mock_fallback (不假装 live)

    Stream:
        event: stage  {stage: dim_scoring | aggregate | llm_reasoning, status}
        event: done   panels={
            risk_assess: {composite_risk_score, risk_grade, dimension_scores,
                          top_risks, mitigations, review_cycle_months,
                          reasoning, confidence, data_source}
        }, metrics={composite_risk_score, risk_grade, review_cycle_months}

    Auth: require_action("riskctrl", "invoke") · 与 dsl_gen/backtest 一致.
    """
    from shared.sse_envelope import (
        DATA_SOURCE_LIVE,
        DATA_SOURCE_MOCK_FALLBACK,
        encode_event,
        make_done,
        make_error_from_exception,
        make_stage,
    )

    def gen():
        try:
            from agent_riskctrl.risk_assess_engine import run_risk_assess
        except (ImportError, ModuleNotFoundError) as e:
            yield encode_event(make_error_from_exception(e, code="IMPORT_FAILED"))
            return

        yield encode_event(make_stage("dim_scoring", "running", message="7 维评分计算中..."))

        # Build LLM caller (optional)
        llm_caller = None
        if req.use_llm:
            try:
                from shared.llm_caller import make_text_caller
                llm_caller = make_text_caller(
                    agent_id="riskctrl",
                    endpoint="/api/riskctrl/risk_assess",
                    temperature=0.0,
                )
            except (ImportError, RuntimeError) as e:
                logger_msg = f"LLM caller unavailable · template fallback · {type(e).__name__}: {e}"
                yield encode_event(make_stage("llm_reasoning", "running", message=logger_msg))

        yield encode_event(make_stage("dim_scoring", "done"))
        yield encode_event(make_stage("aggregate", "running", message="加权汇总 + 评级中..."))

        try:
            result = run_risk_assess(
                client_metadata=req.client_metadata or {},
                decision_context=req.decision_context,
                credit_terms=req.credit_terms,
                material_facts=req.material_facts,
                llm_caller=llm_caller,
            )
        except (RuntimeError, ValueError, TypeError, KeyError, AttributeError) as e:
            yield encode_event(make_error_from_exception(e, code="RISK_ASSESS_FAILED"))
            return

        yield encode_event(make_stage("aggregate", "done"))
        yield encode_event(make_stage(
            "llm_reasoning",
            "done",
            message=f"reasoning 来源: {result.data_source}",
        ))

        data_source = DATA_SOURCE_LIVE if result.data_source == "live" else DATA_SOURCE_MOCK_FALLBACK

        # session_id deterministic per client · 不调用 timestamp / random
        session_id = _deterministic_id(
            "ra",
            req.client_metadata.get("CLIENT_FULL_NAME", ""),
            req.client_metadata.get("CLIENT_USCC", "") or req.client_metadata.get("CLIENT_ID_NUMBER", ""),
            f"{result.composite_risk_score:.1f}",
        )

        yield encode_event(make_done(
            agent_id="riskctrl",
            panels={
                "risk_assess": {
                    "composite_risk_score": result.composite_risk_score,
                    "risk_grade": result.risk_grade,
                    "dimension_scores": result.dimension_scores,
                    "top_risks": result.top_risks,
                    "mitigations": result.mitigations,
                    "review_cycle_months": result.review_cycle_months,
                    "reasoning": result.reasoning,
                    "confidence": result.confidence,
                },
            },
            metrics={
                "composite_risk_score": result.composite_risk_score,
                "risk_grade": result.risk_grade,
                "review_cycle_months": result.review_cycle_months,
                "dim_count": len(result.dimension_scores),
            },
            data_source=data_source,
            session_id=session_id,
        ))

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_sse_headers())


@app.post("/api/riskctrl/export_pdf")
async def riskctrl_export_pdf(
    req: ExportRequest,
    _user: dict = Depends(require_action("riskctrl", "export")),
):
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
