# -*- coding: utf-8 -*-
"""material_index.py

材料全文分段索引，支持按需检索。
解决 material_kb.py 预定义维度之外的信息丢失问题：
将所有客户材料按段落分段，构建关键词倒排索引，
供 section_generator 在构建 prompt 时按需检索相关原文。
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# 中文停用词（高频虚词，不参与索引和检索）
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset(
    "的了是在和与等为有不这那就都也要会被把从到对让向"
    "因由但如果如此以及其他可以已经一个我们他们本公司"
    "该其中之上下中大小多少"
)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _extract_chinese(text: str) -> str:
    """只保留中文字符"""
    return re.sub(r"[^\u4e00-\u9fff]", "", text)


def _ngrams(text: str, ns=(2, 3, 4)) -> list[str]:
    """从中文文本中提取字符级 n-gram，过滤停用词组合"""
    chinese = _extract_chinese(text)
    result = []
    for n in ns:
        for i in range(len(chinese) - n + 1):
            gram = chinese[i:i + n]
            # 跳过全由停用词字符组成的 n-gram
            if all(ch in _STOP_WORDS for ch in gram):
                continue
            result.append(gram)
    return result


def _is_table_line(line: str) -> bool:
    """检测是否为表格行（含连续制表符或管道符分隔）"""
    return "\t" in line or line.count("|") >= 2


# ---------------------------------------------------------------------------
# MaterialIndex 主类
# ---------------------------------------------------------------------------

class MaterialIndex:
    """材料全文分段索引，支持按需检索"""

    def __init__(self, file_contents: dict[str, str]):
        """
        接收 file_contents（文件名→文本），构建分段索引。
        - 将每个文件的文本按段落分段（每段200-500字）
        - 每段保留：来源文件名、段落序号、原文
        - 构建关键词倒排索引
        """
        # chunks: list[dict] — 每个 chunk 包含 source, chunk_idx, text
        self.chunks: list[dict] = []
        # 倒排索引: keyword → set[chunk_idx]
        self.inverted_index: dict[str, set[int]] = {}

        for filename, text in (file_contents or {}).items():
            if not text or not text.strip():
                continue
            segments = self._split_into_chunks(text)
            for seg_text in segments:
                idx = len(self.chunks)
                self.chunks.append({
                    "source": filename,
                    "chunk_idx": idx,
                    "text": seg_text,
                })
                # 为该 chunk 建立倒排索引
                keywords = set(_ngrams(seg_text))
                for kw in keywords:
                    if kw not in self.inverted_index:
                        self.inverted_index[kw] = set()
                    self.inverted_index[kw].add(idx)

    def _split_into_chunks(self, text: str) -> list[str]:
        """
        按段落分段，短段合并，长段截断。
        表格行保持完整（不在表格中间换行处拆分）。
        """
        lines = text.split("\n")
        # 第一步：按空行或非表格换行拆分为原始段落，表格行合并
        raw_paragraphs: list[str] = []
        current_lines: list[str] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            is_tbl = _is_table_line(stripped)

            if not stripped:
                # 空行：结束当前段落（除非在表格中）
                if in_table:
                    # 表格中的空行也保留
                    current_lines.append(line)
                else:
                    if current_lines:
                        raw_paragraphs.append("\n".join(current_lines))
                        current_lines = []
                continue

            if is_tbl:
                if not in_table and current_lines:
                    # 非表格段落结束，开始表格
                    raw_paragraphs.append("\n".join(current_lines))
                    current_lines = []
                in_table = True
                current_lines.append(line)
            else:
                if in_table and current_lines:
                    # 表格结束
                    raw_paragraphs.append("\n".join(current_lines))
                    current_lines = []
                    in_table = False
                current_lines.append(line)

        if current_lines:
            raw_paragraphs.append("\n".join(current_lines))

        # 第二步：短段（<100字）合并相邻段，长段（>500字）截断
        chunks: list[str] = []
        buffer = ""

        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(para) > 500:
                # 先把 buffer 里的内容输出
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                # 长段截断为多个 chunk
                for i in range(0, len(para), 450):
                    chunk = para[i:i + 450]
                    if chunk.strip():
                        chunks.append(chunk)
            elif len(para) < 100:
                # 短段合并
                if buffer:
                    combined = buffer + "\n" + para
                    if len(combined) > 500:
                        chunks.append(buffer)
                        buffer = para
                    else:
                        buffer = combined
                else:
                    buffer = para
            else:
                # 正常段落
                if buffer:
                    combined = buffer + "\n" + para
                    if len(combined) <= 500:
                        buffer = combined
                    else:
                        chunks.append(buffer)
                        buffer = para
                else:
                    buffer = para

        if buffer:
            chunks.append(buffer)

        return chunks

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        检索与 query 最相关的材料段落。
        返回: [{"source": 文件名, "text": 段落原文, "score": 相关度}]

        检索策略（纯 Python，不依赖外部库）：
        1. 将 query 拆成关键词（2-4字的中文词/短语）
        2. 用倒排索引找到包含这些关键词的段落
        3. 按匹配关键词数量排序
        4. 相邻段落加分（上下文连贯性）
        """
        if not self.chunks:
            return []

        query_keywords = set(_ngrams(query))
        if not query_keywords:
            return []

        # 统计每个 chunk 匹配的关键词数量
        chunk_scores: dict[int, float] = {}
        for kw in query_keywords:
            matched_chunks = self.inverted_index.get(kw, set())
            for cidx in matched_chunks:
                chunk_scores[cidx] = chunk_scores.get(cidx, 0) + 1.0

        if not chunk_scores:
            return []

        # 相邻段落加分：如果某 chunk 的前后 chunk 也命中，额外加分
        adjacency_bonus: dict[int, float] = {}
        for cidx in chunk_scores:
            bonus = 0.0
            if (cidx - 1) in chunk_scores:
                bonus += 0.5
            if (cidx + 1) in chunk_scores:
                bonus += 0.5
            if bonus > 0:
                adjacency_bonus[cidx] = bonus

        for cidx, bonus in adjacency_bonus.items():
            chunk_scores[cidx] += bonus

        # 按分数降序排序
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: -x[1])

        results = []
        for cidx, score in sorted_chunks[:top_k]:
            chunk = self.chunks[cidx]
            results.append({
                "source": chunk["source"],
                "text": chunk["text"],
                "score": score,
            })

        return results

    def search_for_section(
        self,
        section_title: str,
        section_hints: list[str],
        top_k: int = 8,
    ) -> str:
        """
        为某个模板段落检索相关材料，返回格式化文本可直接注入 prompt。

        参数:
            section_title: 段落标题
            section_hints: 额外的关键词提示（从 instructions/content 提取）
            top_k: 最多返回段落数

        返回格式:
            【补充材料原文】（来源：xxx.pdf）
            ... 段落文本 ...
        """
        # 组合查询：标题 + hints
        query = section_title + " " + " ".join(section_hints)
        results = self.search(query, top_k=top_k)

        if not results:
            return ""

        output_lines = []
        for r in results:
            source = r["source"]
            text = r["text"].strip()
            if not text:
                continue
            output_lines.append(f"【补充材料原文】（来源：{source}）")
            output_lines.append(text)
            output_lines.append("")  # 空行分隔

        return "\n".join(output_lines).strip()
