# -*- coding: utf-8 -*-
"""FeatureExtractor — ReportJSON / PersonalProfile → 特征向量

对公：抽取约 60 个特征，分 5 类（financial / industry / operational / guarantee / external）
对私：抽取约 22 个评分卡变量，分 4 类（capacity / willingness / stability / collateral）

约定：特征 key 使用扁平化点号命名，如 "financial.debt_ratio"。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_AGENT_DIR = Path(__file__).parent
_BASELINE_PATH = _AGENT_DIR / "mock_data" / "industry_baselines_v2.json"


def _load_baselines() -> dict:
    try:
        with open(_BASELINE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("industries", {}) or {}
    except Exception:
        return {}


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        if not b:
            return default
        return a / b
    except Exception:
        return default


def _normalize_industry_code(industry_str: str) -> str:
    """'I65-互联网与相关服务' -> 'I65'"""
    if not industry_str:
        return "DEFAULT"
    head = industry_str.split("-")[0].strip()
    return head or "DEFAULT"


class FeatureExtractor:
    """特征抽取器（板块感知）"""

    def __init__(self):
        self.baselines = _load_baselines()

    def extract(self, profile: dict, segment: str) -> dict:
        if segment == "corporate":
            return self._extract_corporate(profile or {})
        return self._extract_retail(profile or {})

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

        # ---- financial.* ----
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

        request_amt = float(req.get("amount") or 0)
        term_months = int(req.get("term_months") or 12)

        debt_ratio = _safe_div(total_liab, total_assets)
        revenue_growth = _safe_div(revenue - revenue_prev, revenue_prev) if revenue_prev else 0
        net_margin = _safe_div(net_profit, revenue)
        ar_turnover_days = _safe_div(ar * 365, revenue) if revenue else 0
        current_assets_approx = ar + inv + max(ocf, 0)
        current_ratio = _safe_div(current_assets_approx + ocf, max(st_debt, 1))
        quick_ratio = _safe_div(current_assets_approx - inv, max(st_debt, 1))
        gross_margin = _safe_div(revenue - (revenue - ebitda), revenue) if revenue else 0
        # 估算毛利率差距
        gross_margin_gap = gross_margin - float(baseline.get("gross_margin_median", 0.25))
        consecutive_loss = (1 if net_profit < 0 else 0) + (1 if net_profit_prev < 0 else 0)
        request_to_netasset = _safe_div(request_amt, net_assets) if net_assets else 0
        cashflow_coverage = _safe_div(ocf, request_amt) if request_amt else 0

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
            "financial.short_term_borrowing": st_debt,
            "financial.ebitda": ebitda,
            "financial.consecutive_loss_years": consecutive_loss,
            "financial.request_to_netasset": request_to_netasset,
            "financial.accounts_receivable": ar,
        })

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
        except Exception:
            est_years = 3
        employee_count = int(profile.get("employee_count") or 0)
        features.update({
            "operational.established_years": est_years,
            "operational.employee_count": employee_count,
            "operational.revenue_scale": revenue,
            "operational.cashflow_coverage": cashflow_coverage,
            "operational.customer_concentration": float(rp.get("related_party_revenue_pct") or 0),
            "operational.supplier_concentration": 0.3,
            "operational.inventory_efficiency": _safe_div(revenue, inv) if inv else 8,
        })

        # ---- guarantee.* ----
        collateral_value = float(guar.get("collateral_value") or 0)
        collateral_type = (guar.get("collateral_type") or "").strip()
        has_collateral = 1 if collateral_value > 0 or guar.get("guarantor") else 0
        coverage_ratio = _safe_div(collateral_value, request_amt) if request_amt else 0
        volatile_types = ("股权", "应收账款", "存货")
        is_volatile = 1 if any(v in collateral_type for v in volatile_types) else 0
        guarantor = (guar.get("guarantor") or "")
        guarantor_strength = 70 if ("母公司" in guarantor or "集团" in guarantor) else 50
        if not guarantor:
            guarantor_strength = 30
        features.update({
            "guarantee.collateral_value": collateral_value,
            "guarantee.collateral_type": collateral_type,
            "guarantee.coverage_ratio": coverage_ratio,
            "guarantee.has_any_collateral": has_collateral,
            "guarantee.collateral_is_volatile": is_volatile,
            "guarantee.guarantor_strength_score": guarantor_strength,
            "guarantee.combination_completeness": 0.8 if guar.get("type") and "+" in guar.get("type") else 0.5,
        })

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
            "request.amount": request_amt,
            "request.term_months": term_months,
            "request.purpose": req.get("purpose", ""),
        })

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
