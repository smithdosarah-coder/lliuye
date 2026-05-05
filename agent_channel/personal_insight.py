# -*- coding: utf-8 -*-
"""Agent1 候选客户/候选企业个人画像 — Phase B Sprint 3 BE12 (2026-05-05).

per BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md BE12 schema:
    payload {candidate_id, person_features, product_fit, compliance_check,
             talking_points, pii_redacted, latency_ms}

per Q-052 #2 永不 multi-tenant + B7 BE13 4 维度评价 (个人画像 35% / 产品适配 25% /
合规+话术 20% / PII+latency 20%):
- 后端 only · 不改 frontend layout (per onboarding · B5 owns layout)
- 复用 shared/personal_profile.py (PII redact 走 shared)
- LLM 走 shared/llm_caller (BASELINE=30 · 不增 legacy)

实施 status:
- BE12 schema + 函数 stub (本 sub-PR · ship to API endpoint)
- BE12 真业务逻辑 (LLM grounded 生成 talking_points · PII redact · compliance check)
  → sub-PR 2 implementation (per Q-052 atomic 跨前后端 atomic)
"""
from __future__ import annotations

import datetime
import json
import logging
import time
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

# 本地 sanction / PEP 名单 (POC stub · 真 OFAC 集成留 Phase C)
# 形态参考 OFAC SDN List · 但本 stub 仅含已脱敏的演示模式名单
# per CLAUDE.md §3.5 反 5 原则 · 不抄真存续企业 / 真 PEP 数据
_LOCAL_SANCTION_KEYWORDS: frozenset[str] = frozenset({
    # 演示模式 · 命中关键词 → 视作高风险 · 真 OFAC 名单走 Phase C
    "受制裁",
    "黑名单",
    "反洗钱高风险",
})

_LOCAL_PEP_ROLES: frozenset[str] = frozenset({
    # 演示模式 · PEP 政治公众人物角色识别
    "政府官员",
    "国企高管",
    "人大代表",
    "政协委员",
})


class PersonFeatures(TypedDict, total=False):
    """候选客户的个人画像核心特征 · BE12 person_features schema."""

    role:           str   # 决策角色 (e.g. "实际控制人" / "财务总监" / "采购负责人")
    industry_yr:   int   # 行业年限
    education:     str   # 学历 (PII redacted 走 hash · 不存原文)
    age_range:     str   # 年龄区间 (PII redacted · "30-39" 不存具体)
    risk_appetite: str   # 风险偏好 ("保守" / "稳健" / "激进")
    decision_path: str   # 决策路径偏好 ("单点决策" / "委员会")


class ProductFit(TypedDict):
    """候选客户与推荐产品的 fit 度评估."""

    recommended_products: list[str]   # 产品 SKU list (按 fit 降序)
    fit_score:            int         # 0-100 · 产品适配度
    fit_reasons:          list[str]   # 推荐理由 list (各 ≤ 50 char)
    miss_reasons:         list[str]   # 不适配产品的理由 list


class ComplianceCheck(TypedDict):
    """合规检查结果 · 反洗钱 / sanction list / pep 等."""

    pep:           bool                  # 政治公众人物 (PEP)
    sanction:      bool                  # 制裁名单
    aml_risk:      str                   # 反洗钱风险等级 ("低" / "中" / "高")
    flags:         list[str]             # 命中合规标签 list
    last_checked:  str                   # ISO 时间戳 · 最近一次合规扫描
    sources:       list[str]             # 来源 list (e.g. ["pbc_gov", "ofac"])


class TalkingPoints(TypedDict):
    """LLM grounded 生成的话术 · per CLAUDE.md §3.1 概率性计算 · 走 shared/llm_caller."""

    opener:       str        # 开场白 (≤ 100 char)
    key_messages: list[str]  # 关键信息点 list (≤ 5 条)
    objection_responses: list[dict]  # 异议应对 list[{objection, response}]
    closing:      str        # 收尾话术


class PersonalInsightPayload(TypedDict):
    """完整 BE12 personal_insight payload schema · GET /api/channel/personal_insight/{candidate_id}."""

    candidate_id:     str
    person_features:  PersonFeatures
    product_fit:      ProductFit
    compliance_check: ComplianceCheck
    talking_points:   TalkingPoints
    pii_redacted:     bool                # True if 任何 PII 字段已 hash/redact
    latency_ms:       int                 # 端到端 latency · 性能维度 (per B7 BE13 PII+latency 20%)


