# -*- coding: utf-8 -*-
"""
Agent4 · 贷中风险预警 · v3.1 知识库驱动批量扫描

定位（不可跨界）：
  **客户行为变化**驱动（不是政策变化，那是 Agent5）。
  输入在贷客户池 + 预警规则库 + 内部管理制度 → 输出红/黄/绿分级客户榜单。
  不做单点手动查询（用户动作是被动收预警，不是主动输名字查）。

工具域（MCP 式拆分）：
  - 外部扫描域：裁判文书 / 工商变更 / 舆情监测
      入口：customer_scanner（外部路径）/ knowledge_base
  - 内部交易域：对照内部管理制度，扫流水异常 / 经营指标
      入口：alert_engine / trend_analyzer
  - 双路交叉域：外部 × 内部交叉命中 → 分级
      入口：cross_matcher
  - 规则解析域：管理制度文档 → 结构化规则
      入口：rule_extractor
  - 处置建议域：红灯客户配处置建议 + 台账导出
      入口：disposition / ledger_exporter

共享：
  与 Agent1 / Agent5 共享 SearchProvider + KnowledgeBase 接口（shared/kb_scan/ 底座）。
"""
