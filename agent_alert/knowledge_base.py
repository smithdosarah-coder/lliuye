# -*- coding: utf-8 -*-
"""Agent4 贷中预警 — 知识库装配器（薄包装）

职责：把三类上传（在贷客户名录 / 预警规则 JSON / 内部管理制度 Word/PDF/MD）
解析为结构化知识库，供批量扫描使用。复用 shared.kb_scan.KnowledgeBase，
扩展读取场景预置目录（demo_data/agent_alert）和 policy 的即时抽取。
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from shared.kb_scan.knowledge_base import KnowledgeBase
from shared.kb_scan.models import RuleItem, CompanyProfile, RuleType, RiskLevel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO_DIR = PROJECT_ROOT / "demo_data" / "agent_alert"


class AlertKnowledgeBase(KnowledgeBase):
    """贷中风险预警专用知识库。

    - customers: list[CompanyProfile]  在贷客户名录（Excel/CSV/JSONL）
    - rules:     list[RuleItem]        预警规则（JSON 结构化 + 可选从 policy 抽取）
    - clauses:   list[dict]            内部管理制度条款（政策文档章条切分）
    - scenario_meta: dict              场景元数据（预期结果等）
    """

    def __init__(self, name: str = "alert_kb"):
        super().__init__(name=name)
        self.scenario_meta: dict[str, Any] = {}
        self.policy_text: str = ""

    # ------------------------------------------------------------------
    # 加载入口
    # ------------------------------------------------------------------

    @classmethod
    def from_uploads(
        cls,
        customer_files: list[str] | None = None,
        rule_files: list[str] | None = None,
        policy_files: list[str] | None = None,
    ) -> "AlertKnowledgeBase":
        kb = cls()
        for fp in customer_files or []:
            kb.load_file(fp, doc_type="customer_list")
        for fp in rule_files or []:
            kb.load_file(fp, doc_type="rule")
        for fp in policy_files or []:
            kb.load_policy(fp)
        return kb

    @classmethod
    def from_scenario(
        cls, scenario_dir: str | Path = DEFAULT_SCENARIO_DIR
    ) -> "AlertKnowledgeBase":
        """从预置场景目录加载（Demo 场景卡用）。"""
        d = Path(scenario_dir)
        kb = cls()
        # 客户
        cust = d / "loan_customers.xlsx"
        if cust.exists():
            kb.load_file(str(cust), doc_type="customer_list")
        else:
            # 回退 jsonl
            j = d / "loan_customers.jsonl"
            if j.exists():
                kb.load_file(str(j), doc_type="customer_list")
        # 规则
        rule = d / "warning_rules.json"
        if rule.exists():
            kb.load_file(str(rule), doc_type="rule")
        # 制度
        for pname in ("internal_policy.md", "internal_policy.docx", "internal_policy.pdf"):
            p = d / pname
            if p.exists():
                kb.load_policy(str(p))
                break
        # 场景元数据
        meta = d / "scenario.json"
        if meta.exists():
            try:
                kb.scenario_meta = json.loads(meta.read_text(encoding="utf-8"))
            except Exception:
                kb.scenario_meta = {}
        return kb

    # ------------------------------------------------------------------
    # 制度加载（带即时规则抽取）
    # ------------------------------------------------------------------

    def load_policy(self, policy_path: str | Path, use_llm: bool = False) -> dict:
        """加载内部管理制度。

        - 按"第X条"切分 clauses（供 cross_matcher 逐条匹配）
        - 把 clauses 作为规则补充到 self.rules（带 POL- 前缀的 rule_id）
        - use_llm=True 时调用 shared.RuleExtractor 做结构化抽取（更精准但慢）
        """
        meta = self.load_file(str(policy_path), doc_type="policy")
        # 读取原文（供下游展示）
        try:
            p = Path(policy_path)
            self.policy_text = self._read_text(p)
        except Exception:
            self.policy_text = ""

        # 把 clauses 映射为 POL- 类 RuleItem（覆盖掉默认一段一规则的兜底）
        # 先清掉本次解析产生的非结构化 rule（rule_type=EXTRACTED 且来自本文件）
        src_name = Path(policy_path).name
        self.rules = [r for r in self.rules if r.source_doc != src_name]

        # 从 clauses 选 trigger_condition 明显的条款
        pol_rules = self._clauses_to_rules(self.clauses, src_name)
        self.rules.extend(pol_rules)
        meta["converted_pol_rules"] = len(pol_rules)

        if use_llm:
            try:
                from shared.kb_scan.rule_extractor import RuleExtractor
                extractor = RuleExtractor()
                llm_rules = extractor.extract(policy_path, category_hint="内部制度")
                # 去重 + 补充
                existing_titles = {r.title for r in self.rules}
                for r in llm_rules:
                    if r.title in existing_titles:
                        continue
                    self.rules.append(r)
                meta["llm_extracted_rules"] = len(llm_rules)
            except Exception as e:
                meta["llm_extract_error"] = str(e)[:120]
        return meta

    def _clauses_to_rules(self, clauses: list[dict], src_name: str) -> list[RuleItem]:
        """把政策条款映射为 POL-xxx 规则。

        扫描 clauses 文本，如果出现 trigger 关键词（逾期/资产负债/抵押/重整/变更 等）则生成规则。
        严重度按关键词启发式判定。
        """
        keyword_rules = [
            ("POL-001", "逾期超过阈值", "yellow", ["逾期"]),
            ("POL-002", "抵押物价值下降", "yellow", ["抵押物", "评估价值", "下降"]),
            ("POL-003", "关联方重整预警线", "red",
             ["关联方", "重整", "预警线", "主要客户", "破产"]),
            ("POL-004", "授信集中度超限", "yellow",
             ["授信", "集中度", "一级资本"]),
            ("POL-005", "用款用途偏离", "red",
             ["用途", "偏离", "挪用"]),
            ("POL-006", "贷后检查缺位", "yellow",
             ["贷后检查", "缺位", "逾期"]),
            ("POL-007", "供应链核心企业动向", "yellow",
             ["供应链", "核心企业", "产销"]),
        ]
        out: list[RuleItem] = []
        full_text = "\n".join(c.get("content", "") for c in clauses)
        for rid, title, sev, kws in keyword_rules:
            hit_kw_count = sum(1 for k in kws if k in full_text)
            if hit_kw_count >= max(1, len(kws) // 2):
                # 找出原文最相关的条款 title
                source_title = ""
                for c in clauses:
                    if all(k in c.get("content", "") for k in kws[:2]):
                        source_title = c.get("title", "")
                        break
                sev_enum = {"red": RiskLevel.RED, "yellow": RiskLevel.YELLOW,
                            "green": RiskLevel.GREEN}.get(sev, RiskLevel.YELLOW)
                out.append(RuleItem(
                    rule_id=rid,
                    source_doc=src_name,
                    source_page=source_title,
                    category="内部制度",
                    title=title,
                    content="；".join(kws),
                    trigger_condition=" ".join(kws),
                    severity=sev_enum,
                    rule_type=RuleType.EXTRACTED,
                ))
        return out

    # ------------------------------------------------------------------
    # 上层查询
    # ------------------------------------------------------------------

    def get_external_rules(self) -> list[RuleItem]:
        """外部信号类规则（FIN/LAW/BIZ/IND/REL）"""
        return [r for r in self.rules if not r.rule_id.startswith("POL")]

    def get_internal_rules(self) -> list[RuleItem]:
        """内部制度类规则（POL-xxx）"""
        return [r for r in self.rules if r.rule_id.startswith("POL")]

    def summary(self) -> str:
        parts = []
        if self.companies:
            parts.append(f"{len(self.companies)} 家在贷客户")
        if self.rules:
            ext = len(self.get_external_rules())
            pol = len(self.get_internal_rules())
            parts.append(f"{len(self.rules)} 条规则（外部 {ext} / 内部 {pol}）")
        if self.clauses:
            parts.append(f"{len(self.clauses)} 条制度条款")
        return " · ".join(parts) or "空知识库"
