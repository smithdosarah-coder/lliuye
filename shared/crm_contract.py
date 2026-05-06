"""CRM Contract · 个人金融场景 (toC 零售财富) · 15 字段最小集

per Phase C charter §3 · DP2 PM 拍板 '现在冻 · additive only · breaking change 走 RFC'

设计逻辑 (Codex R3 final):
- A 类 身份 (4 字段): customer_id / name / age / mobile_masked
- B 类 经济能力 (5 字段): occupation / income_monthly / employment_status / credit_score / debt_ratio
- C 类 业务关系 (4 字段): existing_products / risk_level / last_contact_at / relationship_manager_id
- D 类 监管 + 城市 (2 字段): consent_status / city

PIPL + 银保监合规要点:
- mobile_masked 必脱敏 (138****5678) · 不存全号
- consent_status 是个人金融监管核心 (没授权不能用客户数据做 AI 决策)
- risk_level 是适当性销售合规法规硬要求

冻结策略: 15 字段 + 枚举值 + 空值策略 + 版本策略 一次冻 · 后续仅 additive change · breaking 走 RFC.

使用:
    from shared.crm_contract import CrmCustomerProfile, EmploymentStatus, RiskLevel, ConsentStatus

    profile = CrmCustomerProfile(
        customer_id="C-001",
        name="张三",
        age=35,
        mobile_masked="138****5678",
        city="苏州",
        occupation="软件工程师",
        income_monthly=25000,
        employment_status=EmploymentStatus.EMPLOYED,
        existing_products=["活期储蓄", "公募基金"],
        credit_score=750,
        debt_ratio=0.35,
        risk_level=RiskLevel.BALANCED,
        last_contact_at="2026-04-15T10:30:00",
        relationship_manager_id="RM-王哲",
        consent_status=ConsentStatus.GRANTED,
    )
"""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# 枚举值 (冻结清单)
# ---------------------------------------------------------------------------

class EmploymentStatus(str, Enum):
    """就业状态 · 不同产品适配规则不同."""

    EMPLOYED = "employed"  # 在职 (公司聘用)
    SELF_EMPLOYED = "self_employed"  # 自雇 (个体/创业)
    RETIRED = "retired"  # 退休
    STUDENT = "student"  # 学生
    UNEMPLOYED = "unemployed"  # 失业/无业


class RiskLevel(str, Enum):
    """风险偏好 · 适当性销售合规法规硬要求 · 不可与产品风险等级错配."""

    CONSERVATIVE = "conservative"  # 保守型 · 储蓄/货币基金为主
    BALANCED = "balanced"  # 平衡/稳健型 · 债券+部分权益
    GROWTH = "growth"  # 成长型 · 偏权益/混合
    AGGRESSIVE = "aggressive"  # 激进型 · 股票/高波动


class ConsentStatus(str, Enum):
    """授权状态 · PIPL 合规核心 · 没授权不能用客户数据做 AI 决策."""

    GRANTED = "granted"  # 已授权 (含 KYC + 隐私协议)
    PENDING = "pending"  # 待签 (默认 inactive)
    REVOKED = "revoked"  # 已撤销


# ---------------------------------------------------------------------------
# 主 Schema (15 字段 · 冻结契约)
# ---------------------------------------------------------------------------

# 手机脱敏正则: 必须含 ** 或 ****
_MOBILE_MASKED_RE = re.compile(r"^\d{3}\*+\d{4}$")


