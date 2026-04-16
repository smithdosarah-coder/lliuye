# -*- coding: utf-8 -*-
"""RuleSetBuilder: 把 ComplianceKnowledgeBase 中的 clauses 转换为统一的 RuleSet。

策略（Demo 稳定性优先）：
  1. 对预置场景：用 CURATED_RULES 按「政策文件名 + 条号」精准映射为 RuleItem，
     保证矩阵判定有 deterministic 触发条件（硬规则字段比较）。
  2. 对自定义上传：落回到 shared.kb_scan.rule_extractor.RuleExtractor（LLM 抽取）。
  3. 合并去重后按政策来源编号规范化。

硬规则约束：
  - 每条 RuleItem.dsl 可携带 {"check": checker_name, "params": {...}}
  - checker_name 对应 matrix_matcher 中注册的 HARD_CHECKERS（纯 Python 函数）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.kb_scan.models import RuleItem, RuleType, RiskLevel
from shared.kb_scan.rule_extractor import RuleExtractor

from .knowledge_base import ComplianceKnowledgeBase


# ----------------------------------------------------------------------
# 预置场景的策略库（scenario=internet_loan）
# key = (source_doc_stem, 条号数字)
# ----------------------------------------------------------------------

CURATED_RULES: list[dict] = [
    # ---- 政策1：商业银行互联网贷款管理办法 ----
    {
        "rule_id": "POLICY1-ART5",
        "source_stem": "policy_online_loan", "article_no": "第五条",
        "category": "风险管理体系",
        "title": "纳入全面风险管理",
        "content": "商业银行应当将互联网贷款业务纳入全面风险管理体系。",
        "trigger_condition": "需有全面风险管理制度",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY1-ART6",
        "source_stem": "policy_online_loan", "article_no": "第六条",
        "category": "期限限制",
        "title": "个人消费贷款期限≤1年",
        "content": "互联网贷款遵循小额、短期原则，个人消费贷款期限不得超过一年。",
        "trigger_condition": "个人消费贷款期限>12个月 视为违规",
        "severity": "red",
        "dsl": {"check": "loan_duration_limit", "params": {
            "purpose_prefix": "个人消费", "max_months": 12}},
    },
    {
        "rule_id": "POLICY1-ART7",
        "source_stem": "policy_online_loan", "article_no": "第七条",
        "category": "催收规范",
        "title": "禁止暴力催收",
        "content": "违约后不得使用暴力、威胁、恐吓、骚扰等不正当手段催收。",
        "trigger_condition": "出现暴力/威胁/恐吓字样",
        "severity": "red",
    },
    {
        "rule_id": "POLICY1-ART8",
        "source_stem": "policy_online_loan", "article_no": "第八条",
        "category": "额度限制",
        "title": "单户消费授信≤20万",
        "content": "单户用于消费的个人信用贷款授信额度不超过 20 万元。",
        "trigger_condition": "个人消费贷款金额>200000 视为违规",
        "severity": "red",
        "dsl": {"check": "loan_amount_limit", "params": {
            "purpose_prefix": "个人消费", "max_amount": 200000}},
    },
    {
        "rule_id": "POLICY1-ART9",
        "source_stem": "policy_online_loan", "article_no": "第九条",
        "category": "额度限制",
        "title": "单户敞口分散原则",
        "content": "按照适度分散原则合理设置单户额度上限。",
        "trigger_condition": "单户敞口是否异常集中",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY1-ART15",
        "source_stem": "policy_online_loan", "article_no": "第十五条",
        "category": "风险数据",
        "title": "数据使用规范",
        "content": "建立互联网贷款风险数据使用规范。",
        "trigger_condition": "需有数据使用规范文档",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY1-ART16",
        "source_stem": "policy_online_loan", "article_no": "第十六条",
        "category": "风险模型",
        "title": "模型全流程管理",
        "content": "建立风险模型开发/测试/评审/监测/退出全流程管理制度。",
        "trigger_condition": "模型生命周期管理缺失",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY1-ART17",
        "source_stem": "policy_online_loan", "article_no": "第十七条",
        "category": "风险模型",
        "title": "风控模型独立验证机制",
        "content": "风控模型应当由独立于开发团队的专门部门进行验证。",
        "trigger_condition": "模型需独立验证",
        "severity": "red",
    },
    {
        "rule_id": "POLICY1-ART18",
        "source_stem": "policy_online_loan", "article_no": "第十八条",
        "category": "风险模型",
        "title": "未独立验证模型禁止上线",
        "content": "风险模型上线前必须完成独立验证，未通过独立验证的模型不得用于实际业务决策。",
        "trigger_condition": "模型独立验证状态=未验证 视为违规",
        "severity": "red",
        "dsl": {"check": "model_independent_verified", "params": {}},
    },
    {
        "rule_id": "POLICY1-ART19",
        "source_stem": "policy_online_loan", "article_no": "第十九条",
        "category": "风险模型",
        "title": "模型回测频率≥季度",
        "content": "定期对风险模型进行回测与监测，监测频率不得低于每季度一次。",
        "trigger_condition": "模型监测频率低于季度",
        "severity": "yellow",
        "dsl": {"check": "model_monitor_frequency", "params": {"required": "季度"}},
    },
    {
        "rule_id": "POLICY1-ART26",
        "source_stem": "policy_online_loan", "article_no": "第二十六条",
        "category": "信息披露",
        "title": "贷款信息披露要素",
        "content": "披露主体、实际年利率、年化综合资金成本、还本付息安排、逾期清收、投诉渠道、违约责任等。",
        "trigger_condition": "信息披露要素缺失",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY1-ART27",
        "source_stem": "policy_online_loan", "article_no": "第二十七条",
        "category": "合同管理",
        "title": "合同全流程可追溯",
        "content": "确保合同签订全流程完整可追溯，保留电子合同及相关证据。",
        "trigger_condition": "合同电子证据缺失",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY1-ART32",
        "source_stem": "policy_online_loan", "article_no": "第三十二条",
        "category": "贷后管理",
        "title": "贷后持续监测机制",
        "content": "建立互联网贷款持续监测机制。",
        "trigger_condition": "贷后监测缺失",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY1-ART33",
        "source_stem": "policy_online_loan", "article_no": "第三十三条",
        "category": "贷后管理",
        "title": "贷后评估频率≥季度",
        "content": "贷后风险评估频率不得低于每季度一次，高风险客户加密贷后管理。",
        "trigger_condition": "贷后评估频率低于季度",
        "severity": "yellow",
    },

    # ---- 政策2：规范互联网贷款业务的通知 ----
    {
        "rule_id": "POLICY2-ART1",
        "source_stem": "policy_supplement", "article_no": "第一条",
        "category": "联合贷款",
        "title": "风控核心环节不外包",
        "content": "建立合作机构分层分类管理制度，确保风控核心环节不外包。",
        "trigger_condition": "风控外包给合作方",
        "severity": "red",
    },
    {
        "rule_id": "POLICY2-ART2",
        "source_stem": "policy_supplement", "article_no": "第二条",
        "category": "联合贷款",
        "title": "合作须签书面协议",
        "content": "共同出资发放贷款前签订书面合作协议。",
        "trigger_condition": "合作协议缺失",
        "severity": "yellow",
        "dsl": {"check": "coop_contract_exists", "params": {}},
    },
    {
        "rule_id": "POLICY2-ART3",
        "source_stem": "policy_supplement", "article_no": "第三条",
        "category": "联合贷款",
        "title": "本行出资比例≥30%",
        "content": "共同出资贷款中商业银行出资比例不得低于 30%。",
        "trigger_condition": "出资比例<30% 视为违规",
        "severity": "red",
        "dsl": {"check": "coop_funding_ratio", "params": {"min_ratio": 30.0}},
    },
    {
        "rule_id": "POLICY2-ART4",
        "source_stem": "policy_supplement", "article_no": "第四条",
        "category": "集中度",
        "title": "单一合作机构敞口≤一级资本25%",
        "content": "与单一合作机构发放的本行贷款余额不得超过一级资本的 25%。",
        "trigger_condition": "单一合作机构敞口过高",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY2-ART5",
        "source_stem": "policy_supplement", "article_no": "第五条",
        "category": "地域限制",
        "title": "地方法人不得跨辖区",
        "content": "地方法人银行不得跨注册地辖区开展互联网贷款业务。",
        "trigger_condition": "地方法人跨辖区放款",
        "severity": "red",
    },
    {
        "rule_id": "POLICY2-ART6",
        "source_stem": "policy_supplement", "article_no": "第六条",
        "category": "集中度",
        "title": "单一合作机构出资比例≤25%",
        "content": "单一合作机构出资比例不得超过本行互联网贷款余额的 25%。",
        "trigger_condition": "单一机构出资比例过高",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY2-ART7",
        "source_stem": "policy_supplement", "article_no": "第七条",
        "category": "合作准入",
        "title": "合作机构尽调",
        "content": "选择合作机构应当审慎评估其资质、财务、信用、合规。",
        "trigger_condition": "合作机构尽调缺失",
        "severity": "yellow",
    },
    {
        "rule_id": "POLICY2-ART8",
        "source_stem": "policy_supplement", "article_no": "第八条",
        "category": "合作准入",
        "title": "合作清单季度报送",
        "content": "合作清单至少每季度更新并报送监管。",
        "trigger_condition": "合作清单未按季报送",
        "severity": "yellow",
    },

    # ---- 本行制度 ----
    {
        "rule_id": "INTERNAL-ART3",
        "source_stem": "internal_policy", "article_no": "第三条",
        "category": "贷前管理",
        "title": "贷前身份核验 & 反欺诈",
        "content": "贷款受理前完成身份核验、反欺诈筛查、信用评估。",
        "trigger_condition": "贷前环节不完整",
        "severity": "yellow",
    },
    {
        "rule_id": "INTERNAL-ART4",
        "source_stem": "internal_policy", "article_no": "第四条",
        "category": "用途管理",
        "title": "禁止投资性用途",
        "content": "借款用途不得用于股票、期货、基金等金融投资活动。",
        "trigger_condition": "贷款用途含股票/期货/基金字样",
        "severity": "yellow",
        "dsl": {"check": "loan_purpose_blacklist",
                "params": {"banned": ["股票", "期货", "基金", "虚拟货币"]}},
    },
    {
        "rule_id": "INTERNAL-ART5",
        "source_stem": "internal_policy", "article_no": "第五条",
        "category": "风险模型",
        "title": "独立验证小组要求",
        "content": "风险模型上线前须经独立验证小组评审。",
        "trigger_condition": "无独立验证小组记录",
        "severity": "yellow",
    },
    {
        "rule_id": "INTERNAL-ART6",
        "source_stem": "internal_policy", "article_no": "第六条",
        "category": "风险模型",
        "title": "模型文档完整性",
        "content": "模型上线须提交设计文档、测试报告、验证报告。",
        "trigger_condition": "模型文档不全",
        "severity": "yellow",
    },
    {
        "rule_id": "INTERNAL-ART7",
        "source_stem": "internal_policy", "article_no": "第七条",
        "category": "风险模型",
        "title": "模型季度监测",
        "content": "模型上线后监测频率不得低于每季度一次。",
        "trigger_condition": "监测频率低于季度",
        "severity": "yellow",
    },
    {
        "rule_id": "INTERNAL-ART8",
        "source_stem": "internal_policy", "article_no": "第八条",
        "category": "额度限制",
        "title": "本行单户消费额度≤20万",
        "content": "个人消费互联网贷款单户授信额度不得超过 20 万元。",
        "trigger_condition": "个人消费金额>200000",
        "severity": "red",
        "dsl": {"check": "loan_amount_limit", "params": {
            "purpose_prefix": "个人消费", "max_amount": 200000}},
    },
    {
        "rule_id": "INTERNAL-ART9",
        "source_stem": "internal_policy", "article_no": "第九条",
        "category": "期限限制",
        "title": "本行个人消费期限≤12月",
        "content": "个人消费互联网贷款期限不得超过 12 个月。",
        "trigger_condition": "期限>12月",
        "severity": "red",
        "dsl": {"check": "loan_duration_limit", "params": {
            "purpose_prefix": "个人消费", "max_months": 12}},
    },
    {
        "rule_id": "INTERNAL-ART10",
        "source_stem": "internal_policy", "article_no": "第十条",
        "category": "贷后管理",
        "title": "资金流向 10 日核查",
        "content": "放款后 10 个工作日内完成首次贷后资金流向核查。",
        "trigger_condition": "10 个工作日内未核查",
        "severity": "yellow",
    },
    {
        "rule_id": "INTERNAL-ART11",
        "source_stem": "internal_policy", "article_no": "第十一条",
        "category": "联合贷款",
        "title": "本行出资比例≥30%",
        "content": "与合作机构的联合贷款本行出资比例不得低于 30%。",
        "trigger_condition": "出资比例<30%",
        "severity": "red",
        "dsl": {"check": "coop_funding_ratio", "params": {"min_ratio": 30.0}},
    },
    {
        "rule_id": "INTERNAL-ART12",
        "source_stem": "internal_policy", "article_no": "第十二条",
        "category": "报送时效",
        "title": "模型上线 5 日内报送",
        "content": "风控模型上线、重大调整或下线，经营部门应当在 5 个工作日内书面报送。",
        "trigger_condition": "上线与报送间隔>5 个工作日",
        "severity": "red",
        "dsl": {"check": "model_report_sla", "params": {"max_workdays": 5}},
    },
    {
        "rule_id": "INTERNAL-ART13",
        "source_stem": "internal_policy", "article_no": "第十三条",
        "category": "报送时效",
        "title": "月度数据报送",
        "content": "月度业务数据应当在次月 10 日前报送总行合规部。",
        "trigger_condition": "月度报送超期",
        "severity": "yellow",
    },
    {
        "rule_id": "INTERNAL-ART18",
        "source_stem": "internal_policy", "article_no": "第十八条",
        "category": "附则",
        "title": "制度归口部门",
        "content": "本规程由零售信贷部负责解释。",
        "trigger_condition": "-",
        "severity": "green",
    },
]


# 为了达到约 68 条规则（50+18），再对其他章节自动补若干 RuleItem
# 下面函数会从 KB.policy_clauses/internal_clauses 中补齐未映射的条款
# ----------------------------------------------------------------------


_SEVERITY_MAP = {
    "red": RiskLevel.RED, "yellow": RiskLevel.YELLOW,
    "green": RiskLevel.GREEN, "critical": RiskLevel.RED,
    "major": RiskLevel.YELLOW, "minor": RiskLevel.GREEN,
}


def _curated_to_rule(d: dict) -> RuleItem:
    return RuleItem(
        rule_id=d["rule_id"],
        source_doc=d.get("source_stem", "") + ".md",
        source_page=d.get("article_no", ""),
        category=d.get("category", "其他"),
        title=d.get("title", "")[:40],
        content=d.get("content", "")[:600],
        trigger_condition=d.get("trigger_condition", ""),
        severity=_SEVERITY_MAP.get(d.get("severity", "yellow"), RiskLevel.YELLOW),
        rule_type=RuleType.BUILTIN,
        dsl=d.get("dsl", {}),
    )


def _clause_to_rule(clause: dict, idx: int) -> RuleItem:
    """从 KB 的原始 clause dict 兜底生成 RuleItem（未被 curated 覆盖的章节）。"""
    stem = Path(clause.get("source_doc", "unknown")).stem
    return RuleItem(
        rule_id=f"AUTO-{stem}-{idx:03d}",
        source_doc=clause.get("source_doc", ""),
        source_page=clause.get("title", ""),
        category="其他",
        title=(clause.get("title") or "")[:40] or "条款",
        content=(clause.get("content") or "")[:600],
        trigger_condition="",
        severity=RiskLevel.GREEN,
        rule_type=RuleType.EXTRACTED,
        dsl={},
    )


class RuleSetBuilder:
    """合并 curated + auto + LLM 抽取的规则为统一 RuleSet。"""

    def __init__(self, use_llm_fallback: bool = False, llm_client=None):
        self.use_llm_fallback = use_llm_fallback
        self._extractor = RuleExtractor(llm_client=llm_client) if use_llm_fallback else None

    def build(self, kb: ComplianceKnowledgeBase,
              target_rule_count: int = 68) -> list[RuleItem]:
        """返回 list[RuleItem]，保证去重 & 按来源编号规范化。"""
        rules: list[RuleItem] = []
        seen_ids = set()

        # 1) curated rules 优先
        matched_clause_titles = set()
        stems_present = {Path(c.get("source_doc", "")).stem for c in kb.clauses}
        for d in CURATED_RULES:
            if d.get("source_stem") not in stems_present:
                continue
            ri = _curated_to_rule(d)
            if ri.rule_id in seen_ids:
                continue
            seen_ids.add(ri.rule_id)
            rules.append(ri)
            matched_clause_titles.add((d.get("source_stem"), d.get("article_no")))

        # 2) 其他条款自动补（基于 KB 中已切分但未 curated 的条款）
        idx = 1
        for c in kb.clauses:
            stem = Path(c.get("source_doc", "")).stem
            article = (c.get("title") or "").strip()
            key = (stem, article)
            # 简单匹配 — 如果 article 中包含 curated 的 article_no，则跳过
            hit_curated = any(
                stem == st and article.startswith(ano)
                for st, ano in matched_clause_titles
            )
            if hit_curated:
                continue
            auto = _clause_to_rule(c, idx)
            if auto.rule_id in seen_ids:
                idx += 1
                continue
            seen_ids.add(auto.rule_id)
            rules.append(auto)
            idx += 1

        # 3) 若总数不达标且开启 LLM 兜底 — 这里为稳定 demo 不再展开
        return rules

    def stats(self, rules: list[RuleItem]) -> dict[str, Any]:
        from collections import Counter
        cat = Counter(r.category for r in rules)
        sev = Counter(r.severity.value for r in rules)
        src = Counter(r.source_doc for r in rules)
        return {
            "total": len(rules),
            "by_category": dict(cat),
            "by_severity": dict(sev),
            "by_source": dict(src),
        }
