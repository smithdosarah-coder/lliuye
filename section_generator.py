# -*- coding: utf-8 -*-
"""
Section-by-Section Generation Engine

Replaces field-by-field filling with section-level generation.
For each template section, builds a dedicated prompt with KB data,
generates complete section content, then writes back to Word doc.
"""

import re
import logging
from typing import Any, Callable

from template_decomposer import (
    SectionInfo, ParaInfo, TemplateRole,
    detect_leakage, infer_section_dimensions,
)

logger = logging.getLogger(__name__)


# =============================================
# Prompt
# =============================================

_SECTION_SYSTEM_PROMPT = (
    "\u4f60\u662f\u4e00\u540d\u8d44\u6df1\u5546\u4e1a\u94f6\u884c\u4fe1\u8d37\u5206\u6790\u5e08\uff0c"
    "\u6b63\u5728\u64b0\u5199\u666e\u60e0\u6388\u4fe1\u7533\u62a5\u53ca\u5ba1\u67e5\u5ba1\u6279\u610f\u89c1\u8868\u3002\n\n"
    "\u4f60\u7684\u4efb\u52a1\u662f\u6839\u636e\u3010\u672c\u8282\u7ed3\u6784\u8981\u6c42\u3011\u548c"
    "\u3010\u5ba2\u6237\u6750\u6599\u3011\uff0c\u64b0\u5199\u62a5\u544a\u4e2d\u7684\u4e00\u4e2a\u7ae0\u8282\u3002\n\n"
    "\u3010\u6838\u5fc3\u539f\u5219\u3011\n"
    "1. \u8bfb\u61c2\uff1a\u7406\u89e3\u6bcf\u4e2a\u5b50\u9879\u5728\u5ba1\u6279\u6d41\u7a0b\u4e2d\u7684"
    "\u771f\u5b9e\u610f\u56fe\u2014\u2014\u201c\u5b83\u5728\u95ee\u4ec0\u4e48\u3001\u8981\u652f\u6491"
    "\u4ec0\u4e48\u5224\u65ad\u201d\n"
    "2. \u5206\u6790\uff1a\u4ece\u6750\u6599\u4e2d\u63d0\u53d6\u8bc1\u636e\u5e76\u5f62\u6210\u56e0\u679c\u94fe\n"
    "3. \u64b0\u5199\uff1a\u8f93\u51fa\u53ef\u76f4\u63a5\u7528\u4e8e\u6388\u4fe1\u5ba1\u6279\u7684"
    "\u4e13\u4e1a\u6587\u672c\n\n"
    "\u3010\u4e09\u5c42\u4fe1\u606f\u89c4\u5219\u3011\n"
    "- \u7b2c\u4e00\u5c42 \u6750\u6599\u4e8b\u5b9e\uff08\u96f6\u5bb9\u9519\uff09\uff1a"
    "\u53ea\u5f15\u7528\u6750\u6599\u4e2d\u53ef\u6838\u9a8c\u7684\u4e8b\u5b9e\u3002"
    "\u4e25\u7981\u7f16\u9020\u3001\u731c\u6d4b\u3001\u590d\u7528\u6a21\u677f\u793a\u4f8b\u503c\u3002\n"
    "- \u7b2c\u4e8c\u5c42 \u884c\u4e1a\u4e0a\u4e0b\u6587\uff1a"
    "\u5982\u9700\u5f15\u5165\u884c\u4e1a\u80cc\u666f\uff0c\u9700\u6807\u660e\u6765\u6e90\u5c5e\u6027\u3002\n"
    "- \u7b2c\u4e09\u5c42 \u5206\u6790\u63a8\u65ad\uff1a"
    "\u6240\u6709\u7ed3\u8bba\u5fc5\u987b\u53ef\u8ffd\u6eaf\u5230\u8bc1\u636e\u3002\n\n"
    "\u3010\u7f3a\u5931\u6570\u636e\u5904\u7406\u3011\n"
    "- \u6750\u6599\u672a\u63d0\u4f9b\u7684\u4fe1\u606f\uff1a\u76f4\u63a5\u5199"
    "\u201c\u6750\u6599\u672a\u63d0\u4f9bXX\u4fe1\u606f\u201d\uff0c"
    "\u5e76\u8bf4\u660e\u5176\u5bf9\u5ba1\u6279\u5224\u65ad\u7684\u5f71\u54cd\u3002\n"
    "- \u4e0d\u8981\u7528\u201c\u5f85\u8865\u5145\u201d\u3001\u201c____\u201d\u3001"
    "\u201cXX\u201d\u7b49\u5360\u4f4d\u7b26\u3002\n"
    "- \u4e0d\u8981\u7f16\u9020\u6570\u636e\u6765\u586b\u5145\u7a7a\u767d\u3002\n\n"
    "\u3010\u8f93\u51fa\u683c\u5f0f\u3011\n"
    "- \u4e2d\u6587\u4e13\u4e1a\u8868\u8ff0\uff0c\u94f6\u884c\u4fe1\u8d37\u62a5\u544a\u6587\u98ce\n"
    "- \u91d1\u989d\u7edf\u4e00\u7528\u4e07\u5143\u53e3\u5f84\n"
    "- \u7981\u6b62 Markdown \u7b26\u53f7\n"
    "- \u7981\u6b62\u8f93\u51fa\u6a21\u677f\u539f\u6587\u4e2d\u7684\u8303\u4f8b\u5185\u5bb9\n\n"
    "\u3010\u7edd\u5bf9\u7981\u6b62\u3011\n"
    "1. \u590d\u5236\u6a21\u677f\u4e2d\u7684\u8303\u4f8b\u6587\u5b57\n"
    "2. \u7f16\u9020\u6750\u6599\u4e2d\u4e0d\u5b58\u5728\u7684\u6570\u5b57\u3001\u516c\u53f8\u540d\u3001\u4eba\u540d\n"
    "3. \u8f93\u51fa\u7a7a\u6d1e\u5957\u8bdd\u6216\u4e0e\u5ba2\u6237\u65e0\u5173\u7684\u901a\u7528\u63cf\u8ff0"
)


