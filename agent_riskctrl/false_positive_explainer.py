# -*- coding: utf-8 -*-
"""agent_riskctrl.false_positive_explainer — 误杀个案 LLM 解释 (BE8.8).

风险经理痛 1.4.1 (per BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE8):
  "回测出 N 条误杀 (label=正常 但被规则拒) · 只看 rule_id 知道哪条规则拒了 ·
   不知道为什么这条规则在这个客户上判错"

LLM 在这里**不是算 KS** (per CLAUDE.md §3.1 LLM 不算 KS · 这个红线必守) ·
而是给**可解释 reason** — 把 rule 文本 + 客户实际特征 + 业务上下文捏合给业务方读懂.

设计:
  - **§3.1 治本路径**: KS / 误杀检测 / FP 数量计算全 Python 确定性 ·
    LLM 仅消费 (rule_text, customer_features, ground_truth_label) 输出可解释段
  - **§3.6 PIPL fallback chain**: 走 shared/llm_caller.LLMCaller agent_id=riskctrl ·
    默认 chain (deepseek + dashscope · 全境内) · audit log 含 region 字段
  - **不新增 legacy LLM 直连** (DIFF guard 0 新增 · per onboarding grep guard)
  - LLM 失败 silent · 个案 reason 留空 · 业务方仍可看 rule_id + features (raw fallback)
  - LLM 输入 budget 控: 单次最多 5 个 FP 个案 + 字段截断到 800 char prompt

输出形态 (JSON):
  {
    "loan_id": "L000123",
    "hit_rule_id": "R001",
    "hit_rule_name": "高负债拒绝",
    "rule_action": "reject",
    "ground_truth": "good_customer",  # label=days_past_due<=30
    "key_features": {"debt_ratio": 0.78, "credit_score": 720, ...},
    "reason": "<LLM 给的可解释段>",
    "reason_source": "llm" | "fallback"
  }

Public surface:
  - ``identify_false_positives(df, ruleset, ...) -> list[FalsePositive]``
  - ``explain_false_positives(fps, max_explain=5, llm_caller=None) -> list[dict]``
  - ``format_fp_summary(explanations) -> str``
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

import pandas as pd

from agent_riskctrl.baseline_ruleset import BAD_DPD_THRESHOLD, LABEL_COLUMN_DEFAULT
from agent_riskctrl.dsl_field_dict import format_for_business
from agent_riskctrl.rule_engine import RuleSet, apply_ruleset

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Identify FP (确定性 Python · 不走 LLM)
# ---------------------------------------------------------------------------


@dataclass
class FalsePositive:
    """单条误杀: 实际是 good · 但规则给了 reject.

    rule_action='reject' 且 label_value<=bad_threshold 视 FP.
    manual_review 不算 FP (业务上是观望 · 非误杀).
    """
    loan_id: str
    hit_rule_id: str
    hit_rule_name: str
    rule_action: str
    label_value: float
    bad_threshold: int
    key_features: dict
    raw_features: dict


def identify_false_positives(
    df: pd.DataFrame,
    ruleset: RuleSet,
    label_column: str = LABEL_COLUMN_DEFAULT,
    bad_threshold: int = BAD_DPD_THRESHOLD,
    max_features_in_record: int = 8,
) -> list[FalsePositive]:
    """跑 ruleset · 找出 reject 命中但实际 good 的个案.

    Args:
        df: 含 label_column 的样本
        ruleset:
        label_column: bad 标签列
        bad_threshold: label > threshold 视 bad

    Returns:
        list[FalsePositive] · 按 loan_id 字典序
    """
    if df is None or len(df) == 0 or label_column not in df.columns:
        return []

    records = df.to_dict(orient="records")
    hit_results = apply_ruleset(ruleset, records)

    rule_lookup = {r.rule_id: r for r in ruleset.rules}

    fps: list[FalsePositive] = []
    for rec, hit in zip(records, hit_results):
        if hit["action"] != "reject":
            continue
        try:
            label_val = float(rec.get(label_column, 0) or 0)
        except (TypeError, ValueError):
            continue
        if label_val > bad_threshold:
            continue  # 命中且确实 bad · 不是误杀

        rule_obj = rule_lookup.get(hit["hit_rule_id"], None)
        # key_features: rule 涉及字段值 + label · 给 LLM 看的核心
        key_feats: dict = {}
        if rule_obj is not None:
            for cond in rule_obj.conditions:
                if cond.field in rec:
                    key_feats[cond.field] = rec[cond.field]
        # 限制 raw_features 大小 (避免 LLM prompt 撑爆)
        raw_truncated = dict(list(rec.items())[:max_features_in_record])
        fps.append(FalsePositive(
            loan_id=str(rec.get("loan_id", "?")),
            hit_rule_id=hit["hit_rule_id"] or "",
            hit_rule_name=hit["hit_rule_name"] or "",
            rule_action=hit["action"],
            label_value=label_val,
            bad_threshold=bad_threshold,
            key_features=key_feats,
            raw_features=raw_truncated,
        ))

    fps.sort(key=lambda x: x.loan_id)
    return fps


# ---------------------------------------------------------------------------
# LLM explanation (走 shared/llm_caller · §3.6 PIPL fallback chain)
# ---------------------------------------------------------------------------


SYSTEM_PROMPT_FP_EXPLAIN = """你是银行风险经理的助手 · 帮业务方理解风控规则的"误杀"个案。

