# -*- coding: utf-8 -*-
"""Internal policy indexer — 把 data/mock/compliance-kb/ 下 5 个子目录的 docx
展开成结构化 InternalClause 索引,供 Agent5 cross-compare 消费。

约束 (Batch 2 · §3.1 + §3.5):
    - 走 python-docx + 正则/规则抽取,不走 LLM (确定性)
    - 只读 data/mock/compliance-kb/,不修改
    - 每条 clause 带 source_doc / section_title / clause_id 作为证据回指锚点
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


# compliance-kb 5 个业务域
BUSINESS_SCOPES = (
    "credit-sop",
    "customer-admission",
    "kyc-aml",
    "review-checklists",
    "risk-preference",
)

# 章节标题: "第一章 xxx" / "第 1 章 xxx" / "一、xxx" / "1. xxx"
_SECTION_RE = re.compile(
    r"^\s*(?:第\s*[一二三四五六七八九十百\d]+\s*[章节条]|[一二三四五六七八九十]+\s*[、.．])\s*(.+)$",
    re.M,
)

# 编号条款: "1、xxx" / "1.xxx" / "(1) xxx"
_ITEM_RE = re.compile(r"^\s*(?:\d+\s*[、.．]|\(?\d+\)?\s*[、.．]?)\s*(.+)$")

# 关键业务术语抽取(中文名词短语粗扫 — 不走 LLM 只要能做 overlap 命中即可)
_KEY_TERM_PATTERNS = [
    r"营业(?:执照|收入|期限)",
    r"注册资本",
    r"资产\s*负债率",
    r"[0-9]+\s*亿元?\s*以[上下]",
    r"[0-9]+\s*万元?\s*以[上下]",
    r"公司治理",
    r"准入", r"审查", r"审批", r"审核",
    r"流[水转]", r"账户",
    r"KYC", r"反洗钱", r"可疑交易",
    r"受益所有人", r"客户尽职调查",
    r"风险偏好", r"授信", r"担保",
    r"小微", r"对公", r"个人",
]


@dataclass
class InternalClause:
    """一条内部制度条款。"""
    clause_id: str                        # biz-scope__docname__sec-idx__item-idx
    business_scope: str                   # credit-sop / customer-admission / ...
    source_doc: str                       # 绝对路径
    section_title: str = ""
    content: str = ""
    keywords: list[str] = field(default_factory=list)


def _read_docx_paragraphs(path: Path) -> list[str]:
    try:
        import docx
    except ImportError:
        return []
    try:
        doc = docx.Document(str(path))
    except (OSError, ValueError, KeyError):
        return []
    return [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]


def _extract_keywords(text: str) -> list[str]:
    found: list[str] = []
    for pat in _KEY_TERM_PATTERNS:
        for m in re.finditer(pat, text):
            token = m.group(0).strip()
            if token and token not in found:
                found.append(token)
    return found[:12]


def _parse_one_doc(
    path: Path, business_scope: str,
) -> list[InternalClause]:
    """把一份 docx 展平成若干 clause(按章 → 编号条款)。"""
    paragraphs = _read_docx_paragraphs(path)
    if not paragraphs:
        return []

    doc_stem = path.stem[:40]
    clauses: list[InternalClause] = []
    current_section = ""
    section_idx = 0
    item_idx = 0

    for para in paragraphs:
        # 先识别 section 标题
        m_section = _SECTION_RE.match(para)
        if m_section:
            current_section = m_section.group(1).strip()
            section_idx += 1
            item_idx = 0
            continue
        # 再识别 numbered item
        m_item = _ITEM_RE.match(para)
        if m_item:
            item_idx += 1
            content = m_item.group(1).strip()
            clause_id = f"{business_scope}__{doc_stem}__s{section_idx}__i{item_idx}"
            clauses.append(InternalClause(
                clause_id=clause_id,
                business_scope=business_scope,
                source_doc=str(path),
                section_title=current_section or path.stem[:20],
                content=content,
                keywords=_extract_keywords(content + " " + (current_section or "")),
            ))
    # docx 只有自由段落 + 没有任何 numbered item → 把整篇作一个 clause
    if not clauses and paragraphs:
        content = " ".join(paragraphs[:6])[:400]
        clauses.append(InternalClause(
            clause_id=f"{business_scope}__{doc_stem}__whole",
            business_scope=business_scope,
            source_doc=str(path),
            section_title=path.stem[:20],
            content=content,
            keywords=_extract_keywords(content),
        ))
    return clauses


def build_internal_clause_index(kb_dir: str | Path) -> list[InternalClause]:
    """遍历 kb_dir 下的 5 个业务子目录,聚合所有 clause。

    kb_dir 期待指向 data/mock/compliance-kb/ 或其等价目录。
    子目录不存在 / 为空 → 跳过该 scope,不抛。
    """
    base = Path(kb_dir)
    if not base.is_dir():
        return []
    out: list[InternalClause] = []
    for scope in BUSINESS_SCOPES:
        scope_dir = base / scope
        if not scope_dir.is_dir():
            continue
        for fname in sorted(os.listdir(scope_dir)):
            if not fname.lower().endswith(".docx"):
                continue
            out.extend(_parse_one_doc(scope_dir / fname, scope))
    return out
