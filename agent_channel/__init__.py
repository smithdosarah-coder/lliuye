# -*- coding: utf-8 -*-
"""
Agent1 · 全渠道获客 · v4.0 信号驱动搜索

定位（不可跨界）：
  look-alike 获客 + 产品推荐一体化。输入客户画像 / 知识库 → 输出候选企业清单 + 信号时间线 + 推荐产品 Top3。
  不做授信决策（那是 Agent3）。

工具域（MCP 式拆分）：
  - 信号搜索域：Tavily 5 路并行搜索（中标 / 专精特新 / 专利 / 扩产 / 获奖）
      入口：realtime_stream.run_channel_search_stream / lead_finder
  - 企业画像域：企查查二次查询补基础工商信息（法人 / 注册资本 / 成立年份）
      入口：profile_extractor
  - 匹配评分域：信号密度打分 + look-alike 相似度 + 匹配标签生成
      入口：scoring / channel_rules
  - 产品推荐域：规则匹配 + LLM 切入话术生成
      入口：product_recommender

架构硬约束：
  围绕"搜索"设计，抽 SearchProvider 接口，Mock/Web 可切换；下游统一消费 CompanyProfile 结构。
"""
