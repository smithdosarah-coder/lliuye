# -*- coding: utf-8 -*-
"""Agent1 Channel · IdealProfile 12-dim LLM extractor (master plan §B.6b · onboarding W-B-A3).

新文件（与既有 profile_extractor.py 共存 · 不同 schema）：
- 既有 profile_extractor.py 消费 shared.kb_scan.IdealProfile（v2 PRD 简版 · 已落 / 0 改动）
- 本模块产出 12 维 IdealProfile12（onboarding §Acceptance 指定 schema · POST /api/channel/profile 专用）

12 维定义见 §Acceptance：industry_focus / scale_preference / geo_coverage / stage /
capital_relation / business_size / employee_size / customer_type / product_keywords /
value_chain_position / growth_signals / risk_signals。

LLM 调用走 llm.LLMClient.chat_json（自带 max_retries=2 + JSON 模式 + cache）。
JSON 解析失败 → 全空 IdealProfile12 + confidence_score=0.0 + reasoning 标降级，不抛异常。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# 12 维 dataclass
class IdealProfile12(BaseModel):
    """12 维理想客户画像（master plan §B.6b · onboarding W-B-A3）。

    全字段都给默认空值（list[]或""）以便 LLM 部分失败时仍能 model_validate 通过；
    调用方根据 confidence_score 判断是否可用。
    """

    industry_focus: list[str] = Field(default_factory=list, description="行业聚焦（如 制造业 / 信息技术）")
    scale_preference: list[str] = Field(default_factory=list, description="规模偏好（小型 / 微型 / 中型）")
    geo_coverage: list[str] = Field(default_factory=list, description="地域覆盖（省/市级别）")
    stage: str = Field(default="", description="发展阶段（成长期 / 成熟期 / 转型期）")
    capital_relation: str = Field(default="", description="资本关系（独立 / 集团 / 上市 / 关联）")
    business_size: str = Field(default="", description="业务规模描述（如 营收 1000-5000 万）")
    employee_size: str = Field(default="", description="员工规模描述（如 50-200 人）")
    customer_type: list[str] = Field(default_factory=list, description="客户类型（B2B / B2C / 政府）")
    product_keywords: list[str] = Field(default_factory=list, description="产品关键词")
    value_chain_position: str = Field(default="", description="价值链位置（上游 / 中游 / 下游）")
    growth_signals: list[str] = Field(default_factory=list, description="增长信号（专精特新 / 高新认定 / 发明专利）")
    risk_signals: list[str] = Field(default_factory=list, description="风险信号（高负债率 / 行业下行 / 涉诉）")


class IdealProfileResult(BaseModel):
    """endpoint 返回包装。"""

    ideal_profile: IdealProfile12
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning_text: str = ""


# ---------------------------------------------------------------------------
# Prompt — 12 维抽取
# ---------------------------------------------------------------------------

IDEAL_PROFILE_SYSTEM = (
    "你是一位银行获客画像分析专家。"
    "任务：从客户经理上传的知识库（客户名录 / 政策文件 / 行业指引 三选一）中，"
    "提取 12 维「理想客户画像」用于 look-alike 外网检索。"
    "必须输出严格合法 JSON · 12 维全部填齐 · 无依据的字段返回空 list 或空串，"
    "不允许编造行业 / 数字 / 客户名。"
)


IDEAL_PROFILE_USER = """【知识库类型】{kb_type}

【知识库内容（前 6000 字）】
{kb_blob}

【输出要求】
请综合知识库信息，提炼 12 维画像。每个维度的取值原则：
- 列表类（industry_focus / scale_preference / geo_coverage / customer_type / product_keywords / growth_signals / risk_signals）：≤ 5 项 · 按相关度降序
- 字符串类（stage / capital_relation / business_size / employee_size / value_chain_position）：≤ 30 字 · 简短具体

confidence_score 0.0-1.0：
- 知识库样本充足 + 信号一致 → 0.7-1.0
- 部分维度推断 → 0.4-0.7
- 大量维度无证据 / 知识库稀疏 → 0.0-0.4

reasoning_text：80-150 字 · 说明各维度依据 + 哪些字段降级 · 不要重复 12 维原值

