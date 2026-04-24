# -*- coding: utf-8 -*-
"""RuleExtractor: LLM 从非结构化政策/制度 Word/PDF 抽取结构化 RuleItem。

Agent4 从管理制度抽预警规则、Agent5 从政策抽合规规则，共用本模块。
"""

from __future__ import annotations
import json
import re
from pathlib import Path

from .models import RuleItem, RuleType, RiskLevel


RULE_EXTRACT_PROMPT = """你是银行合规/风控规则抽取专家。请从以下文档片段抽取可执行的规则条目。

【文档名】{doc_name}
【片段】
{chunk}

要求：
- 仅抽取"有明确触发条件"的规则条目，空洞宣示性语句跳过
- 阈值/比例/期限要进入 trigger_condition
- severity 判断：涉资金安全/合规红线→red；管理要求/流程缺失→yellow；提示性→green

以 JSON 数组输出，每条：
{{
  "rule_id": "AUTO_001",
  "category": "规则类别，如授信集中度/反洗钱/期限限制/信息披露",
  "title": "规则简短标题（≤20字）",
  "content": "规则原文（尽量保留原话，≤300字）",
  "trigger_condition": "自然语言触发条件，如'单一客户授信余额占资本>10%'",
  "severity": "red|yellow|green",
  "source_page": "章节或条号"
}}

只输出 JSON 数组，不要其他文字。抽不到则输出 []。
"""


class RuleExtractor:
    """LLM 驱动的规则抽取器。"""

    def __init__(self, llm_client=None, chunk_size: int = 3000, max_chunks: int = 20):
        self._llm = llm_client
        self.chunk_size = chunk_size
        self.max_chunks = max_chunks

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        # 延迟导入，避免模块加载失败
        from llm import LLMClient
        self._llm = LLMClient()
        return self._llm

    def extract(self, doc_path: str | Path, category_hint: str = "") -> list[RuleItem]:
        path = Path(doc_path)
        if not path.exists():
            return []
        text = self._read_doc(path)
        if not text:
            return []
        chunks = self._chunk_text(text)[: self.max_chunks]
        all_rules: list[RuleItem] = []
        for idx, chunk in enumerate(chunks):
            rules = self._extract_from_chunk(path.name, chunk, idx, category_hint)
            all_rules.extend(rules)
        return self._dedup(all_rules)

    # ---- 读取 ----
    def _read_doc(self, path: Path) -> str:
        ext = path.suffix.lower()
        if ext in {".md", ".txt"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if ext == ".docx":
            try:
                from docx import Document
                doc = Document(str(path))
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            except (OSError, ImportError, ValueError, TypeError, AttributeError, KeyError):
                return ""
        if ext == ".pdf":
            try:
                import pdfplumber
                parts = []
                with pdfplumber.open(str(path)) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text() or ""
                        parts.append(t)
                return "\n".join(parts)
            except (OSError, ImportError, ValueError, TypeError, AttributeError, KeyError):
                return ""
        return ""

    # ---- 切段 ----
    def _chunk_text(self, text: str) -> list[str]:
        # 优先按"第X条/章"切；不行则按字符数硬切
        parts = re.split(r"(第[一二三四五六七八九十百0-9]+[章条])", text)
        chunks = []
        buf = ""
        for p in parts:
            if len(buf) + len(p) > self.chunk_size:
                if buf:
                    chunks.append(buf)
                buf = p
            else:
                buf += p
        if buf:
            chunks.append(buf)
        # 如果没切出来任何东西，硬切
        if not chunks:
            chunks = [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]
        return chunks

    # ---- LLM 调用 ----
    def _extract_from_chunk(self, doc_name: str, chunk: str, idx: int, category_hint: str) -> list[RuleItem]:
        prompt = RULE_EXTRACT_PROMPT.format(doc_name=doc_name, chunk=chunk[:self.chunk_size])
        if category_hint:
            prompt += f"\n\n提示：本文档 category 倾向于'{category_hint}'。"
        try:
            llm = self._get_llm()
            resp = llm.simple_chat("你是规则抽取助手，只输出 JSON。", prompt)
            data = self._parse_json_array(resp)
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError):
            return []
        out = []
        for j, d in enumerate(data):
            if not isinstance(d, dict):
                continue
            try:
                out.append(RuleItem(
                    rule_id=d.get("rule_id") or f"{Path(doc_name).stem}_C{idx}_R{j:02d}",
                    source_doc=doc_name,
                    source_page=str(d.get("source_page", "")),
                    category=d.get("category") or category_hint or "未分类",
                    title=str(d.get("title") or "")[:40],
                    content=str(d.get("content") or "")[:600],
                    trigger_condition=str(d.get("trigger_condition") or ""),
                    severity=self._parse_severity(d.get("severity")),
                    rule_type=RuleType.EXTRACTED,
                ))
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
        return out

    def _parse_json_array(self, resp: str) -> list:
        resp = re.sub(r"```json\s*", "", resp)
        resp = re.sub(r"```\s*", "", resp)
        m = re.search(r"\[[\s\S]*\]", resp)
        if not m:
            return []
        try:
            data = json.loads(m.group())
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, ValueError, TypeError):
            return []

    def _parse_severity(self, v) -> RiskLevel:
        if isinstance(v, str):
            v = v.lower()
            if v in ("red", "严重", "高"):
                return RiskLevel.RED
            if v in ("green", "提示", "低"):
                return RiskLevel.GREEN
        return RiskLevel.YELLOW

    # ---- 去重 ----
    def _dedup(self, rules: list[RuleItem]) -> list[RuleItem]:
        seen = set()
        out = []
        for r in rules:
            key = (r.title.strip(), r.content[:80].strip())
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out
