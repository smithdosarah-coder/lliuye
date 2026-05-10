# -*- coding: utf-8 -*-
"""shared.live_shell 单测 · per Phase A common worker 共性架构 #1."""
from __future__ import annotations

import asyncio

import pytest

from shared.live_shell import (
    LiveShell,
    RunNotFoundError,
    RunStatus,
    default_shell,
)


@pytest.fixture
def shell():
    return LiveShell(ttl_seconds=600)


class TestStartRun:
    def test_start_returns_run_id(self, shell):
        run_id = shell.start(flow="channel.lookalike", user="rm")
        assert run_id.startswith("run_")
        assert len(run_id) > 4

    def test_start_records_metadata(self, shell):
        run_id = shell.start(flow="report.generate", user="rm_w", ctx={"x": 1})
        run = shell.get_run(run_id)
        assert run["flow"] == "report.generate"
        assert run["user"] == "rm_w"
        assert run["ctx"] == {"x": 1}
        assert run["status"] == RunStatus.PENDING.value

    def test_start_unique_run_ids(self, shell):
        ids = {shell.start(flow="x", user="u") for _ in range(20)}
        assert len(ids) == 20

    def test_start_requires_flow_user(self, shell):
        with pytest.raises(ValueError):
            shell.start(flow="", user="u")
        with pytest.raises(ValueError):
            shell.start(flow="x", user="")


class TestEmitAndStream:
    @pytest.mark.asyncio
    async def test_emit_then_stream_sees_event(self, shell):
        run_id = shell.start(flow="x", user="u")
        await shell.emit(run_id, {"event": "stage", "stage": "intent"})
        shell.mark(run_id, RunStatus.DONE)

        events = []
        async for evt in shell.stream(run_id):
            events.append(evt)
        assert events == [{"event": "stage", "stage": "intent"}]

    @pytest.mark.asyncio
    async def test_status_transitions_to_running_on_emit(self, shell):
        run_id = shell.start(flow="x", user="u")
        assert shell.get_status(run_id) == RunStatus.PENDING
        await shell.emit(run_id, {"event": "stage"})
        assert shell.get_status(run_id) == RunStatus.RUNNING

    @pytest.mark.asyncio
    async def test_stream_replays_history(self, shell):
        run_id = shell.start(flow="x", user="u")
        await shell.emit(run_id, {"event": "stage", "n": 1})
        await shell.emit(run_id, {"event": "stage", "n": 2})
        shell.mark(run_id, RunStatus.DONE)

        events = []
        async for evt in shell.stream(run_id):
            events.append(evt)
        assert [e["n"] for e in events] == [1, 2]

    @pytest.mark.asyncio
    async def test_emit_nowait(self, shell):
        run_id = shell.start(flow="x", user="u")
        shell.emit_nowait(run_id, {"event": "stage"})
        shell.mark(run_id, RunStatus.DONE)
        events = [e async for e in shell.stream(run_id)]
        assert len(events) == 1


class TestMarkLifecycle:
    @pytest.mark.asyncio
    async def test_mark_done_closes_stream(self, shell):
        run_id = shell.start(flow="x", user="u")
        shell.mark(run_id, RunStatus.DONE)
        events = [e async for e in shell.stream(run_id)]
        assert events == []  # 终态 · 无 event

    def test_mark_failed_with_error(self, shell):
        run_id = shell.start(flow="x", user="u")
        shell.mark(run_id, RunStatus.FAILED, error="LLM timeout")
        run = shell.get_run(run_id)
        assert run["status"] == RunStatus.FAILED.value
        assert run["error"] == "LLM timeout"


class TestAction:
    def test_action_records_history(self, shell):
        run_id = shell.start(flow="x", user="u")
        result = shell.action(run_id, cmd="select_candidate", payload={"id": "uscc_X"})
        assert result["ok"]
        assert result["action_id"].startswith("act_")
        actions = shell.get_actions(run_id)
        assert len(actions) == 1
        assert actions[0]["cmd"] == "select_candidate"

    def test_cancel_action_marks_cancelled(self, shell):
        run_id = shell.start(flow="x", user="u")
        shell.action(run_id, cmd="cancel")
        assert shell.get_status(run_id) == RunStatus.CANCELLED

    def test_unknown_cmd_does_not_change_status(self, shell):
        run_id = shell.start(flow="x", user="u")
        shell.action(run_id, cmd="custom_thing")
        # 用户自定 cmd · LiveShell 不解析 · status 不变
        assert shell.get_status(run_id) == RunStatus.PENDING


class TestRunNotFound:
    def test_unknown_run_id_raises(self, shell):
        with pytest.raises(RunNotFoundError):
            shell.get_run("run_nonexistent")
        with pytest.raises(RunNotFoundError):
            shell.get_status("run_nonexistent")
        with pytest.raises(RunNotFoundError):
            shell.action("run_nonexistent", cmd="cancel")


class TestGarbageCollect:
    def test_gc_removes_expired(self, shell):
        # 模拟过期: 改 ttl 为极小
        shell._ttl = 0
        run_id = shell.start(flow="x", user="u")
        # 让 updated_at 落在 TTL 之外
        shell._runs[run_id].updated_at = 0
        cleaned = shell.gc()
        assert cleaned == 1
        with pytest.raises(RunNotFoundError):
            shell.get_status(run_id)


class TestDefaultShell:
    def test_default_shell_singleton(self):
        s1 = default_shell()
        s2 = default_shell()
        assert s1 is s2


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_flow(self, shell):
        # 1. start
        run_id = shell.start(flow="channel.lookalike", user="rm", ctx={"desc": "AI"})

        # 2. producer 串 5 个 stage event + 1 done
        for i, name in enumerate(["intent", "search", "match", "score", "rank"]):
            await shell.emit(run_id, {"event": "stage", "stage": name, "n": i})
        await shell.emit(run_id, {"event": "done", "candidates": []})
        shell.mark(run_id, RunStatus.DONE)

        # 3. consumer 拉全
        events = [e async for e in shell.stream(run_id)]
        assert len(events) == 6
        assert events[-1]["event"] == "done"

        # 4. introspect
        run = shell.get_run(run_id)
        assert run["status"] == RunStatus.DONE.value
        assert run["event_count"] == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
