# -*- coding: utf-8 -*-
"""Agent5 合规专用知识库。

三类物料：
  - policies         监管政策（Word / PDF / MD）
  - internal_rules   内部制度
  - business_data    业务 Excel / CSV（放款 / 合作 / 模型）

策略：
  - 政策 & 内部制度 → 按「第X条」切分为 clauses（沿用 policy_parser 的章节切分思路）
  - 业务 Excel → 按 sheet + 表头解析为 raw rows（event_extractor 负责下一步转换为 BusinessEvent）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from shared.kb_scan.knowledge_base import KnowledgeBase as SharedKB


HERE = Path(__file__).parent
SCENARIO_ROOT = HERE.parent / "demo_data" / "agent_compliance" / "scenarios"


class ComplianceKnowledgeBase(SharedKB):
    """合规巡检知识库装配器。

    使用三槽位上传区分：policies / internal_rules / business_data。
    """

    def __init__(self, name: str = "compliance"):
        super().__init__(name=name)
        # 除了父类的 rules/clauses/business_events/raw_files，再加本 Agent 特有的：
        self.policy_clauses: list[dict] = []   # 监管政策条款
        self.internal_clauses: list[dict] = []  # 内部制度条款
        self.business_tables: dict[str, list[dict]] = {}  # {表名: rows}
        self.source_map: dict[str, str] = {}   # {file_name: 文件类别}

    # ------------------------------------------------------------------
    # 三槽位装载
    # ------------------------------------------------------------------

    def load_policies(self, paths: list[str | Path]) -> list[dict]:
        metas = []
        for p in paths:
            path = Path(p)
            if not path.exists():
                metas.append({"path": str(path), "status": "not_found"})
                continue
            clauses = self._parse_policy_doc(path)
            for c in clauses:
                c["kind"] = "policy"
            self.policy_clauses.extend(clauses)
            self.clauses.extend(clauses)
            self.source_map[path.name] = "policy"
            metas.append({
                "path": str(path), "status": "ok", "kind": "policy",
                "clauses": len(clauses), "name": path.name,
            })
            self.raw_files.append(metas[-1])
        return metas

    def load_internal_rules(self, paths: list[str | Path]) -> list[dict]:
        metas = []
        for p in paths:
            path = Path(p)
            if not path.exists():
                metas.append({"path": str(path), "status": "not_found"})
                continue
            clauses = self._parse_policy_doc(path)
            for c in clauses:
                c["kind"] = "internal"
            self.internal_clauses.extend(clauses)
            self.clauses.extend(clauses)
            self.source_map[path.name] = "internal"
            metas.append({
                "path": str(path), "status": "ok", "kind": "internal",
                "clauses": len(clauses), "name": path.name,
            })
            self.raw_files.append(metas[-1])
        return metas

    def load_business_data(self, paths: list[str | Path]) -> list[dict]:
        metas = []
        for p in paths:
            path = Path(p)
            if not path.exists():
                metas.append({"path": str(path), "status": "not_found"})
                continue
            rows = self._parse_business_data(path)
            # 按 _sheet 归档
            for r in rows:
                sheet = r.get("_sheet") or path.stem
                self.business_tables.setdefault(sheet, []).append(r)
                self.business_events.append({**r, "_source_file": path.name})
            self.source_map[path.name] = "business"
            metas.append({
                "path": str(path), "status": "ok", "kind": "business",
                "rows": len(rows), "name": path.name,
            })
            self.raw_files.append(metas[-1])
        return metas

    # ------------------------------------------------------------------
    # 场景一键加载
    # ------------------------------------------------------------------

    @classmethod
    def from_scenario(cls, scenario_id: str) -> "ComplianceKnowledgeBase":
        """根据 demo_data/agent_compliance/scenarios/{id}/scenario.json 加载。"""
        sdir = SCENARIO_ROOT / scenario_id
        meta_path = sdir / "scenario.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"scenario.json not found: {meta_path}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        kb = cls(name=f"compliance_{scenario_id}")
        kb.scenario_meta = meta
        kb.scenario_dir = sdir

        kb.load_policies([sdir / f for f in meta.get("policies", [])])
        kb.load_internal_rules([sdir / f for f in meta.get("internal_rules", [])])
        kb.load_business_data([sdir / f for f in meta.get("business_data", [])])
        return kb

    @classmethod
    def from_uploads(cls,
                     policy_files: list[str] | None = None,
                     internal_files: list[str] | None = None,
                     business_files: list[str] | None = None,
                     ) -> "ComplianceKnowledgeBase":
        kb = cls(name="compliance_upload")
        if policy_files:
            kb.load_policies(policy_files)
        if internal_files:
            kb.load_internal_rules(internal_files)
        if business_files:
            kb.load_business_data(business_files)
        return kb

    # ------------------------------------------------------------------
    # 摘要
    # ------------------------------------------------------------------

    def summary(self) -> str:
        parts = []
        n_policy_files = sum(1 for v in self.source_map.values() if v == "policy")
        n_internal_files = sum(1 for v in self.source_map.values() if v == "internal")
        n_business_files = sum(1 for v in self.source_map.values() if v == "business")
        if n_policy_files:
            parts.append(f"{n_policy_files} 份监管政策 / {len(self.policy_clauses)} 条条款")
        if n_internal_files:
            parts.append(f"{n_internal_files} 份内部制度 / {len(self.internal_clauses)} 条条款")
        if n_business_files:
            parts.append(
                f"{n_business_files} 份业务数据 / {sum(len(v) for v in self.business_tables.values())} 行"
            )
        return " · ".join(parts) or "空知识库"
