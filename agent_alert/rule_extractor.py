# -*- coding: utf-8 -*-
"""Agent4 — 内部制度 → 结构化预警规则

薄包装：直接复用 shared.kb_scan.RuleExtractor，但注入更契合内部制度的 category hint
和少量后处理（确保 rule_id 以 POL- 开头）。
"""

from __future__ import annotations
from pathlib import Path

from shared.kb_scan.rule_extractor import RuleExtractor
from shared.kb_scan.models import RuleItem, RuleType


class InternalPolicyExtractor:
    """把本行管理制度 Word/PDF/MD 抽为 POL-xxx 结构化规则。"""

    def __init__(self, llm_client=None):
        self._extractor = RuleExtractor(llm_client=llm_client)

    def extract(self, policy_path: str | Path) -> list[RuleItem]:
        rules = self._extractor.extract(policy_path, category_hint="内部制度")
        # 统一 rule_id 前缀为 POL-
        for i, r in enumerate(rules, 1):
            if not r.rule_id.startswith("POL-"):
                r.rule_id = f"POL-{i:03d}"
            r.rule_type = RuleType.EXTRACTED
            if not r.category:
                r.category = "内部制度"
        return rules
