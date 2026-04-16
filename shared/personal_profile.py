# -*- coding: utf-8 -*-
"""个人画像 Pydantic 模型 — Agent3 对私板块的标准载体

对应 PRD v2.0 第 7.1.2 节。承载个人申请人的身份、职业、征信、流水、
社保公积金、抵押、居住、申请等信息，供对私决策流水线消费。
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PersonalProfile(BaseModel):
    """个人画像标准模型（对私）"""

    # ---- 身份信息 ----
    name: str = ""
    id_card_tail: str = ""          # 脱敏（仅后 4 位）
    age: int = 0
    gender: str = ""                # 男/女
    marital_status: str = ""        # 已婚/未婚/离异
    education: str = ""             # 大专/本科/硕士/初中/高中/其他

    # ---- 职业与收入 ----
    occupation: str = ""            # 个体工商户/受薪/自由职业/无业
    business_type: str = ""         # 行业（个体户时填）
    years_in_current_job: int = 0
    monthly_income: float = 0.0     # 月收入（元）
    monthly_income_stability: str = ""  # stable / fluctuating / seasonal

    # ---- 征信 ----
    credit_report: dict = Field(default_factory=dict)
    # 预期字段:
    # {
    #   "current_loans_count": int,
    #   "current_credit_cards": int,
    #   "credit_card_utilization": float,    # 0-1
    #   "query_count_24m": int,
    #   "overdue_history": ["无" | "M1_once" | "M2_once" | ...],
    #   "guarantee_count": int,
    #   "account_age_years": float,
    # }

    # ---- 银行流水 ----
    bank_statement: dict = Field(default_factory=dict)
    # {
    #   "avg_balance_6m": float,
    #   "monthly_inflow_avg": float,
    #   "monthly_outflow_avg": float,
    #   "large_amount_events": [],
    # }

    # ---- 社保公积金 ----
    social_security: dict = Field(default_factory=dict)
    # {"months_paid": int, "monthly_contribution": float}

    # ---- 抵押物 ----
    collateral: dict = Field(default_factory=dict)
    # {
    #   "type": "住宅" | "商铺" | "无",
    #   "area_sqm": float,
    #   "location": str,
    #   "appraised_value": float,    # 元
    #   "ltv": float,                # 申请额度 / 评估值
    #   "mortgage_count": int,
    #   "title_verified": bool,
    #   "valuation_source": str,
    # }

    # ---- 居住稳定性 ----
    residence: dict = Field(default_factory=dict)
    # {"years_at_address": int, "housing_type": "self_owned" | "rented"}

    # ---- 申请信息 ----
    request: dict = Field(default_factory=dict)
    # {"amount": float, "term_months": int, "purpose": str}

    # ---- 元信息 ----
    profile_id: str = ""
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PersonalProfile":
        """从 JSON 字典构造（容错）"""
        if not isinstance(data, dict):
            return cls()
        # 过滤未知字段
        known = {k: data.get(k) for k in cls.model_fields.keys() if k in data}
        if not known.get("created_at"):
            known["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return cls(**known)

    def to_summary(self) -> str:
        """渲染成摘要文本（前端左侧面板 / LLM 上下文）"""
        lines = [
            f"姓名: {self.name or '-'}（尾号 {self.id_card_tail or '-'}）",
            f"年龄: {self.age}  性别: {self.gender}  婚姻: {self.marital_status}",
            f"学历: {self.education or '-'}",
            f"职业: {self.occupation or '-'}"
            + (f"（{self.business_type}）" if self.business_type else ""),
            f"当前岗位年限: {self.years_in_current_job} 年",
            f"月收入: {self.monthly_income:.0f} 元"
            + (f"（{self.monthly_income_stability}）"
               if self.monthly_income_stability else ""),
        ]
        cr = self.credit_report or {}
        if cr:
            lines.append(
                f"征信: 贷款 {cr.get('current_loans_count', 0)} 笔 / "
                f"信用卡 {cr.get('current_credit_cards', 0)} 张（利用率 "
                f"{int(cr.get('credit_card_utilization', 0) * 100)}%）/ "
                f"近 24 月查询 {cr.get('query_count_24m', 0)} 次 / "
                f"逾期 {cr.get('overdue_history') or '无'}"
            )
        col = self.collateral or {}
        if col.get("type") and col.get("type") != "无":
            lines.append(
                f"抵押: {col.get('type')} "
                f"{col.get('area_sqm', 0)} ㎡ "
                f"估值 {col.get('appraised_value', 0) / 10000:.0f} 万 / "
                f"LTV {col.get('ltv', 0) * 100:.0f}%"
            )
        req = self.request or {}
        if req:
            lines.append(
                f"申请: {req.get('amount', 0) / 10000:.0f} 万 / "
                f"{req.get('term_months', 0)} 月 / "
                f"{req.get('purpose', '-')}"
            )
        return "\n".join(lines)
