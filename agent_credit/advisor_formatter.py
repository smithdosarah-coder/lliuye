"""AdvisorFormatter — 决策意见格式化器（调 LLM）

对应 PRD 第 6.9 节。
对公：2 次 LLM 调用（决策说明 + 红线解释）
对私：0-1 次 LLM 调用（仅边界 / 红线命中时）
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

from shared.prompts.agent_helpers import build_credit_ssot_prompt
from .prompts import (
    CORPORATE_DECISION_USER,
    CORPORATE_REDLINE_USER,
    RETAIL_DECISION_USER,
    build_system_prompt,
)

# PB#2 · Codex 越权 4 audit (per docs/contracts/pb2-prompt-governance.md §2)
# Below LLM call sites store output as decision_reason text (truncated [:1500] / [:800]).
# No markdown-structure schema validation. fix-forward to PB#5 (frontend zod) or 续命 #4 (回测 case).
# LLM-OVERSTEP: agent_credit:advisor_formatter.py:~246 (corporate decision_reason · no schema)
# LLM-OVERSTEP: agent_credit:advisor_formatter.py:~359 (retail decision_reason · no schema)
# Note: decision/amount/term/rate are user-prompt INPUT (not LLM output) · 越权 1 误判 (Codex R1).
from .reason_codes import derive_top_reason_codes
from .risk_appetite_config import RiskAppetiteConfig


@dataclass
class DecisionAdvice:
    advice_id: str = ""
    segment: str = ""
    subject_name: str = ""
    decision_time: str = ""

    decision: str = "拒绝"         # 批准 / 有条件批准 / 拒绝
    approved_amount: float = 0     # 万元
    approved_term_months: int = 0
    interest_rate: float = 0.0
    rate_benchmark: str = ""

    composite_score: int = 0
    risk_grade: str = ""

    conditions: list = field(default_factory=list)
    red_line_hits: list = field(default_factory=list)          # list[dict]
    red_line_explanations: list = field(default_factory=list)  # list[dict]

    decision_reason: str = ""
    similar_cases_summary: str = ""

    top_reason_codes: list = field(default_factory=list)  # list[dict]

    features_snapshot: dict = field(default_factory=dict)
    scoring_snapshot: dict = field(default_factory=dict)
    amount_methods: dict = field(default_factory=dict)

    # BE2 (Phase B-3 · 2026-05-01) audit-grade evidence graph
    # Filled by DecisionEngine.run_stream() after `advising_done`.
    # Consumers (export_docx / Agent6 writeback) ignore unknown fields,
    # so empty dict is a safe default.
    decision_graph: dict = field(default_factory=dict)

    approval_section_text: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str)

    def to_agent6_writeback(self) -> dict:
        return {
            "target_section": "四、授信结论 - 审批意见",
            "anchor_pattern": "【审批意见】",
            "structured_fields": {
                "decision": self.decision,
                "approved_amount": self.approved_amount,
                "approved_term_months": self.approved_term_months,
                "interest_rate": self.interest_rate,
                "rate_benchmark": self.rate_benchmark,
                "risk_grade": self.risk_grade,
                "composite_score": self.composite_score,
                "conditions": list(self.conditions),
                "red_line_hits": [
                    {"rule_id": r.get("rule_id", ""), "severity": r.get("severity", "")}
                    for r in (self.red_line_hits or [])
                ],
            },
            "text": self.approval_section_text,
        }


# ---------------------------------------------------------------------------
# 确定性决策核心
# ---------------------------------------------------------------------------

def _decide_corporate(scoring, rule_hits, features, appetite: RiskAppetiteConfig):
    """返回 (decision, amount, term, rate, rate_benchmark, conditions)"""
    hard_hit = any(h.severity == "red" for h in rule_hits)
    soft_hits = [h for h in rule_hits if h.severity != "red"]

    requested = float(features.get("request.amount", 0) or 0)
    term = int(features.get("request.term_months", 12) or 12)
    amounts = scoring.amount_methods or {}
    valid = [v for v in amounts.values() if v and v > 0]
    suggested = min(valid) if valid else 0

    if hard_hit or scoring.risk_grade == "D":
        return ("拒绝", 0, 0, 0.0, "-", [])

    if scoring.risk_grade == "C" or len(soft_hits) >= 2:
        amount = min(requested, suggested) if suggested else requested * 0.6
        amount = round(amount, 0)
        benchmark = appetite.rate_tier_map.get(scoring.risk_grade, "LPR+200BP") or "LPR+200BP"
        rate = _parse_rate_benchmark(benchmark, appetite.lpr_base)
        conditions = [f"需满足红线豁免条件：{h.rule_name}" for h in soft_hits[:3]]
        conditions.append("半年内复查一次经营情况")
        return ("有条件批准", amount, term, rate, benchmark, conditions)

    # A/B
    if soft_hits:
        amount = min(requested, suggested) if suggested else requested
        conditions = [f"提供红线豁免材料：{h.rule_name}（{h.waiver_conditions[0] if h.waiver_conditions else '补充说明'}）"
                      for h in soft_hits[:2]]
        decision = "有条件批准"
    else:
        amount = min(requested, max(suggested, requested)) or requested
        conditions = []
        decision = "批准"
    amount = round(amount, 0)
    benchmark = appetite.rate_tier_map.get(scoring.risk_grade, "LPR+85BP") or "LPR+85BP"
    rate = _parse_rate_benchmark(benchmark, appetite.lpr_base)
    return (decision, amount, term, rate, benchmark, conditions)


def _parse_rate_benchmark(bench: str, lpr: float) -> float:
    if not bench:
        return round(lpr, 4)
    m = re.match(r"LPR\s*([+-])\s*(\d+)\s*BP", bench, re.IGNORECASE)
    if not m:
        return round(lpr, 4)
    sign = 1 if m.group(1) == "+" else -1
    bp = int(m.group(2))
    return round(lpr + sign * bp / 10000.0, 4)


def _decide_retail(scoring, rule_hits, features, appetite: RiskAppetiteConfig):
    hard_hit = any(h.severity == "red" for h in rule_hits)
    if hard_hit or scoring.grade == "拒绝":
        return ("拒绝", 0, 0, 0.0, "-", [])

    requested_yuan = float(features.get("request.amount", 0) or 0)
    requested_wan = requested_yuan / 10000.0
    term = int(features.get("request.term_months", 24) or 24)

    cap_wan = float(scoring.approved_limit_cap or 0)
    # 额外约束：LTV 70% / 月收入 × 20
    col_val_wan = (features.get("collateral.appraised_value", 0) or 0) / 10000
    monthly_income_wan = (features.get("capacity.monthly_income", 0) or 0) / 10000
    caps = [cap_wan]
    if col_val_wan > 0:
        caps.append(col_val_wan * 0.7)
    caps.append(monthly_income_wan * 20)

    max_allowed = min([c for c in caps if c > 0], default=cap_wan)
    amount_wan = min(requested_wan, max_allowed)

    if scoring.grade == "边界（人工复核）" or scoring.grade == "边界":
        decision = "有条件批准"
        conditions = ["建议人工复核", "追加共同借款人或调低额度"]
    elif rule_hits:
        decision = "有条件批准"
        conditions = [f"豁免条件：{h.rule_name}" for h in rule_hits[:2]]
    else:
        decision = "批准"
        conditions = []

    benchmark = scoring.rate_tier or appetite.rate_tier_map.get(scoring.grade, "LPR+20BP") or "LPR+20BP"
    rate = _parse_rate_benchmark(benchmark, appetite.lpr_base)
    return (decision, round(amount_wan, 1), term, rate, benchmark, conditions)


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

class AdvisorFormatter:
    def __init__(self, llm_chat_func=None, llm_json_func=None,
                 appetite: RiskAppetiteConfig | None = None):
        self.llm_chat = llm_chat_func
        self.llm_json = llm_json_func
        self.appetite = appetite or RiskAppetiteConfig.default("corporate")

    def format(self, segment: str, profile: dict, features: dict,
               scoring, rule_hits, cases) -> DecisionAdvice:
        if segment == "corporate":
            return self._format_corporate(profile, features, scoring, rule_hits, cases)
        return self._format_retail(profile, features, scoring, rule_hits, cases)

    # ---- 对公 ----
    def _format_corporate(self, profile, features, scoring, rule_hits, cases) -> DecisionAdvice:
        appetite = self.appetite if self.appetite.segment == "corporate" \
            else RiskAppetiteConfig.default("corporate")

        decision, amount, term, rate, benchmark, conditions = _decide_corporate(
            scoring, rule_hits, features, appetite)

        subject_name = profile.get("company_name", "") or features.get("meta.company_name", "")
        cases_summary = _summarize_cases(cases)

        # LLM 1: 决策说明
        decision_reason = self._template_reason_corporate(
            subject_name, scoring, rule_hits, decision, amount, term)
        if self.llm_chat and decision != "拒绝":
            try:
                user_msg = CORPORATE_DECISION_USER.format(
                    company_summary=_corporate_summary(profile, features),
                    requested_amount=features.get("request.amount", 0),
                    requested_term=features.get("request.term_months", 12),
                    purpose=features.get("request.purpose", "") or "—",
                    financial_score=scoring.financial_score,
                    industry_score=scoring.industry_score,
                    operational_score=scoring.operational_score,
                    guarantee_score=scoring.guarantee_score,
                    composite_score=scoring.composite_score,
                    risk_grade=scoring.risk_grade,
                    red_line_count=len(rule_hits),
                    red_line_detail=_format_redlines_for_prompt(rule_hits),
                    revenue_method=scoring.amount_methods.get("revenue_method", 0),
                    netasset_method=scoring.amount_methods.get("netasset_method", 0),
                    cashflow_method=scoring.amount_methods.get("cashflow_method", 0),
                    collateral_method=scoring.amount_methods.get("collateral_method", 0),
                    suggested_amount_range=f"{amount}",
                    similar_cases_summary=cases_summary,
                    decision=decision,
                    approved_amount=amount,
                    approved_term=term,
                    interest_rate=f"{rate*100:.2f}%",
                    rate_benchmark=benchmark,
                    conditions="；".join(conditions) if conditions else "无",
                )
                # PB#2 SSOT · base = build_credit_ssot_prompt + few-shot 注入
                ssot_base = build_credit_ssot_prompt(
                    task_type="corporate_decision_explain",
                    schema_hint=(
                        "决策解释 markdown · 5 节 (客户基本情况/评分结论/决策说明/"
                        "额度利率依据/附加条件) · ≤ 500 字 · "
                        "user prompt 中 decision/amount/term/rate 为固定输入 · 不得改动只解释"
                    ),
                )
                llm_out = self.llm_chat(build_system_prompt(ssot_base), user_msg)
                if llm_out and len(llm_out) > 40:
                    decision_reason = llm_out[:1500]
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError):
                pass

        # LLM 2: 红线解释
        red_line_explanations: list[dict] = []
        if rule_hits and self.llm_json:
            try:
                user_msg = CORPORATE_REDLINE_USER.format(
                    company_summary=_corporate_summary(profile, features),
                    hit_rules_detail=_format_redlines_for_prompt(rule_hits),
                )
                # PB#2 SSOT · 红线解释走 helper (无 few-shot · 严格 schema)
                ssot_redline = build_credit_ssot_prompt(
                    task_type="corporate_redline_explain",
                    schema_hint=(
                        '[{"rule_id": str, "explanation": str (≤ 150 字 · 必引数字), '
                        '"severity": "高/中/低", "waiver_advice": str}]'
                    ),
                )
                raw = self.llm_json(ssot_redline, user_msg)
                if isinstance(raw, list):
                    red_line_explanations = raw
                elif isinstance(raw, dict) and "rules" in raw:
                    red_line_explanations = raw.get("rules", [])
            except (RuntimeError, ValueError, TypeError, KeyError, AttributeError):
                red_line_explanations = []
        if not red_line_explanations:
            red_line_explanations = [{
                "rule_id": h.rule_id,
                "explanation": h.description
                    + f"（当前值 {h.actual_value}，阈值 {h.threshold}）",
                "severity": h.severity,
                "waiver_advice": "；".join(h.waiver_conditions) if h.waiver_conditions else "不可豁免",
            } for h in rule_hits]

        features_snapshot = {k: v for k, v in features.items()
                             if not k.startswith("chapters") and not k.startswith("_")}
        top_reason_codes = derive_top_reason_codes(
            segment="corporate",
            decision=decision,
            rule_hits=rule_hits,
            features=features_snapshot,
            top_n=5,
        )
        advice = DecisionAdvice(
            advice_id=str(uuid.uuid4())[:12],
            segment="corporate",
            subject_name=subject_name,
            decision_time=datetime.now().isoformat(timespec="seconds"),
            decision=decision,
            approved_amount=amount,
            approved_term_months=term,
            interest_rate=rate,
            rate_benchmark=benchmark,
            composite_score=scoring.composite_score,
            risk_grade=scoring.risk_grade,
            conditions=conditions,
            red_line_hits=[h.to_dict() for h in rule_hits],
            red_line_explanations=red_line_explanations,
            decision_reason=decision_reason,
            similar_cases_summary=cases_summary,
            top_reason_codes=top_reason_codes,
            features_snapshot=features_snapshot,
            scoring_snapshot=scoring.to_dict(),
            amount_methods=scoring.amount_methods or {},
        )
        advice.approval_section_text = _build_writeback_text_corporate(advice)
        return advice

    def _template_reason_corporate(self, name, scoring, rule_hits, decision, amount, term) -> str:
        lines = [
            f"企业 {name} 综合评分 {scoring.composite_score} 分（{scoring.risk_grade} 级）。",
            f"四维评分：财务 {scoring.financial_score} / 行业 {scoring.industry_score} / "
            f"经营 {scoring.operational_score} / 担保 {scoring.guarantee_score}。",
        ]
        if rule_hits:
            lines.append(
                f"触发 {len(rule_hits)} 条红线："
                + "、".join(h.rule_name for h in rule_hits[:3]) + "。"
            )
        if decision == "拒绝":
            lines.append("结论：建议拒绝本次授信申请。")
        else:
            lines.append(f"结论：{decision}，建议额度 {amount} 万元，期限 {term} 个月。")
        return "\n".join(lines)

    # ---- 对私 ----
    def _format_retail(self, profile, features, scoring, rule_hits, cases) -> DecisionAdvice:
        appetite = self.appetite if self.appetite.segment == "retail" \
            else RiskAppetiteConfig.default("retail")

        decision, amount, term, rate, benchmark, conditions = _decide_retail(
            scoring, rule_hits, features, appetite)

        subject_name = profile.get("name", "") or features.get("meta.name", "")
        cases_summary = _summarize_cases(cases)

        # 对私：边界 / 红线 → LLM；否则走模板
        is_border = "边界" in (scoring.grade or "")
        decision_reason = self._template_reason_retail(
            subject_name, scoring, rule_hits, decision, amount, term)
        if (is_border or rule_hits) and self.llm_chat and decision != "拒绝":
            try:
                user_msg = RETAIL_DECISION_USER.format(
                    customer_summary=_retail_summary(profile, features),
                    fico_score=scoring.fico_score,
                    grade=scoring.grade,
                    repayment_capacity=scoring.category_scores.get("repayment_capacity", 0),
                    repayment_willingness=scoring.category_scores.get("repayment_willingness", 0),
                    stability=scoring.category_scores.get("stability", 0),
                    collateral=scoring.category_scores.get("collateral", 0),
                    count=len(rule_hits),
                    red_line_detail=_format_redlines_for_prompt(rule_hits) or "无",
                    decision=decision,
                    approved_amount=amount,
                    interest_rate=f"{rate*100:.2f}%",
                )
                # PB#2 SSOT · few-shot 同接零售决策路径
                ssot_base = build_credit_ssot_prompt(
                    task_type="retail_decision_explain",
                    schema_hint=(
                        "决策说明文字 · 一句话结论 + 主要理由 (2-3 点) + 附加说明 · "
                        "≤ 200 字 · 面向个贷岗 · 不用对公术语 · "
                        "user prompt 中 decision/amount/rate 为固定输入 · 不得改动"
                    ),
                )
                llm_out = self.llm_chat(build_system_prompt(ssot_base), user_msg)
                if llm_out and len(llm_out) > 30:
                    decision_reason = llm_out[:800]
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError):
                pass

        features_snapshot = dict(features)
        top_reason_codes = derive_top_reason_codes(
            segment="retail",
            decision=decision,
            rule_hits=rule_hits,
            features=features_snapshot,
            top_n=5,
        )
        advice = DecisionAdvice(
            advice_id=str(uuid.uuid4())[:12],
            segment="retail",
            subject_name=subject_name,
            decision_time=datetime.now().isoformat(timespec="seconds"),
            decision=decision,
            approved_amount=amount,
            approved_term_months=term,
            interest_rate=rate,
            rate_benchmark=benchmark,
            composite_score=scoring.fico_score,
            risk_grade=scoring.grade,
            conditions=conditions,
            red_line_hits=[h.to_dict() for h in rule_hits],
            red_line_explanations=[{
                "rule_id": h.rule_id,
                "explanation": h.description
                    + f"（当前 {h.actual_value}，阈值 {h.threshold}）",
                "severity": h.severity,
                "waiver_advice": "；".join(h.waiver_conditions) if h.waiver_conditions else "不可豁免",
            } for h in rule_hits],
            decision_reason=decision_reason,
            similar_cases_summary=cases_summary,
            top_reason_codes=top_reason_codes,
            features_snapshot=features_snapshot,
            scoring_snapshot=scoring.to_dict(),
            amount_methods={},
        )
        advice.approval_section_text = _build_writeback_text_retail(advice)
        return advice

    def _template_reason_retail(self, name, scoring, rule_hits, decision, amount, term) -> str:
        lines = [
            f"{name} 个人信用评分 {scoring.fico_score}，档位 {scoring.grade}。",
            f"大类得分：偿债 {scoring.category_scores.get('repayment_capacity', 0)} / "
            f"意愿 {scoring.category_scores.get('repayment_willingness', 0)} / "
            f"稳定性 {scoring.category_scores.get('stability', 0)} / "
            f"抵押 {scoring.category_scores.get('collateral', 0)}。",
        ]
        if rule_hits:
            lines.append(
                "触发红线：" + "、".join(h.rule_name for h in rule_hits[:3]) + "。"
            )
        if decision == "拒绝":
            lines.append("结论：建议拒绝本次申请。")
        else:
            lines.append(f"结论：{decision}，额度 {amount} 万元，期限 {term} 个月。")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 辅助：摘要 / 回写文本
# ---------------------------------------------------------------------------

def _corporate_summary(profile: dict, features: dict) -> str:
    lines = [
        f"企业: {profile.get('company_name', '-')}",
        f"行业: {profile.get('industry', '-')}",
        f"成立: {profile.get('establishment_date', '-')}",
        f"员工: {profile.get('employee_count', 0)} 人",
        f"最近营收: {features.get('financial.revenue', 0)} 万元",
        f"净资产: {features.get('financial.net_assets', 0)} 万元",
        f"资产负债率: {features.get('financial.debt_ratio', 0):.1%}",
        f"净利率: {features.get('financial.net_margin', 0):.1%}",
        f"担保: {profile.get('guarantee_info', {}).get('type', '-')}",
    ]
    # §3.1 反模式修复：把 financial_analyzer.format_for_prompt 块原文挂上去，
    # LLM 直接引用确定性比率/同比/异常项，禁止再算。
    block = features.get("_financial_prompt_block")
    if block:
        lines.append("")
        lines.append(block)
    return "\n".join(lines)


def _retail_summary(profile: dict, features: dict) -> str:
    lines = [
        f"姓名: {profile.get('name', '-')}",
        f"年龄: {profile.get('age', 0)}",
        f"职业: {profile.get('occupation', '-')}（{profile.get('business_type', '')}）",
        f"月收入: {profile.get('monthly_income', 0)} 元（{profile.get('monthly_income_stability', '')}）",
        f"抵押物: {profile.get('collateral', {}).get('type', '无')}",
        f"申请: {features.get('request.amount', 0)/10000:.0f} 万 / {features.get('request.term_months', 0)} 月",
    ]
    return "\n".join(lines)


def _summarize_cases(cases) -> str:
    if not cases:
        return "无相似案例"
    parts = []
    for c in cases[:3]:
        parts.append(
            f"{c.company_name}(相似度 {c.similarity*100:.0f}% / {c.decision})"
        )
    return "；".join(parts)


def _format_redlines_for_prompt(rule_hits) -> str:
    if not rule_hits:
        return "无"
    lines = []
    sev_label = {"red": "红灯-硬红线", "yellow": "黄灯-软告警", "green": "绿灯-信息提示"}
    for h in rule_hits:
        lines.append(
            f"- {h.rule_id} {h.rule_name}: 实际值 {h.actual_value}，阈值 {h.threshold}，"
            f"严重度 {sev_label.get(h.severity, h.severity)}。{h.description}"
        )
    return "\n".join(lines)


def _build_writeback_text_corporate(a: DecisionAdvice) -> str:
    lines = [
        "## 四、授信结论",
        "",
        "### 审批意见",
        "",
        f"- 结论：{a.decision}",
        f"- 综合评分：{a.composite_score}（{a.risk_grade} 级）",
        f"- 建议额度：{a.approved_amount} 万元",
        f"- 期限：{a.approved_term_months} 个月",
        f"- 利率：{a.interest_rate*100:.2f}%（{a.rate_benchmark}）",
        "",
        f"决策说明：{a.decision_reason}",
    ]
    if a.conditions:
        lines.append("")
        lines.append("附加条件：")
        for c in a.conditions:
            lines.append(f"  - {c}")
    if a.red_line_hits:
        lines.append("")
        lines.append(f"触发红线（{len(a.red_line_hits)} 条）：")
        for h in a.red_line_hits:
            lines.append(f"  - {h.get('rule_name')}（实际 {h.get('actual_value')}，阈值 {h.get('threshold')}）")
    return "\n".join(lines)


def _build_writeback_text_retail(a: DecisionAdvice) -> str:
    lines = [
        "## 审批意见（零售）",
        "",
        f"- 结论：{a.decision}",
        f"- 信用评分：{a.composite_score}（{a.risk_grade}）",
        f"- 建议额度：{a.approved_amount} 万元",
        f"- 期限：{a.approved_term_months} 个月",
        f"- 利率：{a.interest_rate*100:.2f}%（{a.rate_benchmark}）",
        "",
        f"决策说明：{a.decision_reason}",
    ]
    if a.conditions:
        lines.append("")
        for c in a.conditions:
            lines.append(f"- {c}")
    return "\n".join(lines)
