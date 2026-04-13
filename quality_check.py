# -*- coding: utf-8 -*-
"""Lightweight post-generation quality checks for filled credit reports."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Issue:
    code: str
    message: str
    snippet: str = ""
    evidence: str = ""
    severity: str = "warning"


class QualityChecker:
    """Rule-based checker for common placeholder/template leakage."""

    ERROR_CODES = {
        "fake_name_placeholder",
        "template_range_percent",
        "template_range_decimal",
        "industry_mismatch_mould",
        "template_guidance_text",
        "template_sample_industry",
    }

    PLACEHOLDER_PATTERNS = [
        (
            "fake_name_placeholder",
            "发现虚假姓名占位符（张XX/李XX/王XX/陈XX/刘XX）",
            re.compile(r"(?:张|李|王|陈|刘)XX"),
        ),
        (
            "template_range_percent",
            "发现模板区间数字（如65-70%之间）",
            re.compile(r"\d{2,3}\s*-\s*\d{2,3}%\s*之间"),
        ),
        (
            "template_range_decimal",
            "发现模板区间数字（如1.4-1.5）",
            re.compile(r"(?<!\d)\d{1,3}(?:\.\d+)?\s*-\s*\d{1,3}(?:\.\d+)?(?!\d)"),
        ),
        (
            "template_yi_data",
            "发现亿级数据（\\d+\\.\\d+亿[元营收]）",
            re.compile(r"\d+\.\d+亿(?:元|营收)"),
        ),
        (
            "industry_mismatch_mould",
            "发现行业词错配（主要生产模具）",
            re.compile(r"主要生产模具|主要从事模具|模具生产|模具加工"),
        ),
        (
            "supply_chain_placeholder",
            "发现未填上下游占位符",
            re.compile(
                r"(?:上游供应商|下游客户|上游|下游)[^\n。；]{0,40}"
                r"(?:XX|XXX|____|待核实|待补充|未提供|\[待核实：[^]]*\])"
            ),
        ),
        (
            "template_guidance_text",
            "发现模板指导性文字残留（描述/简述/列明）",
            re.compile(r"(?:请简述|请描述|请列明|描述实地走访)"),
        ),
        (
            "template_sample_industry",
            "发现模板示例行业内容残留（塑胶/注塑）",
            re.compile(r"塑胶|注塑|模具(?:加工|制造|生产)"),
        ),
    ]

    @staticmethod
    def _snippet(text: str, start: int, end: int, window: int = 16) -> str:
        left = max(0, start - window)
        right = min(len(text), end + window)
        return text[left:right].replace("\n", " ").strip()

    def check(self, doc_text: str, kb_facts: dict | None = None) -> list[Issue]:
        text = (doc_text or "").strip()
        if not text:
            return []

        issues: list[Issue] = []
        seen = set()
        for code, message, pattern in self.PLACEHOLDER_PATTERNS:
            hit_count = 0
            for m in pattern.finditer(text):
                snip = self._snippet(text, m.start(), m.end())
                key = (code, snip)
                if key in seen:
                    continue
                seen.add(key)
                severity = "error" if code in self.ERROR_CODES else "warning"
                issues.append(
                    Issue(
                        code=code,
                        message=message,
                        snippet=snip,
                        evidence=snip,
                        severity=severity,
                    )
                )
                hit_count += 1
                if hit_count >= 3:
                    break

        return issues

    @staticmethod
    def format_report(issues: list[Issue]) -> str:
        if not issues:
            return "未发现命中规则的问题。"
        lines = ["[质量校验] 命中问题如下："]
        for issue in issues:
            lines.append(f"[质量校验] {issue.code} | {issue.message} | {issue.snippet}")
        return "\n".join(lines)
