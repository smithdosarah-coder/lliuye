# -*- coding: utf-8 -*-
"""agent_compliance.policy_loader — deterministic policy → registry pipeline.

Reads raw policy text, segments at article + paragraph level, and registers
the resulting (policy, version, clauses) bundle into
`shared.policy_registry`. Pure deterministic — no LLM, no external API.
LLM-driven extraction is still done by `scan_engine.extract_rules_from_policy_text`
on top of (or alongside) the deterministic segmentation; both paths live in
the same registry so policy_coverage / conflict_recall metrics share ids.

Why deterministic?
  - `policy_coverage` (extracted_clauses ∩ gold / gold) needs stable
    clause_ids so the gold annotator and the runtime agree on what was
    extracted. LLM clause boundaries fluctuate across runs.
  - Reproducibility of conflict_recall depends on the registry being
    a snapshot whose ids don't drift across re-imports.

Segmentation rules (per docs/contracts/agent-compliance-policy-registry.md §3):
  1. Split at `第X条` headers (re-uses scan_engine._ARTICLE_RE pattern).
  2. Inside each article, split at numbered paragraphs:
     - 一、 / 二、 / (一) / 1. / (1) at line start
  3. A trailing paragraph (no numeric prefix) under an article still gets
     its own clause with paragraph_index = 0.
  4. Threshold extraction reuses the heuristic regexes already shipped in
     scan_engine (max_months / min_ratio / max_amount). Not a "blacklist" —
     these are deterministic quantitative-language templates (per CLAUDE.md
     §12 "general structural mechanism" exception).
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Iterable

from shared.policy_registry import (
    PolicyClause,
    PolicyRegistry,
    RegisterResult,
    register_policy_version,
)

# ---------------------------------------------------------------------------
# Article + paragraph regexes
# ---------------------------------------------------------------------------

# Capture group 1: article number (汉字 / 数字), group 2: head of body up to
# the *next* 第X条 marker. We use a re.split-style approach below for clarity
# instead of one giant lookahead.
_ARTICLE_HEADER_RE = re.compile(
    r"第\s*([一二三四五六七八九十百零\d]+)\s*条",
)

# Sub-paragraph markers (line-start). Order matters — try the longest first.
# Both half-width "(...)" and full-width "（...）" are accepted; Chinese policy
# docs mix the two even within one document.
_PARAGRAPH_MARKERS = [
    re.compile(r"^\s*[\(（]\s*([一二三四五六七八九十]+)\s*[\)）]\s*"),  # (一) / （一）
    re.compile(r"^\s*[\(（]\s*(\d+)\s*[\)）]\s*"),                       # (1) / （1）
    re.compile(r"^\s*([一二三四五六七八九十]+)\s*[、,.]\s*"),             # 一、
    re.compile(r"^\s*(\d+)\s*[、.,)）]\s*"),                              # 1.
]

# Lifted verbatim from scan_engine — same heuristic-quantitative templates.
_THRESHOLD_PATTERNS = [
    (re.compile(r"(?:不(?:得|应)?超过|不\s*高于|≤|<=)\s*(\d+(?:\.\d+)?)\s*(?:个)?月"),
     "max_months", float),
    (re.compile(r"(?:不(?:得|应)?低于|不\s*少于|≥|>=)\s*(\d+(?:\.\d+)?)\s*%"),
     "min_bank_share_ratio", lambda x: float(x) / 100.0),
    (re.compile(r"(?:不(?:得|应)?超过|≤|<=)\s*(\d+(?:\.\d+)?)\s*万元"),
     "max_amount_wan", float),
    (re.compile(r"(?:不(?:得|应)?低于|不\s*少于|≥|>=)\s*(\d+(?:\.\d+)?)\s*万元"),
     "min_amount_wan", float),
    (re.compile(r"(?:不(?:得|应)?低于|不\s*少于|≥|>=)\s*(\d+(?:\.\d+)?)\s*年"),
     "min_years", float),
    (re.compile(r"(?:不(?:得|应)?超过|不\s*高于|≤|<=)\s*(\d+(?:\.\d+)?)\s*小时"),
     "max_hours", float),
]

# Category hints — *not* a blacklist. These are well-known regulatory
# vocabulary buckets used to bucket clauses for downstream filtering.
# Empty-bucket fallback is "其他".
_CATEGORY_HINTS = {
    "客户准入": ("客户准入", "营业收入", "注册资本", "经营期限"),
    "反洗钱": ("反洗钱", "受益所有人", "可疑交易", "尽职调查", "KYC"),
    "信息披露": ("披露", "公告", "信息公开"),
    "风险管理": ("风险", "限额", "敞口", "拨备"),
    "信贷管理": ("贷款", "授信", "用途", "受托支付"),
    "合规检查": ("合规", "检查", "审计", "内审"),
    "数据保护": ("个人信息", "隐私", "数据安全"),
    "投资管理": ("投资", "理财", "代销"),
}


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------


def _split_articles(text: str) -> list[tuple[str, str]]:
    """Return list of (article_label, body) starting at each 第X条 header.

    The text *before* the first 第X条 (preamble) is discarded — registries
    only store enforceable clauses, not preamble.
    """
    if not text:
        return []
    matches = list(_ARTICLE_HEADER_RE.finditer(text))
    if not matches:
        # No 第X条 markers — treat the whole document as one untitled clause.
        return [("", text.strip())]
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        article_no = m.group(1)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        # Strip leading punctuation that follows the header marker.
        body = re.sub(r"^[\s:：.\-—、]+", "", body)
        out.append((f"第{article_no}条", body))
    return out


def _split_paragraphs(body: str) -> list[str]:
    """Split an article body into paragraphs.

    Strategy:
    1. Split first on blank lines (most policy docs separate paragraphs
       with one blank line).
    2. Then split each piece at line-start numbered markers (一、 / (一) / 1.).
    3. Drop empties.
    """
    if not body:
        return []

    blocks: list[str] = []
    for chunk in re.split(r"\n\s*\n", body):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Walk lines; whenever a line begins with a marker, start a new block.
        cur: list[str] = []
        for line in chunk.splitlines():
            if any(p.match(line) for p in _PARAGRAPH_MARKERS) and cur:
                joined = " ".join(s.strip() for s in cur if s.strip())
                if joined:
                    blocks.append(joined)
                cur = [line]
            else:
                cur.append(line)
        if cur:
            joined = " ".join(s.strip() for s in cur if s.strip())
            if joined:
                blocks.append(joined)
    return [b for b in blocks if b.strip()]


def _strip_paragraph_marker(text: str) -> str:
    for pattern in _PARAGRAPH_MARKERS:
        m = pattern.match(text)
        if m:
            return text[m.end():].strip()
    return text.strip()


def _extract_threshold(text: str) -> dict:
    """Quantitative-language template extraction · same as scan_engine heuristic."""
    threshold: dict = {}
    for regex, key, conv in _THRESHOLD_PATTERNS:
        m = regex.search(text)
        if m:
            try:
                threshold[key] = conv(m.group(1))
            except (ValueError, TypeError):
                continue
    return threshold


def _infer_category(text: str) -> str:
    """First hit wins; empty → 其他.

    This is the single non-deterministic heuristic and it is intentionally
    *coarse* (8 buckets, lifted from regulatory vocabulary). Used only for
    UI grouping; it does NOT affect clause_id, policy_coverage, or conflict_recall.
    """
    for cat, hints in _CATEGORY_HINTS.items():
        for hint in hints:
            if hint in text:
                return cat
    return "其他"


def _extract_keywords(text: str, *, limit: int = 8) -> list[str]:
    """Extract noun-phrase candidates conservatively.

    Strategy: take 2–6-character runs of CJK chars that aren't connectors
    (的/了/和/与/或) and dedupe preserving order. Bounded to `limit`.
    The result is a *hint* set used by downstream cross_compare; it does
    NOT participate in clause_id (so changing this function never breaks
    existing registry rows).
    """
    if not text:
        return []
    seen: list[str] = []
    for token in re.findall(r"[一-龥]{2,6}", text):
        if token in {"的", "了", "和", "与", "或", "在", "对", "其", "及", "等",
                     "可以", "不得", "应当", "应该", "不少于", "不超过", "不低于",
                     "不高于", "本条", "本款", "前款"}:
            continue
        if token not in seen:
            seen.append(token)
        if len(seen) >= limit:
            break
    return seen


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def segment_policy_text(policy_text: str) -> list[dict]:
    """Segment a raw policy doc into clauses (no registry write).

    Returns plain dicts (not yet hydrated with version_id / clause_id) so
    callers can preview before persisting.

    Each dict carries:
        article            "第X条" or "" for preamble-only docs
        paragraph_index    0-based ordinal within the article
        text               clause text with marker prefix stripped
        category           hint bucket (see _CATEGORY_HINTS)
        keywords           noun-phrase candidates (max 8)
        threshold          dict of detected quantitative caps/floors
        severity_hint      "major" baseline; "critical" if threshold non-empty
                           AND article contains 强制/严禁/必须 -- per spec §3.4
    """
    out: list[dict] = []
    for article_label, body in _split_articles(policy_text):
        paragraphs = _split_paragraphs(body)
        if not paragraphs:
            # Empty article body — keep one row so coverage doesn't drop.
            out.append({
                "article": article_label,
                "paragraph_index": 0,
                "text": "",
                "category": "其他",
                "keywords": [],
                "threshold": {},
                "severity_hint": "minor",
            })
            continue
        for idx, para in enumerate(paragraphs):
            stripped = _strip_paragraph_marker(para)
            if not stripped:
                continue
            threshold = _extract_threshold(stripped)
            has_mandate = bool(re.search(r"(强制|严禁|必须|不得|禁止)", stripped))
            if threshold and has_mandate:
                severity = "critical"
            elif threshold or has_mandate:
                severity = "major"
            else:
                severity = "minor"
            out.append({
                "article": article_label,
                "paragraph_index": idx,
                "text": stripped,
                "category": _infer_category(stripped),
                "keywords": _extract_keywords(stripped),
                "threshold": threshold,
                "severity_hint": severity,
            })
    return out


def load_policy(
    *,
    title: str,
    issuer: str,
    body_text: str,
    effective_date: str = "",
    fetched_at: str | None = None,
    source_url: str = "",
    category: str = "",
    description: str = "",
    registry: PolicyRegistry | None = None,
) -> RegisterResult:
    """Segment + register in one call.

    Idempotent — re-importing the same body returns the existing version_id
    without dup rows. The PolicyRegistry layer enforces this.
    """
    clauses = segment_policy_text(body_text)
    return register_policy_version(
        title=title,
        issuer=issuer,
        body_text=body_text,
        clauses=clauses,
        effective_date=effective_date,
        fetched_at=fetched_at,
        source_url=source_url,
        category=category,
        description=description,
        registry=registry,
    )


def clauses_to_scan_rules(clauses: Iterable[dict | PolicyClause]) -> list[dict]:
    """Bridge: convert registry clauses into scan_engine-style rule dicts.

    scan_engine.matrix_check expects {rule_id, article, category, condition,
    threshold, severity_hint}. Mapping:
        rule_id   ← clause_id (from registry; deterministic across runs)
        article   ← article label
        category  ← bucket
        condition ← clause text (truncated to 160 chars to match heuristic out)
        threshold ← unchanged
        severity_hint ← unchanged
    """
    out: list[dict] = []
    for c in clauses or []:
        if isinstance(c, PolicyClause):
            d = asdict(c)
        elif isinstance(c, dict):
            d = c
        else:
            continue
        text = (d.get("text") or "").strip()
        if not text:
            continue
        out.append({
            "rule_id": d.get("clause_id") or d.get("rule_id") or "",
            "article": d.get("article") or "",
            "category": d.get("category") or "其他",
            "condition": text[:160],
            "threshold": d.get("threshold") or {},
            "severity_hint": d.get("severity_hint") or "major",
            # Pass-through fields (consumed by violation_schema):
            "clause_id": d.get("clause_id") or "",
            "version_id": d.get("version_id") or "",
            "policy_excerpt": text,
        })
    return out


__all__ = [
    "clauses_to_scan_rules",
    "load_policy",
    "segment_policy_text",
]
