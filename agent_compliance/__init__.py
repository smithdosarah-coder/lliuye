# -*- coding: utf-8 -*-
"""
Agent5 · 合规巡检 · v3.1 政策事件驱动

定位（不可跨界）：
  **政策变更事件**驱动（不是定期巡检，不是客户行为变化 — 那是 Agent4）。
  输入新监管办法 + 存量业务制度库 → 输出违规冲突点明细清单。
  不做财务审计 / 客户级预警。

工具域（MCP 式拆分）：
  - 政策解析域：新政策文件关键条款抽取
      入口：policy_parser / event_extractor
  - 业务矩阵域：存量业务制度 / 产品文档的结构化索引
      入口：knowledge_base / rule_set_builder
  - 矩阵匹配域：政策条款 × 业务制度交叉矩阵扫描
      入口：matrix_matcher
  - 违规判定域：命中项走合规判定逻辑，分级（严重 / 重要 / 一般）
      入口：compliance_checker / defect_classifier
  - 台账导出域：违规清单导出 + 整改跟进
      入口：ledger_exporter

共享：
  与 Agent1 / Agent4 共享 shared/kb_scan/ 底座，但触发源 / 输入 / 输出差异清晰，不合并。
"""
