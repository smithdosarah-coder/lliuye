# -*- coding: utf-8 -*-
"""shared.source_health · 数据源健康检查.

per docs/working/allin-final-exec-2026-05-08.md §3.2 共性架构 #3.

抽象 6 agent 数据源 (Tavily / 企查查 / akshare / gov_cn / 央行 / 内部) 的健康检查公共 component:

  check(source_id) → HealthReport
    · 新鲜度 (last_call ts vs now)
    · SLA (p50 / p99 latency)
    · 认证 (api_key 在 / 过期)
    · 血缘 (上次调用次数 / 失败率)
    · 综合分 0-100

设计:
- 各 source 自己 register(source_id, tier, sla_p99_ms, auth_method, ...)
- 调用方在 invoke source 后调 record_call(source_id, latency_ms, success, error_code)
- check(source_id) 返实时报告 · 主 CLI 跑 health dashboard 用
- 跨 agent 共享 · 任一 agent record · 全 agent 看

下游 (Phase B 各 agent):
- channel: Tavily / akshare / 企查查 (已用 shared/sources)
- credit/report: gsxt / 内部 CRM / 征信
- alert: 司法 / 工商 / 监管
- compliance: 银保监 / 央行 / FLK
- riskctrl: 内部样本 (无外部源)

复用:
- shared.data_tiers.DataTier (1-4 分层)
- shared.sources.base.SourceTier (existing)
"""
from .health import (
    HealthReport,
    SourceHealth,
    SourceRegistration,
    default_health,
)

__all__ = [
    "HealthReport",
    "SourceHealth",
    "SourceRegistration",
    "default_health",
]
