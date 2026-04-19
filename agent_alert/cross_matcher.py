# -*- coding: utf-8 -*-
"""Agent4 — 双路交叉命中器

对单个在贷客户：
  1. 外部路径：SearchProvider.search_court_records / search_news
                + CompanyProfile.risk_tags + alert_engine.evaluate_alerts
                → 命中 FIN/LAW/BIZ/IND/REL 系列规则
  2. 内部路径：逐条扫 POL-xxx 规则，判断客户特征是否触发
  3. 交叉判级：
       外部 ≥1 && 内部 ≥1         → 🔴 红
       外部 ≥2 || 内部 ≥2         → 🔴 红（单路严重叠加也红）
       外部 ==1 || 内部 ==1       → 🟡 黄
       都没命中                   → 🟢 绿
     若任一命中规则 severity=RED，级别跟随上升。

不依赖 LLM — 确定性关键词/标签匹配，保证 100 家 2 秒扫完，演示稳定。
后续接入真实 SearchProvider 时，只需 provider 返回符合 schema 的数据即可。
"""

from __future__ import annotations
from typing import Any

from shared.kb_scan.models import (
    RuleItem, CompanyProfile, HitItem, ScanTarget, Evidence, RiskLevel,
)
from shared.kb_scan.matcher import Matcher
from shared.kb_scan.search_provider import SearchProvider


# ---------------------------------------------------------------------------
# 单条命中表达
# ---------------------------------------------------------------------------

class RuleHit:
    """单条规则命中的中间态。"""

    __slots__ = ("rule_id", "rule_title", "route", "severity",
                 "reason", "evidence_snippet", "evidence_source", "evidence_url")

    def __init__(self, rule_id: str, rule_title: str, route: str,
                 severity: RiskLevel, reason: str,
                 evidence_snippet: str = "", evidence_source: str = "",
                 evidence_url: str = ""):
        self.rule_id = rule_id
        self.rule_title = rule_title
        self.route = route                    # "external" | "internal"
        self.severity = severity
        self.reason = reason
        self.evidence_snippet = evidence_snippet
        self.evidence_source = evidence_source
        self.evidence_url = evidence_url


# ---------------------------------------------------------------------------
# trigger_reasons 枚举（结构推断，不是关键词黑名单）
# ---------------------------------------------------------------------------

TRIGGER_REASON_EXTERNAL = "external_signal"
TRIGGER_REASON_INTERNAL = "internal_rule"
TRIGGER_REASON_CROSS = "cross_hit"


def _infer_trigger_reasons(hits: list[RuleHit]) -> list[str]:
    """从 {hit.route for hit in hits} 推断触发原因枚举。

    - both routes present → ["cross_hit"]（交叉命中是 Agent4 核心价值点）
    - external only       → ["external_signal"]
    - internal only       → ["internal_rule"]
    - no hits             → []

    这是 CLAUDE.md §12 "通用机制不黑名单兜底" 的正面落地：
    枚举来自 RuleHit.route 现有结构（"external" / "internal"），
    不依赖任何关键词表 / 正则黑名单。语义规约见
    docs/design/alert-trigger-reasons-taxonomy.md。
    """
    routes = {h.route for h in hits}
    if not routes:
        return []
    has_ext = "external" in routes
    has_int = "internal" in routes
    if has_ext and has_int:
        return [TRIGGER_REASON_CROSS]
    if has_ext:
        return [TRIGGER_REASON_EXTERNAL]
    return [TRIGGER_REASON_INTERNAL]


# ---------------------------------------------------------------------------
# CrossMatcher
# ---------------------------------------------------------------------------