严格输出 JSON：
{{
  "ideal_profile": {{
    "industry_focus": ["..."],
    "scale_preference": ["..."],
    "geo_coverage": ["..."],
    "stage": "...",
    "capital_relation": "...",
    "business_size": "...",
    "employee_size": "...",
    "customer_type": ["..."],
    "product_keywords": ["..."],
    "value_chain_position": "...",
    "growth_signals": ["..."],
    "risk_signals": ["..."]
  }},
  "confidence_score": 0.0,
  "reasoning_text": "..."
}}
"""


# ---------------------------------------------------------------------------
# KB blob loader（消费 A2 worker 写出的 data/channel_kb/{kb_id}.json）
# ---------------------------------------------------------------------------

# 与 onboarding W-B-A2 对齐：kb_id → data/channel_kb/{kb_id}.json
# A2 worker 写出形如:
#   {"kb_id": "...", "kb_type": "customer_list" | "policy" | "industry_guide",
#    "n_rows": int | None, "n_pages": int | None, "summary_text": "...",
#    "rows": [...] | None, "raw_text": "..."}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = PROJECT_ROOT / "data" / "channel_kb"


class KBNotFoundError(FileNotFoundError):
    """kb_id 对应文件不在 data/channel_kb/ 下."""


def load_kb_blob(kb_id: str) -> dict[str, Any]:
    """读 A2 worker 写出的 KB 文件 · 不存在抛 KBNotFoundError."""
    json_path = KB_DIR / f"{kb_id}.json"
    if not json_path.is_file():
        raise KBNotFoundError(f"kb_id={kb_id} not found at {json_path}")
    return json.loads(json_path.read_text(encoding="utf-8"))


def kb_blob_to_text(blob: dict[str, Any], max_chars: int = 6000) -> str:
    """把 A2 KB blob 拼成给 LLM 的 user prompt 用文本.

    优先级：summary_text → raw_text → rows（前 30 行 dump）。
    """
    summary = (blob.get("summary_text") or "").strip()
    if summary:
        return summary[:max_chars]

    raw = (blob.get("raw_text") or "").strip()
    if raw:
        return raw[:max_chars]

    rows = blob.get("rows") or []
    if rows:
        sample = rows[:30]
        text = json.dumps(sample, ensure_ascii=False, indent=2)
        return text[:max_chars]

    return "（KB 内容为空）"


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class LLMTimeoutError(TimeoutError):
    """LLM 调用超时（504 信号）."""


def extract_ideal_profile(
    kb_blob: dict[str, Any],
    kb_type: str,
    *,
    llm_client=None,
    timeout: float | None = None,
) -> IdealProfileResult:
    """从 KB blob 抽 12 维 IdealProfile.

    - llm_client: 实现 chat_json(system, user) -> dict 的对象（见 llm.LLMClient.chat_json）。
                  None 时按 env DEEPSEEK_API_KEY 自动构造（缺 key 直降级返空 profile）。
    - timeout: 当前底层 OpenAI client 全局 timeout · 这里仅用于显式 wrap (Timeout error)。

    返回 IdealProfileResult · 12 维 schema-validated · LLM 失败时返空 + 标降级。
    """
    kb_text = kb_blob_to_text(kb_blob)

    if llm_client is None:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            return _degrade_result(reason="DEEPSEEK_API_KEY 未配置 · 无法调 LLM · 返回空画像")
        try:
            from llm import LLMClient  # 延迟 import 防 test 时无 openai dep
            llm_client = LLMClient(provider="deepseek", api_key=api_key)
        except ImportError as e:
            return _degrade_result(reason=f"LLMClient import 失败 ({e}) · 返回空画像")

    user = IDEAL_PROFILE_USER.format(kb_type=kb_type, kb_blob=kb_text)

    try:
        raw = llm_client.chat_json(
            IDEAL_PROFILE_SYSTEM,
            user,
            schema_hint="IdealProfile12 12 维 + confidence_score + reasoning_text",
            temperature=0.2,
        )
    except TimeoutError as e:
        raise LLMTimeoutError(f"LLM chat_json 超时: {e}") from e
    except (RuntimeError, ValueError, OSError) as e:
        return _degrade_result(reason=f"LLM 调用失败 ({type(e).__name__}: {e}) · 返回空画像")

    return _normalize_llm_output(raw)


def _normalize_llm_output(raw: Any) -> IdealProfileResult:
    """把 LLM 返回的 dict 校准成 IdealProfileResult，schema 不合时降级."""
    if not isinstance(raw, dict):
        return _degrade_result(reason="LLM 返回非 dict · 已降级")

    # 双层兼容：根级直放 12 维 / 套了 ideal_profile 子字典
    if "ideal_profile" in raw and isinstance(raw["ideal_profile"], dict):
        profile_data = raw["ideal_profile"]
    else:
        profile_data = {k: v for k, v in raw.items()
                        if k not in {"confidence_score", "reasoning_text"}}

    # Pydantic 容错：对应字段类型不对的话强制改空 list/空 str
    cleaned = {}
    for field_name, model_field in IdealProfile12.model_fields.items():
        val = profile_data.get(field_name)
        # list 字段
        if model_field.annotation == list[str]:
            if isinstance(val, list):
                cleaned[field_name] = [str(x) for x in val if x is not None]
            elif isinstance(val, str) and val.strip():
                cleaned[field_name] = [val.strip()]
            else:
                cleaned[field_name] = []
        # str 字段
        else:
            cleaned[field_name] = str(val).strip() if val is not None else ""

    try:
        ideal_profile = IdealProfile12.model_validate(cleaned)
    except (ValueError, TypeError):
        ideal_profile = IdealProfile12()

    confidence = raw.get("confidence_score", 0.0)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 0.0

    reasoning = str(raw.get("reasoning_text", "")).strip()

    return IdealProfileResult(
        ideal_profile=ideal_profile,
        confidence_score=confidence,
        reasoning_text=reasoning,
    )


def _degrade_result(reason: str) -> IdealProfileResult:
    return IdealProfileResult(
        ideal_profile=IdealProfile12(),
        confidence_score=0.0,
        reasoning_text=reason,
    )
