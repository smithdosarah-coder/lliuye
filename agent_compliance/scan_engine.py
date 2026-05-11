# -*- coding: utf-8 -*-
"""Agent5 Compliance · Scan engine (Stage C.4 · onboarding W-C3-A3 compli-backend-complete).

新建 thin layer 之上 · 既有 ComplianceRadarAgent / RuleSetBuilder / EventExtractor /
MatrixMatcher 全保留 · 本模块面向 inline text input (新 POST endpoints):

1. **inline policy_doc + business_docs** → 抽规则 + 抽事件 + 矩阵比对 + 修订意见
2. **LLM 真接 (DeepSeek)** 解析政策 + 业务比对 · 不硬编关键词
3. **改 / 补 / 强 三类修订** LLM 生成 · 模板兜底
4. **Tavily 401 fallback** (Q-040) · 复用 Alert pattern
5. **持久化** `data/compliance/sessions/{scan_id}.json` + `latest.json`
6. **empty-state 协议** · 默认走真扫 · `force_mock=True` 时显式加载 demo session

不破坏：
- ComplianceRadarAgent / RuleSetBuilder / EventExtractor / MatrixMatcher 0 改动
- (注: GET `/api/compliance/policy_scan` Tavily 政策发现端点已下架 · batch 4 cleanup)
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPLI_DATA_DIR = PROJECT_ROOT / "data" / "compliance"
SESSIONS_DIR = COMPLI_DATA_DIR / "sessions"
LATEST_POINTER = COMPLI_DATA_DIR / "latest.json"


# ---------------------------------------------------------------------------
# Tavily 401 fallback provider (复用 Alert pattern · Q-040)
# ---------------------------------------------------------------------------


def build_compli_provider(*, force_mock: bool = False) -> tuple[Any, str]:
    """构建 Agent5 用 SearchProvider (合规外部政策发现 fallback).

    ALL IN Phase B step 3 (2026-05-09):
      - 删 COMPLI_USE_TAVILY env gate · 默认 demo_mode=False (key 在即试 live)
      - 不 silent fallback · 任一失败模式都通过 mode_label 显式传 frontend banner

    Returns:
        (provider, mode_label) where mode_label ∈ {
          "demo_forced":             force_mock=True · 用户显式
          "tavily_key_missing":      未配 TAVILY_API_KEY · → MOCK_FALLBACK banner
          "web_live":                Tavily 真接通 · → LIVE
          "web_fallback_<Err>":      Web init 抛错 · → MOCK_FALLBACK banner
        }
    """
    from shared.kb_scan.search_provider import build_search_provider

    if force_mock:
        return build_search_provider(demo_mode=True), "demo_forced"

    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        return build_search_provider(demo_mode=True), "tavily_key_missing"

    try:
        web = build_search_provider(demo_mode=False, api_keys={"tavily": tavily_key})
    except (RuntimeError, ValueError, ImportError, OSError, AttributeError) as e:
        return build_search_provider(demo_mode=True), f"web_fallback_{type(e).__name__}"

    return web, "web_live"


# ---------------------------------------------------------------------------
# LLM caller wrapper · 走 shared.llm_caller · PIPL 境内优先 fallback chain
# (deepseek 主 + dashscope 备 · per A2 V2 cat 7-5 · §3.6 LLM Caller 唯一化)
# 任一 provider 配 key 即返 caller · 全无 key → None (上层模板兜底)
# ---------------------------------------------------------------------------


_LLM_CALLER_AGENT_ID = "compliance"
_LLM_CALLER_ENDPOINT = "/api/compliance/policy_scan"


def _any_llm_provider_key_present() -> bool:
    """检 fallback chain 头部 provider 是否至少 1 个 key 配齐 (PIPL 境内 chain)."""
    for key_env in ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"):
        if os.environ.get(key_env, "").strip():
            return True
    return False


def build_llm_caller():
    """构造 (system, user) -> str caller · 全无 key 返 None (兜底 fallback)·

    迁 shared.llm_caller (per A2 V2 cat 7-5) · 内部走 fallback chain · audit log 自动留痕.
    保持 None 短路语义不变 · 让 has_llm flag 与 run_policy_scan_and_persist 上层逻辑一致.
    """
    if not _any_llm_provider_key_present():
        return None
    try:
        from shared.llm_caller import make_text_caller
        return make_text_caller(
            agent_id=_LLM_CALLER_AGENT_ID,
            endpoint=_LLM_CALLER_ENDPOINT,
            temperature=0.2,
        )
    except (ImportError, RuntimeError, ValueError, OSError):
        return None


def build_llm_json_caller():
    """构造 (system, user, schema_hint) -> dict|list|None caller · 全无 key 返 None.

    迁 shared.llm_caller · JSON path · fallback chain (deepseek 主 / dashscope 备) ·
    上层 matrix_check / extract_rules / generate_revisions 等保持 None 兜底语义.
    """
    if not _any_llm_provider_key_present():
        return None
    try:
        from shared.llm_caller import make_json_caller
        return make_json_caller(
            agent_id=_LLM_CALLER_AGENT_ID,
            endpoint=_LLM_CALLER_ENDPOINT,
            temperature=0.2,
        )
    except (ImportError, RuntimeError, ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


POLICY_RULE_EXTRACT_SYSTEM = (
    "你是银行合规专家。任务：从给定的监管政策原文中抽取条款规则。"
    "要求：每条规则带 rule_id / article / category / condition / threshold（如有量化阈值） / severity_hint。"
    "**严格基于原文** · 不允许编造数字 · 阈值取不到留空。"
)


def _policy_rule_extract_user(policy_text: str) -> str:
    return (
        f"【监管政策原文（前 6000 字）】\n{policy_text[:6000]}\n\n"
        "【输出要求】\n"
        "严格 JSON list · 每元素 schema:\n"
        '{"rule_id": "POL-001", "article": "第六条", '
        '"category": "期限/额度/流程/披露/时效/身份识别/其他", '
        '"condition": "自然语言条件", '
        '"threshold": {"max_months": 12} 或 {} 若无量化, '
        '"severity_hint": "critical/major/minor"}\n\n'
        "返回 list 形式 (顶层就是 array · 不要套字典)。"
    )


BUSINESS_EVENT_EXTRACT_SYSTEM = (
    "你是合规事件抽取专家。任务：从业务记录中抽取事件结构。"
    "要求：每事件带 event_id / event_type / fields。"
    "fields 为业务字段 dict · **严格基于原文** · 不编造金额。"
)


def _business_event_extract_user(business_text: str, doc_type: str = "") -> str:
    return (
        f"【业务记录（{doc_type or 'unknown'}）（前 4000 字）】\n{business_text[:4000]}\n\n"
        "【输出要求】\n"
        "严格 JSON list · 每元素 schema:\n"
        '{"event_id": "...", "event_type": "loan/cooperation/model/large_txn/...", '
        '"fields": {...}}\n\n'
        "顶层就是 array · 不要套字典。"
    )


MATRIX_JUDGE_SYSTEM = (
    "你是合规判定专家。给定一条规则 + 一条事件 · 判断该事件是否违反规则。"
    "**只能基于事件的客观字段** · 不允许臆测。"
)


def _matrix_judge_user(rule: dict, event: dict) -> str:
    return (
        f"【规则】\n{json.dumps(rule, ensure_ascii=False, indent=2)}\n\n"
        f"【事件】\n{json.dumps(event, ensure_ascii=False, indent=2)}\n\n"
        "【输出要求】严格 JSON：\n"
        '{"status": "violate/comply/not_applicable", '
        '"severity": "critical/major/minor/none", '
        '"evidence": "事件原文片段", '
        '"match_reason": "一句话说明为何违反/合规/不适用"}'
    )


REVISION_SYSTEM = (
    "你是银行合规修订专家。给定一条违规命中 · 输出三类修订建议 (改/补/强):\n"
    "- 改 (modify): 业务条款明确违反新政策 · 修改原条款\n"
    "- 补 (supplement): 业务条款未覆盖新政策要求 · 补充新条款\n"
    "- 强 (strengthen): 业务条款部分覆盖但松散 · 强化要求\n"
    "**严格基于命中信息** · 不编造条款编号 · 每类只给最贴切的一条 · 单条 60-120 字。\n"
    "**合规官 actionable**: 每条建议必含 (责任部门 + 时限 + 触发条件) · "
    "按 severity 推荐 disposition (critical=暂停 法律部 review · major=强制整改 14d 内 · "
    "minor=监测 风险提示)。\n"
    "**示例 (改类 · 政策刚性约束优先 per PB#2 不可照搬 #1)**: "
    "「针对银保监〔2025〕12 号第 3 条单笔上限要求 · 业务部门 14d 内将《对私贷款管理办法》"
    "第 X 条单笔最高额度由 50 万下调至 30 万 · 同步系统硬控配置 · 合规终审签字后生效」。"
)


def _revision_user(violation: dict) -> str:
    return (
        f"【命中违规】\n{json.dumps(violation, ensure_ascii=False, indent=2)}\n\n"
        "【输出要求】严格 JSON · 顶层 array · 包含 1-3 个对象 (按 改/补/强 顺序选最贴切):\n"
        '[{"category": "改", "title": "...", "text": "..."}, '
        '{"category": "补", "title": "...", "text": "..."}, '
        '{"category": "强", "title": "...", "text": "..."}]\n\n'
        "若只有一类适用 · 只返一项 · 不要凑数。"
    )


# ---------------------------------------------------------------------------
# Inline rule + event extraction
# ---------------------------------------------------------------------------


def extract_rules_from_policy_text(
    policy_text: str,
    *,
    llm_json_caller=None,
) -> list[dict]:
    """从政策文本抽规则 list[dict] · LLM 优先 · 失败回退正则启发式."""
    if not policy_text or not policy_text.strip():
        return []

    if llm_json_caller is not None:
        try:
            result = llm_json_caller(
                POLICY_RULE_EXTRACT_SYSTEM,
                _policy_rule_extract_user(policy_text),
                schema_hint="list[{rule_id, article, category, condition, threshold, severity_hint}]",
            )
            rules = _normalize_rule_list(result)
            if rules:
                return rules
        except (RuntimeError, ValueError, OSError):
            pass

    return _heuristic_extract_rules(policy_text)


def _normalize_rule_list(raw: Any) -> list[dict]:
    """LLM 返回 normalize · 容忍 list / {items: list} / 各种字段缺失."""
    if isinstance(raw, dict):
        for key in ("rules", "items", "data"):
            if key in raw and isinstance(raw[key], list):
                raw = raw[key]
                break
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for i, r in enumerate(raw):
        if not isinstance(r, dict):
            continue
        rule = {
            "rule_id": str(r.get("rule_id") or f"POL-{i+1:03d}").strip(),
            "article": str(r.get("article") or "").strip(),
            "category": str(r.get("category") or "其他").strip(),
            "condition": str(r.get("condition") or "").strip(),
            "threshold": r.get("threshold") or {},
            "severity_hint": str(r.get("severity_hint") or "major").strip().lower(),
        }
        if not rule["condition"]:
            continue
        out.append(rule)
    return out


_ARTICLE_RE = re.compile(r"第\s*([一二三四五六七八九十百零\d]+)\s*条[\s:：]*([^\n。；]{8,200})")

# Heuristic threshold patterns · LLM 不可用时也能识别简单数字阈值
# 不是黑名单 · 是结构化语言模板（CLAUDE.md §12 「通用机制不黑名单兜底」原则下属于
# 「定量约束的语言形态有限可枚举」类）。
_THRESHOLD_PATTERNS = [
    # "不超过 X 个月" / "≤ X 月" / "不得超过 X 月" → max_months
    (re.compile(r"(?:不(?:得|应)?超过|不\s*高于|≤|<=)\s*(\d+(?:\.\d+)?)\s*(?:个)?月"),
     "max_months", float),
    # "不低于 X%" / "≥ X%" / "不得低于 X 成" → min_ratio (转小数)
    (re.compile(r"(?:不(?:得|应)?低于|不\s*少于|≥|>=)\s*(\d+(?:\.\d+)?)\s*%"),
     "min_bank_share_ratio", lambda x: float(x) / 100.0),
    # "不超过 X 万元" / "不得超过 X 元" → max_amount
    (re.compile(r"(?:不(?:得|应)?超过|≤|<=)\s*(\d+(?:\.\d+)?)\s*万元"),
     "max_amount_wan", float),
]


def _heuristic_threshold(condition_text: str) -> dict:
    """从条款文本提取量化阈值 · LLM 不可用时的兜底."""
    threshold: dict = {}
    for regex, key, conv in _THRESHOLD_PATTERNS:
        m = regex.search(condition_text)
        if m:
            try:
                threshold[key] = conv(m.group(1))
            except (ValueError, TypeError):
                continue
    return threshold


def _heuristic_extract_rules(policy_text: str) -> list[dict]:
    """LLM 不可用时的兜底 · 用「第 X 条」正则切分政策 + 简单阈值识别."""
    rules = []
    for i, m in enumerate(_ARTICLE_RE.finditer(policy_text)):
        article_no, body = m.group(1), m.group(2).strip()
        if not body:
            continue
        threshold = _heuristic_threshold(body)
        rules.append({
            "rule_id": f"POL-{i+1:03d}",
            "article": f"第{article_no}条",
            "category": "其他",
            "condition": body[:160],
            "threshold": threshold,
            "severity_hint": "major",
        })
    return rules


def extract_events_from_business_docs(
    business_docs: list[Any],
    *,
    llm_json_caller=None,
) -> list[dict]:
    """从业务文档列表抽事件 list[dict].

    business_docs 可以是:
      - list[str] · 每条是业务记录文本
      - list[dict] · 每条已经是结构化事件（直接 normalize 通过）
      - 混合
    """
    events: list[dict] = []
    for idx, doc in enumerate(business_docs or []):
        if isinstance(doc, dict):
            events.append(_normalize_event_dict(doc, idx))
            continue
        if isinstance(doc, str) and doc.strip():
            events.extend(_extract_events_from_text(doc, idx, llm_json_caller))
    return events


def _normalize_event_dict(d: dict, idx: int) -> dict:
    return {
        "event_id": str(d.get("event_id") or d.get("id") or f"EVT-{idx+1:04d}").strip(),
        "event_type": str(d.get("event_type") or d.get("type") or "loan").strip(),
        "fields": d.get("fields") or {k: v for k, v in d.items()
                                       if k not in ("event_id", "id", "event_type", "type", "fields")},
    }


def _extract_events_from_text(text: str, idx: int, llm_caller) -> list[dict]:
    if llm_caller is not None:
        try:
            raw = llm_caller(
                BUSINESS_EVENT_EXTRACT_SYSTEM,
                _business_event_extract_user(text),
                schema_hint="list[{event_id, event_type, fields}]",
            )
            if isinstance(raw, list) and raw:
                return [_normalize_event_dict(d, i + idx) for i, d in enumerate(raw) if isinstance(d, dict)]
        except (RuntimeError, ValueError, OSError):
            pass
    # heuristic 兜底：把整段文本作为单事件
    return [{
        "event_id": f"EVT-TXT-{idx+1:04d}",
        "event_type": "text_fragment",
        "fields": {"raw": text[:300]},
    }]


# ---------------------------------------------------------------------------
# Matrix check (N×M)
# ---------------------------------------------------------------------------


def matrix_check(
    rules: list[dict],
    events: list[dict],
    *,
    llm_json_caller=None,
) -> dict:
    """N×M 矩阵比对 · 硬规则 fast path + LLM slow path.

    Returns:
      {
        "rule_count": N,
        "event_count": M,
        "cell_count": N*M,
        "violations": list[dict] · 每条 {rule_id, event_id, severity, evidence, match_reason},
        "matrix": [[cell_status, ...], ...] · 二维 (rule × event)
      }
    """
    n, m = len(rules), len(events)
    cells: list[list[str]] = [["not_applicable"] * m for _ in range(n)]
    violations: list[dict] = []

    for i, rule in enumerate(rules):
        for j, event in enumerate(events):
            cell = _judge_cell(rule, event, llm_json_caller)
            cells[i][j] = cell["status"]
            if cell["status"] == "violate":
                violations.append({
                    "violation_id": f"VIO-{len(violations)+1:03d}",
                    "rule_id": rule["rule_id"],
                    "rule_article": rule.get("article", ""),
                    "rule_condition": rule.get("condition", ""),
                    "rule_category": rule.get("category", ""),
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "event_fields": event.get("fields", {}),
                    "severity": cell.get("severity", "major"),
                    "evidence": cell.get("evidence", ""),
                    "match_reason": cell.get("match_reason", ""),
                })

    return {
        "rule_count": n,
        "event_count": m,
        "cell_count": n * m,
        "violations": violations,
        "matrix": cells,
    }


def _judge_cell(rule: dict, event: dict, llm_json_caller) -> dict:
    """单格判定 · 优先 hard rule (基于 threshold) · 不能判则走 LLM · LLM 也不能则 N/A."""
    hard = _hard_rule_judge(rule, event)
    if hard is not None:
        return hard

    if llm_json_caller is not None:
        try:
            raw = llm_json_caller(
                MATRIX_JUDGE_SYSTEM,
                _matrix_judge_user(rule, event),
                schema_hint="{status, severity, evidence, match_reason}",
            )
            if isinstance(raw, dict) and raw.get("status") in {"violate", "comply", "not_applicable"}:
                return {
                    "status": raw["status"],
                    "severity": raw.get("severity", "minor"),
                    "evidence": str(raw.get("evidence", ""))[:200],
                    "match_reason": str(raw.get("match_reason", ""))[:200],
                }
        except (RuntimeError, ValueError, OSError):
            pass

    return {"status": "not_applicable", "severity": "none", "evidence": "", "match_reason": "无硬规则可判 · LLM 不可用"}


def _hard_rule_judge(rule: dict, event: dict) -> dict | None:
    """硬规则 fast path · 利用 threshold dict 做结构化比较 · 命中返结果 · 不命中返 None 让 LLM 接."""
    threshold = rule.get("threshold") or {}
    if not isinstance(threshold, dict) or not threshold:
        return None
    fields = event.get("fields") or {}

    # max_X 检查 (event.fields.X > threshold.max_X → violate)
    for key, limit in threshold.items():
        if not isinstance(limit, (int, float)):
            continue
        if not key.startswith("max_"):
            continue
        field_name = key[4:]                 # "max_months" → "months"
        # 兼容多种命名
        for fkey in (field_name, f"duration_{field_name}", f"{field_name}_value"):
            if fkey in fields:
                actual = fields[fkey]
                try:
                    actual = float(actual)
                except (TypeError, ValueError):
                    continue
                if actual > float(limit):
                    return {
                        "status": "violate",
                        "severity": rule.get("severity_hint", "major"),
                        "evidence": f"{fkey}={actual} 超阈值 {key}={limit}",
                        "match_reason": f"事件 {event.get('event_id')} {fkey}={actual} > 上限 {limit}",
                    }
                return {
                    "status": "comply",
                    "severity": "none",
                    "evidence": f"{fkey}={actual} ≤ {limit}",
                    "match_reason": "硬规则比较通过",
                }

    # min_ratio_X 检查 (event.fields.X < threshold.min_ratio_X → violate)
    for key, limit in threshold.items():
        if not isinstance(limit, (int, float)):
            continue
        if not key.startswith("min_"):
            continue
        field_name = key[4:]
        for fkey in (field_name, f"{field_name}_ratio", f"{field_name}_pct"):
            if fkey in fields:
                actual = fields[fkey]
                try:
                    actual = float(actual)
                except (TypeError, ValueError):
                    continue
                if actual < float(limit):
                    return {
                        "status": "violate",
                        "severity": rule.get("severity_hint", "major"),
                        "evidence": f"{fkey}={actual} 低于阈值 {key}={limit}",
                        "match_reason": f"事件 {event.get('event_id')} {fkey}={actual} < 下限 {limit}",
                    }
                return {
                    "status": "comply",
                    "severity": "none",
                    "evidence": f"{fkey}={actual} ≥ {limit}",
                    "match_reason": "硬规则比较通过",
                }

    return None


# ---------------------------------------------------------------------------
# Revision generation (改 / 补 / 强)
# ---------------------------------------------------------------------------


REVISION_CATEGORIES = ("改", "补", "强")


def generate_revisions(
    violation: dict,
    *,
    llm_json_caller=None,
) -> list[dict]:
    """为单条违规生成改/补/强修订建议 list.

    Returns:
      list[{category: "改"|"补"|"强", title, text}] · 1-3 项 (LLM 选最贴切)
    """
    if llm_json_caller is not None:
        try:
            raw = llm_json_caller(
                REVISION_SYSTEM,
                _revision_user(violation),
                schema_hint="list[{category, title, text}]",
            )
            normalized = _normalize_revisions(raw)
            if normalized:
                return normalized
        except (RuntimeError, ValueError, OSError):
            pass
    return _template_revisions(violation)


def _normalize_revisions(raw: Any) -> list[dict]:
    if isinstance(raw, dict):
        for key in ("revisions", "items", "data"):
            if key in raw and isinstance(raw[key], list):
                raw = raw[key]
                break
    if not isinstance(raw, list):
        return []
    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        cat = str(r.get("category") or "").strip()
        if cat not in REVISION_CATEGORIES:
            continue
        out.append({
            "category": cat,
            "title": str(r.get("title") or "").strip(),
            "text": str(r.get("text") or "").strip(),
        })
    return out


def _template_revisions(violation: dict) -> list[dict]:
    """LLM 不可用时的模板兜底 · severity 映射 disposition + 合规官 actionable
    (per docs/contracts/agent-output-rubric-2026-05-11.md §3.4 compliance · audit P1)."""
    severity = violation.get("severity", "major")
    rule_article = violation.get("rule_article", "新政策条款")
    rule_id = violation.get("rule_id", "")
    event_id = violation.get("event_id", "")
    event_type = violation.get("event_type", "")
    conflict = violation.get("reason", {}).get("conflict_field") or violation.get("rule_category", "")
    # severity → disposition 动作映射 (合规 desk 视角 · 不引入 schema enum)
    disposition_map = {
        "critical": ("暂停 / 法律部 review", "立即暂停本笔业务 · 法律部 7d 内 review 该政策条款"),
        "major": ("强制整改", "合规官下发整改单 · 业务部门 14d 内完成条款修订"),
        "minor": ("监测 + 风险提示", "纳入下月合规通报 · 风险经理监测同类事件"),
    }
    disp_label, disp_action = disposition_map.get(severity, disposition_map["major"])
    return [{
        "category": "改",
        "title": f"修订条款以匹配 {rule_article} · disposition: {disp_label}",
        "text": (
            f"业务事件 {event_id}（{event_type}）冲突字段「{conflict}」"
            f"触发 {rule_id} {rule_article} · 严重程度 {severity} · "
            f"建议: {disp_action} · 业务条款责任部门同步修订对应字段定义、阈值与触发规则 · "
            "修订稿提交合规专家终审."
        ),
    }]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def persist_scan_result(payload: dict, *, scan_id: str = "") -> str:
    """落盘 + 更新 latest pointer · 返 scan_id."""
    _ensure_dirs()
    sid = (scan_id or payload.get("scan_id") or "").strip() or f"compli-{uuid.uuid4().hex[:12]}"
    payload["scan_id"] = sid
    payload.setdefault("generated_at", datetime.now().isoformat(timespec="seconds"))

    out_path = SESSIONS_DIR / f"{sid}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        rel_path = str(out_path.relative_to(PROJECT_ROOT))
    except ValueError:
        try:
            rel_path = os.path.relpath(out_path, PROJECT_ROOT)
        except ValueError:
            rel_path = str(out_path)
    LATEST_POINTER.write_text(
        json.dumps({"scan_id": sid, "path": rel_path}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return sid


class ScanResultNotFoundError(FileNotFoundError):
    """scan_id 对应文件不存在."""


def load_scan_result(scan_id: str = "") -> dict:
    if scan_id:
        path = SESSIONS_DIR / f"{scan_id}.json"
        if not path.is_file():
            raise ScanResultNotFoundError(f"scan_id={scan_id} not found at {path}")
        return json.loads(path.read_text(encoding="utf-8"))
    if not LATEST_POINTER.is_file():
        raise ScanResultNotFoundError(
            "尚无任何扫描记录 · 先调 POST /api/compliance/policy_scan 生成 scan"
        )
    pointer = json.loads(LATEST_POINTER.read_text(encoding="utf-8"))
    return load_scan_result(pointer["scan_id"])


# ---------------------------------------------------------------------------
# 高层封装：run_policy_scan_and_persist (供 SSE endpoint 调用)
# ---------------------------------------------------------------------------


def _registry_rules_for_policy(
    policy_doc: str, policy_meta: dict | None,
) -> tuple[list[dict], dict]:
    """Run the deterministic loader path when policy_meta has enough metadata.

    Returns (rules, registry_info). When metadata is too thin to register
    a stable policy (title + issuer required), returns ([], {}) so the
    caller falls back to the LLM/heuristic path.

    BE4 (Phase B Sprint 2 · 2026-05-04): registry rules carry
    clause_id/policy_id/version_id so downstream matrix_check violations
    can be enriched with auditable ViolationReason rows. When this path
    runs, every "violate" cell yields a fully-populated 7-field reason.
    """
    meta = policy_meta or {}
    title = (meta.get("title") or "").strip()
    issuer = (meta.get("issuer") or "").strip()
    if not (title and issuer):
        return [], {}
    try:
        from agent_compliance.policy_loader import (
            clauses_to_scan_rules,
            load_policy,
        )
        from shared.policy_registry import get_clauses
    except ImportError:
        return [], {}

    try:
        result = load_policy(
            title=title,
            issuer=issuer,
            body_text=policy_doc,
            effective_date=str(meta.get("effective_date") or ""),
            source_url=str(meta.get("source_url") or ""),
            category=str(meta.get("category") or ""),
            description=str(meta.get("description") or ""),
        )
    except (RuntimeError, ValueError, OSError, AttributeError):
        return [], {}

    clauses = get_clauses(result.version_id)
    rules = clauses_to_scan_rules(clauses)
    # Stamp the policy_id / version_id so build_violation_reason can read them.
    for r in rules:
        r["policy_id"] = result.policy_id
        r["version_id"] = result.version_id

    return rules, {
        "policy_id": result.policy_id,
        "version_id": result.version_id,
        "is_new_version": result.is_new_version,
        "clause_count": len(clauses),
    }


_CLIENT_NAME_ALIASES = ("client", "client_name", "customer", "customer_name", "企业名", "企业名称", "公司")
_CLIENT_USCC_ALIASES = ("client_uscc", "uscc", "USCC", "credit_code", "统一社会信用代码", "社会信用代码")


def _extract_client_fields(violation: dict) -> tuple[str, str]:
    """从 violation.event_fields 抽 client + client_uscc · 用于 ensure_candidate_id.

    业务事件有多种字段名 · 容错扫几个常见 alias.
    返 ("", "") 时 ensure_candidate_id 退化到 cand_<idx> 兜底.
    """
    fields = violation.get("event_fields") or {}
    if not isinstance(fields, dict):
        return "", ""
    name = ""
    uscc = ""
    for k in _CLIENT_NAME_ALIASES:
        if isinstance(fields.get(k), str) and fields[k].strip():
            name = fields[k].strip()
            break
    for k in _CLIENT_USCC_ALIASES:
        if isinstance(fields.get(k), str) and fields[k].strip():
            uscc = fields[k].strip()
            break
    return name, uscc


def _ensure_violation_ids(violations: list[dict]) -> list[dict]:
    """ALL IN step 5 (per candidate-identity-contract v1.1):

    每条 violation 出 unique `id` 字段 (按 client + client_uscc 派生 · cand_<idx> 兜底).
    保 violation_id (VIO-NNN) backwards-compat · 仅添加新 id 字段.

    业务事件字段 client / client_uscc 多 alias 容错抽取 · 缺失走 cand_<idx>.
    """
    try:
        from shared.entity_resolver import ensure_list_unique_ids
    except ImportError:
        # shared.entity_resolver 缺 · in-place 兜底 cand_NNN
        for idx, v in enumerate(violations):
            v.setdefault("id", f"cand_{idx:03d}")
        return violations

    # 把 client / client_uscc 平铺到 violation 顶层 · 让 ensure_candidate_id 能取
    for v in violations:
        client, client_uscc = _extract_client_fields(v)
        v.setdefault("client", client)
        v.setdefault("client_uscc", client_uscc)

    ensure_list_unique_ids(
        violations,
        name_field="client",
        uscc_field="client_uscc",
        id_field="id",
    )
    return violations


def _enrich_violations_with_reasons(
    violations: list[dict],
    rules_by_id: dict[str, dict],
    events_by_id: dict[str, dict],
    *,
    policy_meta: dict | None = None,
    retrieved_at: str | None = None,
) -> list[dict]:
    """Attach an 8-field ViolationReason + 3 freshness fields to every registry-aware violation.

    For non-registry rules (LLM fallback path with no clause_id/POL-/VER-),
    sets `reason = None` so the SSE schema is still consistent — frontends
    can render "未能自动填写" rather than guessing.

    ALL IN Phase B step 4 (2026-05-09):
      - 透传 policy_meta + retrieved_at 到 build_violation_reason
      - clause_text_hash + freshness 三字段同步入 reason dict (SSE 真到 frontend)

    Pure-additive: existing violation keys (rule_id, severity, evidence,
    match_reason, revisions, …) are untouched.
    """
    try:
        from agent_compliance.violation_schema import build_violation_reason
    except ImportError:
        for v in violations:
            v.setdefault("reason", None)
        return violations

    for v in violations:
        rule = rules_by_id.get(v.get("rule_id", ""))
        event = events_by_id.get(v.get("event_id", ""))
        if not rule or not event:
            v.setdefault("reason", None)
            continue
        cell = {
            "status": "violate",
            "evidence": v.get("evidence", ""),
            "match_reason": v.get("match_reason", ""),
        }
        try:
            reason = build_violation_reason(
                rule=rule,
                event=event,
                cell=cell,
                policy_meta=policy_meta,
                retrieved_at=retrieved_at,
            )
        except (RuntimeError, ValueError, AttributeError):
            reason = None
        v["reason"] = reason.to_dict() if reason is not None else None
    return violations


def run_policy_scan_and_persist(
    *,
    policy_doc: str,
    business_docs: list[Any],
    policy_meta: dict | None = None,
    force_mock: bool = False,
) -> Generator[dict, None, str]:
    """走完整 4 阶段 + 生成修订 + 持久化 · yield SSE-friendly events · 返 scan_id.

    阶段:
      1. rule_extract       · 政策 → 规则 list (registry-aware when policy_meta has title+issuer)
      2. event_extract      · 业务 → 事件 list
      3. matrix_match       · N×M 矩阵 + 命中违规 list
      4. revision_generate  · 每违规生成 改/补/强 + 7-field ViolationReason
    """
    _, mode_label = build_compli_provider(force_mock=force_mock)
    yield {"type": "tool_result", "tool": "compli_provider",
           "result": f"mode={mode_label}"}

    llm_json = build_llm_json_caller()
    has_llm = llm_json is not None
    yield {"type": "tool_result", "tool": "llm",
           "result": f"deepseek={'live' if has_llm else 'unavailable_template_fallback'}"}

    # ALL IN step 3: LLM 不可用时降级 mode_label · 不假装 web_live
    # 真业务依赖 LLM 抽规则 / 抽事件 / 矩阵判定 · 全无 LLM 走 heuristic 不算 live
    if mode_label == "web_live" and not has_llm:
        mode_label = "llm_unavailable_heuristic"

    # Phase 1 · prefer deterministic registry path; fall back to LLM/heuristic
    yield {"type": "stage", "stage": "rule_extract", "status": "running"}
    t0 = time.time()
    rules, registry_info = _registry_rules_for_policy(policy_doc, policy_meta)
    rule_path = "registry" if rules else "heuristic"
    if not rules:
        rules = extract_rules_from_policy_text(policy_doc, llm_json_caller=llm_json)
    yield {"type": "stage", "stage": "rule_extract", "status": "done",
           "count": len(rules), "duration_s": round(time.time() - t0, 2),
           "path": rule_path}

    # Phase 2
    yield {"type": "stage", "stage": "event_extract", "status": "running"}
    t1 = time.time()
    events = extract_events_from_business_docs(business_docs, llm_json_caller=llm_json)
    yield {"type": "stage", "stage": "event_extract", "status": "done",
           "count": len(events), "duration_s": round(time.time() - t1, 2)}

    # Phase 3
    yield {"type": "stage", "stage": "matrix_match", "status": "running",
           "total_cells": len(rules) * len(events)}
    t2 = time.time()
    matrix = matrix_check(rules, events, llm_json_caller=llm_json)
    yield {"type": "stage", "stage": "matrix_match", "status": "done",
           "violations": len(matrix["violations"]),
           "duration_s": round(time.time() - t2, 2)}

    # Phase 4 · revisions for each violation + 7-field ViolationReason
    yield {"type": "stage", "stage": "revision_generate", "status": "running",
           "total": len(matrix["violations"])}
    t3 = time.time()
    enriched_violations: list[dict] = []
    for v in matrix["violations"]:
        revisions = generate_revisions(v, llm_json_caller=llm_json)
        v["revisions"] = revisions
        enriched_violations.append(v)

    rules_by_id = {r.get("rule_id", ""): r for r in rules}
    events_by_id = {e.get("event_id", ""): e for e in events}
    # ALL IN step 4: 透传 policy_meta + retrieved_at (今天) · build_violation_reason 算 freshness
    retrieved_at_iso = datetime.now().date().isoformat()
    enriched_violations = _enrich_violations_with_reasons(
        enriched_violations,
        rules_by_id,
        events_by_id,
        policy_meta=policy_meta,
        retrieved_at=retrieved_at_iso,
    )

    # ALL IN step 5 (per candidate-identity-contract v1.1 §3 + ensure_*):
    # 每条 violation 必出 unique id 字段 (按 client + client_uscc 派生 · cand_<idx> 兜底)
    # 旧 violation_id (VIO-NNN) 保留 backwards-compat · 前端可优先消费新 id 字段
    enriched_violations = _ensure_violation_ids(enriched_violations)
    reason_count = sum(1 for v in enriched_violations if v.get("reason"))
    yield {"type": "stage", "stage": "revision_generate", "status": "done",
           "duration_s": round(time.time() - t3, 2),
           "reason_filled": reason_count}

    # Persist
    payload = {
        "scan_id": "",
        "mode": mode_label,
        "policy_meta": policy_meta or {},
        "rule_path": rule_path,
        "registry_info": registry_info,
        "rule_count": matrix["rule_count"],
        "event_count": matrix["event_count"],
        "cell_count": matrix["cell_count"],
        "rules": rules,
        "events": events,
        "matrix": matrix["matrix"],
        "violations": enriched_violations,
        "stats": {
            "rule_count": matrix["rule_count"],
            "event_count": matrix["event_count"],
            "cell_count": matrix["cell_count"],
            "violation_count": len(enriched_violations),
            "reason_filled_count": reason_count,
            "severe_count": sum(1 for v in enriched_violations if v.get("severity") == "critical"),
            "normal_count": sum(1 for v in enriched_violations if v.get("severity") == "major"),
            "observation_count": sum(1 for v in enriched_violations if v.get("severity") == "minor"),
        },
    }
    sid = persist_scan_result(payload)
    yield {"type": "scan", "scan_id": sid, "stats": payload["stats"]}
    return sid
