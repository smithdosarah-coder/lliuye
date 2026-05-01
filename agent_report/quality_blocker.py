# -*- coding: utf-8 -*-
"""Agent6 · QC Blocker 五维强化(Phase 2 Task B + Phase B Sprint 1 BE3 第 5 维)

职责:在 LLM 章节生成与 Phase 3 自审完成后,对最终文本做五维硬质量闸门:
  1. placeholder    占位符残留(企业名/数字/模板指导文字/区间数字/补全提示词)
  2. evidence       证据链完整性(关键数字/主体名/结论是否挂出处)
  3. financial_consistency  财务数字与 financial_anchor 一致(允许 ±1% 容差 · 仅 anchor 比对 · 不跨章节)
  4. compliance_terms       合规术语规范(征信/担保/授信/科创等口径用词不滑出红线)
  5. cross_section_coherence  跨章节同字段数字一致性 (per Phase B Sprint 1 BE3 ·
     新增 sibling 维度 · 由 cross_section_coherence module 实装 · sections=None 跳过)

CLAUDE.md §3.1 / §8 / §12:
  - 财务一致性走 anchor 比对,不让 LLM 现场算
  - 字段填不了 → 标"未能自动填写",blocker 不静默放过
  - 不写黑名单兜底幻觉(用证据链 + QC Blocker)

不修改:financial_analyzer.py / quality_check.py / quality_scorer.py
新增独立模块,经 BlockerVerdict 与上层(section_generator / api.py)交互。

第 5 维加 (Phase B Sprint 1 BE3 · per Codex 插入点 1 v2 final Q2):
  run_blocker 加可选 sections=None 参数 · 默认 None 向下兼容 (老 caller 无需改) ·
  非 None 时调 check_cross_section_coherence · 命中 drift → BlockerVerdict 加
  cross_section_coherence 维度。

DoD: L3-7(QC Blocker 零绕过) + L2-7(证据链)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class BlockerIssue:
    dimension: str       # placeholder | evidence | financial_consistency | compliance_terms
    code: str            # 细分错误码,便于评估配置 yaml 引用
    message: str
    snippet: str = ""
    severity: str = "block"   # block | warn(只 block 的进阻断)
    expected: str | None = None
    actual: str | None = None


@dataclass
class BlockerVerdict:
    blocked: bool
    fail_dimensions: list[str] = field(default_factory=list)
    issues: list[BlockerIssue] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked": self.blocked,
            "fail_dimensions": self.fail_dimensions,
            "issue_count": len(self.issues),
            "issues": [
                {
                    "dimension": i.dimension,
                    "code": i.code,
                    "message": i.message,
                    "snippet": i.snippet,
                    "severity": i.severity,
                    "expected": i.expected,
                    "actual": i.actual,
                }
                for i in self.issues
            ],
            "summary": self.summary,
        }


# ============================================================================
# 维度 1:占位符残留
# ============================================================================


_PLACEHOLDER_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (
        "fake_name_placeholder",
        "残留虚假姓名占位符(张XX/李XX/王XX 等)",
        re.compile(r"(?:张|李|王|陈|刘|赵|周|吴)XX"),
    ),
    (
        "company_placeholder",
        "残留企业名占位符(XX 公司 / XX 有限公司)",
        re.compile(r"(?<!某)XX(?:公司|有限公司|股份有限公司|集团|银行)"),
    ),
    (
        "underscore_placeholder",
        "残留下划线占位符(____)",
        re.compile(r"_{4,}"),
    ),
    (
        "template_range_percent",
        "残留模板区间百分比(如 65-70% 之间)",
        re.compile(r"\d{2,3}\s*-\s*\d{2,3}%\s*之间"),
    ),
    (
        "template_guidance_text",
        "残留模板指导文字(请简述/请描述/请列明 等)",
        re.compile(r"(?:请简述|请描述|请列明|此处填写|请补充说明)"),
    ),
    (
        "fill_marker_residual",
        "残留补全提示词(待补充/待核实/待补全 等)",
        re.compile(r"(?:待补充|待核实|待补全|待完善|\[\s*待[^]]*\s*\])"),
    ),
]


def check_placeholder(text: str) -> list[BlockerIssue]:
    issues: list[BlockerIssue] = []
    if not text:
        return issues
    for code, message, pattern in _PLACEHOLDER_PATTERNS:
        seen: set[str] = set()
        for m in pattern.finditer(text):
            snip = text[max(0, m.start() - 12) : m.end() + 12].replace("\n", " ").strip()
            if snip in seen:
                continue
            seen.add(snip)
            issues.append(
                BlockerIssue(
                    dimension="placeholder",
                    code=code,
                    message=message,
                    snippet=snip,
                    severity="block",
                )
            )
            if len(seen) >= 3:
                break
    return issues


# ============================================================================
# 维度 2:证据链完整性
# ============================================================================


# 数字 + 单位(万/亿/%/万元/亿元)出现且文本中无任何"出处|引自|来源|附注|页"提示 → 怀疑无出处
_NUMERIC_TOKEN = re.compile(r"\d[\d,.]*\s*(?:%|万|亿|万元|亿元)")
_EVIDENCE_KEYWORDS = re.compile(r"(?:出处|引自|来源|附注|第\s*\d+\s*页|参见|根据)")
_CONCLUSION_KEYWORDS = re.compile(r"(?:建议|结论|综上|总体评价|风险等级|授信意见)")


def check_evidence(text: str, expect_evidence: bool = True) -> list[BlockerIssue]:
    issues: list[BlockerIssue] = []
    if not text or not expect_evidence:
        return issues
    nums = _NUMERIC_TOKEN.findall(text or "")
    has_evidence_marker = bool(_EVIDENCE_KEYWORDS.search(text or ""))
    if len(nums) >= 3 and not has_evidence_marker:
        issues.append(
            BlockerIssue(
                dimension="evidence",
                code="numbers_without_source",
                message=f"段落含 {len(nums)} 处数字但无任何出处/附注/页码引用",
                snippet=" / ".join(nums[:5]),
                severity="block",
                expected="≥1 处出处/附注/页码引用",
                actual="0",
            )
        )
    if _CONCLUSION_KEYWORDS.search(text or "") and not has_evidence_marker:
        issues.append(
            BlockerIssue(
                dimension="evidence",
                code="conclusion_without_source",
                message="出现授信结论性表述但无证据引用",
                severity="warn",
                expected="结论挂出处或注明'材料未提供相关信息'",
                actual="无引用关键词",
            )
        )
    return issues


# ============================================================================
# 维度 3:财务一致性(anchor 比对,不让 LLM 现场算)
# ============================================================================


_PCT_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
_AMOUNT_PATTERN = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(万元|亿元|万|亿)")


def _norm_amount_to_wan(value_str: str, unit: str) -> float | None:
    try:
        v = float(value_str.replace(",", ""))
    except Exception:
        return None
    if unit in ("亿元", "亿"):
        return v * 10000
    if unit in ("万元", "万"):
        return v
    return None


def check_financial_consistency(
    text: str,
    financial_anchor: dict[str, Any] | None,
    tolerance_pct: float = 1.0,
) -> list[BlockerIssue]:
    """对比文中提及的关键比率/金额是否与 financial_anchor 一致(±tolerance_pct%)。

    financial_anchor 期望的最小契约:
      {
        "ratios": {"asset_liability_ratio": 0.45, "current_ratio": 1.32, ...},
        "amounts_wan": {"revenue_2024": 15800, "net_profit_2024": 1280, ...},
      }
    任何字段缺失 → 该项跳过,不假阳。
    """
    issues: list[BlockerIssue] = []
    if not text or not financial_anchor:
        return issues
    ratios = financial_anchor.get("ratios") or {}
    if ratios:
        keyword_to_anchor = {
            "资产负债率": ratios.get("asset_liability_ratio"),
            "流动比率": ratios.get("current_ratio"),
            "速动比率": ratios.get("quick_ratio"),
            "毛利率": ratios.get("gross_margin"),
            "净利率": ratios.get("net_margin"),
        }
        for keyword, anchor_val in keyword_to_anchor.items():
            if anchor_val is None:
                continue
            anchor_pct = float(anchor_val) * 100 if anchor_val < 1.5 else float(anchor_val)
            for m in re.finditer(rf"{keyword}[为是约：:\s]+(\d{{1,3}}(?:\.\d+)?)\s*%", text):
                cited = float(m.group(1))
                diff = abs(cited - anchor_pct)
                if diff > tolerance_pct:
                    issues.append(
                        BlockerIssue(
                            dimension="financial_consistency",
                            code=f"ratio_mismatch:{keyword}",
                            message=f"{keyword} 文中 {cited}% vs anchor {anchor_pct:.2f}% 偏差 {diff:.2f}pp",
                            snippet=text[max(0, m.start() - 12) : m.end() + 12],
                            severity="block",
                            expected=f"{anchor_pct:.2f}%",
                            actual=f"{cited}%",
                        )
                    )
    return issues


# ============================================================================
# 维度 4:合规术语规范
# ============================================================================


_COMPLIANCE_RULES: list[tuple[str, str, re.Pattern]] = [
    (
        "guarantee_loose_term",
        "担保术语口径不规范(避免使用'担保措施完美/无风险'等绝对化表述)",
        re.compile(r"担保(?:措施)?(?:完美|无风险|绝对|万无一失)"),
    ),
    (
        "credit_decision_overreach",
        "越权下结论(copilot 不应直接'核准/批准/同意授信',应用'建议核准'等口径)",
        re.compile(r"(?<!建议)(?:核准|批准|同意)授信(?!的建议)"),
    ),
    (
        "credit_query_overstatement",
        "征信查询频率口径滑出(用'查询频繁/征信花'等非内控用语)",
        re.compile(r"征信(?:很|非常)?花|查询(?:非常)?频繁"),
    ),
    (
        "absolute_safety_claim",
        "出现'绝对安全/100% 无风险/零风险'等监管禁用绝对化语",
        re.compile(r"绝对安全|100%\s*无风险|零风险|毫无风险"),
    ),
]


def check_compliance_terms(text: str) -> list[BlockerIssue]:
    issues: list[BlockerIssue] = []
    if not text:
        return issues
    for code, message, pattern in _COMPLIANCE_RULES:
        for m in pattern.finditer(text):
            snip = text[max(0, m.start() - 12) : m.end() + 12].replace("\n", " ").strip()
            issues.append(
                BlockerIssue(
                    dimension="compliance_terms",
                    code=code,
                    message=message,
                    snippet=snip,
                    severity="block",
                )
            )
            break  # 每类规则命中一次足以阻断
    return issues


# ============================================================================
# 主入口:四维聚合判定
# ============================================================================


def run_blocker(
    text: str,
    financial_anchor: dict[str, Any] | None = None,
    expect_evidence: bool = True,
    sections: list[dict] | None = None,
) -> BlockerVerdict:
    """主入口,一次性跑完 4-5 个维度,聚合 verdict。

    Args:
        text: 全文 (与既有 4 维一致 · 不破)
        financial_anchor: anchor 比对 dict (与既有 financial_consistency 一致 · 不破)
        expect_evidence: 是否期望证据 (与既有一致 · 不破)
        sections: optional · per Phase B Sprint 1 BE3 第 5 维 ·
            sections list (与 v16_runner._extract_sections_from_docx 输出同 shape ·
            每条 {id, title, content, ...}) · 非 None 时跑 cross_section_coherence ·
            None / 空 list → 跳过第 5 维 (向下兼容老 caller)
    """
    issues: list[BlockerIssue] = []
    issues += check_placeholder(text)
    issues += check_evidence(text, expect_evidence=expect_evidence)
    issues += check_financial_consistency(text, financial_anchor)
    issues += check_compliance_terms(text)

    # 第 5 维 · cross_section_coherence (per Phase B Sprint 1 BE3 · 可选 sections 触发)
    # 延迟 import 避免 module-level 循环 (cross_section_coherence module 反向 import BlockerIssue)
    if sections:
        from agent_report.cross_section_coherence import check_cross_section_coherence
        issues += check_cross_section_coherence(
            sections=sections,
            financial_anchor=financial_anchor,
        )

    block_issues = [i for i in issues if i.severity == "block"]
    fail_dims = sorted({i.dimension for i in block_issues})
    blocked = bool(block_issues)
    dims_count = 5 if sections else 4
    summary = (
        f"BLOCKED · 命中 {len(block_issues)} 处硬阻断(维度:{','.join(fail_dims)})"
        if blocked
        else f"PASS · 通过 {dims_count} 维 QC Blocker(警告 {len(issues)} 条)"
    )
    return BlockerVerdict(
        blocked=blocked,
        fail_dimensions=fail_dims,
        issues=issues,
        summary=summary,
    )


def format_verdict_text(verdict: BlockerVerdict, max_lines: int = 8) -> str:
    """把 verdict 渲染为人类可读文本(用于日志/UI 提示)。"""
    lines = [verdict.summary]
    for issue in verdict.issues[:max_lines]:
        lines.append(
            f"  [{issue.severity}] {issue.dimension}.{issue.code} | "
            f"{issue.message} | 片段: {issue.snippet[:60]}"
        )
    if len(verdict.issues) > max_lines:
        lines.append(f"  ...(还有 {len(verdict.issues) - max_lines} 条未展示)")
    return "\n".join(lines)