class CrmCustomerProfile(BaseModel):
    """CRM 客户档案 · 15 字段冻结契约 · 个人金融场景.

    冻结日期: 2026-05-06 (Phase C charter ratify)
    版本: 1.0
    修改路径: 仅 additive (新加字段 OK) · breaking change (改字段名/类型/枚举) 走 RFC + PM 拍板

    Adapter 模式: 客户银行 CRM 真接入时 · 用 adapter 把客户字段映射到本 schema · 不动本 schema.
    """

    # === A 类 身份 (4 字段) ===

    customer_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="客户唯一 ID · 跨 6 Agent 关联同一客户的钩子",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="客户姓名 · 显示用",
    )
    age: int = Field(
        ...,
        ge=18,
        le=120,
        description="年龄 · 决定生命周期阶段 (青年/中年/退休) · 18-120",
    )
    mobile_masked: str = Field(
        ...,
        description="手机号脱敏 · 格式 138****5678 · PIPL 合规 · 不存全号",
    )

    # === D 类 城市 (1 字段 · 与 D 类合并) ===

    city: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="城市 · 一线 vs 县城 风险/产品差异化",
    )

    # === B 类 经济能力 (5 字段) ===

    occupation: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="职业 · 决定收入稳定性 + 风险偏好",
    )
    income_monthly: float = Field(
        ...,
        ge=0,
        description="月收入 (元) · 决定产品适配 + 授信额度 + 保险保额",
    )
    employment_status: EmploymentStatus = Field(
        ...,
        description="就业状态 · 不同产品适配规则",
    )
    credit_score: int = Field(
        ...,
        ge=300,
        le=900,
        description="征信分 · 决定授信通过与否 · 300-900 (央行征信中心范围)",
    )
    debt_ratio: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="负债比 · 总负债/月收入 · 决定授信额度上限 + 风险评估",
    )

    # === C 类 业务关系 (4 字段) ===

    existing_products: List[str] = Field(
        default_factory=list,
        description="现持产品列表 · AI 推荐避免重复 + 找交叉销售机会",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="风险偏好 · 适当性销售合规硬要求",
    )
    last_contact_at: Optional[datetime] = Field(
        None,
        description="上次接触时间 · RM 跟进周期 + 防流失 (3m=沉睡, 6m=流失风险)",
    )
    relationship_manager_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="RM 工号 · 行级权限隔离基础 · 跨 Agent 知道客户归谁",
    )

    # === D 类 监管 (1 字段) ===

    consent_status: ConsentStatus = Field(
        ...,
        description="授权状态 · PIPL + 监管核心 · 没授权不能用客户数据做 AI 决策",
    )

    # ---------------------------------------------------------------------------
    # 校验
    # ---------------------------------------------------------------------------

    @field_validator("mobile_masked")
    @classmethod
    def _validate_mobile_masked(cls, v: str) -> str:
        """mobile_masked 必须脱敏格式 138****5678 · 不允许全号."""
        if not _MOBILE_MASKED_RE.match(v):
            raise ValueError(
                f"mobile_masked 必须脱敏 (格式 138****5678) · 收到: {v[:3]}***"
            )
        return v

    @field_validator("name")
    @classmethod
    def _no_id_number_in_name(cls, v: str) -> str:
        """name 不允许含身份证号 · 防数据污染."""
        if re.search(r"\d{15,18}", v):
            raise ValueError("name 不允许含身份证号 · 请清理后再传")
        return v


# ---------------------------------------------------------------------------
# 空值策略 (DP2 PM 拍板)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {
    "customer_id", "name", "age", "mobile_masked", "city",
    "occupation", "income_monthly", "employment_status",
    "credit_score", "debt_ratio", "risk_level",
    "relationship_manager_id", "consent_status",
}

OPTIONAL_FIELDS = {
    "existing_products",  # default []
    "last_contact_at",  # 新客户尚未接触
}

ENUM_FIELDS = {
    "employment_status": EmploymentStatus,
    "risk_level": RiskLevel,
    "consent_status": ConsentStatus,
}


# ---------------------------------------------------------------------------
# 版本管理
# ---------------------------------------------------------------------------

CRM_CONTRACT_VERSION = "1.0"
CRM_CONTRACT_FROZEN_AT = "2026-05-06"
CRM_CONTRACT_FIELDS_COUNT = 15


def get_contract_metadata() -> dict:
    """返回契约元数据 · 用于 audit + adapter 校验."""
    return {
        "version": CRM_CONTRACT_VERSION,
        "frozen_at": CRM_CONTRACT_FROZEN_AT,
        "fields_count": CRM_CONTRACT_FIELDS_COUNT,
        "required_fields": sorted(REQUIRED_FIELDS),
        "optional_fields": sorted(OPTIONAL_FIELDS),
        "enum_fields": list(ENUM_FIELDS.keys()),
    }


__all__ = [
    "CrmCustomerProfile",
    "EmploymentStatus",
    "RiskLevel",
    "ConsentStatus",
    "REQUIRED_FIELDS",
    "OPTIONAL_FIELDS",
    "ENUM_FIELDS",
    "CRM_CONTRACT_VERSION",
    "CRM_CONTRACT_FROZEN_AT",
    "CRM_CONTRACT_FIELDS_COUNT",
    "get_contract_metadata",
]
