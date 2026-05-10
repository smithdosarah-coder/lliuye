# -*- coding: utf-8 -*-
"""LiveShell · 6 agent 统一 "启动→流式→操作" 框架.

设计:
- run_id = uuid · 主 CLI 单进程内 unique (TTL 30 min)
- run state = in-memory dict (Cowork agent · 不持久化 · 进程重启即丢)
- stream queue = asyncio.Queue (per run_id · 多消费者支持)
- action = sync method · 修改 run state · 不直接产 event (event 由 producer side 写)

Boundary:
- 本模块**不做** business logic (intent 解析 / 候选生成 等) · 仅 shell
- 各 agent 自己写 producer (调 shell.emit_stage / shell.emit_done / shell.emit_error)
- 失败隔离: stream/action/status 任一 raise 都不破 run state · caller 自己捕获

线程安全: asyncio · 单线程 event loop 内安全 · 跨进程不安全
"""
from __future__ import annotations

import asyncio
import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


class RunStatus(str, enum.Enum):
    """Run 生命周期状态."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunNotFoundError(KeyError):
    """run_id 不存在 · 通常是 TTL 过期或 typo."""


@dataclass
class _RunState:
    run_id: str
    flow: str  # e.g. "channel.lookalike", "report.generate", "credit.score"
    user: str
    ctx: dict[str, Any]
    status: RunStatus
    created_at: float
    updated_at: float
    queue: asyncio.Queue  # event queue · producer push · stream consume
    history: list[dict[str, Any]] = field(default_factory=list)  # 已 emit 的 event 副本 (replay 用)
    actions: list[dict[str, Any]] = field(default_factory=list)  # action 历史
    error: Optional[str] = None


class LiveShell:
    """6 agent Cowork 任务公共 shell.

    Usage (各 agent producer 侧):

        from shared.live_shell import default_shell, RunStatus
        from shared.sse_envelope import make_stage, make_done, encode_event

        shell = default_shell()

        # 1. 启动 run
        run_id = shell.start(
            flow="channel.lookalike",
            user="rm_wangzhe",
            ctx={"description": "对公科技小微企业", "industry": "AI"},
        )

        # 2. agent 内部 producer (e.g. realtime_stream) 调:
        await shell.emit(run_id, make_stage("intent", "running", "解析中..."))
        await shell.emit(run_id, make_done(panels={...}))
        shell.mark(run_id, RunStatus.DONE)

        # 3. FastAPI route 内消费:
        async def stream_route(run_id):
            async for evt in shell.stream(run_id):
                yield encode_event(evt)

        # 4. 用户 action (e.g. 选某 candidate)
        shell.action(run_id, cmd="select_candidate", payload={"candidate_id": "uscc_X"})
    """

    DEFAULT_TTL_SECONDS = 30 * 60  # 30 min · per CLAUDE.md §3.1.1 Cowork

    def __init__(self, *, ttl_seconds: int | None = None) -> None:
        self._runs: dict[str, _RunState] = {}
        self._ttl = ttl_seconds if ttl_seconds is not None else self.DEFAULT_TTL_SECONDS

    # -- lifecycle --

    def start(self, *, flow: str, user: str, ctx: dict[str, Any] | None = None) -> str:
        """启动 run · 返 idempotent run_id (uuid4)."""
        if not flow or not user:
            raise ValueError("flow and user required")
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        now = time.time()
        self._runs[run_id] = _RunState(
            run_id=run_id,
            flow=flow,
            user=user,
            ctx=dict(ctx or {}),
            status=RunStatus.PENDING,
            created_at=now,
            updated_at=now,
            queue=asyncio.Queue(),
        )
        return run_id

    def mark(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """更新 run 状态 · 终态 (DONE/FAILED/CANCELLED) 时关 queue (推 sentinel)."""
        run = self._get(run_id)
        run.status = status
        run.updated_at = time.time()
        if error:
            run.error = error
        if status in {RunStatus.DONE, RunStatus.FAILED, RunStatus.CANCELLED}:
            # 推 None sentinel 关 stream
            try:
                run.queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

    def get_status(self, run_id: str) -> RunStatus:
        return self._get(run_id).status

    # -- producer (agent 内部 emit event) --

    async def emit(self, run_id: str, event: dict[str, Any]) -> None:
        """producer 推 event 到 queue (调用方需 await)."""
        run = self._get(run_id)
        run.history.append(event)
        run.updated_at = time.time()
        if run.status == RunStatus.PENDING:
            run.status = RunStatus.RUNNING
        await run.queue.put(event)

    def emit_nowait(self, run_id: str, event: dict[str, Any]) -> None:
        """同步 emit (不 await · queue 满会 raise QueueFull)."""
        run = self._get(run_id)
        run.history.append(event)
        run.updated_at = time.time()
        if run.status == RunStatus.PENDING:
            run.status = RunStatus.RUNNING
        run.queue.put_nowait(event)

    # -- consumer (FastAPI route side) --

    async def stream(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        """流式拉 event · 终态后 close stream.

        语义: 每个 stream() 调用都从当前 queue 拉新 event · 不 replay history.
        Reconnect 场景: caller 自己调 get_history() 拼前面 + stream() 拼后续.
        理由: queue 单消费者 · stream 内 replay 会和后续 queue 拉的 event 重复.
        """
        run = self._get(run_id)
        # 终态已 mark · queue 已 sentinel · 直接 drain queue 后退
        while True:
            evt = await run.queue.get()
            if evt is None:
                break
            yield evt

    # -- user action --

    def action(
        self,
        run_id: str,
        *,
        cmd: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """用户 action (e.g. select_candidate / confirm / cancel) · 修改 run state.

        各 agent 自定 cmd 集 · LiveShell 不解析业务语义 · 仅落 actions 历史 +
        cancel 时改 status 到 CANCELLED.

        Returns: {ok: bool, action_id: str, ...}
        """
        run = self._get(run_id)
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        record = {
            "action_id": action_id,
            "cmd": cmd,
            "payload": dict(payload or {}),
            "ts": time.time(),
        }
        run.actions.append(record)
        run.updated_at = time.time()

        # built-in cancel cmd
        if cmd == "cancel":
            self.mark(run_id, RunStatus.CANCELLED)

        return {"ok": True, "action_id": action_id, "run_status": run.status.value}

    # -- introspection / housekeeping --

    def get_history(self, run_id: str) -> list[dict[str, Any]]:
        return list(self._get(run_id).history)

    def get_actions(self, run_id: str) -> list[dict[str, Any]]:
        return list(self._get(run_id).actions)

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self._get(run_id)
        return {
            "run_id": run.run_id,
            "flow": run.flow,
            "user": run.user,
            "ctx": run.ctx,
            "status": run.status.value,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "error": run.error,
            "event_count": len(run.history),
            "action_count": len(run.actions),
        }

    def gc(self) -> int:
        """清 TTL 过期的 run · 返清的 run 数. 主 CLI 周期调."""
        now = time.time()
        expired = [
            rid for rid, run in self._runs.items()
            if now - run.updated_at > self._ttl
        ]
        for rid in expired:
            del self._runs[rid]
        return len(expired)

    # -- internal --

    def _get(self, run_id: str) -> _RunState:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return run


_DEFAULT: LiveShell | None = None


def default_shell() -> LiveShell:
    """主进程 singleton · 6 agent 共享."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = LiveShell()
    return _DEFAULT
