# -*- coding: utf-8 -*-
"""agent_report — FastAPI/SSE wrapper around the V13 form-fill pipeline.

职责:
  - 暴露 /api/report/fill 与 /api/report/refine 两个 SSE 端点供 Next.js 前端使用
  - 以 5 段阶段(ingest/extract/infer/write/audit)抽象封装内部多阶段进度回调
  - 产出跨 Agent 可消费的 EnterpriseProfile JSON
  - 支持 mock 模式(预置 fixture,跳过真 pipeline)
"""

__version__ = "0.1.0"