def build_section_prompt(
    section,
    kb=None,
    company_profile="",
    build_dimension_text_fn=None,
    truth_financial_data=None,
    material_index=None,
):
    """Build LLM prompt for generating a complete section.

    Returns: (system_prompt, user_prompt)
    """
    structure_lines = []
    structure_lines.append(
        "\u3010\u672c\u8282\u6807\u9898\u3011" + section.title)
    structure_lines.append("")
    structure_lines.append("\u3010\u672c\u8282\u7ed3\u6784\u8981\u6c42\u3011")
    structure_lines.append(
        "\u6309\u4ee5\u4e0b\u7ed3\u6784\u64b0\u5199\uff08\u6709\u6570\u636e\u5199\uff0c"
        "\u65e0\u6570\u636e\u8bf4\u660e\u201c\u6750\u6599\u672a\u63d0\u4f9bXX\u201d"
        "\u5e76\u5206\u6790\u5f71\u54cd\uff09\uff1a")
    structure_lines.append("")

    for p in section.paragraphs:
        if p.role == TemplateRole.SKELETON and p.text.strip():
            text = p.text.strip()
            text = re.sub(r'_{3,}', '______', text)
            text = re.sub(r'[ \u3000]{4,}', '______', text)
            structure_lines.append("  " + text)

    instructions = section.all_instructions
    if instructions:
        structure_lines.append("")
        structure_lines.append("\u3010\u5199\u4f5c\u63d0\u793a\u3011")
        for inst in instructions:
            structure_lines.append("  - " + inst)

    content_lines = section.content_lines
    if content_lines:
        structure_lines.append("")
        structure_lines.append(
            "\u3010\u6a21\u677f\u8303\u4f8b\uff08\u4ec5\u4f9b\u7406\u89e3\u683c\u5f0f\u8981\u6c42\uff0c"
            "\u4e0d\u8981\u590d\u5236\u8fd9\u4e9b\u5185\u5bb9\uff01"
            "\u7528\u771f\u5b9e\u5ba2\u6237\u6570\u636e\u66ff\u6362\uff09\u3011")
        example_text = "\n".join(content_lines)
        if len(example_text) > 2000:
            example_text = example_text[:2000] + "\n...(\u8303\u4f8b\u622a\u65ad)"
        structure_lines.append(example_text)

    structure_block = "\n".join(structure_lines)

    materials_block = ""
    if kb and build_dimension_text_fn:
        dimensions = infer_section_dimensions(section)
        materials_block = build_dimension_text_fn(
            kb, dimensions, max_chars=10000, include_raw_tables=True
        )

    profile_block = ""
    if company_profile:
        profile_block = (
            "\n\u3010\u4f01\u4e1a\u753b\u50cf\u951a\u70b9"
            "\uff08\u8fd9\u4e9b\u662f\u5df2\u786e\u8ba4\u7684\u4e8b\u5b9e"
            "\uff0c\u52a1\u5fc5\u4f7f\u7528\uff09\u3011\n" + company_profile)

    financial_block = ""
    if truth_financial_data:
        financial_block = _build_financial_anchor(truth_financial_data)

    user_parts = [structure_block]
    if profile_block:
        user_parts.append(profile_block)
    if financial_block:
        user_parts.append(financial_block)
    if materials_block:
        user_parts.append(
            "\n\u3010\u5ba2\u6237\u6750\u6599\u6458\u8981\u3011\n" + materials_block)
    else:
        user_parts.append(
            "\n\u3010\u5ba2\u6237\u6750\u6599\u3011\n"
            "\uff08\u672c\u8282\u65e0\u53ef\u7528\u6750\u6599\uff0c"
            "\u8bf7\u5728\u5404\u5b50\u9879\u6807\u6ce8\u201c\u6750\u6599\u672a\u63d0\u4f9b\u201d"
            "\u5e76\u8bf4\u660e\u5f71\u54cd\uff09")

    # 材料全文检索：从客户原始材料中补充相关段落
    material_supplement = ""
    if material_index is not None:
        # 从 section 的 title、instructions、content_lines 提取检索提示
        hints = list(instructions) if instructions else []
        if content_lines:
            for cl in content_lines[:5]:
                if len(cl) < 200:
                    hints.append(cl)
        material_supplement = material_index.search_for_section(
            section.title, hints
        )

    if material_supplement:
        user_parts.append(
            "\n\u3010\u8865\u5145\u6750\u6599\u539f\u6587\uff08\u4ece\u5ba2\u6237"
            "\u63d0\u4f9b\u6750\u6599\u4e2d\u68c0\u7d22\uff09\u3011\n"
            + material_supplement)

    user_parts.append(
        "\n\u8bf7\u73b0\u5728\u64b0\u5199\u672c\u8282\u5185\u5bb9\u3002"
        "\u76f4\u63a5\u8f93\u51fa\u6b63\u6587\uff0c"
        "\u4e0d\u8981\u8f93\u51fa\u6807\u9898\u884c\uff08\u6807\u9898\u5df2\u7531\u6a21\u677f\u4fdd\u7559\uff09\u3002")

    system_prompt = _SECTION_SYSTEM_PROMPT
    if material_supplement:
        system_prompt += (
            "\n\u5982\u679c\u3010\u8865\u5145\u6750\u6599\u539f\u6587\u3011"
            "\u4e2d\u5305\u542b\u4e0e\u672c\u8282\u76f8\u5173\u7684\u6570\u636e"
            "\u6216\u4e8b\u5b9e\uff0c\u52a1\u5fc5\u4f18\u5148\u4f7f\u7528\uff0c"
            "\u4e0d\u8981\u9057\u6f0f\u3002"
        )

    return system_prompt, "\n".join(user_parts)


