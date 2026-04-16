# -*- coding: utf-8 -*-
"""KB 扫描范式的通用 Pydantic 模型。

三个 Agent（1 全渠道流量匹配 / 4 贷中风险预警 / 5 合规巡检）共享这套数据契约。
"""

from __future__ import annotations
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# ========== 通用枚举 ==========

class RiskLevel(str, Enum):
    """统一的分级枚举。三个 Agent 都用这套色值和语义。"""
    RED = "red"          # 严重 / 强匹配 / 红灯
    YELLOW = "yellow"    # 一般 / 中匹配 / 黄灯
    GREEN = "green"      # 提示 / 弱匹配 / 绿灯
    INFO = "info"        # 信息性提示，不计入违规/风险统计


class RuleType(str, Enum):
    """规则来源类型。"""
    STRUCTURED = "structured"       # 结构化规则（JSON/Excel 直接可用）
    EXTRACTED = "extracted"         # LLM 从 Word/PDF 抽取
    BUILTIN = "builtin"             # 系统预置


# ========== KB 层模型 ==========

class RuleItem(BaseModel):
    """从 KB 中抽取出的单条规则（策略/政策条款/预警规则通用）。"""
    rule_id: str = Field(description="规则唯一 ID，如 RULE_001")
    source_doc: str = Field(default="", description="来源文件名")
    source_page: str = Field(default="", description="页码/章节")
    category: str = Field(default="", description="规则类别")
    title: str = Field(description="规则标题")
    content: str = Field(description="规则原文")
    trigger_condition: str = Field(default="", description="触发条件（自然语言）")
    dsl: dict = Field(default_factory=dict, description="可选：结构化 DSL")
    severity: RiskLevel = RiskLevel.YELLOW
    rule_type: RuleType = RuleType.EXTRACTED


class CompanyProfile(BaseModel):
    """企业画像，Agent1/Agent4 共用。"""
    company_id: str = ""
    company_name: str
    unified_credit_code: str = ""
    industry: str = ""
    sub_industry: str = ""
    region: str = ""
    scale: str = ""                          # 大型/中型/小型/微型
    revenue_latest: str = ""
    employee_count: int = 0
    ownership_type: str = ""                 # 国有/民营/外资/混合
    keywords: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    establishment_date: str = ""
    registered_capital: str = ""
    main_business: str = ""
    upstream: list[dict] = Field(default_factory=list)
    downstream: list[dict] = Field(default_factory=list)
    # 风险相关（Agent4 用）
    risk_tags: list[str] = Field(default_factory=list)
    credit_balance: str = ""                 # 在贷余额
    overdue_days: int = 0
    # 自由扩展位
    extras: dict = Field(default_factory=dict)


class IdealProfile(BaseModel):
    """Agent1 专用：从已有客户名录 + 政策 LLM 抽出的'理想客户画像'。"""
    profile_id: str
    name: str
    target_industries: list[str] = Field(default_factory=list)
    target_sub_industries: list[str] = Field(default_factory=list)
    target_regions: list[str] = Field(default_factory=list)
    scale_range: list[str] = Field(default_factory=list)
    revenue_range: tuple[float, float] | None = None
    must_have_tags: list[str] = Field(default_factory=list)
    nice_to_have_tags: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)
    policy_context: str = ""
    reasoning: str = ""
    editable: bool = True


# ========== 扫描层模型 ==========

class ScanTarget(BaseModel):
    """扫描目标的抽象载体。"""
    target_id: str
    target_type: str                          # "company" | "policy_clause" | "business_event" | "loan_customer"
    payload: dict


class ScanResult(BaseModel):
    """一次扫描的原始输出（未排序）。"""
    scan_id: str
    scanned_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    provider_name: str
    query_used: str = ""
    targets: list[ScanTarget]
    total_found: int


# ========== 命中层模型 ==========

class Evidence(BaseModel):
    """证据链单元。所有命中都必须有证据。"""
    source: str
    snippet: str
    url: str = ""


class HitItem(BaseModel):
    """分级命中清单的单条。三 Agent 共用结构。"""
    hit_id: str
    rank: int = 0
    level: RiskLevel
    score: float = 0.0
    target: ScanTarget
    matched_rules: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    evidences: list[Evidence] = Field(default_factory=list)
    extras: dict = Field(default_factory=dict)


class HitList(BaseModel):
    """最终交付给用户的分级命中榜。"""
    list_id: str
    agent_name: str                           # "channel" | "alert" | "compliance"
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    kb_summary: str = ""
    scan_summary: str = ""
    total_scanned: int = 0
    total_hit: int = 0
    red_count: int = 0
    yellow_count: int = 0
    green_count: int = 0
    hits: list[HitItem] = Field(default_factory=list)
    exportable: bool = True

    def recount(self) -> None:
        """从 hits 重新统计分级数。"""
        self.red_count = sum(1 for h in self.hits if h.level == RiskLevel.RED)
        self.yellow_count = sum(1 for h in self.hits if h.level == RiskLevel.YELLOW)
        self.green_count = sum(1 for h in self.hits if h.level == RiskLevel.GREEN)
        self.total_hit = self.red_count + self.yellow_count + self.green_count
