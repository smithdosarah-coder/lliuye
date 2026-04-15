# -*- coding: utf-8 -*-
"""EnterpriseProfile — 跨 Agent 可消费的企业画像 schema.

设计对齐:
  - schema 参照 agent_credit/mock_data/corporate_profiles/*.json
  - 所有字段都允许为 None / 空字符串,以便真 pipeline 在字段缺失时仍能产出合法对象
  - 目前的主要消费方:Agent3 (授信决策) / Agent4 (贷中预警) / Agent5 (合规审核)
"""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

BusinessLine = Literal["inclusive", "corporate", "reserved"]


class FinancialAnchors(BaseModel):
    revenue_latest: Optional[float] = None
    revenue_prev: Optional[float] = None
    net_profit_latest: Optional[float] = None
    net_profit_prev: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    net_assets: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    short_term_borrowing: Optional[float] = None
    ebitda: Optional[float] = None
    period: Optional[str] = None


class GuaranteeInfo(BaseModel):
    type: Optional[str] = None
    collateral: Optional[str] = None
    collateral_value: Optional[float] = None
    collateral_type: Optional[str] = None
    guarantor: Optional[str] = None


class RelatedPartyInfo(BaseModel):
    related_party_revenue_pct: Optional[float] = None
    related_party_txn_desc: Optional[str] = None


class ExistingCredit(BaseModel):
    total_approved: Optional[float] = None
    total_used: Optional[float] = None
    overdue_history: Optional[str] = None


class CreditRequest(BaseModel):
    amount: Optional[float] = None
    purpose: Optional[str] = None
    term_months: Optional[int] = None


class Chapters(BaseModel):
    chapter_1_background: Optional[str] = None
    chapter_2_operation: Optional[str] = None
    chapter_3_finance: Optional[str] = None
    chapter_4_conclusion: Optional[str] = None


class AgentOutputs(BaseModel):
    # 与 agent_credit schema 对齐的下游可消费字段
    agent6_report_json: Optional[str] = None


class EnterpriseProfile(BaseModel):
    """跨 Agent 可消费的企业画像对象.

    与 agent_credit/mock_data/corporate_profiles/*.json 字段兼容,
    Agent3 的 load_profile_from_report_json 可直接消费此对象。
    """
    profile_id: str
    company_name: str
    unified_credit_code: Optional[str] = None
    industry: Optional[str] = None
    establishment_date: Optional[str] = None
    registered_capital: Optional[str] = None
    employee_count: Optional[int] = None
    region: Optional[str] = None
    main_business: Optional[str] = None
    controller_name: Optional[str] = None
    controller_share_pct: Optional[str] = None

    financial_anchors: FinancialAnchors = Field(default_factory=FinancialAnchors)
    guarantee_info: GuaranteeInfo = Field(default_factory=GuaranteeInfo)
    related_party_info: RelatedPartyInfo = Field(default_factory=RelatedPartyInfo)
    existing_credit: ExistingCredit = Field(default_factory=ExistingCredit)
    tax_rating: Optional[str] = None
    request: CreditRequest = Field(default_factory=CreditRequest)
    chapters: Chapters = Field(default_factory=Chapters)
    agent_outputs: AgentOutputs = Field(default_factory=AgentOutputs)

    # V13 扩展字段(非 agent_credit 必需,便于追溯与调试)
    source_materials: list[str] = Field(default_factory=list)
    generated_at: Optional[str] = None

    # V14-D 扩展:业务线(普惠 / 对公 / 预留)
    business_line: Optional[BusinessLine] = None


class PendingQuestion(BaseModel):
    """外因问题——由 V14-C Agent 生成,此处仅定义消费接口."""
    id: str
    section_id: str
    question: str
    hint: Optional[str] = None
    input_type: str = "textarea"  # textarea | scale | select
    options: Optional[list[str]] = None  # for select