def _build_financial_anchor(truth_data):
    """Build financial data anchor block from truth data."""
    if not truth_data:
        return ""

    lines = ["\n\u3010\u8d22\u52a1\u6570\u636e\u951a\u70b9"
             "\uff08\u5df2\u9a8c\u8bc1\uff0c\u52a1\u5fc5\u4f7f\u7528\u8fd9\u4e9b\u6570\u5b57\uff09\u3011"]

    periods = sorted(truth_data.keys())
    for period in periods[-3:]:
        data = truth_data[period]
        if not data:
            continue
        lines.append("\n" + str(period) + "\uff1a")
        key_items = [
            ("\u8425\u4e1a\u6536\u5165", "revenue", "operating_revenue"),
            ("\u51c0\u5229\u6da6", "net_profit"),
            ("\u8d44\u4ea7\u603b\u8ba1", "total_assets"),
            ("\u8d1f\u503a\u5408\u8ba1", "total_liabilities"),
            ("\u6240\u6709\u8005\u6743\u76ca", "total_equity", "owners_equity"),
            ("\u5e94\u6536\u8d26\u6b3e", "accounts_receivable"),
            ("\u5b58\u8d27", "inventory"),
            ("\u8d27\u5e01\u8d44\u91d1", "cash_and_equivalents", "monetary_funds"),
            ("\u77ed\u671f\u501f\u6b3e", "short_term_borrowings"),
            ("\u7ecf\u8425\u6d3b\u52a8\u73b0\u91d1\u6d41\u91cf\u51c0\u989d",
             "operating_cash_flow_net"),
        ]
        for item_names in key_items:
            for name in item_names:
                if name in data:
                    val = data[name]
                    if isinstance(val, (int, float)):
                        lines.append(
                            "  " + item_names[0] + "\uff1a"
                            + str(val) + "\u4e07\u5143")
                    break

    return "\n".join(lines) if len(lines) > 1 else ""


