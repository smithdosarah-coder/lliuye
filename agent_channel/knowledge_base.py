# -*- coding: utf-8 -*-
"""Agent1 专用的 KnowledgeBase 薄包装。

对 shared.kb_scan.KnowledgeBase 的 Agent1 专用装载逻辑封装：
- 客户名录（Excel/CSV/JSON）→ kb.companies
- 政策文件（Word/PDF/TXT）→ kb.clauses
- 行业指引（Word/PDF/TXT）→ kb.raw_files["raw_text"]

单独抽出来是为了让 Agent1 拥有"这三类文件"的专用语义，
但底层完全复用共享 KnowledgeBase，避免重复造轮子。
"""
from __future__ import annotations

from pathlib import Path

from shared.kb_scan.knowledge_base import KnowledgeBase as SharedKB


class ChannelKnowledgeBase(SharedKB):
    """Agent1 专用 KB。

    在共享 KB 基础上增加：
    - industry_guide_texts：行业指引原文拼接，供 LLM 画像抽取时引用
    - 强类型装载方法（显式传入文件类别，不依赖文件名推断）
    """

    def __init__(self, name: str = "channel"):
        super().__init__(name=name)
        self.industry_guide_texts: list[str] = []

    # ---- 显式装载入口（推荐使用，避免类型推断失败） ----

    def load_customer_file(self, file_path: str) -> dict:
        return self.load_file(file_path, doc_type="customer_list")

    def load_policy_file(self, file_path: str) -> dict:
        return self.load_file(file_path, doc_type="policy")

    def load_industry_guide(self, file_path: str) -> dict:
        meta = self.load_file(file_path, doc_type="industry_guide")
        raw = meta.get("raw_text") or ""
        if raw:
            self.industry_guide_texts.append(raw)
        return meta

    # ---- 批量自动装载（按文件名推断） ----

    def load_mixed_files(self, file_paths: list[str]) -> list[dict]:
        """智能推断类型并装载。文件名命中"客户/名录/customer" → customer_list；
        "政策/办法/policy" → policy；"指引/guide/行业" → industry_guide；其余按扩展名兜底。"""
        metas = []
        for fp in file_paths:
            p = Path(fp)
            name = p.name.lower()
            ext = p.suffix.lower()
            if any(k in name for k in ["客户", "名录", "customer", "list"]):
                meta = self.load_customer_file(fp)
            elif any(k in name for k in ["政策", "办法", "通知", "方案", "policy"]):
                meta = self.load_policy_file(fp)
            elif any(k in name for k in ["指引", "guide", "行业"]):
                meta = self.load_industry_guide(fp)
            elif ext in {".xlsx", ".xls", ".csv"}:
                meta = self.load_customer_file(fp)
            elif ext in {".docx", ".pdf", ".txt", ".md"}:
                # 无法强判时：按"含客户列数据"打开失败再回落成 policy
                meta = self.load_policy_file(fp)
            else:
                meta = {"path": fp, "status": "skipped", "reason": "unknown_type"}
            metas.append(meta)
        return metas

    # ---- 给 LLM 的 context 拼装 ----

    def policy_text(self, max_chars: int = 4000) -> str:
        """把 clauses 拼成一段文本给 LLM 用。"""
        if not self.clauses:
            return ""
        buf = []
        total = 0
        for c in self.clauses:
            chunk = f"【{c.get('title','')}】{c.get('content','')}"
            if total + len(chunk) > max_chars:
                break
            buf.append(chunk)
            total += len(chunk)
        return "\n".join(buf)

    def industry_guide_text(self, max_chars: int = 3000) -> str:
        if not self.industry_guide_texts:
            return ""
        joined = "\n\n".join(self.industry_guide_texts)
        return joined[:max_chars]

    def customer_count(self) -> int:
        return len(self.companies)