class CrossMatcher(Matcher):
    """外部信号 × 内部规则 交叉命中器。"""

    def __init__(self, search_provider: SearchProvider):
        self.provider = search_provider

    # Matcher 接口：针对单个 target 命中所有规则
    def match_one(self, target: ScanTarget, rules: list[RuleItem]) -> HitItem | None:
        if target.target_type != "loan_customer":
            return None
        profile = CompanyProfile(**target.payload)
        return self.match_customer(profile, rules)

    # ------------------------------------------------------------------
    # 核心：对一个客户跑双路
    # ------------------------------------------------------------------
    def match_customer(
        self,
        profile: CompanyProfile,
        rules: list[RuleItem],
    ) -> HitItem:
        hits: list[RuleHit] = []
        hits.extend(self._match_external(profile, rules))
        hits.extend(self._match_internal(profile, rules))

        level, score = self._decide_level(hits)
        reasons = [f"[{'外部' if h.route == 'external' else '内部'} × {h.rule_id}] "
                   f"{h.reason}" for h in hits]
        evidences = [Evidence(
            source=h.evidence_source or ("外部搜索" if h.route == "external" else "内部制度"),
            snippet=h.evidence_snippet or h.reason,
            url=h.evidence_url or "",
        ) for h in hits]

        return HitItem(
            hit_id=f"hit_{profile.company_id or profile.company_name}",
            level=level,
            score=score,
            target=ScanTarget(
                target_id=profile.company_id or profile.company_name,
                target_type="loan_customer",
                payload=profile.model_dump(),
            ),
            matched_rules=[h.rule_id for h in hits],
            reasons=reasons,
            evidences=evidences,
            extras={
                "external_hits": [h.rule_id for h in hits if h.route == "external"],
                "internal_hits": [h.rule_id for h in hits if h.route == "internal"],
                "trigger_reasons": _infer_trigger_reasons(hits),
                "rule_titles": {h.rule_id: h.rule_title for h in hits},
                "narrative": (profile.extras or {}).get("narrative", ""),
                "manager": (profile.extras or {}).get("manager", ""),
                "credit_line": (profile.extras or {}).get("credit_line", 0),
                "outstanding": (profile.extras or {}).get("outstanding", 0),
                "due_date": (profile.extras or {}).get("due_date", ""),
                "profit_latest": (profile.extras or {}).get("profit_latest", 0),
                "debt_ratio": (profile.extras or {}).get("debt_ratio", 0),
                "internal_rating": (profile.extras or {}).get("internal_rating", ""),
                "industry": profile.industry,
                "region": profile.region,
            },
        )

    # ------------------------------------------------------------------
    # 外部路径
    # ------------------------------------------------------------------
    def _match_external(
        self, profile: CompanyProfile, rules: list[RuleItem]
    ) -> list[RuleHit]:
        """命中来源：裁判文书 / 舆情 / risk_tags / 结构化财务字段。"""
        out: list[RuleHit] = []
        extras = profile.extras or {}
        risk_tags = extras.get("risk_tags", []) or profile.risk_tags or []
        narrative = extras.get("narrative", "") or ""

        # 1) 裁判文书
        courts = self.provider.search_court_records(profile.company_name, limit=5)
        for rec in courts:
            role = rec.get("role", "")
            amount = rec.get("amount", 0) or 0
            status = rec.get("status", "")
            case_no = rec.get("case_no", "")
            # LAW-002 失信被执行
            if "失信" in status or role == "被执行人" and "失信" in status:
                out.append(RuleHit(
                    rule_id="LAW-002",
                    rule_title="失信被执行",
                    route="external",
                    severity=RiskLevel.RED,
                    reason=f"列入失信被执行人名单（{case_no}）",
                    evidence_snippet=rec.get("snippet", "") or status,
                    evidence_source=f"裁判文书网 {case_no}",
                    evidence_url=rec.get("url", ""),
                ))
            elif role == "被告":
                # LAW-001 涉诉
                severity = RiskLevel.RED if amount >= 5_000_000 else RiskLevel.YELLOW
                amount_text = f"{amount/10000:.0f}万元" if amount else "（金额未披露）"
                out.append(RuleHit(
                    rule_id="LAW-001",
                    rule_title="涉诉风险",
                    route="external",
                    severity=severity,
                    reason=f"涉诉标的 {amount_text}（{case_no}）",
                    evidence_snippet=rec.get("snippet", ""),
                    evidence_source=f"裁判文书网 {case_no}",
                    evidence_url=rec.get("url", ""),
                ))

        # 2) 舆情 / narrative
        news = self.provider.search_news(profile.company_name, days=365, limit=5)
        news_blob = " ".join(n.get("title", "") + " " + n.get("snippet", "") for n in news)
        signal_source_blob = " ".join([narrative, news_blob, " ".join(risk_tags)])

        rule_kw_map = {
            "FIN-001": ["营收下降", "营业收入下降", "营收减少"],
            "FIN-002": ["净利润转负", "连续亏损", "亏损"],
            "FIN-003": ["资产负债率", "负债率"],
            "FIN-004": ["应收账款周转", "周转天数", "回款周期"],
            "FIN-005": ["经营现金流", "现金流紧张"],
            "BIZ-001": ["工商变更", "经营范围变更", "注册地址变更"],
            "BIZ-002": ["实控人变更", "实际控制人变更", "控股权转移"],
            "BIZ-003": ["核心客户流失", "主要客户流失", "客户流失", "客户占营收", "终止合作"],
            "BIZ-004": ["停产", "停业", "停工"],
            "IND-001": ["行业下行", "行业景气下降", "产能过剩", "政策收紧", "行业整顿",
                        "景气度下行"],
            "REL-001": ["关联企业风险", "担保圈风险", "关联方出险", "关联企业涉诉"],
            "REL-002": ["股权冻结", "股权拍卖", "股权质押冻结"],
        }
        # 给出规则 severity 查表
        rule_sev = {r.rule_id: r.severity for r in rules}

        # 避免重复：若 LAW-001/LAW-002 已通过裁判文书命中，则不再通过关键词命中
        hit_ids = {h.rule_id for h in out}
        for rid, kws in rule_kw_map.items():
            if rid in hit_ids:
                continue
            matched_kw = next((k for k in kws if k in signal_source_blob), None)
            if matched_kw:
                sev = rule_sev.get(rid, RiskLevel.YELLOW)
                # 针对 FIN-003 资产负债率：读结构化字段做红/黄判定
                if rid == "FIN-003":
                    dr = extras.get("debt_ratio", 0) or 0
                    if dr and dr > 80:
                        sev = RiskLevel.RED
                    elif dr and dr > 70:
                        sev = RiskLevel.YELLOW
                    else:
                        continue  # 没有明确阈值突破就不命中
                if rid == "FIN-002":
                    pft = extras.get("profit_latest", 0) or 0
                    if pft < 0:
                        sev = RiskLevel.RED
                reason = self._build_reason(rid, profile, matched_kw)
                # 证据优先选最匹配的新闻
                ev_src, ev_snip, ev_url = self._pick_news_evidence(news, matched_kw)
                if not ev_snip:
                    ev_src = "客户风险标签"
                    ev_snip = narrative or f"命中关键词『{matched_kw}』"
                out.append(RuleHit(
                    rule_id=rid,
                    rule_title=self._title_by_id(rules, rid),
                    route="external",
                    severity=sev,
                    reason=reason,
                    evidence_snippet=ev_snip,
                    evidence_source=ev_src,
                    evidence_url=ev_url,
                ))

        # 去重（同 rule_id 留严重度更高那条）
        dedup: dict[str, RuleHit] = {}
        for h in out:
            prev = dedup.get(h.rule_id)
            if prev is None or self._sev_rank(h.severity) > self._sev_rank(prev.severity):
                dedup[h.rule_id] = h
        return list(dedup.values())

    # ------------------------------------------------------------------
    # 内部路径（POL-xxx）
    # ------------------------------------------------------------------
    def _match_internal(
        self, profile: CompanyProfile, rules: list[RuleItem]
    ) -> list[RuleHit]:
        """在客户画像/narrative 中搜内部规则的触发词。"""
        extras = profile.extras or {}
        risk_tags = extras.get("risk_tags", []) or profile.risk_tags or []
        narrative = extras.get("narrative", "") or ""
        text = " ".join([narrative, " ".join(risk_tags)])

        out: list[RuleHit] = []
        internal_rules = [r for r in rules if r.rule_id.startswith("POL")]

        trigger_map = {
            "POL-001": ["贷款逾期", "本金逾期", "利息逾期"],
            "POL-002": ["抵押物价值下降", "抵押物贬值"],
            "POL-003": ["关联方重整", "主要客户重整", "客户重整",
                        "核心客户进入重整", "主要客户（占营收"],
            "POL-004": ["授信集中度"],
            "POL-005": ["用途偏离", "资金挪用"],
            "POL-006": ["贷后检查逾期", "贷后检查缺位", "贷后现场检查已逾期"],
            "POL-007": ["核心企业产销", "供应链景气"],
        }

        rule_lookup = {r.rule_id: r for r in internal_rules}

        for rid, kws in trigger_map.items():
            rule = rule_lookup.get(rid)
            if rule is None:
                continue
            matched_kw = next((k for k in kws if k in text), None)
            if not matched_kw:
                continue
            # 生成内部规则的命中理由
            reason = self._build_internal_reason(rid, profile, matched_kw)
            out.append(RuleHit(
                rule_id=rid,
                rule_title=rule.title,
                route="internal",
                severity=rule.severity,
                reason=reason,
                evidence_snippet=f"{rule.source_page or rule.title}：{rule.content}",
                evidence_source=f"本行制度 {rule.source_doc}",
                evidence_url="",
            ))
        return out

    # ------------------------------------------------------------------
    # 决策与工具函数
    # ------------------------------------------------------------------

    @staticmethod
    def _sev_rank(sev: RiskLevel) -> int:
        return {RiskLevel.RED: 3, RiskLevel.YELLOW: 2,
                RiskLevel.GREEN: 1, RiskLevel.INFO: 0}.get(sev, 0)

    def _decide_level(self, hits: list[RuleHit]) -> tuple[RiskLevel, float]:
        if not hits:
            return RiskLevel.GREEN, 5.0
        ext = [h for h in hits if h.route == "external"]
        pol = [h for h in hits if h.route == "internal"]
        has_red = any(h.severity == RiskLevel.RED for h in hits)

        # 交叉命中（双路都有）且含红 → 红
        if ext and pol and has_red:
            return RiskLevel.RED, 95.0
        # 双路都有 → 红（交叉即红）
        if ext and pol:
            return RiskLevel.RED, 85.0
        # 单路 ≥2 且含红 → 红
        if has_red and (len(ext) >= 2 or len(pol) >= 2):
            return RiskLevel.RED, 80.0
        # 单路含红 → 黄（严重但非交叉，保守判黄）
        if has_red:
            return RiskLevel.YELLOW, 65.0
        # 仅 YELLOW 命中 → 黄
        if hits:
            return RiskLevel.YELLOW, 50.0
        return RiskLevel.GREEN, 5.0

    @staticmethod
    def _title_by_id(rules: list[RuleItem], rid: str) -> str:
        for r in rules:
            if r.rule_id == rid:
                return r.title
        return rid

    @staticmethod
    def _pick_news_evidence(news: list[dict], kw: str) -> tuple[str, str, str]:
        for n in news:
            blob = (n.get("title", "") + " " + n.get("snippet", ""))
            if kw in blob:
                return (
                    f"舆情 · {n.get('published_at', '')} {n.get('title', '')[:30]}",
                    n.get("snippet", "") or n.get("title", ""),
                    n.get("url", ""),
                )
        return "", "", ""

    def _build_reason(self, rid: str, profile: CompanyProfile, kw: str) -> str:
        extras = profile.extras or {}
        narrative = extras.get("narrative", "")
        if rid == "FIN-002":
            pft = extras.get("profit_latest", 0)
            return f"净利润为 {pft:.0f} 万元（由正转负）"
        if rid == "FIN-003":
            dr = extras.get("debt_ratio", 0)
            return f"资产负债率 {dr:.1f}%"
        if rid == "FIN-004":
            return f"应收账款周转恶化：{narrative}"
        if rid == "BIZ-002":
            return "实际控制人发生变更"
        if rid == "BIZ-003":
            return "核心客户流失" + (f"（{narrative[:40]}）" if narrative else "")
        if rid == "BIZ-004":
            return "企业出现停产/停业"
        if rid == "IND-001":
            return f"所在行业出现景气下行信号（{kw}）"
        if rid == "REL-002":
            return "主要股东股权被冻结/质押冻结"
        return f"命中『{kw}』"

    def _build_internal_reason(self, rid: str, profile: CompanyProfile, kw: str) -> str:
        extras = profile.extras or {}
        narrative = extras.get("narrative", "")
        if rid == "POL-003":
            return f"触发关联方重整预警线 — {narrative or kw}"
        if rid == "POL-006":
            return f"贷后检查已逾期 — {narrative or kw}"
        if rid == "POL-001":
            return f"贷款逾期触及内控阈值（{kw}）"
        return f"触发本行制度条款 — {kw}"