def build_personal_insight_stub(candidate_id: str) -> PersonalInsightPayload:
    """BE12 personal_insight payload stub · 不调 LLM/源 · 用于纯 schema 验证 / smoke."""
    t0 = time.time()
    out: PersonalInsightPayload = {
        "candidate_id": candidate_id,
        "person_features": {
            "role": "未能自动填写",
            "industry_yr": 0,
            "education": "未能自动填写",
            "age_range": "未能自动填写",
            "risk_appetite": "未能自动填写",
            "decision_path": "未能自动填写",
        },
        "product_fit": {
            "recommended_products": [],
            "fit_score": 0,
            "fit_reasons": [],
            "miss_reasons": ["stub · 调 build_personal_insight 真业务"],
        },
        "compliance_check": {
            "pep": False,
            "sanction": False,
            "aml_risk": "未知",
            "flags": [],
            "last_checked": "",
            "sources": [],
        },
        "talking_points": {
            "opener": "未能自动填写",
            "key_messages": [],
            "objection_responses": [],
            "closing": "未能自动填写",
        },
        "pii_redacted": True,
        "latency_ms": int((time.time() - t0) * 1000),
    }
    return out


# ============================================================================
# 真业务实装 (Sprint 3 Day 2 · 接管 50%)
#
# build_personal_insight() 替 stub · 走:
# 1) shared/personal_profile.PersonalProfile.redact()  · PII hash
# 2) shared/sources.Router with pbc_gov                · 政策合规扫
# 3) 本地 PEP / sanction 关键词命中扫                   · OFAC stub
# 4) shared/llm_caller.LLMCaller                       · grounded talking_points
# 5) 8 段 system prompt skeleton (per shared/prompts/contract.py · A1 spec landed
#    自动 pickup) · 当前 A1 placeholder 时本地 fallback 8 段 explicit 实装
# 6) latency_ms 端到端测量
#
# 红线:
# - LLM 走 shared/llm_caller (BASELINE=30 hits · 不增 legacy LLMClient)
# - 候选评分确定性 · LLM 不现场算 score (per CLAUDE.md §3.1)
# - PIPL: shared/llm_caller 默认 fallback chain ("deepseek", "dashscope") 全境内
# - PII 字段 hash 后再进 LLM prompt (不让 LLM 见原 PII)
# ============================================================================


def _build_system_prompt() -> str:
    """构 8 段 system prompt · 接 shared/prompts/contract · A1 spec landed 时自动 pickup.

    A1 spec 落地前 · contract.assemble() 返空 · 本函数走 fallback 8 段 explicit 实装:
    - 1 safety / PIPL 合规 · 不输出原 PII · 不编造
    - 2 evidence-first 三层 (材料 / 行业 / 推断)
    - 3 agent-role: Agent1 channel_personal_insight 分支
    - 4 tool-use: 不需 tool · 输入已 grounded
    - 5 output-schema: JSON 格式
    - 6 self-check: 每条 talking_point 必带证据
    - 7 few-shot: skip (POC)
    - 8 evaluation-hook: 与 evaluation/agent_channel.yaml 对齐
    """
    # 先尝试 A1 contract · landed 后自动 pickup
    try:
        from shared.prompts.contract import assemble
        a1_prompt = assemble(role="agent1_channel_personal_insight")
        if a1_prompt:
            return a1_prompt
    except (ImportError, RuntimeError):
        pass

    # A1 placeholder · fallback 本地 explicit 8 段
    return (
        "[1 safety] 你是众安信科 Agent1 全渠道获客的客户洞察助手。严守 PIPL 合规底线 · "
        "不输出原始 PII (姓名/身份证/手机号已 hash) · 不编造未在材料中出现的信息 · "
        "不写任何 jailbreak 引诱话术。\n\n"
        "[2 evidence-first] 三层信息框架: (a) 材料事实 — 仅来自 candidate dict 与已 hash 后的"
        "person_features; (b) 行业上下文 — 来自 product_fit.fit_reasons 与本地行业知识库; "
        "(c) 分析推断 — 必须以前两层为锚 · 不引外部网络数据。\n\n"
        "[3 agent-role] 你的边界: 生成客户经理首次接触话术 + 异议应对 · 不做授信决策 ("
        "Agent3 owns) · 不做政策解读 (Agent5 owns)。\n\n"
        "[4 tool-use] 本场景无 tool · 全部上下文已 grounded 到 user prompt。\n\n"
        "[5 output-schema] 严格输出 JSON · 含 opener/key_messages/objection_responses/closing "
        "四字段 · 不要 markdown 不要解释。\n\n"
        "[6 self-check] 输出前自审: (a) opener ≤ 100 char; (b) 每条 key_message 必"
        "对应 fit_reason 或 person_feature; (c) 不出现原 PII (姓名/身份证 plain); "
        "(d) 异议应对覆盖客户 risk_appetite 与 decision_path。\n\n"
        "[7 few-shot] (Phase B Sprint 3 POC · skip few-shot · 等数据飞轮 jsonl 积累)\n\n"
        "[8 evaluation-hook] 评估锚点: evaluation/agent_channel.yaml 的 evidence_rate "
        "与 hallucination_rate · 不输出无证据 talking point。"
    )