# =============================================
# Batch section generation
# =============================================

def generate_all_sections(
    sections,
    kb=None,
    company_profile="",
    llm_fn=None,
    build_dimension_text_fn=None,
    truth_financial_data=None,
    template_paragraphs=None,
    progress_cb=None,
    max_retries=1,
    material_index=None,
):
    """Generate content for all sections that need rewriting.

    Returns: {para_idx: generated_text}
    """
    all_results = {}
    total = sum(1 for s in sections if s.has_content_to_rewrite)
    done = 0

    for section in sections:
        if not section.has_content_to_rewrite:
            continue

        done += 1
        if progress_cb:
            progress_cb(
                "[\u9010\u8282\u751f\u6210] ("
                + str(done) + "/" + str(total) + ") "
                + section.title[:30] + "...")

        sys_p, usr_p = build_section_prompt(
            section=section,
            kb=kb,
            company_profile=company_profile,
            build_dimension_text_fn=build_dimension_text_fn,
            truth_financial_data=truth_financial_data,
            material_index=material_index,
        )

        response = llm_fn(sys_p, usr_p)
        if not response:
            continue

        response = _clean_response(response)

        content_indices = section.content_para_indices
        para_texts = _distribute_to_paragraphs(response, content_indices, section)

        # Leakage detection + retry
        if template_paragraphs and max_retries > 0:
            leaks = detect_leakage(para_texts, template_paragraphs, threshold=0.5)
            if leaks:
                logger.warning(
                    "Template leakage in %s: %d paragraphs",
                    section.section_id, len(leaks))
                retry_usr = (
                    usr_p
                    + "\n\n\u3010\u91cd\u8981\u8b66\u544a\u3011"
                    "\u4e0a\u4e00\u6b21\u751f\u6210\u7684\u5185\u5bb9"
                    "\u4e0e\u6a21\u677f\u8303\u4f8b\u8fc7\u4e8e\u76f8\u4f3c\uff0c"
                    "\u88ab\u5224\u5b9a\u4e3a\u6a21\u677f\u6cc4\u6f0f\u3002"
                    "\u8bf7\u786e\u4fdd\u5b8c\u5168\u4f7f\u7528\u5ba2\u6237"
                    "\u771f\u5b9e\u6570\u636e\u64b0\u5199\u3002")
                response2 = llm_fn(sys_p, retry_usr)
                if response2:
                    response2 = _clean_response(response2)
                    para_texts2 = _distribute_to_paragraphs(
                        response2, content_indices, section)
                    leaks2 = detect_leakage(
                        para_texts2, template_paragraphs, threshold=0.5)
                    if len(leaks2) < len(leaks):
                        para_texts = para_texts2

        all_results.update(para_texts)

    return all_results


