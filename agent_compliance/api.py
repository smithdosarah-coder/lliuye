# -*- coding: utf-8 -*-
"""agent_compliance.api — Agent5 合规雷达 FastAPI 路由模块。

端点：
  GET /api/compliance/policy_scan  — 主动从 gov.cn / pbc / flk_npc 拉最新政策候选

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- 与 ComplianceRadarAgent.process_message（"上传文件触发"）并行
- 本端点是事件驱动入口，前端可定期轮询新政策、按需触发巡检
- 所有候选自带 source_url + fetched_at（Evidence-First）
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(title="Agent5 Compliance Radar API", version="3.1")


@app.get("/api/compliance/policy_scan")
async def compliance_policy_scan(query: str = "", limit: int = 10):
    """主动从政策源拉最新候选清单。失败优雅降级返回空 list + error，前端不崩。"""
    try:
        from agent_compliance.agent import ComplianceRadarAgent
        agent = ComplianceRadarAgent()
        return {"policies": agent.scan_external_policies(query, limit)}
    except Exception as e:
        return {"policies": [], "error": f"{type(e).__name__}: {e}"}
