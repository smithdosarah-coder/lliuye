# -*- coding: utf-8 -*-
"""agent_report.cross_section_coherence — Sprint 1 BE3 quality_blocker 第 5 维.

check_cross_section_coherence(sections, anchor, tolerance_pct=1.0) -> list[BlockerIssue]
  跨章节同字段数字一致性 sanity (financial_consistency 仅比 anchor · 不跨章节).

红线 (per docs/contracts/agent-report-material-gap.md §3 + §6):
  - 不引 LLM (per CLAUDE.md §3.1 确定性计算 · 全规则引擎)
  - canonical key 表是 NER 同义词归一 (与 quality_blocker._PLACEHOLDER_PATTERNS 同性质) ·
    不是反幻觉黑名单 (per Codex 插入点 1 v2 final answer Q3 risk-clarification)
  - 不破 quality_blocker.check_financial_consistency 内部 anchor 比对逻辑
    (本 module 独立 module · 通过 quality_blocker.run_blocker(sections=...)
    sibling 路径调用)

算法:
  1. 从 sections (4 章 dict list · 每条含 id + content) 抽数字 token
     (复用 _AMOUNT_PATTERN + _PCT_PATTERN regex)
  2. 数字前后窗口 (±20 char) 找上下文关键词 · 归一到 canonical key
  3. 同 canonical key 跨 section 收集所有提及 (section_id, value, snippet)
  4. 同 key 跨 section 数值差 > tolerance_pct (默认 1%) → block issue
  5. (v1.0 限定) Historical anchor 校验 留 v1.1
"""
from __future__ import annotations

import re
from typing import Any

# ============================================================================
# Canonical key 同义词归一表 (NER · 不是黑名单)
# 每 key → tuple of 中文同义词 · 用 word boundary 匹配
# 与 quality_blocker financial_anchor.ratios + amounts_wan key 命名 align
# ============================================================================

CANONICAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    # 金额类 (单位 万 / 亿 / 万元 / 亿元)
    "revenue":               ("营业收入", "营收", "营业额", "主营业务收入"),
    "total_asset":           ("资产总计", "总资产", "资产合计"),
    "net_profit":            ("归母净利润", "净利润", "净利"),
    "operating_cashflow":    ("经营性现金流", "经营现金流净额", "经营活动现金流"),
    "owner_equity":          ("所有者权益", "股东权益"),
    # 数量类 (无单位 · 整数)
    "headcount":             ("员工人数", "员工", "在职员工", "在职人数"),
    # 百分比类
    "asset_liability_ratio": ("资产负债率",),
    "current_ratio":         ("流动比率",),
    "quick_ratio":           ("速动比率",),
    "gross_margin":          ("毛利率", "综合毛利率"),
    "net_margin":            ("净利率", "净利润率"),
    "roe":                   ("净资产收益率", "ROE"),
    "roa":                   ("总资产收益率", "ROA"),
    "revenue_growth":        ("营收增长率", "营业收入增长率"),
}

# 数字 token 正则 (复用 quality_blocker.py 风格 · 但加 "亿/万/%/元" + 位数支持)
_AMOUNT_PATTERN = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(亿元|万元|亿|万|元)")
_PCT_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
_INT_PATTERN = re.compile(r"\b(\d{1,5})\b")  # headcount 类纯整数

# 上下文窗口 (数字前后 ±N 字 找关键词)
_CONTEXT_WINDOW = 20


# ============================================================================
# 内部 helper · 数字 token 归一到 (canonical_key, value_normalized)
# ============================================================================

def _norm_amount(value_str: str, unit: str) -> float | None:
    """金额 → 万元 (统一单位 · 与 financial_anchor.amounts_wan 同口径)."""
    try:
        v = float(value_str.replace(",", ""))
    except (ValueError, AttributeError):
        return None
    if unit in ("亿元", "亿"):
        return v * 10000
    if unit in ("万元", "万"):
        return v
    if unit == "元":
        return v / 10000
    return None


def _find_canonical_key(text_window: str) -> str | None:
    """文本窗口里找 canonical key 关键词 · 返第一个命中的 key (优先长 keyword)."""
    # 优先匹配长 keyword (避免 "净利润" 命中 "净利")
    candidates: list[tuple[int, str]] = []
    for key, syns in CANONICAL_KEYWORDS.items():
        for syn in syns:
            if syn in text_window:
                candidates.append((len(syn), key))
                break
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _is_amount_key(key: str) -> bool:
    """金额类 canonical key (用 _norm_amount 归一到万元)."""
    return key in (
        "revenue", "total_asset", "net_profit",
        "operating_cashflow", "owner_equity",
    )


def _is_pct_key(key: str) -> bool:
    """百分比类 canonical key."""
    return key in (
        "asset_liability_ratio", "current_ratio", "quick_ratio",
        "gross_margin", "net_margin", "roe", "roa", "revenue_growth",
    )


def _is_int_key(key: str) -> bool:
    """数量类 (整数无单位 · headcount)."""
    return key in ("headcount",)


# ============================================================================
# Section 内数字 token 抽取
# ============================================================================