## 任务

给一个被规则拒绝但实际**未逾期**的客户个案 · 用 2-3 句话解释:
1. 规则拒绝的原因 (规则名 + 客户实际命中的特征值)
2. 为什么这个客户实际是好的 (征信分 / 收入 / 历史等其他维度的对冲信号)
3. 业务方可以怎么看 (规则阈值是否过严 · 是否要加补充条件)

## 输出格式

纯文本 · 中文 · 不超过 200 字 · 不输出 JSON · 不带前后缀。
"""


def _build_fp_user_prompt(fp: FalsePositive) -> str:
    feats_lines = []
    for k, v in fp.raw_features.items():
        feats_lines.append(f"- {format_for_business(k, v)}")

    return (
        f"## 误杀个案\n\n"
        f"**贷款 ID**: {fp.loan_id}\n"
        f"**命中规则**: {fp.hit_rule_id} · {fp.hit_rule_name} · 拒绝\n"
        f"**实际逾期天数**: {fp.label_value} (阈值 {fp.bad_threshold} · "
        f"<= 阈值视未逾期)\n\n"
        f"### 客户特征\n"
        + "\n".join(feats_lines) +
        "\n\n请给出可解释 reason."
    )


def _fallback_reason(fp: FalsePositive) -> str:
    """LLM 不可用时的最简 fallback · 仅事实 · 不做推理."""
    feats_str = ", ".join(
        f"{k}={v}" for k, v in fp.key_features.items()
    )
    return (
        f"该客户被规则 [{fp.hit_rule_id}] {fp.hit_rule_name} 拒绝 · "
        f"命中字段: {feats_str} · 实际逾期天数 {fp.label_value} "
        f"(<= {fp.bad_threshold} 视未逾期 · 属误杀) · "
        f"LLM 解释不可用 · 业务方需手动判断"
    )


def explain_false_positives(
    fps: list[FalsePositive],
    max_explain: int = 5,
    llm_caller=None,  # type: ignore[no-untyped-def]
) -> list[dict]:
    """对 max_explain 个 FP 跑 LLM 解释 · 其余仅事实输出.

    Args:
        fps: identify_false_positives 输出
        max_explain: 最多 LLM 跑几条 (cost 控)
        llm_caller: 可注入 (test 用 fake) · None 时建 LLMCaller(agent_id="riskctrl",
                    endpoint="/api/riskctrl/explain_fp")

    Returns:
        list[dict] · 每条含 loan_id / hit_rule_id / reason / reason_source
    """
    if not fps:
        return []

    # Lazy 构建 caller (避免 import 副作用 in test)
    caller = llm_caller
    if caller is None:
        try:
            from shared.llm_caller import LLMCaller
            caller = LLMCaller(
                agent_id="riskctrl",
                endpoint="/api/riskctrl/explain_fp",
            )
        except ImportError as e:
            logger.warning("shared.llm_caller import failed: %s", e)
            caller = None

    out: list[dict] = []
    for i, fp in enumerate(fps):
        base_record = asdict(fp)

        if i < max_explain and caller is not None:
            try:
                user_prompt = _build_fp_user_prompt(fp)
                # 走 simple_chat → str (走 fallback chain · audit 自动)
                reason_text = caller.simple_chat(
                    SYSTEM_PROMPT_FP_EXPLAIN, user_prompt,
                    temperature=0.3,
                )
                if reason_text and reason_text.strip():
                    base_record["reason"] = reason_text.strip()
                    base_record["reason_source"] = "llm"
                else:
                    base_record["reason"] = _fallback_reason(fp)
                    base_record["reason_source"] = "fallback"
            except (RuntimeError, ValueError, TypeError, OSError, KeyError) as e:
                logger.warning(
                    "LLM explain failed for loan %s: %s", fp.loan_id, e,
                )
                base_record["reason"] = _fallback_reason(fp)
                base_record["reason_source"] = "fallback_on_error"
        else:
            base_record["reason"] = _fallback_reason(fp)
            base_record["reason_source"] = "skipped_over_limit" if i >= max_explain else "no_llm"

        out.append(base_record)
    return out


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------


def format_fp_summary(explanations: list[dict]) -> str:
    """误杀解释 → markdown."""
    if not explanations:
        return "_未发现误杀 (规则拒绝且实际逾期 ≥ 阈值)_"

    lines = [
        f"### 误杀个案解释 (共 {len(explanations)} 条)",
        "",
    ]
    for exp in explanations:
        loan_id = exp.get("loan_id", "?")
        rule_id = exp.get("hit_rule_id", "?")
        rule_name = exp.get("hit_rule_name", "")
        reason = exp.get("reason", "(未生成)")
        source = exp.get("reason_source", "")
        source_tag = {
            "llm": "🤖 LLM",
            "fallback": "📋 事实",
            "fallback_on_error": "⚠️ Fallback",
            "skipped_over_limit": "⏭️ 跳过",
            "no_llm": "📋 无 LLM",
        }.get(source, source)
        lines.extend([
            f"#### {loan_id} · 命中 [{rule_id}] {rule_name} ({source_tag})",
            "",
            f"> {reason}",
            "",
        ])
    return "\n".join(lines)


__all__ = [
    "FalsePositive",
    "SYSTEM_PROMPT_FP_EXPLAIN",
    "explain_false_positives",
    "format_fp_summary",
    "identify_false_positives",
]
