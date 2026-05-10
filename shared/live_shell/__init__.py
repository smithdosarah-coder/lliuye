# -*- coding: utf-8 -*-
"""shared.live_shell · 6 agent 统一 "启动→流式→操作" 框架.

per docs/working/allin-final-exec-2026-05-08.md §3.2 共性架构 #1.

抽象 6 agent 实时 (Cowork) 类任务的公共 shell:
  - start(flow, user, ctx) → run_id          · 启动 run · 返 idempotent run_id
  - stream(run_id) → AsyncIterator[bytes]    · 流式拉 SSE event (复用 shared/sse_envelope)
  - action(run_id, cmd, payload) → result    · run-time 操作 (e.g. 选候选 / 确认 / 取消)
  - status(run_id) → RunStatus               · 同步查 run 状态

设计 (per CLAUDE.md §3.1.1 Cowork vs Managed):
- Cowork agent (channel/credit/report) 用 LiveShell · run TTL 短 (内存 + 30min)
- Managed agent (alert/compliance/riskctrl) 不用 LiveShell · 走 job_runtime (Phase D)
- 失败隔离: 任何 stream 失败 silent · 不破上游业务 flow

依赖:
- shared.sse_envelope (event 共形)
- shared.entity_resolver (candidate id 派生 · 在 action 入口校验 id 合规)

下游 (Phase B 各 agent 接入):
- channel: 已有 realtime_stream · Phase B refactor 入 LiveShell (可选 · 不破现状)
- credit/report: Phase B 直接基于 LiveShell 写
- alert/compliance/riskctrl: 不用 LiveShell · 走 job_runtime
"""
from .shell import (
    LiveShell,
    RunNotFoundError,
    RunStatus,
    default_shell,
)

__all__ = [
    "LiveShell",
    "RunNotFoundError",
    "RunStatus",
    "default_shell",
]