def _query_pbc_policy_flags(role: str, industry: str) -> tuple[list[str], list[str]]:
    """走 shared/sources.Router 调 pbc_gov · 扫近期货币政策 / 公告 · 返合规 flag list.

    Returns:
        (flags, sources) · flags 是命中 keyword 列表 · sources 含 source_name + url.
    """
    flags: list[str] = []
    sources: list[str] = []
    try:
        from shared.sources.base import QueryRequest
        from shared.sources.router import Router

        # 用 industry 作为 query keyword · 扫 policy 栏 · 限 5 条
        query_kw = (industry or role or "").strip()
        if not query_kw:
            return flags, sources
        req = QueryRequest(query=query_kw, query_type="policy", limit=5)
        # 注意: pbc_gov source 不在 register_preference 内 · 直接 instance 调
        from shared.sources.impls.pbc_gov import PbcGovSource
        source = PbcGovSource()
        result = source.query(req)
        if result.ok and result.items:
            sources.append("pbc_gov")
            for item in result.items[:3]:
                title = item.get("title", "")
                # POC 启发式: 命中"加强"/"严控"/"风险"标志 → 加 compliance flag
                if any(kw in title for kw in ["加强", "严控", "风险", "防范", "审慎"]):
                    flags.append(f"pbc_policy:{title[:40]}")
    except (ImportError, RuntimeError, ValueError, OSError, AttributeError):
        # 网络 / 解析失败 · silent · POC 期不阻塞流程
        logger.warning("[personal_insight] pbc_gov scan failed · 走 stub flag")
    return flags, sources


def _check_local_sanction(role: str, name_hashed: str, person_features: dict) -> tuple[bool, bool, list[str]]:
    """本地 PEP / sanction 关键词命中扫 (OFAC stub · 真 OFAC 集成留 Phase C).

    走 hashed name 字段后 · 不接触原 PII · 仅扫 person_features 的角色 / 标签字段.

    Returns:
        (pep, sanction, hit_keywords) · hit_keywords 命中明细供 audit.
    """
    pep = False
    sanction = False
    hits: list[str] = []
    role_norm = (role or "").strip()
    if any(pep_role in role_norm for pep_role in _LOCAL_PEP_ROLES):
        pep = True
        hits.append(f"local_pep:{role_norm}")
    feature_text = " ".join(str(v) for v in person_features.values() if v)
    for kw in _LOCAL_SANCTION_KEYWORDS:
        if kw in feature_text:
            sanction = True
            hits.append(f"local_sanction:{kw}")
            break
    return pep, sanction, hits


