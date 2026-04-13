# -*- coding: utf-8 -*-
"""material_kb.py

Build a lightweight, truth-first knowledge base (KB) from extracted materials.

Design goals:
- Deterministic where possible (regex/table parsing), to reduce hallucination.
- Keep provenance: every fact comes from a specific source file.
- Keep output small enough to be embedded into LLM prompts.

This is intentionally narrow: it focuses on commonly used fields in the
"福建普惠授信申报及审查审批意见表（2025新版）" flow.
"""

from __future__ import annotations

import re
from typing import Any


def _clean_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _split_lines(text: str) -> list[str]:
    if not text:
        return []
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", text) if ln and ln.strip()]
    return lines


def _extract_block(lines: list[str], start_pat: str, end_pat: str | None = None) -> str:
    """Extract a block of lines between start_pat and end_pat (regex patterns)."""
    start_re = re.compile(start_pat)
    end_re = re.compile(end_pat) if end_pat else None

    start_i = None
    for i, ln in enumerate(lines):
        if start_re.search(ln):
            start_i = i + 1
            break
    if start_i is None:
        return ""

    out: list[str] = []
    for j in range(start_i, len(lines)):
        ln = lines[j]
        if end_re and end_re.search(ln):
            break
        out.append(ln)
    return "\n".join(out).strip()


def _parse_docx_export_tables(lines: list[str]) -> dict[str, list[list[str]]]:
    """Parse tables exported by tools._read_single_file for docx.

    The exporter emits:
      [表格N]
      col1\tcol2\t...
      ...

    Returns: {"表格1": [[...], ...], ...}
    """
    tables: dict[str, list[list[str]]] = {}
    current: list[list[str]] | None = None
    current_name: str | None = None

    for ln in lines:
        m = re.match(r"^\[表格(\d+)\]$", ln)
        if m:
            current_name = f"表格{m.group(1)}"
            current = []
            tables[current_name] = current
            continue
        if current is None:
            continue
        # table row line: tab-separated
        row = [c.strip() for c in ln.split("\t")]
        # ignore empty rows
        if any(c for c in row):
            current.append(row)

    return tables


def _pick_source_file(file_contents: dict[str, str]) -> str | None:
    """Pick the most likely 'credit supplement' doc as KB seed."""
    if not file_contents:
        return None

    preferred_kw = [
        "授信补充",
        "补充问题",
        "补充材料",
        "授信补充问题",
    ]

    best = None
    best_score = -1
    for fname in file_contents.keys():
        score = 0
        for kw in preferred_kw:
            if kw in (fname or ""):
                score += 3
        if (fname or "").lower().endswith(".docx"):
            score += 1
        if score > best_score:
            best = fname
            best_score = score

    if best_score <= 0:
        return None
    return best


