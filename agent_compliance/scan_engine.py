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

    Returns:
        (provider, mode_label) where mode_label ∈ {
          "demo_forced":             force_mock=True · 用户显式
          "tavily_disabled":         COMPLI_USE_TAVILY 未开
          "tavily_key_missing":      未配 TAVILY_API_KEY
          "web_live":                Tavily 真接通
          "web_fallback_<Err>":      Web init 抛错 · 自动降级 mock
        }
    """
    from shared.kb_scan.search_provider import build_search_provider

    if force_mock:
        return build_search_provider(demo_mode=True), "demo_forced"

    use_web = os.environ.get("COMPLI_USE_TAVILY", "0").strip() in {"1", "true", "yes"}
    if not use_web:
        return build_search_provider(demo_mode=True), "tavily_disabled"

    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        return build_search_provider(demo_mode=True), "tavily_key_missing"

    try:
        web = build_search_provider(demo_mode=False, api_keys={"tavily": tavily_key})
    except (RuntimeError, ValueError, ImportError, OSError, AttributeError) as e:
        return build_search_provider(demo_mode=True), f"web_fallback_{type(e).__name__}"

    return web, "web_live"


# ---------------------------------------------------------------------------
# LLM caller wrapper · 自动用 DEEPSEEK_API_KEY · 缺 key 返 None (走模板兜底)
# ---------------------------------------------------------------------------


def build_llm_caller():
    """构造 (system, user) -> str caller · 缺 key 返 None."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from llm import LLMClient
        client = LLMClient(provider="deepseek", api_key=api_key)
        def caller(system: str, user: str) -> str:
            return (client.simple_chat(system, user, temperature=0.2) or "").strip()
        return caller
    except (ImportError, RuntimeError, ValueError, OSError):
        return None


def build_llm_json_caller():
    """构造 (system, user, schema_hint) -> dict|list caller · 缺 key 返 None."""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from llm import LLMClient
        client = LLMClient(provider="deepseek", api_key=api_key)
        def caller(system: str, user: str, schema_hint: str = "") -> Any:
            try:
                return client.chat_json(system, user, schema_hint=schema_hint, temperature=0.2)
            except (RuntimeError, ValueError):
                return None
        return caller
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
    "**严格基于命中信息** · 不编造条款编号 · 每类只给最贴切的一条 · 单条 60-120 字。"
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
    """LLM 不可用时的模板兜底 · 按 severity 给一条 改 类建议."""
    severity = violation.get("severity", "major")
    rule_article = violation.get("rule_article", "新政策条款")
    return [{
        "category": "改",
        "title": f"修改业务条款以匹配 {rule_article}",
        "text": (
            f"业务事件 {violation.get('event_id', '')} 触发 {rule_article} · "
            f"严重程度 {severity} · 模板兜底建议：修改相关业务条款 ·"
            "确保字段满足新规要求 (具体修改细节需合规专家复核)"
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


def run_policy_scan_and_persist(
    *,
    policy_doc: str,
    business_docs: list[Any],
    policy_meta: dict | None = None,
    force_mock: bool = False,
) -> Generator[dict, None, str]:
    """走完整 4 阶段 + 生成修订 + 持久化 · yield SSE-friendly events · 返 scan_id.

    阶段:
      1. rule_extract       · 政策 → 规则 list
      2. event_extract      · 业务 → 事件 list
      3. matrix_match       · N×M 矩阵 + 命中违规 list
      4. revision_generate  · 每违规生成 改/补/强
    """
    _, mode_label = build_compli_provider(force_mock=force_mock)
    yield {"type": "tool_result", "tool": "compli_provider",
           "result": f"mode={mode_label}"}

    llm_json = build_llm_json_caller()
    has_llm = llm_json is not None
    yield {"type": "tool_result", "tool": "llm",
           "result": f"deepseek={'live' if has_llm else 'unavailable_template_fallback'}"}

    # Phase 1
    yield {"type": "stage", "stage": "rule_extract", "status": "running"}
    t0 = time.time()
    rules = extract_rules_from_policy_text(policy_doc, llm_json_caller=llm_json)
    yield {"type": "stage", "stage": "rule_extract", "status": "done",
           "count": len(rules), "duration_s": round(time.time() - t0, 2)}

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

    # Phase 4 · revisions for each violation
    yield {"type": "stage", "stage": "revision_generate", "status": "running",
           "total": len(matrix["violations"])}
    t3 = time.time()
    enriched_violations: list[dict] = []
    for v in matrix["violations"]:
        revisions = generate_revisions(v, llm_json_caller=llm_json)
        v["revisions"] = revisions
        enriched_violations.append(v)
    yield {"type": "stage", "stage": "revision_generate", "status": "done",
           "duration_s": round(time.time() - t3, 2)}

    # Persist
    payload = {
        "scan_id": "",
        "mode": mode_label,
        "policy_meta": policy_meta or {},
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
            "severe_count": sum(1 for v in enriched_violations if v.get("severity") == "critical"),
            "normal_count": sum(1 for v in enriched_violations if v.get("severity") == "major"),
            "observation_count": sum(1 for v in enriched_violations if v.get("severity") == "minor"),
        },
    }
    sid = persist_scan_result(payload)
    yield {"type": "scan", "scan_id": sid, "stats": payload["stats"]}
    return sid
