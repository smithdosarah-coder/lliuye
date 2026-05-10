# -*- coding: utf-8 -*-
"""DecisionEngine — Agent3 v2.0 决策流水线总调度

流水线（对应 PRD 第 6.3 节）：
  1. FeatureExtractor : profile → 特征（~60 项对公 / ~22 项对私）
  2. ScoringModel(按板块分派) : 特征 → 评分
  3. RuleEngine : 特征 → 红线命中列表
  4. CaseRetriever : 特征 → Top-K 相似案例
  5. AdvisorFormatter : 汇总 → DecisionAdvice（含 LLM 自然语言包装）

前 4 步无 LLM 调用（确定性计算）；第 5 步调 LLM 1-2 次。
run_stream() 以 generator 形式实时吐出中间结果，供 UI 更新状态灯。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Generator, Any

from .feature_extractor import FeatureExtractor
from .rule_engine_v2 import RuleEngineV2, RedLineHit
from .case_retriever import CaseRetriever, CaseMatch
from .advisor_formatter import AdvisorFormatter, DecisionAdvice
from .decision_graph import build_decision_graph, load_industry_baselines
from .risk_appetite_config import RiskAppetiteConfig

Segment = Literal["corporate", "retail"]


@dataclass
class DecisionPipelineResult:
    features: dict = field(default_factory=dict)
    scoring_result: Any = None
    rule_hits: list = field(default_factory=list)
    case_matches: list = field(default_factory=list)
    advice: DecisionAdvice | None = None


class DecisionEngine:
    """对公/对私共用的流水线调度器"""

    def __init__(self, llm_chat_func=None, llm_json_func=None,
                 appetite_corp: RiskAppetiteConfig | None = None,
                 appetite_retail: RiskAppetiteConfig | None = None):
        self.llm_chat = llm_chat_func
        self.llm_json = llm_json_func
        self.appetite_corp = appetite_corp or RiskAppetiteConfig.default("corporate")
        self.appetite_retail = appetite_retail or RiskAppetiteConfig.default("retail")

        self.feature_extractor = FeatureExtractor()
        # Rule engine 每个板块各持有一份（appetite 可能不同）
        self.rule_engine_corp = RuleEngineV2(self.appetite_corp)
        self.rule_engine_retail = RuleEngineV2(self.appetite_retail)
        self.case_retriever = CaseRetriever()
        self._scoring_models: dict[str, Any] = {}

    # ------------------------------------------------------------------
    def _get_appetite(self, segment: Segment) -> RiskAppetiteConfig:
        return self.appetite_corp if segment == "corporate" else self.appetite_retail

    def _get_rule_engine(self, segment: Segment) -> RuleEngineV2:
        return self.rule_engine_corp if segment == "corporate" else self.rule_engine_retail

    def _get_scoring_model(self, segment: Segment):
        if segment in self._scoring_models:
            return self._scoring_models[segment]
        if segment == "corporate":
            from .scoring_model_corporate import CorporateScoringModel
            model = CorporateScoringModel(self.appetite_corp)
        else:
            from .scoring_model_retail import RetailScoringModel
            model = RetailScoringModel(self.appetite_retail)
        self._scoring_models[segment] = model
        return model

    # ------------------------------------------------------------------
    def reload_rules(self, segment: Segment | None = None):
        if segment is None or segment == "corporate":
            self.rule_engine_corp.reload("corporate")
        if segment is None or segment == "retail":
            self.rule_engine_retail.reload("retail")

    def refresh_appetite(self, segment: Segment, appetite: RiskAppetiteConfig):
        if segment == "corporate":
            self.appetite_corp = appetite
            self.rule_engine_corp = RuleEngineV2(appetite)
            from .scoring_model_corporate import CorporateScoringModel
            self._scoring_models["corporate"] = CorporateScoringModel(appetite)
        else:
            self.appetite_retail = appetite
            self.rule_engine_retail = RuleEngineV2(appetite)
            from .scoring_model_retail import RetailScoringModel
            self._scoring_models["retail"] = RetailScoringModel(appetite)

    # ------------------------------------------------------------------
    def run_stream(self, profile: dict, segment: Segment
                   ) -> Generator[tuple[str, Any], None, None]:
        """流式执行。每步 yield (stage, payload)。最后 yield ("all_done", result)"""
        yield "feature_extracting", None
        features = self.feature_extractor.extract(profile, segment)
        yield "feature_done", features

        yield "scoring", None
        scoring_model = self._get_scoring_model(segment)
        scoring_result = scoring_model.score(features)
        yield "scoring_done", scoring_result

        yield "rule_checking", None
        rule_engine = self._get_rule_engine(segment)
        rule_hits = rule_engine.check(features, segment)
        yield "rule_done", rule_hits

        yield "case_retrieving", None
        case_matches = self.case_retriever.retrieve(
            features, segment, top_k=5, scoring_result=scoring_result)
        yield "case_done", case_matches

        yield "advising", None
        advisor = AdvisorFormatter(
            llm_chat_func=self.llm_chat,
            llm_json_func=self.llm_json,
            appetite=self._get_appetite(segment),
        )
        advice = advisor.format(
            segment=segment, profile=profile, features=features,
            scoring=scoring_result, rule_hits=rule_hits, cases=case_matches,
        )
        yield "advising_done", advice

        # BE2 (Phase B-3 · 2026-05-01) — wrapper above the 4 deterministic
        # steps. Builds an audit-grade evidence graph; the existing pipeline
        # is untouched. Failure here MUST NOT break the decision flow.
        yield "graph_building", None
        try:
            features_snapshot = {
                k: v for k, v in features.items()
                if not k.startswith("chapters") and not k.startswith("_")
            }
            graph = build_decision_graph(
                features=features_snapshot,
                scoring=scoring_result,
                rule_hits=rule_hits,
                advice=advice,
                segment=segment,
                appetite=self._get_appetite(segment),
                baselines=load_industry_baselines(),
            )
            advice.decision_graph = graph.to_dict()
            yield "graph_done", advice.decision_graph
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as exc:
            advice.decision_graph = {
                "schema_version": "1.0.0",
                "error": f"{type(exc).__name__}: {exc}",
                "nodes": [],
                "edges": [],
            }
            yield "graph_done", advice.decision_graph

        # BE7 (Phase B-3 · 2026-05-01) — cross-agent decision ledger.
        # Persists the decision + evidence chain (BE2 graph) to the
        # jurisdiction-scoped audit log. Same try/except discipline as
        # BE2: ledger 是观察层不是阻塞层 · 写入失败不破 decision flow.
        # Uses the lower-level `default_ledger().record(...)` so we can
        # surface the real `persisted` flag — the public `record_decision`
        # façade silently swallows failure and only returns the id.
        yield "ledger_persisting", None
        try:
            from shared.decision_ledger import default_ledger
            # ALL IN Phase B step 5 (2026-05-09) · subject_id thread-through
            # per CLAUDE.md §3.7.5 + AGENT_IDENTITY-credit 红线 #4 (subject_id 必 hash · plain PII 禁入 ledger)
            # 从 Agent6 handoff ReportJSON 提取 USCC · fallback 路径多源 (production · 多种命名都覆盖)
            # ledger.record() 内部 hash_subject_id 自动 hash · 此处传 plain USCC 即可 (双 hash 会冲突)
            uscc = (
                profile.get("unified_social_credit_code")
                or profile.get("usuc")
                or profile.get("uscc")
                or profile.get("business_license_no")
                or (profile.get("legal_info") or {}).get("unified_social_credit_code")
                or (profile.get("financial_anchors") or {}).get("unified_social_credit_code")
            )
            ledger_result = default_ledger().record(
                agent_id="credit",
                endpoint="/api/credit/decision",
                input_payload=profile,
                output_payload=advice.to_dict(),
                evidence_chain=advice.decision_graph,
                subject_name=getattr(advice, "subject_name", None) or profile.get("company_name") or None,
                subject_id=uscc,  # plain USCC · ledger.record() 内部 hash_subject_id 自动 hash 16-hex
            )
            # Reuse advice_id slot · 1:1 mapping with ledger decision_id.
            advice.advice_id = ledger_result.decision_id
            event_payload: dict = {
                "decision_id": ledger_result.decision_id,
                "persisted": ledger_result.persisted,
            }
            if ledger_result.error:
                event_payload["error"] = ledger_result.error
            yield "ledger_done", event_payload
        except (RuntimeError, ValueError, TypeError, OSError,
                AttributeError, KeyError, ImportError) as exc:
            yield "ledger_done", {
                "decision_id": getattr(advice, "advice_id", "") or "",
                "persisted": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

        yield "all_done", DecisionPipelineResult(
            features=features,
            scoring_result=scoring_result,
            rule_hits=rule_hits,
            case_matches=case_matches,
            advice=advice,
        )

    def run(self, profile: dict, segment: Segment) -> DecisionPipelineResult:
        result: DecisionPipelineResult | None = None
        for stage, data in self.run_stream(profile, segment):
            if stage == "all_done":
                result = data
        return result or DecisionPipelineResult()