def _extract_section_numbers(section: dict) -> list[tuple[str, float, str]]:
    """从 section.content 抽 (canonical_key, normalized_value, snippet) tuples.

    一个 section 内同 key 可能多次出现 · 全部进 list (caller 跨 section 比时去重).
    """
    content = section.get("content") or ""
    if not content:
        return []
    out: list[tuple[str, float, str]] = []

    # ---- 1. 金额 tokens ----
    for m in _AMOUNT_PATTERN.finditer(content):
        value_str, unit = m.group(1), m.group(2)
        # 上下文窗口 ±20 char
        start = max(0, m.start() - _CONTEXT_WINDOW)
        end = min(len(content), m.end() + _CONTEXT_WINDOW)
        window = content[start:end]
        key = _find_canonical_key(window)
        if not key or not _is_amount_key(key):
            continue
        val_wan = _norm_amount(value_str, unit)
        if val_wan is None or val_wan <= 0:
            continue
        snippet = window.replace("\n", " ").strip()
        out.append((key, val_wan, snippet))

    # ---- 2. 百分比 tokens ----
    for m in _PCT_PATTERN.finditer(content):
        value_str = m.group(1)
        start = max(0, m.start() - _CONTEXT_WINDOW)
        end = min(len(content), m.end() + _CONTEXT_WINDOW)
        window = content[start:end]
        key = _find_canonical_key(window)
        if not key or not _is_pct_key(key):
            continue
        try:
            val = float(value_str)
        except ValueError:
            continue
        snippet = window.replace("\n", " ").strip()
        out.append((key, val, snippet))

    # ---- 3. 整数 tokens (headcount) ----
    for m in _INT_PATTERN.finditer(content):
        value_str = m.group(1)
        # 跳过太大 (>100k) · 不是 headcount (避免命中年份 / 金额无单位残段)
        try:
            val = int(value_str)
        except ValueError:
            continue
        if val <= 0 or val >= 100000:
            continue
        start = max(0, m.start() - _CONTEXT_WINDOW)
        end = min(len(content), m.end() + _CONTEXT_WINDOW)
        window = content[start:end]
        key = _find_canonical_key(window)
        if not key or not _is_int_key(key):
            continue
        snippet = window.replace("\n", " ").strip()
        out.append((key, float(val), snippet))

    return out


# ============================================================================
# 主入口 · check_cross_section_coherence
# ============================================================================

def check_cross_section_coherence(
    sections: list[dict] | None,
    financial_anchor: dict[str, Any] | None = None,
    tolerance_pct: float = 1.0,
) -> list:
    """跨章节同字段数字一致性 sanity check (quality_blocker 第 5 维).

    Args:
        sections: 4 章 dict list · 每条 {id, title, content, status, word_count}
                  (与 v16_runner._extract_sections_from_docx 输出同 shape)
                  · None / 空 list → 返空 (向下兼容 · run_blocker 跳过第 5 维)
        financial_anchor: optional · v1.0 暂未消费 (历史一致性留 v1.1)
        tolerance_pct: 跨 section 数值偏差容差 (默认 1.0%) · 同金额类按相对偏差算

    Returns:
        list[BlockerIssue] · 同 quality_blocker.BlockerIssue dataclass
        每个 issue:
          dimension="cross_section_coherence"
          code=f"value_drift:{key}"
          severity="block"
    """
    # 延迟 import 避免循环依赖 (quality_blocker imports from this module via run_blocker)
    from agent_report.quality_blocker import BlockerIssue

    issues: list = []
    if not sections:
        return issues

    # ---- 1. 每 section 抽数字 token ----
    section_numbers: dict[str, list[tuple[str, float, str]]] = {}  # section_id → tokens
    for sect in sections:
        sid = sect.get("id")
        if not sid:
            continue
        section_numbers[sid] = _extract_section_numbers(sect)

    # ---- 2. 按 canonical key 跨 section 收集 ----
    # key → list[(section_id, value, snippet)]
    key_to_mentions: dict[str, list[tuple[str, float, str]]] = {}
    for sid, tokens in section_numbers.items():
        for key, val, snippet in tokens:
            key_to_mentions.setdefault(key, []).append((sid, val, snippet))

    # ---- 3. 跨 section drift 检测 ----
    for key, mentions in key_to_mentions.items():
        # 同 section 多次提及取首次 (避免一段内重复触发)
        seen_sections: dict[str, tuple[float, str]] = {}
        for sid, val, snippet in mentions:
            if sid not in seen_sections:
                seen_sections[sid] = (val, snippet)
        if len(seen_sections) < 2:
            continue   # 单 section 提及 · 无跨章节比对必要

        # 取第一个 section 的值作 baseline · 其他 section 与之比
        section_list = list(seen_sections.items())
        baseline_sid, (baseline_val, baseline_snip) = section_list[0]
        for sid, (val, snippet) in section_list[1:]:
            # 同 key 跨 section 数值 diff
            if baseline_val == 0:
                continue
            diff_pct = abs(val - baseline_val) / abs(baseline_val) * 100
            if diff_pct <= tolerance_pct:
                continue
            # drift block
            issues.append(BlockerIssue(
                dimension="cross_section_coherence",
                code=f"value_drift:{key}",
                message=(
                    f"{key} 跨章节数值不一致 · "
                    f"{baseline_sid} {baseline_val:.2f} vs "
                    f"{sid} {val:.2f} · 偏差 {diff_pct:.2f}%"
                ),
                snippet=f"[{baseline_sid}] {baseline_snip[:60]} || [{sid}] {snippet[:60]}",
                severity="block",
                expected=f"{baseline_val:.2f} (来自 {baseline_sid})",
                actual=f"{val:.2f} (来自 {sid})",
            ))

    return issues
