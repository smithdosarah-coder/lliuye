# -*- coding: utf-8 -*-
"""
Agent6 · 报告生成 · API wrapper 层（unreleased · API wrapper over v16 pipeline）

主管线在项目根的 v16_pipeline.py + v16_generator.py + v16_classifier.py 等 10 个
v16_*.py 模块。本包是其 FastAPI 化外壳,通过 api.py 暴露 SSE 端点供前端消费。

定位（不可跨界）：
  文书自动化。输入企业材料 + 模板 → 输出 ReportJSON + Word（面向审批委员会）。
  不出决策意见（那是 Agent3 的事，Agent3 消费本 Agent 的 ReportJSON）。

工具域（MCP 式拆分）：
  - 材料解析域：xlsx / docx / pdf 多源材料读取 + 归一化
      入口：material_kb / material_index / material_anchor / period_matcher
  - 字段抽取域：结构化字段预填（标签字段 + 复选框）+ 确定性财务指标计算
      入口：truth_fill / financial_analyzer / industry_benchmark
  - 段落生成域：Evidence-First 三阶段协议（证据汇集 → Grounded 生成 → 自审）
      入口：section_generator / template_decomposer / form_filler
  - QC 终审域：企业名 / 数字占位符残留检查 + 幻觉检测 + 质量打分
      入口：quality_check / quality_scorer / output_validator / numeric_validator
  - 文档导出域：填充 Word 模板 + 标注「未能自动填写」字段
      入口：word_export / form_filler

对外接口：
  api.py 暴露 /api/report/fill 与 /api/report/refine SSE 端点，5 段阶段（ingest/extract/infer/write/audit）。
  产出 EnterpriseProfile JSON 作为跨 Agent（主要被 Agent3 消费）的数据载体。

硬约束：
  - 财务比率 / 同比 / 周转天数等可确定性计算的，禁止让 LLM 现场算 —— 走 financial_analyzer
  - 填不了的字段必须标「未能自动填写」，绝不编
"""

__version__ = "0.0.0-unreleased+v16-wrapper"  # 真实版本见根 v16_pipeline.py 主管线
