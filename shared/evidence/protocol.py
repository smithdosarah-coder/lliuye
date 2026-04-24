# -*- coding: utf-8 -*-
"""Evidence-First Protocol · 三阶段抽象基类（CLAUDE.md §3.3）

三阶段 = Collect / Generate Grounded / Self-Audit。5 个 Agent 的 LLM 生成调用
都应走 `EvidenceFirstPipeline.run(...)`，实现各子类的三个钩子。

为什么是抽象类而不是函数 —— 三阶段之间有共享 context（evidence bundle / audit 记录），
用 template method 约束生命周期，避免子类"写 generate 忘了写 audit"。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)


UNFILLED_MARKER = "未能自动填写"
"""低置信字段的统一标记；比编一个看起来对的数字更有价值（CLAUDE.md §3.3）。"""


# ---------------------------------------------------------------------------
# 通用数据容器
# ---------------------------------------------------------------------------


@dataclass
class EvidenceItem:
    """单条证据 —— 带出处 + 置信度。

    - `source`: 来源标识（文件名 / URL / 数据表名）
    - `snippet`: 原文摘录（供后续 audit 反查）
    - `ref_id`: 稳定 ID，LLM 正文里可引用 `[ref:ref_id]`
    - `confidence`: 0-1，< 0.5 的字段被视为"未能自动填写"
    - `meta`: 附加业务字段（年份、单位、主体名等）
    """

    source: str
    snippet: str
    ref_id: str
    confidence: float = 1.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "snippet": self.snippet,
            "ref_id": self.ref_id,
            "confidence": self.confidence,
            "meta": self.meta,
        }


@dataclass
class EvidenceBundle:
    """Phase 1 产物 —— 本次生成用到的全部证据。"""

    items: list[EvidenceItem] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    """本次 collect 已知无证据的字段名，Phase 2 会把它们写成 `UNFILLED_MARKER`。"""

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item)

    def mark_missing(self, field_name: str) -> None:
        if field_name not in self.missing_fields:
            self.missing_fields.append(field_name)

    def by_ref(self, ref_id: str) -> EvidenceItem | None:
        for it in self.items:
            if it.ref_id == ref_id:
                return it
        return None


@dataclass
class GroundedDraft:
    """Phase 2 产物 —— LLM 锚定生成的初稿 + 引用反查索引。"""

    content: str
    citations: list[str] = field(default_factory=list)
    """本草稿里使用到的 evidence ref_id 列表（用于 audit 反查）。"""
    unfilled_fields: list[str] = field(default_factory=list)


@dataclass
class AuditFinding:
    """Phase 3 中单条审计发现。"""

    level: str  # 'block' | 'warn' | 'info'
    code: str
    message: str
    related_ref: str | None = None


@dataclass
class AuditedResult:
    """Phase 3 产物 —— 过闸后的最终输出。"""

    content: str
    evidence_trail: list[dict[str, Any]]
    unfilled_fields: list[str]
    findings: list[AuditFinding]
    blocked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "evidence_trail": self.evidence_trail,
            "unfilled_fields": self.unfilled_fields,
            "findings": [
                {"level": f.level, "code": f.code, "message": f.message,
                 "related_ref": f.related_ref}
                for f in self.findings
            ],
            "blocked": self.blocked,
        }


# ---------------------------------------------------------------------------
# 抽象管线
# ---------------------------------------------------------------------------


C = TypeVar("C")
"""子类的上下文类型（LLM client / 输入 payload / prompt 配置等的集合）。"""


class EvidenceFirstPipeline(ABC, Generic[C]):
    """Evidence-First Protocol 三阶段基类 —— 所有 5 Agent 的 LLM 生成应继承此类。

    **钩子方法**（子类必须实现）：
    - `collect(context)` → `EvidenceBundle`
    - `generate_grounded(context, bundle)` → `GroundedDraft`
    - `self_audit(context, bundle, draft)` → `list[AuditFinding]`

    **主入口 `run(context)`**（template method）：
    1. 调 collect 收集证据（若没拿到任何证据则短路走降级）
    2. 调 generate_grounded 用证据写初稿
    3. 调 self_audit 审核初稿
    4. 若 audit 标 block → content 替换为 UNFILLED_MARKER 并回传 blocked=True
    """

    name: str = "unnamed_pipeline"

    # ---- 钩子 ----

    @abstractmethod
    def collect(self, context: C) -> EvidenceBundle:
        """Phase 1 —— 逐字段查找材料/工具产出，产出证据清单。"""

    @abstractmethod
    def generate_grounded(self, context: C, bundle: EvidenceBundle) -> GroundedDraft:
        """Phase 2 —— 只用证据清单生成正文；缺证据字段写 UNFILLED_MARKER。"""

    @abstractmethod
    def self_audit(
        self, context: C, bundle: EvidenceBundle, draft: GroundedDraft
    ) -> list[AuditFinding]:
        """Phase 3 —— 反查每个数字/事实的证据；检幻觉/矛盾/冗余。"""

    # ---- 模板方法 ----

    def run(self, context: C) -> AuditedResult:
        bundle = self.collect(context)
        logger.debug(
            "[%s] collect → %d items, %d missing",
            self.name, len(bundle.items), len(bundle.missing_fields),
        )

        draft = self.generate_grounded(context, bundle)
        logger.debug(
            "[%s] generate → %d chars, %d citations, %d unfilled",
            self.name, len(draft.content), len(draft.citations), len(draft.unfilled_fields),
        )

        findings = self.self_audit(context, bundle, draft)
        blocked = any(f.level == "block" for f in findings)

        content = draft.content
        if blocked:
            logger.warning(
                "[%s] audit blocked: %s",
                self.name,
                "; ".join(f.message for f in findings if f.level == "block"),
            )

        return AuditedResult(
            content=content,
            evidence_trail=[it.to_dict() for it in bundle.items],
            unfilled_fields=sorted(set(draft.unfilled_fields) | set(bundle.missing_fields)),
            findings=findings,
            blocked=blocked,
        )

    # ---- 工具 ----

    @staticmethod
    def is_low_confidence(item: EvidenceItem, threshold: float = 0.5) -> bool:
        return item.confidence < threshold