def _clean_response(text):
    """Clean LLM response."""
    text = re.sub(r'^```[a-z]*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    return text.strip()


def _distribute_to_paragraphs(generated_text, content_indices, section):
    """Distribute generated text to CONTENT paragraph slots."""
    if not content_indices:
        return {}

    blocks = [b.strip() for b in generated_text.split('\n') if b.strip()]

    merged = []
    for b in blocks:
        if merged and len(b) < 30 and not _looks_like_new_paragraph(b):
            merged[-1] += b
        else:
            merged.append(b)
    blocks = merged if merged else [generated_text.strip()]

    result = {}

    if len(content_indices) == 1:
        result[content_indices[0]] = generated_text.strip()
    elif len(blocks) <= len(content_indices):
        for i, idx in enumerate(content_indices):
            if i < len(blocks):
                result[idx] = blocks[i]
            else:
                result[idx] = ""
    else:
        for i in range(len(content_indices) - 1):
            result[content_indices[i]] = blocks[i]
        remaining = "\n".join(blocks[len(content_indices) - 1:])
        result[content_indices[-1]] = remaining

    return result


def _looks_like_new_paragraph(text):
    """Check if text looks like a new paragraph start."""
    pat = (r'^[(\uff08][\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]'
           r'|^\d+[.\uff0e\u3001]'
           r'|^[\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2469]'
           r'|^[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+\u3001'
           r'|^\u203b')
    return bool(re.match(pat, text.strip()))


# =============================================
# Apply to Word document
# =============================================

def apply_section_results(doc, results, body_cell_path=(0, 3, 0)):
    """Write generated content back to Word document.

    Returns: number of paragraphs applied
    """
    table_idx, row_idx, col_idx = body_cell_path
    cell = doc.tables[table_idx].rows[row_idx].cells[col_idx]
    paragraphs = cell.paragraphs
    applied = 0

    for para_idx, new_text in results.items():
        if para_idx >= len(paragraphs):
            continue

        para = paragraphs[para_idx]
        if not new_text:
            _clear_paragraph(para)
            applied += 1
            continue

        _distribute_text_to_runs(para, new_text)
        applied += 1

    return applied


def _clear_paragraph(para):
    """Clear paragraph text, preserving the paragraph element."""
    for run in para.runs:
        run.text = ""


def _distribute_text_to_runs(para, new_text):
    """Distribute new text to runs, preserving formatting."""
    runs = para.runs
    if not runs:
        para.add_run(new_text)
        return

    if len(runs) == 1:
        runs[0].text = new_text
    else:
        runs[0].text = new_text
        for run in runs[1:]:
            run.text = ""


# =============================================
# Output validation gate
# =============================================

def validate_output(doc, template_paragraphs, body_cell_path=(0, 3, 0),
                    threshold=0.5):
    """Final output validation: detect template leakage."""
    table_idx, row_idx, col_idx = body_cell_path
    cell = doc.tables[table_idx].rows[row_idx].cells[col_idx]
    paragraphs = cell.paragraphs

    generated = {}
    for p in template_paragraphs:
        if p.role == TemplateRole.CONTENT and p.para_idx < len(paragraphs):
            generated[p.para_idx] = paragraphs[p.para_idx].text

    return detect_leakage(generated, template_paragraphs, threshold=threshold)
