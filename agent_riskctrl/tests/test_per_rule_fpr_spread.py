# -*- coding: utf-8 -*-
"""Phase 1 Task C · per_rule_fpr_spread 单测

覆盖：
  1. backtesting.run_backtest 对 reject 规则产出 per-rule {FP, TN, FP_rate}
  2. adapter compute_domain_metrics 消费 rule.backtest 的 FP/TN 算总体方差 σ²
  3. A-019 N/A 规则跳过（approve / manual_review / (FP+TN)=0）
  4. 手算 σ² 对照（2 规则构造 FPR 分布 → 已知方差）
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from agent_riskctrl.backtesting import run_backtest
from agent_riskctrl.rule_engine import RuleSet, StrategyRule, RuleCondition


REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_df() -> pd.DataFrame:
    """10 行构造数据：
        label=0 (正常) 6 条；label=1 (坏账) 4 条
        credit 档位：low(<580) 4 条 / mid 3 条 / high(>=700) 3 条
        debt 档位：0.5 / 0.9 两档
    R_LOW (reject credit<580) 命中正常客户 2 个 → FP_low=2
    R_HIGH (reject debt>=0.8) 命中正常客户 1 个 → FP_high=1
    TN_low = 6 - 2 = 4；TN_high = 6 - 1 = 5
    FPR_low = 2/6 ≈ 0.3333；FPR_high = 1/6 ≈ 0.1667
    mean = 0.25；σ² = ((0.3333-0.25)² + (0.1667-0.25)²) / 2 ≈ 0.006944
    """
    rows = [
        # label=0 正常客户
        {"credit_score": 600, "debt_ratio": 0.5, "label_default": 0},  # 不命中
        {"credit_score": 650, "debt_ratio": 0.5, "label_default": 0},  # 不命中
        {"credit_score": 720, "debt_ratio": 0.5, "label_default": 0},  # 不命中
        {"credit_score": 560, "debt_ratio": 0.5, "label_default": 0},  # R_LOW 命中 → FP_low
        {"credit_score": 540, "debt_ratio": 0.5, "label_default": 0},  # R_LOW 命中 → FP_low
        {"credit_score": 700, "debt_ratio": 0.9, "label_default": 0},  # R_HIGH 命中 → FP_high
        # label=1 坏账客户（per_rule FP/TN 只看 label=0，此 4 条不入 FP/TN）
        {"credit_score": 520, "debt_ratio": 0.9, "label_default": 1},
        {"credit_score": 550, "debt_ratio": 0.85, "label_default": 1},
        {"credit_score": 600, "debt_ratio": 0.95, "label_default": 1},
        {"credit_score": 500, "debt_ratio": 0.6, "label_default": 1},
    ]
    return pd.DataFrame(rows)


def _build_ruleset() -> RuleSet:
    r_low = StrategyRule(
        rule_id="R_LOW",
        name="低信用拒",
        conditions=[RuleCondition(field="credit_score", operator="<", value=580)],
        action="reject",
        priority=1,
    )
    r_high = StrategyRule(
        rule_id="R_HIGH",
        name="高负债拒",
        conditions=[RuleCondition(field="debt_ratio", operator=">=", value=0.8)],
        action="reject",
        priority=2,
    )
    r_info = StrategyRule(
        rule_id="R_INFO",
        name="信息审",
        conditions=[RuleCondition(field="credit_score", operator=">=", value=700)],
        action="manual_review",
        priority=3,
    )
    return RuleSet(rules=[r_low, r_high, r_info], description="test ruleset")


def test_run_backtest_emits_per_rule_fp_tn():
    df = _build_df()
    rs = _build_ruleset()

    result = run_backtest(df, rs)
    rule_stats = result.metrics["rule_stats"]
    by_id = {s["rule_id"]: s for s in rule_stats}

    # R_LOW: reject, 独立匹配 label=0 中 2 个命中
    assert by_id["R_LOW"]["FP"] == 2
    assert by_id["R_LOW"]["TN"] == 4
    assert math.isclose(by_id["R_LOW"]["FP_rate"], 2 / 6, abs_tol=1e-3)

    # R_HIGH: reject, 独立匹配 label=0 中 1 个命中
    assert by_id["R_HIGH"]["FP"] == 1
    assert by_id["R_HIGH"]["TN"] == 5
    assert math.isclose(by_id["R_HIGH"]["FP_rate"], 1 / 6, abs_tol=1e-3)

    # R_INFO: manual_review → 应跳过 per-rule FP/TN，全 0
    assert by_id["R_INFO"]["FP"] == 0
    assert by_id["R_INFO"]["TN"] == 0
    assert by_id["R_INFO"]["FP_rate"] == 0.0


def test_per_rule_fpr_spread_variance_matches_manual_calc(tmp_path: Path):
    """adapter 算总体方差 σ² 对上手算值 ≈ 0.006944."""
    # 构造 adapter 消费的 rules.json 结构（含 backtest.FP/TN）
    df = _build_df()
    rs = _build_ruleset()
    result = run_backtest(df, rs)
    rule_stats = {s["rule_id"]: s for s in result.metrics["rule_stats"]}

    rules_doc = {
        "inputs_total": 1,
        "outputs_successful": 1,
        "ruleset": {
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "action": r.action,
                    "conditions": [{"field": c.field, "operator": c.operator, "value": c.value} for c in r.conditions],
                    "backtest": {
                        "FP": rule_stats[r.rule_id]["FP"],
                        "TN": rule_stats[r.rule_id]["TN"],
                        "FP_rate": rule_stats[r.rule_id]["FP_rate"],
                        "ks": None,
                        "approve_rate": 0.0,
                        "bad_rate": 0.0,
                        "hit_count": rule_stats[r.rule_id]["hit_count"],
                        "hit_rate": rule_stats[r.rule_id]["hit_rate"],
                    },
                }
                for r in rs.rules
            ]
        },
    }
    schema_doc = {"columns": list(df.columns), "label_column": "label_default"}
    cm = {"TP": 0, "FP": 3, "TN": 3, "FN": 0}  # dummy 主 confusion_matrix（false_positive_rate 用）
    backtest_doc = {"tool_calls": [{"status": "success"}], "confusion_matrix": cm}

    fx = tmp_path
    (fx / "rules.json").write_text(json.dumps(rules_doc, ensure_ascii=False), encoding="utf-8")
    (fx / "sample_schema.json").write_text(json.dumps(schema_doc, ensure_ascii=False), encoding="utf-8")
    (fx / "backtest.json").write_text(json.dumps(backtest_doc, ensure_ascii=False), encoding="utf-8")

    from evaluation.runner.adapters.agent2_riskctrl import Agent2RiskCtrlEvaluator
    from evaluation.runner.schemas import EvalRun

    ev = Agent2RiskCtrlEvaluator()
    run = EvalRun(agent_id="riskctrl", artifacts=[str(fx)])
    arts = ev.load_artifacts(run)
    domain = ev.compute_domain_metrics(arts)

    by_name = {m.name: m for m in domain}
    assert "per_rule_fpr_spread" in by_name

    spread = by_name["per_rule_fpr_spread"]
    assert spread.method == "deterministic"
    assert spread.value is not None

    # 手算：fprs=[2/6, 1/6]；mean=0.25；σ²= ((2/6-0.25)²+(1/6-0.25)²)/2 = 0.006944...
    expected = (((2 / 6) - 0.25) ** 2 + ((1 / 6) - 0.25) ** 2) / 2
    assert math.isclose(spread.value, expected, abs_tol=1e-6)
    assert math.isclose(spread.value, 0.006944, abs_tol=1e-4)

    # target "<= 0.03" → 0.006944 PASS
    assert spread.passed is True


def test_per_rule_fpr_spread_insufficient_rules(tmp_path: Path):
    """仅 1 条 reject 规则 → value=None, passed=None (pending 语义)."""
    rules_doc = {
        "inputs_total": 1,
        "outputs_successful": 1,
        "ruleset": {
            "rules": [
                {
                    "rule_id": "R_ONLY",
                    "action": "reject",
                    "conditions": [],
                    "backtest": {"FP": 1, "TN": 5},
                }
            ]
        },
    }
    schema_doc = {"columns": ["x"], "label_column": "label_default"}
    backtest_doc = {"tool_calls": [], "confusion_matrix": {"FP": 1, "TN": 5}}

    (tmp_path / "rules.json").write_text(json.dumps(rules_doc), encoding="utf-8")
    (tmp_path / "sample_schema.json").write_text(json.dumps(schema_doc), encoding="utf-8")
    (tmp_path / "backtest.json").write_text(json.dumps(backtest_doc), encoding="utf-8")

    from evaluation.runner.adapters.agent2_riskctrl import Agent2RiskCtrlEvaluator
    from evaluation.runner.schemas import EvalRun

    ev = Agent2RiskCtrlEvaluator()
    run = EvalRun(agent_id="riskctrl", artifacts=[str(tmp_path)])
    arts = ev.load_artifacts(run)
    domain = ev.compute_domain_metrics(arts)
    by_name = {m.name: m for m in domain}

    assert by_name["per_rule_fpr_spread"].value is None
    assert by_name["per_rule_fpr_spread"].passed is None