def build_material_kb(file_contents: dict[str, str]) -> dict[str, Any]:
    """Build KB from extracted file_contents.

    Returns a dict with keys:
    - source_file
    - facts: dict[str, Any]
    - tables: dict[str, Any]
    """
    src = _pick_source_file(file_contents)
    kb: dict[str, Any] = {
        "source_file": src or "",
        "facts": {},
        "tables": {},
    }
    if not src:
        return kb

    text = file_contents.get(src, "") or ""
    lines = _split_lines(text)
    tables = _parse_docx_export_tables(lines)

    facts: dict[str, Any] = {}

    # Customer manager / receiver info (often appears as: 姓名+手机号+收)
    m = re.search(r"(?P<name>[\u4e00-\u9fff]{2,4})(?P<phone>1\d{10})收", text)
    if m:
        facts["customer_manager_name"] = m.group("name")
        facts["customer_manager_phone"] = m.group("phone")

    # Business sections
    water = _extract_block(lines, r"^主营业务[—\-－]+智慧水利$", r"^主营业务[—\-－]+智慧教育$")
    edu = _extract_block(lines, r"^主营业务[—\-－]+智慧教育$", r"^公司产品优势")
    if water:
        facts["business_water"] = water
    if edu:
        facts["business_education"] = edu

    comp = _extract_block(lines, r"^公司产品优势以及企业的核心竞争力：$", r"^公司水利和教育的销售收入")
    if comp:
        facts["core_competence"] = comp

    rev = _extract_block(lines, r"^公司水利和教育的销售收入以及结构占比情况：$", r"^公司经营账期")
    if rev:
        facts["revenue_split"] = _clean_ws(rev)

    ap = _extract_block(lines, r"^公司经营账期情况描述：$", r"^实际控制人")
    if ap:
        facts["account_period"] = ap

    ctrl = _extract_block(lines, r"^实际控制人.*个人简介：$", r"^配偶：")
    if ctrl:
        facts["controller_resume"] = ctrl
        m2 = re.search(r"实控人(?P<name>[\u4e00-\u9fff]{2,4})", ctrl)
        if m2:
            facts["controller_name"] = m2.group("name")
        mid = re.search(r"身份证号：(?P<id>\d{17}[\dXx])", ctrl)
        if mid:
            facts["controller_id"] = mid.group("id")

    spouse_line = None
    for ln in lines:
        if ln.startswith("配偶："):
            spouse_line = ln
            break
    if spouse_line:
        m3 = re.search(r"配偶：(?P<name>[\u4e00-\u9fff]{2,6})", spouse_line)
        if m3:
            facts["spouse_name"] = m3.group("name")
        sid = re.search(r"身份证号：(?P<id>\d{17}[\dXx])", spouse_line)
        if sid:
            facts["spouse_id"] = sid.group("id")

    # Upstream / downstream tables
    upstream = tables.get("表格2")
    if upstream and len(upstream) >= 2:
        hdr = upstream[0]
        rows = []
        for r in upstream[1:6]:
            if not any(c.strip() for c in r):
                continue
            item = {}
            for i, col in enumerate(hdr):
                if i < len(r):
                    item[col] = r[i]
            rows.append(item)
        if rows:
            facts["upstream_top5"] = rows

    downstream = tables.get("表格3")
    if downstream and len(downstream) >= 2:
        hdr = downstream[0]
        rows = []
        for r in downstream[1:6]:
            if not any(c.strip() for c in r):
                continue
            item = {}
            for i, col in enumerate(hdr):
                if i < len(r):
                    item[col] = r[i]
            rows.append(item)
        if rows:
            facts["downstream_top5"] = rows

    financing = tables.get("表格5")
    if financing and len(financing) >= 2:
        hdr = financing[0]
        rows = []
        for r in financing[1:]:
            if not any(c.strip() for c in r):
                continue
            item = {}
            for i, col in enumerate(hdr):
                if i < len(r):
                    item[col] = r[i]
            rows.append(item)
        if rows:
            facts["financing"] = rows

    rnd = tables.get("表格6")
    if rnd and len(rnd) >= 2:
        hdr = rnd[0]
        rows = []
        for r in rnd[1:]:
            if not any(c.strip() for c in r):
                continue
            item = {}
            for i, col in enumerate(hdr):
                if i < len(r):
                    item[col] = r[i]
            rows.append(item)
        if rows:
            facts["r_and_d"] = rows

    affiliates = tables.get("表格8")
    if affiliates and len(affiliates) >= 2:
        hdr = affiliates[0]
        rows = []
        for r in affiliates[1:]:
            if not any(c.strip() for c in r):
                continue
            item = {}
            for i, col in enumerate(hdr):
                if i < len(r):
                    item[col] = r[i]
            rows.append(item)
        if rows:
            facts["affiliates"] = rows

    kb["facts"] = facts
    kb["tables"] = {k: v for k, v in tables.items() if k in ("表格2", "表格3", "表格5", "表格6", "表格8")}
    return kb


def kb_to_prompt_text(kb: dict[str, Any], max_chars: int = 4000) -> str:
    """Build a compact KB text for LLM prompts."""
    facts = (kb or {}).get("facts", {}) or {}
    parts: list[str] = []

    def add(title: str, body: str):
        b = (body or "").strip()
        if not b:
            return
        parts.append(f"[{title}]\n{b}")

    add("客户经理", f"{facts.get('customer_manager_name','')} {facts.get('customer_manager_phone','')}".strip())
    add("主营业务-智慧水利", facts.get("business_water", ""))
    add("主营业务-智慧教育", facts.get("business_education", ""))
    add("核心竞争力", facts.get("core_competence", ""))
    add("收入结构", facts.get("revenue_split", ""))
    add("经营账期", facts.get("account_period", ""))
    add("实控人简介", facts.get("controller_resume", ""))

    # Up/down summaries
    up = facts.get("upstream_top5") or []
    if isinstance(up, list) and up:
        names = [it.get("主要上游供应商", "") for it in up if isinstance(it, dict)]
        names = [n for n in names if n]
        if names:
            add("主要上游(前五)", "、".join(names))

    dn = facts.get("downstream_top5") or []
    if isinstance(dn, list) and dn:
        names = [it.get("主要下游销售客户", "") for it in dn if isinstance(it, dict)]
        names = [n for n in names if n]
        if names:
            add("主要下游(前五)", "、".join(names))

    text = "\n\n".join(parts)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[KB截断]"
