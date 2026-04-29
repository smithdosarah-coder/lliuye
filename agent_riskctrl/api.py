# -*- coding: utf-8 -*-
"""agent_riskctrl.api — Agent2 风控策略运营 FastAPI 路由模块。

端点 (Stage C v4.0 · 2026-04-28 · onboarding W-C2-A2):
  POST /api/riskctrl/dsl_gen          — 自然语言 → RuleSet JSON (LLM 真接 · 单 turn)
  POST /api/riskctrl/backtest         — RuleSet + CSV → metrics JSON (KS/通过率/坏账率)

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- v4.0 JSON 端点直调 LLMClient.chat_json + parse_natural_language_rules + run_backtest
- mock=true 切 fixture RuleSet · 不调 LLM (curl 验 / 无 key 环境可用)
- 输出前过 shared.qc.placeholder_guard

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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

app = FastAPI(title="Agent2 Risk Control API", version="4.0")


@app.get("/api/riskctrl/health")
async def riskctrl_health():
    """Agent2 sub-app 健康探针 (与 portal /health 平级, 用于精细化故障定位)。"""
    return {"status": "ok", "agent": "agent_riskctrl"}


# ============================================================================
# Stage C v4.0 (2026-04-28 · onboarding W-C2-A2) · JSON 单 turn 端点
# 直调 LLM + parse_natural_language_rules + run_backtest · 非 SSE
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
    """v4.0 JSON dsl_gen body."""

    strategy_intent: str = Field(..., description="自然语言策略意图描述")
    sample_csv_path: str | None = Field(
        default=None, description="(可选) 历史样本 CSV 路径 · 用于 LLM 对照字段"
    )
    provider: str = Field(default="deepseek", description="LLM provider")
    api_key: str = Field(default="", description="LLM api_key (留空走 env)")
    mock: bool = Field(
        default=False,
        description="true → 返预设 RuleSet · 不调 LLM (无 key 环境可 demo)",
    )


@app.post("/api/riskctrl/dsl_gen")
@audit_llm_call(agent_id="riskctrl", endpoint="/api/riskctrl/dsl_gen", model="deepseek-chat")
async def riskctrl_dsl_gen(req: DslGenRequest):
    """自然语言 → RuleSet JSON · 单 turn LLM 真接.

    Body: { strategy_intent, sample_csv_path?, provider?, api_key?, mock? }
    Returns: { ruleset: RuleSet, source: "llm"|"mock", csv_columns?: [...] }
    """
    from agent_riskctrl.prompts import SYSTEM_RULE_PARSER
    from agent_riskctrl.rule_engine import parse_natural_language_rules

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
                # 失败软降级 · LLM 仍可工作 (无 csv hint)
                data_context = f"\n\n[csv 加载失败: {type(e).__name__}: {e}]"

    user_prompt = f"请将以下策略意图转换为结构化规则:\n\n{req.strategy_intent}{data_context}"

    # mock 模式 (curl demo / 无 key) → 预设 RuleSet 不调 LLM
    if req.mock:
        ruleset = parse_natural_language_rules(_MOCK_DSL_RESPONSE)
        return {
            "ruleset": ruleset.model_dump(),
            "source": "mock",
            "csv_columns": csv_columns,
        }

    # LLM 真接
    try:
        from llm import LLMClient
        llm = LLMClient(provider=req.provider, api_key=req.api_key)
        llm_json = llm.chat_json(
            system_prompt=SYSTEM_RULE_PARSER,
            user_content=user_prompt,
            temperature=0.3,
        )
    except (RuntimeError, ValueError, TypeError, OSError, KeyError) as e:
        raise HTTPException(
            500, f"LLM call failed: {type(e).__name__}: {e}"
        ) from e

    if not isinstance(llm_json, dict):
        # chat_json 可能返 list (rules 列表直接返) · normalize 一下
        llm_json = {"rules": llm_json} if isinstance(llm_json, list) else {}

    ruleset = parse_natural_language_rules(llm_json)
    if not ruleset.rules:
        raise HTTPException(
            400,
            "LLM 返回未能解析出有效规则 · 请尝试更具体的策略意图描述",
        )
    return {
        "ruleset": ruleset.model_dump(),
        "source": "llm",
        "csv_columns": csv_columns,
    }


class BacktestRequest(BaseModel):
    """v4.0 JSON backtest body."""

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


@app.post("/api/riskctrl/backtest")
async def riskctrl_backtest(req: BacktestRequest):
    """RuleSet + CSV 历史数据 → metrics JSON (KS / 通过率 / 坏账率 / 规则命中).

    Body: { ruleset, csv_path, label_column?, bad_threshold? }
    Returns: { total_records, approved, rejected, manual_review, approval_rate,
               bad_rate, ks, rule_stats: [...] }
    """
    from agent_riskctrl.backtesting import load_csv_data, run_backtest
    from agent_riskctrl.metrics import calculate_ks
    from agent_riskctrl.rule_engine import RuleSet

    # csv 路径解析
    csv_path = Path(req.csv_path)
    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / req.csv_path
    if not csv_path.exists():
        raise HTTPException(400, f"csv_path 不存在: {csv_path}")

    # ruleset 反序列化
    try:
        ruleset = RuleSet.model_validate(req.ruleset)
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(400, f"ruleset 反序列化失败: {type(e).__name__}: {e}") from e
    if not ruleset.rules:
        raise HTTPException(400, "ruleset.rules 不能为空")

    # load + 决定 label_col (run_backtest 内部仅自检 label_default/label · 此处补 days_past_due)
    try:
        df = load_csv_data(str(csv_path))
    except (OSError, ValueError) as e:
        raise HTTPException(400, f"csv 加载失败: {e}") from e

    label_col = req.label_column
    if label_col is None:
        for cand in ("days_past_due", "label_default", "label"):
            if cand in df.columns:
                label_col = cand
                break

    # 显式把 label_col 传给 run_backtest (per-rule FP/TN 依赖此参数)
    result = run_backtest(df, ruleset, label_column=label_col)

    bad_rate: float | None = None
    ks: float | None = None

    if label_col and label_col in df.columns:
        try:
            # bad = days_past_due > bad_threshold (or label==1 if 0/1 标签)
            if label_col == "days_past_due":
                bad_mask = df[label_col].fillna(0).astype(float) > req.bad_threshold
            else:
                bad_mask = df[label_col].fillna(0).astype(float) > 0.5
            bad_rate = round(float(bad_mask.mean()), 4)

            # KS: y_true=bad_mask · y_pred=拒绝/审查得 1 (用 hit_results action)
            hit_results = result.metrics.get("hit_results", []) if result.metrics else []
            y_true = bad_mask.astype(int).tolist()
            y_pred = [1 if r["action"] in ("reject", "manual_review") else 0 for r in hit_results]
            if len(y_true) == len(y_pred) and y_pred:
                ks = calculate_ks(y_true, y_pred)
        except (TypeError, ValueError, KeyError):
            pass

    rule_stats = (result.metrics or {}).get("rule_stats", [])

    return {
        "total_records": result.total_records,
        "approved": result.approved,
        "rejected": result.rejected,
        "manual_review": result.manual_review,
        "approval_rate": result.approval_rate,
        "bad_rate": bad_rate,
        "ks": ks,
        "label_column_used": label_col,
        "rule_stats": rule_stats,
    }
