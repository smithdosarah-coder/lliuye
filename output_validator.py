# -*- coding: utf-8 -*-
"""
输出质量验证模块 (Output Validator)

验证输出文档质量：
1. 检测模板示例残留（XX万元、注塑/模具等行业样例、占位符）
2. 检测结构完整性（标题是否丢失）
3. 综合评分

用于 form_filler.py 在输出前进行最终验证和自动修复。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from difflib import SequenceMatcher


# ═══════════════════════════════════════════
# 检测规则常量
# ═══════════════════════════════════════════

# 模板示例关键词（出现在输出中大概率是残留）
_EXAMPLE_KEYWORDS = [
    "XX万元", "XX年", "XX月", "XX日", "XX公司", "XX银行",
    "XX事务所", "XX有限", "XX集团", "XX%", "XXX%", "XX人",
    "XX台", "XX套", "XX吨", "XX亿", "XX名下", "XX生产线",
    "XX平方", "XX元", "XX万",
]

# 模板行业样例词（这些几乎不可能是客户真实内容）
_SAMPLE_INDUSTRY_KEYWORDS = [
    "注塑", "模具", "塑胶", "某某",
]

# 未替换占位符模式
_PLACEHOLDER_PATTERNS = [
    re.compile(r'\bX{2,}\b'),         # XX, XXX, XXXX ...
    re.compile(r'_{3,}'),              # _____, ______
    re.compile(r'□{2,}'),             # □□□
]

# 模板指导性文字（出现在输出中说明未被替换）
_GUIDANCE_PATTERNS = [
    re.compile(r'请简述|请描述|请列明|请填写|请说明'),
    re.compile(r'描述实地走访'),
    re.compile(r'简述.*情况'),
]


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def _clean_for_fingerprint(text: str) -> str:
    """去掉数字、标点、空白，只留中文和字母，用于指纹比对"""
    cleaned = re.sub(r'[\d\s\u3000.,;:!?，。；：！？、\-\(\)（）\[\]【】""\'\"""'']+', '', text)
    return cleaned


def _char_overlap_ratio(text1: str, text2: str) -> float:
    """计算两段文本的字符级重叠率"""
    if not text1 or not text2:
        return 0.0
    a = _clean_for_fingerprint(text1)
    b = _clean_for_fingerprint(text2)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _split_sentences(text: str) -> list[str]:
    """将文本拆分为句子"""
    # 按中文句号、分号、换行拆分
    parts = re.split(r'[。；\n]+', text)
    return [s.strip() for s in parts if s.strip() and len(s.strip()) > 5]


# ═══════════════════════════════════════════
# 主类
# ═══════════════════════════════════════════

@dataclass
class ValidationIssue:
    """一个验证问题"""
    type: str           # "example_leakage" | "structure_loss" | "placeholder_残留"
    text: str           # 问题文本
    reason: str         # 原因说明
    severity: str = "warning"  # "warning" | "error"


class OutputValidator:
    """验证输出文档质量：检测模板示例残留、结构完整性"""

    def __init__(self, template_fingerprints: dict[str, str] | None = None):
        """
        初始化验证器。

        Args:
            template_fingerprints: 模板指纹，由 extract_template_fingerprints() 提取
                格式: {paragraph_location → cleaned_text}
        """
        self._fingerprints = template_fingerprints or {}

    def check_example_leakage(self, generated_text: str) -> list[dict]:
        """
        检测生成文本中是否残留模板示例。

        检测方法：
        1. 关键词检测：XX万元、XX年、XX公司、注塑、模具、塑胶、某某、XX%
        2. 指纹比对：将 generated_text 的每个句子与 template_fingerprints 比对
           - 去掉数字和标点后，计算字符级重叠率
           - 重叠率 > 60% → 标记为示例残留
        3. 占位符模式：检测 XX+、___+、□ 等未替换标记
        4. 指导性文字：检测"请简述"、"请描述"等模板指导残留

        Args:
            generated_text: 生成的文本

        Returns:
            [{"type": "example_leakage", "text": 问题句子, "reason": 原因}]
        """
        if not generated_text or not generated_text.strip():
            return []

        issues: list[dict] = []
        seen_texts: set[str] = set()  # 去重

        # 1. 关键词检测
        for kw in _EXAMPLE_KEYWORDS:
            if kw in generated_text:
                # 提取包含关键词的句子
                for sentence in _split_sentences(generated_text):
                    if kw in sentence and sentence not in seen_texts:
                        seen_texts.add(sentence)
                        issues.append({
                            "type": "example_leakage",
                            "text": sentence[:200],
                            "reason": f"包含模板占位关键词「{kw}」",
                        })

        # 模板行业样例词
        for kw in _SAMPLE_INDUSTRY_KEYWORDS:
            if kw in generated_text:
                for sentence in _split_sentences(generated_text):
                    if kw in sentence and sentence not in seen_texts:
                        seen_texts.add(sentence)
                        issues.append({
                            "type": "example_leakage",
                            "text": sentence[:200],
                            "reason": f"包含模板示例行业词「{kw}」",
                        })

        # 2. 指纹比对
        if self._fingerprints:
            sentences = _split_sentences(generated_text)
            for sentence in sentences:
                if sentence in seen_texts:
                    continue
                if len(sentence) < 10:
                    continue
                for loc, fp_text in self._fingerprints.items():
                    ratio = _char_overlap_ratio(sentence, fp_text)
                    if ratio > 0.6:
                        seen_texts.add(sentence)
                        issues.append({
                            "type": "example_leakage",
                            "text": sentence[:200],
                            "reason": f"与模板指纹相似度 {ratio:.0%}（位置 {loc}）",
                        })
                        break  # 一个句子只报一次

        # 3. 占位符模式
        for pattern in _PLACEHOLDER_PATTERNS:
            for m in pattern.finditer(generated_text):
                # 提取上下文
                start = max(0, m.start() - 30)
                end = min(len(generated_text), m.end() + 30)
                context = generated_text[start:end].replace('\n', ' ').strip()
                if context not in seen_texts:
                    seen_texts.add(context)
                    issues.append({
                        "type": "example_leakage",
                        "text": context[:200],
                        "reason": f"发现未替换占位符「{m.group()[:20]}」",
                    })

        # 4. 指导性文字检测
        for pattern in _GUIDANCE_PATTERNS:
            for m in pattern.finditer(generated_text):
                start = max(0, m.start() - 20)
                end = min(len(generated_text), m.end() + 40)
                context = generated_text[start:end].replace('\n', ' ').strip()
                if context not in seen_texts:
                    seen_texts.add(context)
                    issues.append({
                        "type": "example_leakage",
                        "text": context[:200],
                        "reason": f"发现模板指导性文字残留「{m.group()}」",
                    })

        return issues

    def check_structure_integrity(
        self,
        original_headings: list[str],
        output_text: str,
    ) -> list[dict]:
        """
        检测输出文本是否保留了模板的结构标题。

        Args:
            original_headings: 模板中标记为 PRESERVE 的标题列表
            output_text: 生成的输出文本

        Returns:
            [{"type": "structure_loss", "heading": 丢失的标题}]
        """
        if not original_headings or not output_text:
            return []

        issues: list[dict] = []
        for heading in original_headings:
            heading_stripped = heading.strip()
            if not heading_stripped:
                continue
            # 检查标题是否还在输出中（允许前后有少量差异）
            # 提取标题的核心部分（去掉编号前缀后的关键文字）
            core = re.sub(
                r'^[\(（][一二三四五六七八九十]+[\)）]\s*'
                r'|^\d+[.．、]\s*'
                r'|^[①②③④⑤⑥⑦⑧⑨⑩]\s*'
                r'|^※\s*\d*[.．、]?\s*',
                '', heading_stripped
            ).strip()

            if not core:
                continue

            # 核心文字至少部分匹配
            if core not in output_text and heading_stripped not in output_text:
                # 再尝试模糊匹配（允许小变化）
                found = False
                for line in output_text.split('\n'):
                    if _char_overlap_ratio(core, line.strip()) > 0.7:
                        found = True
                        break
                if not found:
                    issues.append({
                        "type": "structure_loss",
                        "heading": heading_stripped,
                    })

        return issues

    def validate(
        self,
        generated_text: str,
        original_headings: list[str] | None = None,
    ) -> dict:
        """
        综合验证。

        Args:
            generated_text: 生成的文本
            original_headings: 模板中标记为 PRESERVE 的标题列表

        Returns:
            {
                "passed": bool,
                "issues": [...所有问题],
                "score": 0-100 质量分数
            }
        """
        all_issues: list[dict] = []

        # 示例残留检测
        leakage_issues = self.check_example_leakage(generated_text)
        all_issues.extend(leakage_issues)

        # 结构完整性检测
        if original_headings:
            struct_issues = self.check_structure_integrity(
                original_headings, generated_text
            )
            all_issues.extend(struct_issues)

        # 评分：满分100，每个问题扣分
        score = 100
        for issue in all_issues:
            if issue.get("type") == "example_leakage":
                score -= 5  # 每个示例残留扣5分
            elif issue.get("type") == "structure_loss":
                score -= 8  # 每个结构丢失扣8分
        score = max(0, score)

        passed = len(all_issues) == 0

        return {
            "passed": passed,
            "issues": all_issues,
            "score": score,
        }
