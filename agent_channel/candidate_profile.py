"""Agent1 候选企业 Profile — 绿区包装层。

设计：
- `CandidateProfile` 是 Agent1 自己的完整载体，**绿区自由**，字段随 Agent1 演进
- 内含 `enterprise_profile: EnterpriseProfile` 作为跨 Agent handoff 严格 subset
- Agent3 消费 handoff 时**只读 `enterprise_profile` 字段**；Agent1 其它字段视为不稳定

handoff JSON 结构（写入 data/handoff/channel_to_credit/{session_id}/{profile_id}.json）：
    {
      "schema_version": "1.0",
      "candidate_profile": { ...完整版，Agent1 UI / 内部消费... },
      "enterprise_profile": { ...EnterpriseProfile 严格 subset，Agent3 消费... }
    }

字段命名遵守 docs/contracts/field-naming.md v1.0：
- snake_case
- business_line 取值：corporate / inclusive / retail / reserved
- match_score 0-100 int
- 金额带 _yuan 后缀
- profile_id / session_id UUID v4

合规约束：
- 不含任何 L3 核心数据（客户内部编号 / 征信报告等），见 docs/data_classification/agent1.md
- source_urls 仅记录公开可访问 URL（mock 场景可空，标 data_sources=["内部 Mock 客户库"]）
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from shared.enterprise_profile import EnterpriseProfile

# ---- 业务口径常量 ----

SCHEMA_VERSION = "1.0"

BusinessLine = Literal["corporate", "inclusive", "retail", "reserved"]

# 简单额度启发式（不走 LLM，走确定性规则）
# 规则见 CLAUDE.md §3.1 — 可确定性的事用 Python
BASE_AMOUNT_YUAN = 5_000_000
BIDDING_BONUS_YUAN = 3_000_000
GROWTH_BONUS_YUAN = 3_000_000
RECOGNITION_BONUS_YUAN = 2_000_000
TECH_BONUS_YUAN = 1_000_000
AMOUNT_CAP_YUAN = 50_000_000


class SignalItem(BaseModel):
    """单条信号记录。字段与 realtime_stream 产出 1:1。"""

    signal_type: str
    signal_title: str
    signal_detail: str = ""
    signal_date: str = ""
    signal_source: str = ""
    source_url: str = ""


class CandidateProfile(BaseModel):
    """Agent1 候选企业完整画像 + handoff 载体。"""

    # ---- handoff 元信息 ----
    schema_version: str = SCHEMA_VERSION
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    # ---- 跨 Agent handoff 核心（Agent3 只读这个）----
    enterprise_profile: EnterpriseProfile

    # ---- Agent1 评分与匹配（绿区自由）----
    match_score: int = 0                 # 0-100
    business_line: BusinessLine = "corporate"
    signal_count: int = 0
    signal_types: list[str] = Field(default_factory=list)  # unique, sorted
    signal_timeline: list[SignalItem] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    approved_amount_yuan: int = 0        # 推荐授信额度上限
    recommended_products: list[str] = Field(default_factory=list)
    pitch: str = ""
    data_sources: list[str] = Field(default_factory=list)
    below_diversity_gate: bool = False

    # ---- 工厂 ----

    @classmethod
    def from_candidate_dict(
        cls,
        candidate: dict,
        session_id: str,
        business_line: BusinessLine = "corporate",
    ) -> CandidateProfile:
        """从 realtime_stream._build_final_output 产出的 candidate dict 构建。

        candidate dict 结构参见 agent_channel/realtime_stream.py _build_final_output。
        """
        qcc_cap = _parse_capital_yuan(candidate.get("registeredCapital", ""))

        enterprise = EnterpriseProfile(
            company_name=candidate.get("name", ""),
            unified_credit_code=_clean_na(candidate.get("uscc", "")),
            legal_representative=_clean_na(candidate.get("legalRep", "")),
            registered_capital=_clean_na(candidate.get("registeredCapital", "")),
            establishment_date=_clean_na(candidate.get("founded", "")),
            industry=_clean_na(candidate.get("industry", "")),
            region=_clean_na(candidate.get("region", "")),
            employee_count=_safe_int(candidate.get("employees", 0)),
            main_business=_clean_na(candidate.get("mainBusiness", "")),
        )

        signals = [
            SignalItem(
                signal_type=s.get("type", ""),
                signal_title=s.get("title", ""),
                signal_detail=s.get("detail", ""),
                signal_date=s.get("date", ""),
                signal_source=s.get("source", ""),
                source_url=s.get("url", ""),
            )
            for s in candidate.get("signals", [])
        ]
        # 按日期倒序（空日期沉底）
        signals.sort(key=lambda s: s.signal_date or "", reverse=True)

        unique_urls = sorted({s.source_url for s in signals if s.source_url})
        types = candidate.get("signalTypes") or sorted(
            {s.signal_type for s in signals if s.signal_type}
        )

        return cls(
            session_id=session_id,
            enterprise_profile=enterprise,
            match_score=_signal_score_to_match(candidate.get("signalScore", 0)),
            business_line=business_line,
            signal_count=candidate.get("signalCount", len(signals)),
            signal_types=list(types),
            signal_timeline=signals,
            source_urls=unique_urls,
            approved_amount_yuan=_estimate_amount_yuan(types, qcc_cap),
            recommended_products=list(candidate.get("recommendedProducts", [])),
            pitch=candidate.get("pitch", ""),
            data_sources=[
                ds.get("label", "") for ds in candidate.get("dataSources", [])
                if ds.get("label")
            ],
            below_diversity_gate=bool(candidate.get("belowDiversityGate", False)),
        )

    def to_handoff_json(self) -> dict:
        """产出标准 handoff JSON：外层分 candidate_profile + enterprise_profile 两份。

        Agent3 消费路径：json["enterprise_profile"]（严格 subset）
        Agent1 UI 消费路径：json["candidate_profile"]（完整版）
        """
        return {
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "candidate_profile": self.model_dump(mode="json"),
            "enterprise_profile": self.enterprise_profile.model_dump(mode="json"),
        }


# ========== 私有工具 ==========

_NA_TOKENS = {"未获取", "N/A", "NA", "null", "None", ""}


def _clean_na(v: str | None) -> str:
    """去掉占位符 '未获取' 等，统一回空串（下游好判空）。"""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s in _NA_TOKENS else s


def _safe_int(v) -> int:
    """宽松 int 转换。"""
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _parse_capital_yuan(text: str) -> int:
    """从 '500 万' / '1.2 亿' 等字符串解析成元。无效返回 0。"""
    s = _clean_na(text)
    if not s:
        return 0
    import re
    m = re.search(r"([\d\.]+)\s*([万亿])?", s)
    if not m:
        return 0
    try:
        num = float(m.group(1))
    except ValueError:
        return 0
    unit = m.group(2) or ""
    if unit == "亿":
        return int(num * 100_000_000)
    if unit == "万":
        return int(num * 10_000)
    return int(num)


def _signal_score_to_match(signal_score: int | float) -> int:
    """signalScore（理论无上限）→ match_score 0-100 归一化。

    signalScore 典型分布：30（2 type）- 100+（5 type + 加权）。clip 到 [0, 100]。
    """
    try:
        s = float(signal_score)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, int(s)))


def _estimate_amount_yuan(signal_types: list[str], capital_yuan: int) -> int:
    """基于信号类型 + 注册资本粗估授信上限。

    启发式（非 LLM，走 CLAUDE.md §3.1 确定性路径）：
      基础 500 万 + bidding +300 + growth +300 + recognition +200 + tech +100
      上限 cap = min(5000 万, 注册资本 × 0.5)  # 简化版杠杆约束
    """
    amount = BASE_AMOUNT_YUAN
    types = set(signal_types or [])
    if "bidding" in types:
        amount += BIDDING_BONUS_YUAN
    if "growth" in types:
        amount += GROWTH_BONUS_YUAN
    if "recognition" in types:
        amount += RECOGNITION_BONUS_YUAN
    if "tech" in types:
        amount += TECH_BONUS_YUAN
    amount = min(amount, AMOUNT_CAP_YUAN)
    if capital_yuan > 0:
        amount = min(amount, int(capital_yuan * 0.5))
    return max(0, amount)
