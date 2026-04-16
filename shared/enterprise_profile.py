# -*- coding: utf-8 -*-
"""企业画像 Pydantic 模型 — Agent间数据流通的标准载体"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EnterpriseProfile(BaseModel):
    """企业画像标准模型，所有Agent输入输出统一通过此模型流通"""

    # 基本信息
    company_name: str = ""
    unified_credit_code: str = ""
    establishment_date: str = ""
    registered_capital: str = ""
    paid_in_capital: str = ""
    legal_representative: str = ""
    industry: str = ""
    region: str = ""
    ownership_type: str = ""  # 国有/民营/外资/混合
    employee_count: int = 0

    # 经营信息
    main_business: str = ""
    revenue_latest: str = ""
    profit_latest: str = ""
    upstream_top5: list[dict] = Field(default_factory=list)
    downstream_top5: list[dict] = Field(default_factory=list)

    # 股权与控制人
    controller_name: str = ""
    controller_share_pct: str = ""
    shareholders: list[dict] = Field(default_factory=list)
    affiliates: list[dict] = Field(default_factory=list)

    # 财务摘要
    financial_summary: dict = Field(default_factory=dict)

    # 融资与授信
    financing: list[dict] = Field(default_factory=list)
    credit_history: dict = Field(default_factory=dict)
    is_existing_customer: Optional[bool] = None

    # 风险标签 — Agent间流通的核心
    risk_tags: list[dict] = Field(default_factory=list)
    risk_rating: str = ""
    esg_rating: str = ""

    # Agent输出记录
    agent_outputs: dict = Field(default_factory=dict)

    # 元信息
    source_files: list[str] = Field(default_factory=list)
    updated_at: str = ""

    @classmethod
    def from_kb(cls, kb: dict) -> "EnterpriseProfile":
        """从 build_material_kb() 输出构建"""
        facts = kb.get("facts", {}) or {}
        tables = kb.get("tables", {}) or {}
        return cls(
            company_name=facts.get("company_name", ""),
            establishment_date=facts.get("establishment_date", ""),
            registered_capital=facts.get("registered_capital", ""),
            paid_in_capital=facts.get("paid_in_capital", ""),
            legal_representative=facts.get("legal_representative", ""),
            industry=facts.get("industry", ""),
            operating_address=facts.get("operating_address", ""),
            employee_count=int(facts.get("employee_count", 0) or 0),
            controller_name=facts.get("controller_name", ""),
            controller_share_pct=facts.get("controller_share_pct", ""),
            shareholders=tables.get("shareholders", []),
            affiliates=tables.get("affiliates", []),
            financing=tables.get("financing", []),
            upstream_top5=tables.get("upstream", [])[:5],
            downstream_top5=tables.get("downstream", [])[:5],
            source_files=kb.get("source_files", []),
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    @classmethod
    def from_input(cls, **kwargs) -> "EnterpriseProfile":
        """从用户输入的表单构建"""
        return cls(**{k: v for k, v in kwargs.items() if v})

    def to_context(self) -> str:
        """生成用于LLM prompt的上下文文本"""
        lines = []
        if self.company_name:
            lines.append(f"企业名称：{self.company_name}")
        if self.industry:
            lines.append(f"所属行业：{self.industry}")
        if self.region:
            lines.append(f"所在地区：{self.region}")
        if self.registered_capital:
            lines.append(f"注册资本：{self.registered_capital}")
        if self.ownership_type:
            lines.append(f"企业性质：{self.ownership_type}")
        if self.employee_count:
            lines.append(f"员工人数：{self.employee_count}")
        if self.main_business:
            lines.append(f"主营业务：{self.main_business}")
        if self.revenue_latest:
            lines.append(f"最近营收：{self.revenue_latest}")
        if self.risk_rating:
            lines.append(f"风险评级：{self.risk_rating}")
        if self.risk_tags:
            tags = ", ".join(t.get("tag", "") for t in self.risk_tags)
            lines.append(f"风险标签：{tags}")
        return "\n".join(lines)
