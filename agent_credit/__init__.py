# -*- coding: utf-8 -*-
"""
Agent3 · 授信决策辅助 · v3.1 对公 / 普惠 / 对私三板块

定位（不可跨界）：
  Agent6 的下游决策引擎（非平级替代）。
  输入 Agent6 ReportJSON + 材料 → 输出四维评分 + 额度 / 期限建议 + 红线提示。
  面向审贷会主席 / 分管领导。不写报告（那是 Agent6）。

工具域（MCP 式拆分）：
  - 画像消费域：读取 Agent6 的 EnterpriseProfile，提取决策所需特征
      入口：feature_extractor
  - 评分计算域：对公 / 对私双模型可切换，输出四维分数
      入口：scoring_model_corporate / scoring_model_retail / rating_engine
  - 红线检查域：规则引擎 v2，确定性判定不让 LLM 现场算
      入口：rule_engine_v2 / risk_classifier / risk_appetite_config
  - 案例召回域：历史相似案例检索 + 同业对标
      入口：case_retriever
  - 决策编排域：组装输出 Dashboard，生成审贷建议文案
      入口：decision_engine / approval_engine / advisor_formatter

架构核心：
  DecisionEngine = FeatureExtractor + ScoringModel(对公/对私可切换) + RuleEngine + CaseRetriever + AdvisorFormatter
  不套 Agent1/4/5 的"知识库扫描范式"—— 这里是"一对多维深入"（对 1 做 N 维判断），不是"一对多筛选"。
"""