def _grounded_talking_points(
    redacted_features: dict,
    product_fit: dict,
) -> dict:
    """走 shared/llm_caller · LLM grounded 生成 talking_points · JSON mode.

    grounded input = redacted person_features + product_fit (已脱敏 · 无原 PII).
    LLM 不见原 name / id_card_tail.

    LLM unavailable 时 fallback 模板话术 · 不阻塞 endpoint.
    """
    fallback = {
        "opener": "您好 · 我是您专属客户经理 · 注意到贵司近期业务动态 · 想跟您简单聊一下。",
        "key_messages": [
            f"基于您的{redacted_features.get('role', '决策角色')}定位 · 我们准备了适配方案",
        ],
        "objection_responses": [],
        "closing": "方便约个时间 (15 分钟内) 详细沟通吗?",
    }

    try:
        from shared.llm_caller.client import LLMCaller
        from shared.llm_caller.provider import ProviderUnavailableError

        caller = LLMCaller(
            agent_id="channel",
            endpoint="/api/channel/personal_insight",
        )
        system = _build_system_prompt()
        user = (
            f"客户脱敏特征 (已 hash 原 PII):\n{json.dumps(redacted_features, ensure_ascii=False, indent=2)}\n\n"
            f"产品适配评估:\n{json.dumps(product_fit, ensure_ascii=False, indent=2)}\n\n"
            "请生成 JSON 含 opener / key_messages (≤ 5) / objection_responses "
            "(list[{objection, response}]) / closing 四字段."
        )
        try:
            result = caller.chat_json(
                system, user,
                schema_hint=(
                    '{"opener": str, "key_messages": [str], '
                    '"objection_responses": [{"objection": str, "response": str}], '
                    '"closing": str}'
                ),
                temperature=0.4,
            )
        except ProviderUnavailableError:
            logger.warning("[personal_insight] LLMCaller unavailable · fallback")
            return fallback
        payload = result.json_payload or {}
        if not isinstance(payload, dict):
            return fallback
        # schema 校验: 缺字段补 fallback 对应 key
        return {
            "opener": str(payload.get("opener") or fallback["opener"])[:200],
            "key_messages": [str(m)[:120] for m in (payload.get("key_messages") or [])][:5],
            "objection_responses": [
                {"objection": str(o.get("objection", ""))[:80], "response": str(o.get("response", ""))[:200]}
                for o in (payload.get("objection_responses") or [])
                if isinstance(o, dict)
            ][:5],
            "closing": str(payload.get("closing") or fallback["closing"])[:200],
        }
    except (ImportError, RuntimeError, ValueError, TypeError):
        return fallback


def _derive_product_fit(
    redacted_features: dict,
    candidate_industry: str = "",
) -> ProductFit:
    """从 redacted features 派生 product_fit · 确定性规则 (per §3.1 · LLM 不算 score)."""
    role = redacted_features.get("role", "")
    risk = redacted_features.get("risk_appetite", "")
    decision = redacted_features.get("decision_path", "")

    products: list[str] = []
    fit_reasons: list[str] = []
    miss_reasons: list[str] = []

    # 决策角色映射 (启发式 · 不调 LLM)
    if role in ("实际控制人", "法人代表"):
        products.append("流动资金贷款")
        fit_reasons.append("实际控制人决策权高 · 流动资金贷款响应快")
    elif role == "财务总监":
        products.append("供应链金融")
        fit_reasons.append("财务总监关注 cash flow · 供应链金融降低应收账款占用")
    elif role == "采购负责人":
        products.append("保理融资")
        fit_reasons.append("采购侧需账期管理 · 保理融资匹配")

    # 风险偏好映射
    if risk == "稳健":
        products.append("固定资产贷款")
        fit_reasons.append("稳健风险偏好 · 固定资产贷款利率优惠")
    elif risk == "激进":
        miss_reasons.append("激进偏好不适配中长期固定资产贷款 (期限不匹配)")

    # 决策路径
    if decision == "委员会":
        miss_reasons.append("委员会决策路径需多方拍板 · 短期产品 (≤ 3 个月) 拍板周期不匹配")

    # fit_score: 确定性公式 · # products * 30 + # reasons * 5 (cap 100)
    fit_score = min(100, len(products) * 30 + len(fit_reasons) * 5)

    return {
        "recommended_products": products or ["流动资金贷款"],
        "fit_score": fit_score if products else 30,
        "fit_reasons": fit_reasons,
        "miss_reasons": miss_reasons,
    }


