# -*- coding: utf-8 -*-
"""FeatureExtractor — ReportJSON / PersonalProfile → 特征向量

对公：抽取约 60 个特征，分 5 类（financial / industry / operational / guarantee / external）
对私：抽取约 22 个评分卡变量，分 4 类（capacity / willingness / stability / collateral）

约定：特征 key 使用扁平化点号命名，如 "financial.debt_ratio"。

§3.1 反模式修复（Product Hardening Batch 1 · Task A）：
对公财务比率（debt_ratio / net_margin / current_ratio / 应收周转天数 等）一律
路由 financial_analyzer.FinancialAnalyzer.compute_indicators 计算，禁止本模块
内重复实现。下游 scoring_model_corporate / advisor_formatter 同样消费这一计算
结果（feature dict + format_for_prompt 文本），确保 Agent3 与 Agent6 在同一组
报表上得到完全一致的比率。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_AGENT_DIR = Path(__file__).parent
_BASELINE_PATH = _AGENT_DIR / "mock_data" / "industry_baselines_v2.json"

_PROJECT_ROOT = str(_AGENT_DIR.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from financial_analyzer import (  # noqa: E402
    FinancialAnalyzer,
    FinancialIndicators,
    FinancialStatements,
    PeriodValue,
)


def _load_baselines() -> dict:
    try:
        with open(_BASELINE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("industries", {}) or {}
    except (OSError, json.JSONDecodeError, ValueError, TypeError, AttributeError):
        return {}


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        if not b:
            return default
        return a / b
    except (ZeroDivisionError, TypeError, ValueError):
        return default


def _normalize_industry_code(industry_str: str) -> str:
    """'I65-互联网与相关服务' -> 'I65'"""
    if not industry_str:
        return "DEFAULT"
    head = industry_str.split("-")[0].strip()
    return head or "DEFAULT"


# ----------------------------------------------------------------------
# §3.1 反模式修复：profile.financial_anchors → FinancialIndicators
# ----------------------------------------------------------------------

# financial_anchors 的口径与 financial_analyzer 解析 xlsx 后的 raw 表保持一致：
# 期末值/当期累计是"元"。但 mock 数据 / Agent6 ReportJSON 通常已经是"万元"。
# 这里统一约定：anchors 的 *_latest / *_prev / total_* / accounts_receivable
# 等量级字段都按"万元"传入，由本模块统一 ×10000 拉回"元"喂给 financial_analyzer
# （后者对外输出已按单位格式化，无需额外换算）。

_BS_FIELDS_WAN: tuple[tuple[str, str, str], ...] = (
    # (anchor_key, balance_sheet_subject, anchors_unit)
    ("total_assets", "资产总计", "万元"),
    ("total_liabilities", "负债合计", "万元"),
    ("net_assets", "所有者权益合计", "万元"),
    ("accounts_receivable", "应收账款", "万元"),
    ("inventory", "存货", "万元"),
    ("short_term_borrowing", "短期借款", "万元"),
)

_IS_FIELDS_WAN: tuple[tuple[str, str, str, str], ...] = (
    # (latest_key, prev_key, statement_subject, anchors_unit)
    ("revenue_latest", "revenue_prev", "营业收入", "万元"),
    ("net_profit_latest", "net_profit_prev", "净利润", "万元"),
)


def _wan_to_yuan(v) -> float | None:
    if v in (None, "") or v == 0:
        return float(v) * 10000.0 if v == 0 else None
    try:
        return float(v) * 10000.0
    except (TypeError, ValueError):
        return None


def _anchors_to_indicators(fin_anchors: dict) -> FinancialIndicators:
    """把 ReportJSON.financial_anchors（万元口径）拼成 FinancialStatements
    并交给 FinancialAnalyzer 计算 FinancialIndicators。
    所有比率/同比/异常均由 financial_analyzer 一处产出。
    """
    fin = fin_anchors or {}
    stmts = FinancialStatements(source_file="agent_credit.feature_extractor::anchors")

    for anchor_key, subj, _unit in _BS_FIELDS_WAN:
        cur = _wan_to_yuan(fin.get(anchor_key))
        if cur is None:
            continue
        stmts.balance_sheet[subj] = PeriodValue(
            current=cur, previous=None, unit="万元",
            current_label="当期", previous_label="上期",
            compare_caption="较年初",
        )

    # 流动资产/流动负债缺直接字段时，给 financial_analyzer 留空 → 流动比率自然
    # 退化为 None，由下游 fallback；不要在本模块自算 flow ratio。

    for cur_key, prev_key, subj, _unit in _IS_FIELDS_WAN:
        cur = _wan_to_yuan(fin.get(cur_key))
        prev = _wan_to_yuan(fin.get(prev_key))
        if cur is None and prev is None:
            continue
        stmts.income_statement[subj] = PeriodValue(
            current=cur, previous=prev, unit="万元",
            current_label="当期", previous_label="上期",
            compare_caption="同比",
        )

    # 现金流：anchors 提供 operating_cash_flow（万元）单期
    ocf_yuan = _wan_to_yuan(fin.get("operating_cash_flow"))
    if ocf_yuan is not None:
        stmts.cash_flow["经营活动产生的现金流量净额"] = PeriodValue(
            current=ocf_yuan, previous=None, unit="万元",
            current_label="当期", previous_label="",
        )

    analyzer = FinancialAnalyzer()
    indicators = analyzer.compute_indicators(stmts)
    indicators.anomalies = analyzer.detect_anomalies(indicators)
    indicators.trend_labels = analyzer.summarize_trends(indicators)
    return indicators


def _pct_to_decimal(pv: PeriodValue) -> float:
    """financial_analyzer 输出的百分比指标（unit='%'）回拉成小数喂评分曲线。"""
    if pv is None or pv.current is None:
        return 0.0
    return pv.current / 100.0


def _yoy_pct_to_decimal(pv: PeriodValue) -> float:
    if pv is None or pv.yoy_pct is None:
        return 0.0
    return pv.yoy_pct / 100.0


def _ratio_value(pv: PeriodValue) -> float:
    """流动/速动比率(unit='倍')、应收周转天数(unit='天')等直接量纲指标。"""
    if pv is None or pv.current is None:
        return 0.0
    return float(pv.current)


class FeatureExtractor:
    """特征抽取器（板块感知）"""

    def __init__(self):
        self.baselines = _load_baselines()

    def extract(self, profile: dict, segment: str) -> dict:
        if segment == "corporate":
            features = self._extract_corporate(profile or {})
        else:
            features = self._extract_retail(profile or {})
        # 增强（可选；失败优雅降级，不影响主流程）— wire enterprise_info + akshare
        try:
            from .profile_enhancer import enhance_enterprise_profile
            enriched, evidence = enhance_enterprise_profile(profile or {})
            for k, v in enriched.items():
                features[f"enriched.{k}"] = v
            if evidence:
                features["enriched._evidence"] = evidence  # 供 QC / UI 审计
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
            pass
        return features

    # ------------------------------------------------------------------
    # 对公
    # ------------------------------------------------------------------

    def _extract_corporate(self, profile: dict) -> dict:
        fin = profile.get("financial_anchors", {}) or {}
        guar = profile.get("guarantee_info", {}) or {}
        rp = profile.get("related_party_info", {}) or {}
        req = profile.get("request", {}) or {}
        existing = profile.get("existing_credit", {}) or {}

        industry_code = _normalize_industry_code(profile.get("industry", ""))
        baseline = self.baselines.get(industry_code) or self.baselines.get("DEFAULT") or {}

        features: dict[str, Any] = {}

        # 量纲：anchors 一律按"万元"输入，对外保留原值；财务比率走 financial_analyzer。
        revenue = float(fin.get("revenue_latest") or 0)
        revenue_prev = float(fin.get("revenue_prev") or 0)
        net_profit = float(fin.get("net_profit_latest") or 0)
        net_profit_prev = float(fin.get("net_profit_prev") or 0)
        total_assets = float(fin.get("total_assets") or 0)
        total_liab = float(fin.get("total_liabilities") or 0)
        net_assets = float(fin.get("net_assets") or 0) or max(total_assets - total_liab, 0)
        ar = float(fin.get("accounts_receivable") or 0)
        inv = float(fin.get("inventory") or 0)
        ocf = float(fin.get("operating_cash_flow") or 0)
        st_debt = float(fin.get("short_term_borrowing") or 0)
        ebitda = float(fin.get("ebitda") or 0)

        raw_request_amt = req.get("amount")
        request_amt = (
            float(raw_request_amt)
            if raw_request_amt not in (None, "")
            else None
        )
        term_months = int(req.get("term_months") or 12)

        # ---- §3.1 反模式修复：所有比率走 financial_analyzer ----
        indicators = _anchors_to_indicators(fin)
        debt_ratio = _pct_to_decimal(indicators.debt_to_asset_ratio)
        revenue_growth = _yoy_pct_to_decimal(indicators.revenue)
        net_margin = _pct_to_decimal(indicators.net_margin)
        gross_margin = _pct_to_decimal(indicators.gross_margin)
        ar_turnover_days = _ratio_value(indicators.ar_turnover_days)
        current_ratio = _ratio_value(indicators.current_ratio)
        quick_ratio = _ratio_value(indicators.quick_ratio)
        # OCF/Revenue 单点派生（曾散落在 scoring_model_corporate._score_financial 内）
        ocf_to_revenue = (
            indicators.operating_cf_net / indicators.revenue.current
            if indicators.operating_cf_net is not None and indicators.revenue.current
            else 0.0
        )

        gross_margin_gap = gross_margin - float(baseline.get("gross_margin_median", 0.25))
        consecutive_loss = (1 if net_profit < 0 else 0) + (1 if net_profit_prev < 0 else 0)
        # 同一份 indicators 下游 advisor_formatter 直接消费，避免重复构造
        try:
            from financial_analyzer import FinancialAnalyzer as _FA
            financial_prompt_block = _FA().format_for_prompt(indicators)
        except (RuntimeError, ValueError, TypeError, AttributeError, ImportError):
            financial_prompt_block = ""

        features.update({
            "financial.revenue": revenue,
            "financial.revenue_prev": revenue_prev,
            "financial.net_profit": net_profit,
            "financial.total_assets": total_assets,
            "financial.total_liabilities": total_liab,
            "financial.net_assets": net_assets,
            "financial.debt_ratio": debt_ratio,
            "financial.revenue_growth": revenue_growth,
            "financial.net_margin": net_margin,
            "financial.gross_margin": gross_margin,
            "financial.gross_margin_gap": gross_margin_gap,
            "financial.ar_turnover_days": ar_turnover_days,
            "financial.current_ratio": current_ratio,
            "financial.quick_ratio": quick_ratio,
            "financial.operating_cash_flow": ocf,
            "financial.ocf_to_revenue": ocf_to_revenue,
            "financial.short_term_borrowing": st_debt,
            "financial.ebitda": ebitda,
            "financial.consecutive_loss_years": consecutive_loss,
            "financial.accounts_receivable": ar,
            # 下划线前缀：内部传递给 advisor_formatter，不进 features_snapshot
            "_financial_prompt_block": financial_prompt_block,
        })
        if request_amt is not None:
            features["financial.request_to_netasset"] = (
                _safe_div(request_amt, net_assets) if net_assets else 0
            )

        # ---- industry.* ----
        features.update({
            "industry.code": industry_code,
            "industry.name": baseline.get("name", ""),
            "industry.prosperity_index": float(baseline.get("prosperity_index", 60)),
            "industry.cyclicality": baseline.get("cyclicality", "medium"),
            "industry.policy_sensitivity": float(baseline.get("policy_sensitivity", 0.4)),
            "industry.in_blacklist": int(baseline.get("in_blacklist", 0)),
            "industry.debt_ratio_median": float(baseline.get("debt_ratio_median", 0.55)),
            "industry.net_margin_median": float(baseline.get("net_margin_median", 0.05)),
            "industry.revenue_growth_median": float(baseline.get("revenue_growth_median", 0.08)),
            "industry.ar_turnover_days_median": float(baseline.get("ar_turnover_days_median", 90)),
        })

        # ---- operational.* ----
        est_date = (profile.get("establishment_date") or "")[:4]
        try:
            est_years = max(0, 2026 - int(est_date)) if est_date.isdigit() else 3
        except (ValueError, TypeError):
            est_years = 3
        raw_employee_count = profile.get("employee_count")
        employee_count = (
            int(raw_employee_count)
            if raw_employee_count not in (None, "")
            else None
        )
        features.update({
            "operational.established_years": est_years,
            "operational.employee_count": employee_count,
            "operational.revenue_scale": revenue,
            "operational.customer_concentration": float(rp.get("related_party_revenue_pct") or 0),
            "operational.supplier_concentration": 0.3,
            "operational.inventory_efficiency": _safe_div(revenue, inv) if inv else 8,
        })
        if request_amt is not None:
            features["operational.cashflow_coverage"] = (
                _safe_div(ocf, request_amt) if request_amt else 0
            )

        # ---- guarantee.* ----
        collateral_value = float(guar.get("collateral_value") or 0)
        collateral_type = (guar.get("collateral_type") or "").strip()
        has_collateral = 1 if collateral_value > 0 or guar.get("guarantor") else 0
        volatile_types = ("股权", "应收账款", "存货")
        is_volatile = 1 if any(v in collateral_type for v in volatile_types) else 0
        guarantor = (guar.get("guarantor") or "")
        guarantor_strength = 70 if ("母公司" in guarantor or "集团" in guarantor) else 50
        if not guarantor:
            guarantor_strength = 30
        features.update({
            "guarantee.collateral_value": collateral_value,
            "guarantee.collateral_type": collateral_type,
            "guarantee.has_any_collateral": has_collateral,
            "guarantee.collateral_is_volatile": is_volatile,
            "guarantee.guarantor_strength_score": guarantor_strength,
            "guarantee.combination_completeness": 0.8 if guar.get("type") and "+" in guar.get("type") else 0.5,
        })
        if request_amt is not None:
            features["guarantee.coverage_ratio"] = (
                _safe_div(collateral_value, request_amt) if request_amt else 0
            )

        # ---- external.* ----
        overdue_hist = (existing.get("overdue_history") or "").strip()
        serious_overdue = 1 if ("M3" in overdue_hist or "M6" in overdue_hist) else 0
        features.update({
            "external.related_party_pct": float(rp.get("related_party_revenue_pct") or 0),
            "external.related_party_desc": rp.get("related_party_txn_desc", ""),
            "external.tax_rating": profile.get("tax_rating", ""),
            "external.tax_abnormal": 1 if profile.get("tax_rating") == "D" else 0,
            "external.has_industrial_abnormal": 0,
            "external.litigation_count": 0,
            "external.env_penalty_count": 0,
            "external.controller_pledge_ratio": 0.0,
            "external.serious_overdue_count": serious_overdue,
            "external.in_dishonest_list": 0,
            "external.aml_flag": 0,
        })

        # ---- request.* ----
        features.update({
            "request.term_months": term_months,
            "request.purpose": req.get("purpose", ""),
        })
        if request_amt is not None:
            features["request.amount"] = request_amt

        # ---- meta ----
        features["meta.company_name"] = profile.get("company_name", "")
        features["meta.industry_code"] = industry_code

        return features

    # ------------------------------------------------------------------
    # 对私
    # ------------------------------------------------------------------

    def _extract_retail(self, profile: dict) -> dict:
        cr = profile.get("credit_report", {}) or {}
        bs = profile.get("bank_statement", {}) or {}
        ss = profile.get("social_security", {}) or {}
        col = profile.get("collateral", {}) or {}
        res = profile.get("residence", {}) or {}
        req = profile.get("request", {}) or {}

        monthly_income = float(profile.get("monthly_income") or 0)
        request_amount = float(req.get("amount") or 0)
        term_months = int(req.get("term_months") or 12)

        # 估算 DTI: 本次贷款月还款 / 月收入（简化等额本息）
        # 月还款近似 = amount * (rate/12 + 1/term)
        rate_est = 0.06
        monthly_pay = (request_amount * (rate_est / 12 + 1 / max(term_months, 1)))
        dti_ratio = _safe_div(monthly_pay, monthly_income)

        avg_balance = float(bs.get("avg_balance_6m") or 0)
        cash_surplus = float(bs.get("monthly_inflow_avg") or 0) - float(bs.get("monthly_outflow_avg") or 0)

        # 征信严重度：M3=3, M6+=4, 其他 1-2
        overdue = (cr.get("overdue_history") or "无")
        if isinstance(overdue, list):
            overdue = overdue[0] if overdue else "无"
        severity_map = {"无": 0, "M1_once": 1, "M2_once": 2, "M3_once": 3, "M6+": 4}
        overdue_severity = severity_map.get(overdue, 0)

        ltv_val = float(col.get("ltv") or 0)
        if ltv_val == 0 and col.get("appraised_value"):
            ltv_val = _safe_div(request_amount, float(col.get("appraised_value") or 1))

        features: dict[str, Any] = {}

        # capacity.*
        features.update({
            "capacity.monthly_income": monthly_income,
            "capacity.monthly_income_stability": profile.get("monthly_income_stability", ""),
            "capacity.dti_ratio": dti_ratio,
            "capacity.avg_balance_6m": avg_balance,
            "capacity.cash_surplus": cash_surplus,
            "capacity.monthly_repay_capacity": _safe_div(monthly_income, max(monthly_pay, 1)) - 1,
            "capacity.unstable_and_no_collateral": 1 if (
                profile.get("monthly_income_stability") in ("fluctuating", "seasonal")
                and (col.get("type", "无") == "无")
            ) else 0,
        })

        # credit.* / willingness.*
        features.update({
            "credit.overdue_history": overdue,
            "credit.overdue_severity": overdue_severity,
            "credit.query_count_24m": int(cr.get("query_count_24m") or 0),
            "credit.card_utilization": float(cr.get("credit_card_utilization") or 0),
            "credit.current_loans_count": int(cr.get("current_loans_count") or 0),
            "credit.current_credit_cards": int(cr.get("current_credit_cards") or 0),
            "credit.guarantee_count": int(cr.get("guarantee_count") or 0),
            "credit.account_age_years": float(cr.get("account_age_years") or 0),
        })

        # stability.*
        age = int(profile.get("age") or 0)
        features.update({
            "stability.age": age,
            "stability.age_out_of_range": 1 if (age < 22 or age > 65) else 0,
            "stability.years_in_job": int(profile.get("years_in_current_job") or 0),
            "stability.years_at_address": int(res.get("years_at_address") or 0),
            "stability.marital_status": profile.get("marital_status", ""),
            "stability.education": profile.get("education", ""),
            "stability.housing_type": res.get("housing_type", ""),
            "stability.social_security_months": int(ss.get("months_paid") or 0),
        })

        # collateral.*
        features.update({
            "collateral.type": col.get("type", "无"),
            "collateral.appraised_value": float(col.get("appraised_value") or 0),
            "collateral.ltv": ltv_val,
            "collateral.mortgage_count": int(col.get("mortgage_count") or 0),
            "collateral.title_verified": 1 if col.get("title_verified") else 0,
            "collateral.valuation_source": col.get("valuation_source", ""),
        })

        # compliance.*
        purpose = (req.get("purpose") or "").lower()
        blacklist_keywords = ("炒股", "证券", "炒房", "购房首付", "博彩")
        features.update({
            "compliance.purpose_blacklist": 1 if any(k in purpose for k in blacklist_keywords) else 0,
            "compliance.amount_over_tier": 0,  # 由 rule engine 运行时设定
            "compliance.fraud_flag": 0,
        })

        # request.*
        features.update({
            "request.amount": request_amount,
            "request.term_months": term_months,
            "request.purpose": req.get("purpose", ""),
        })

        # meta
        features["meta.name"] = profile.get("name", "")
        features["meta.occupation"] = profile.get("occupation", "")

        return features