def build_personal_insight(
    candidate_id: str,
    *,
    person_features: dict[str, Any] | None = None,
    candidate_industry: str = "",
) -> PersonalInsightPayload:
    """BE12 真业务实装 · 走 redact + sources + LLMCaller · 端到端 latency_ms.

    Args:
        candidate_id:        候选企业 ID (与 SSE candidates list 内 candidate_id 对齐)
        person_features:     可选 · 已 (尽可能) 脱敏的 features dict · 无则走默认占位
        candidate_industry:  可选 · 候选企业行业 · 用于 pbc_gov 政策扫 query keyword

    Returns:
        PersonalInsightPayload · pii_redacted=True if 任 PII 字段已 hash · 否则 False.

    实施细节:
    - LLM 走 shared/llm_caller (PIPL 境内 fallback chain)
    - PII 走 shared/personal_profile.PersonalProfile.redact (自带 hash + 年龄桶)
    - compliance 走 shared/sources Router (pbc_gov 政策) + 本地 PEP/sanction 关键词
    - latency_ms 端到端测量 (per B7 BE13 evaluation 维度 PII+latency 20%)
    """
    t0 = time.time()

    # Step 1 · 用 PersonalProfile + redact 构造脱敏 features
    pii_redacted = False
    redacted_features_dict: dict[str, Any] = {}
    if person_features:
        try:
            from shared.personal_profile import PersonalProfile
            profile = PersonalProfile.from_dict(person_features)
            redacted_dump = profile.redact()
            # 提取 person_insight schema 用到的字段
            redacted_features_dict = {
                "role": person_features.get("role", "未能自动填写"),
                "industry_yr": int(person_features.get("industry_yr", 0) or 0),
                "education": redacted_dump.get("education") or person_features.get("education", "未能自动填写"),
                "age_range": redacted_dump.get("age", "未能自动填写"),
                "risk_appetite": person_features.get("risk_appetite", "未能自动填写"),
                "decision_path": person_features.get("decision_path", "未能自动填写"),
            }
            pii_redacted = True
        except (ImportError, RuntimeError, ValueError, TypeError):
            logger.warning("[personal_insight] PersonalProfile.redact failed · raw features → 占位")
            redacted_features_dict = {
                k: person_features.get(k, "未能自动填写")
                for k in ("role", "industry_yr", "education", "age_range", "risk_appetite", "decision_path")
            }
    else:
        redacted_features_dict = {
            "role": "未能自动填写",
            "industry_yr": 0,
            "education": "未能自动填写",
            "age_range": "未能自动填写",
            "risk_appetite": "未能自动填写",
            "decision_path": "未能自动填写",
        }
        pii_redacted = True  # 没原 PII 输入 · 视作已 redact

    # Step 2 · 派生 product_fit (确定性 · 不调 LLM)
    product_fit = _derive_product_fit(redacted_features_dict, candidate_industry)

    # Step 3 · compliance check · 走 pbc_gov 政策扫 + 本地 PEP/sanction 关键词
    role = str(redacted_features_dict.get("role", ""))
    name_hashed = str(person_features.get("name", "") if person_features else "")  # 已 hash by upstream
    pep, sanction, local_hits = _check_local_sanction(role, name_hashed, redacted_features_dict)
    pbc_flags, pbc_sources = _query_pbc_policy_flags(role, candidate_industry)
    all_flags = list(pbc_flags) + list(local_hits)
    sources = list(pbc_sources)
    sources.append("local_pep_keywords")  # OFAC stub identifier

    # AML 风险综合判定 (确定性规则)
    if sanction:
        aml_risk = "高"
    elif pep or len(all_flags) >= 3:
        aml_risk = "中"
    else:
        aml_risk = "低"

    compliance_check: ComplianceCheck = {
        "pep": pep,
        "sanction": sanction,
        "aml_risk": aml_risk,
        "flags": all_flags,
        "last_checked": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "sources": sources,
    }

    # Step 4 · LLM grounded talking_points (走 shared/llm_caller · 8 段 system prompt)
    talking_points_raw = _grounded_talking_points(
        redacted_features_dict,
        dict(product_fit),
    )
    talking_points: TalkingPoints = {
        "opener": talking_points_raw["opener"],
        "key_messages": talking_points_raw["key_messages"],
        "objection_responses": talking_points_raw["objection_responses"],
        "closing": talking_points_raw["closing"],
    }

    # Step 5 · 输出 + latency_ms 端到端
    out: PersonalInsightPayload = {
        "candidate_id": candidate_id,
        "person_features": {
            "role": str(redacted_features_dict.get("role", "")),
            "industry_yr": int(redacted_features_dict.get("industry_yr", 0) or 0),
            "education": str(redacted_features_dict.get("education", "")),
            "age_range": str(redacted_features_dict.get("age_range", "")),
            "risk_appetite": str(redacted_features_dict.get("risk_appetite", "")),
            "decision_path": str(redacted_features_dict.get("decision_path", "")),
        },
        "product_fit": product_fit,
        "compliance_check": compliance_check,
        "talking_points": talking_points,
        "pii_redacted": pii_redacted,
        "latency_ms": int((time.time() - t0) * 1000),
    }
    return out
