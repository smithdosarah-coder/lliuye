# -*- coding: utf-8 -*-
"""liuye_service.tests.test_integration_live — end-to-end SSE integration.

Per W2-backend brief §3 file 5 (第 4 棒 e2e integration · 最大一棒) +
``liuye_service/CLAUDE.md`` §3 + v3 §2.1.

**整条链路 e2e**: FastAPI app + register_liuye_routes(app) + mock adapter
注入到 orchestrator → POST /api/liuye/sessions → drive ``_stream_skeleton``
direct → 收 11-event SSE wire → 验 (seq monotonic + heartbeat 15s +
Last-Event-ID 重连 + LB retry dedup).

**为什么不起真 subprocess uvicorn / 不用 httpx ASGI transport for SSE**:
- ``httpx.ASGITransport.handle_async_request`` 等 ``response_complete.set()``
  才返 · 对 infinite SSE generator (heartbeat 永不停) 永远不退 (验证: httpx
  0.28.1 + Python 3.14 在 ``client.stream("GET", ...).__aenter__()`` 永挂)
- subprocess.Popen uvicorn 跨 Windows/Linux 不稳 · 端口冲突 unpredictable ·
  Iocp event loop 兼容差
- 解法: 直接驱 ``_stream_skeleton(orch, turn_id)`` async generator + ``_dispatch_via_adapter``
  在同 loop 跑 · 抓 generator yield 的 wire 字符串 verify · 这是 SSE wire
  format 真正的 SSOT (FastAPI/Starlette 只是把 generator output bytes 写 socket)
- 非 SSE endpoint (POST /sessions / POST /messages / GET /health) 走 httpx
  ASGITransport · 正常 work (response_complete 会真 set)

**mock 6 agent backend 内嵌 SSE producer**:
- 不依赖真 agent_*/api.py (D6-D7 接通才有 · 第 4 棒不依赖)
- 通过 ``MockProducerAdapter`` 实现 AgentAdapter Protocol · 注入 orchestrator
- producer 直接 yield liuye-shaped event dict (跳过 sse_v1_to_liuye 翻译 ·
  因为 W1 + W2 第 3 棒已 156 test cover 翻译 · 这里测 wire 整体)
- Edge case: LB retry 同 v1 event 推 2 次 · 验 ``sse_v1_to_liuye`` dedup gate

**验收点 (per W2 brief §3 file 5)**:
1. 11 event 序列出现 (turn.started → tool.started → tool.progress → tool.completed → turn.completed)
2. seq 单调递增 (1, 2, 3, ...)
3. Last-Event-ID 格式 ``<turn_id>:<seq>`` (id 行格式 verify)
4. heartbeat 15s 触发 (本测试缩短到 0.2s · 验启用)
5. LB retry 同 event 重发 → dedup gate 不二次 emit (sse_v1_to_liuye unit)

**SSOT 引用**:
- ``liuye_service/api.py:register_liuye_routes`` (FastAPI mount · POST 端点)
- ``liuye_service/api.py:_stream_skeleton`` (SSE writer · id + event + data · 直接驱)
- ``liuye_service/api.py:_dispatch_via_adapter`` (adapter → queue 桥 · 直接 await)
- ``liuye_service/orchestrator.py:CoworkOrchestrator`` (per-turn queue + seq)
- ``liuye_service/adapters/sse_v1_to_liuye.py:SseV1ToLiuyeAdapter.translate`` (dedup gate)
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncIterator, Mapping

import httpx
import pytest
from fastapi import FastAPI

from liuye_service.adapters.base import reset_seq
from liuye_service.adapters.sse_v1_to_liuye import SseV1ToLiuyeAdapter
from liuye_service.api import (
    _dispatch_via_adapter,
    _stream_skeleton,
    register_liuye_routes,
)
from liuye_service.config import Settings, set_default_settings
from liuye_service.orchestrator import (
    CoworkOrchestrator,
    set_default_orchestrator,
)


# ---------------------------------------------------------------------------
# Mock backend SSE producer · 内嵌 fixture · 不 import production agent_*
# ---------------------------------------------------------------------------


class MockProducerAdapter:
    """Inline mock backend Cowork adapter · 直接 yield liuye 11-event 序列.

    实现 AgentAdapter Protocol (agent_id / boundary / dispatch_message).
    给 orchestrator.dispatch_message 驱动 · emit 走 _emit closure 进 per-turn
    SSE queue.

    用法: 注入到 orchestrator.register_adapter() · 不动 production 6 agent
    adapter (channel/credit/report).
    """

    def __init__(
        self,
        *,
        agent_id: str = "credit",
        events_sequence: list[dict[str, Any]] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.boundary = "cowork"
        self.events_sequence = events_sequence or _DEFAULT_11_EVENT_SEQUENCE
        # LB retry simulation · 调 dispatch_message 时把同 event 推 N 次 (默认 1)
        self.duplicate_count: int = 1
        self.dispatched_count: int = 0

    async def dispatch_message(
        self,
        turn_id: str,
        message: Mapping[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Emit the canonical 11-event sequence · AsyncIterator surface.

        Per orchestrator.dispatch_message · ``hasattr adapter, 'dispatch_message'``
        + ``not hasattr 'dispatch'`` 走 AsyncIterator 路径 (新式). 每个 yield
        进 orchestrator emit() → per-turn asyncio.Queue → SSE stream.
        """
        for evt in self.events_sequence:
            # LB retry 模拟 · duplicate_count 控制同 event 推几次 (orchestrator
            # 端没 dedup · 由 sse_v1_to_liuye translator 在翻译时 dedup ·
            # 我们这里跳过翻译 · 模拟未 dedup 时的 wire 表现)
            for _ in range(self.duplicate_count):
                self.dispatched_count += 1
                yield evt
                await asyncio.sleep(0)  # 让出 loop · 防 burst 把 queue 充满


_DEFAULT_11_EVENT_SEQUENCE: list[dict[str, Any]] = [
    # turn.started 由 _stream_skeleton 在 SSE 开口处自己 emit · 这里跳过
    {
        "event": "message.created",
        "payload": {"content": "正在分析授信申请...", "role": "assistant"},
    },
    {
        "event": "tool.started",
        "payload": {
            "agent": "credit",
            "tool_id": "scoring_model_corporate",
            "input": {"applied_product": "CORP_CREDIT"},
            "boundary": "cowork",
        },
    },
    {
        "event": "tool.progress",
        "payload": {
            "stage_key": "load_profile",
            "stage_label": "加载企业画像",
            "status": "running",
            "percent": 25,
        },
    },
    {
        "event": "tool.progress",
        "payload": {
            "stage_key": "evidence_check",
            "stage_label": "Evidence 三角校验",
            "status": "running",
            "percent": 60,
        },
    },
    {
        "event": "tool.progress",
        "payload": {
            "stage_key": "redline_check",
            "stage_label": "红线规则核查",
            "status": "done",
            "percent": 90,
        },
    },
    {
        "event": "tool.completed",
        "payload": {
            "result": {
                "verdict": "PASS",
                "score": 78,
                "amount_suggested": 5_000_000,
            },
        },
    },
    {
        "event": "evidence.attached",
        "payload": {
            "evidence_id": "evi_credit_001",
            "source_tier": 2,
            "claim_type": "financial",
        },
    },
    {
        "event": "artifact.patch",
        "payload": {
            "artifact_id": "art_decision_001",
            "patch_ops": [
                {"op": "replace", "path": "/verdict", "value": "PASS"},
            ],
        },
    },
    {
        "event": "turn.completed",
        "payload": {
            "final_snapshot": {
                "verdict": "PASS",
                "ok": True,
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Fixtures · isolated FastAPI app + orchestrator + auth bypass
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    """Reset all module-level singletons between tests."""
    reset_seq()
    set_default_settings(None)
    set_default_orchestrator(None)
    yield
    reset_seq()
    set_default_settings(None)
    set_default_orchestrator(None)


@pytest.fixture
def app_with_mock_adapter(monkeypatch: pytest.MonkeyPatch) -> tuple[FastAPI, MockProducerAdapter, CoworkOrchestrator]:
    """Build a FastAPI app · register liuye routes · inject mock adapter."""
    monkeypatch.setenv("LIUYE_ENABLED", "1")
    set_default_settings(Settings(enabled=True, demo_mode=False))

    # 缩 heartbeat 到 0.2s 给 test 在 5s 内看到 · 不动 production 默认 15s.
    # api.py imports HEARTBEAT_INTERVAL_SECONDS at module load · patch both.
    import liuye_service.orchestrator as orch_mod
    import liuye_service.api as api_mod
    monkeypatch.setattr(orch_mod, "HEARTBEAT_INTERVAL_SECONDS", 0.2)
    monkeypatch.setattr(api_mod, "HEARTBEAT_INTERVAL_SECONDS", 0.2)

    # orchestrator 注册 mock adapter (替代 channel/credit/report)
    orch = CoworkOrchestrator()
    mock_adapter = MockProducerAdapter(agent_id="credit")
    orch.register_adapter(mock_adapter)
    orch.register_adapter(MockProducerAdapter(agent_id="channel"))
    orch.register_adapter(MockProducerAdapter(agent_id="report"))
    set_default_orchestrator(orch)

    # FastAPI app · auth bypass via dependency_overrides
    app = FastAPI()
    mounted = register_liuye_routes(app, orchestrator=orch)
    assert mounted, "register_liuye_routes should mount (LIUYE_ENABLED=1)"

    from auth_service.dependencies import require_user
    async def _stub_user() -> dict[str, Any]:
        return {"sub": "test-rm", "role": "rm"}
    app.dependency_overrides[require_user] = _stub_user

    return app, mock_adapter, orch


# ---------------------------------------------------------------------------
# Helpers · parse SSE wire bytes + bounded stream drain
# ---------------------------------------------------------------------------


def _parse_sse_chunk(chunk: str) -> dict[str, Any] | None:
    """Parse one ``id:\\nevent:\\ndata:\\n\\n`` SSE frame into dict."""
    out: dict[str, Any] = {}
    for line in chunk.splitlines():
        if line.startswith("id:"):
            out["id"] = line[3:].strip()
        elif line.startswith("event:"):
            out["event"] = line[6:].strip()
        elif line.startswith("data:"):
            data_text = line[5:].strip()
            try:
                out["data"] = json.loads(data_text)
            except json.JSONDecodeError:
                out["data"] = data_text
    return out if out else None


async def _drive_stream(
    orch: CoworkOrchestrator,
    turn_id: str,
    *,
    max_seconds: float = 5.0,
    max_frames: int = 50,
    until_event: str | None = None,
) -> list[dict[str, Any]]:
    """Drive ``_stream_skeleton`` async generator directly · 抓 wire frames.

    Bypasses httpx ASGI transport (it buffers infinite generator). Returns
    one dict per SSE frame (with id / event / data).
    """
    frames: list[dict[str, Any]] = []
    deadline = asyncio.get_event_loop().time() + max_seconds
    gen = _stream_skeleton(orch, turn_id)
    try:
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                async with asyncio.timeout(remaining):
                    chunk = await gen.__anext__()
            except (asyncio.TimeoutError, TimeoutError):
                break
            except StopAsyncIteration:
                break
            frame = _parse_sse_chunk(chunk)
            if frame:
                frames.append(frame)
                if until_event and frame.get("event") == until_event:
                    break
            if len(frames) >= max_frames:
                break
    finally:
        await gen.aclose()
    return frames


# ---------------------------------------------------------------------------
# Test 1: 11 event 序列 · 完整 e2e
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_full_11_event_sequence(
    app_with_mock_adapter: tuple[FastAPI, MockProducerAdapter, CoworkOrchestrator],
) -> None:
    """POST /sessions (httpx) → dispatch via adapter (in-process task) →
    drive _stream_skeleton (async gen) → 验 9 mock + turn.started 全到."""
    app, _mock, orch = app_with_mock_adapter

    # 1. POST /sessions via httpx ASGI (这是非 streaming endpoint · ASGI OK)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/liuye/sessions",
            json={"persona": "rm", "agent_id": "credit", "payload": {"q": "e2e"}},
        )
        assert resp.status_code == 201, resp.text
        turn_id = resp.json()["turn_id"]
        assert turn_id.startswith("turn_")

    # 2. dispatch_via_adapter · in-process task · push events into the queue
    asyncio.create_task(_dispatch_via_adapter(
        orchestrator=orch,
        turn_id=turn_id,
        message={"text": "审贷申请"},
    ))

    # 3. Drive _stream_skeleton · 收 SSE 直到 turn.completed (mock 收尾 + None sentinel)
    frames = await _drive_stream(
        orch, turn_id,
        max_seconds=5.0,
        until_event="turn.completed",
    )

    # 4. 验序列
    event_names = [f["event"] for f in frames if "event" in f]
    # turn.started 必有 (_stream_skeleton 第一个 yield)
    assert "turn.started" in event_names, f"missing turn.started · got {event_names}"
    # mock 9 event 全到
    for must in ("message.created", "tool.started", "tool.progress",
                 "tool.completed", "evidence.attached", "artifact.patch",
                 "turn.completed"):
        assert must in event_names, f"missing {must} · got {event_names}"


# ---------------------------------------------------------------------------
# Test 2: seq 单调递增
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_seq_monotonic_increasing(
    app_with_mock_adapter: tuple[FastAPI, MockProducerAdapter, CoworkOrchestrator],
) -> None:
    """每条 SSE id 是 ``<turn_id>:<seq>`` · seq 单调递增 (1, 2, 3, ...)."""
    app, _, orch = app_with_mock_adapter

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/liuye/sessions",
            json={"persona": "rm", "agent_id": "credit", "payload": {}},
        )
        turn_id = resp.json()["turn_id"]

    asyncio.create_task(_dispatch_via_adapter(
        orchestrator=orch, turn_id=turn_id, message={},
    ))

    frames = await _drive_stream(
        orch, turn_id,
        max_seconds=5.0,
        until_event="turn.completed",
    )

    # parse seq from each id field
    seqs: list[int] = []
    for f in frames:
        if "id" not in f:
            continue
        m = re.match(rf"^{re.escape(turn_id)}:(\d+)$", f["id"])
        assert m, f"malformed id {f['id']!r}"
        seqs.append(int(m.group(1)))

    assert seqs, "expected at least one frame with id"
    # 单调递增 +1 (heartbeat 也 bump seq · 这里 stream 持续输出 · 序列严格 +1)
    for prev, nxt in zip(seqs, seqs[1:]):
        assert nxt == prev + 1, f"seq not monotonic +1: {prev} → {nxt} · full={seqs}"


# ---------------------------------------------------------------------------
# Test 3: heartbeat 触发 (15s · test 缩到 0.2s)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_heartbeat_fires_when_adapter_idle(
    app_with_mock_adapter: tuple[FastAPI, MockProducerAdapter, CoworkOrchestrator],
) -> None:
    """Adapter 不 dispatch 时 (没 POST /messages) · _stream_skeleton 每 0.2s
    emit heartbeat (HEARTBEAT_INTERVAL_SECONDS · 已 patch to 0.2 in fixture).
    Production 是 15s."""
    app, _, orch = app_with_mock_adapter

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/liuye/sessions",
            json={"persona": "rm", "agent_id": "credit", "payload": {}},
        )
        turn_id = resp.json()["turn_id"]

    # 不 dispatch · 让 _stream_skeleton 走 timeout path 真发 heartbeat
    frames = await _drive_stream(
        orch, turn_id,
        max_seconds=1.5,  # 0.2s tick · 1.5s 至少 5-6 个 heartbeat
        max_frames=5,
    )

    event_names = [f.get("event") for f in frames]
    assert "turn.started" in event_names, f"expected turn.started · got {event_names}"
    # 应有 ≥1 heartbeat (0.2s tick · 1.5s timeout = 至少 5-6 个 heartbeat 机会)
    assert event_names.count("heartbeat") >= 1, f"expected heartbeat · got {event_names}"


# ---------------------------------------------------------------------------
# Test 4: Last-Event-ID 格式
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_id_format_supports_last_event_id_reconnect(
    app_with_mock_adapter: tuple[FastAPI, MockProducerAdapter, CoworkOrchestrator],
) -> None:
    """SSE id 格式 ``<turn_id>:<seq>`` 给浏览器 EventSource Last-Event-ID 重连用."""
    app, _, orch = app_with_mock_adapter

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/liuye/sessions",
            json={"persona": "rm", "agent_id": "credit", "payload": {}},
        )
        turn_id = resp.json()["turn_id"]

    asyncio.create_task(_dispatch_via_adapter(
        orchestrator=orch, turn_id=turn_id, message={},
    ))

    frames = await _drive_stream(
        orch, turn_id,
        max_seconds=5.0,
        until_event="turn.completed",
    )

    # 验每个 frame 都有 id · 格式正确
    id_count = 0
    for f in frames:
        if "id" in f:
            id_count += 1
            assert re.match(rf"^{re.escape(turn_id)}:\d+$", f["id"]), \
                f"malformed id {f['id']!r} · expected <turn_id>:<seq>"
    assert id_count >= 5, f"expected ≥5 framed events with id · got {id_count}"


# ---------------------------------------------------------------------------
# Test 5: LB retry dedup gate · sse_v1_to_liuye 翻译层 dedup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_v1_dedup_blocks_lb_retry_double_emit() -> None:
    """LB retry 把同 v1 event 推 2 次 · ``sse_v1_to_liuye.translate`` 的 dedup
    gate (``dedup_key = (event, sha256(payload))``) 第二次跳 · 不二次 emit
    liuye 事件.

    这是 W2 第 4 棒 brief 强调的 'integration test cover' (W2 第 3 棒只用 sync
    dict mock · 这里走 translator 真实路径)."""
    translator = SseV1ToLiuyeAdapter(agent_id="credit", trace_id="trace_lb_retry")
    turn_id = "turn_dedup_001"

    v1_event = {
        "event": "stage",
        "stage": "scoring",
        "message": "评分中",
        "progress": 0.5,
        "status": "running",
    }

    # First push · expect 1 liuye event
    first: list[dict[str, Any]] = []
    async for e in translator.translate(v1_event, turn_id):
        first.append(e)
    assert len(first) == 1
    assert first[0]["event"] == "tool.progress"

    # Second push · same v1 event · dedup gate fires · no liuye event
    second: list[dict[str, Any]] = []
    async for e in translator.translate(v1_event, turn_id):
        second.append(e)
    assert len(second) == 0, f"LB retry should be deduped · got {second}"

    # 验 translator_metrics 计数
    assert translator.translator_metrics.events_translated == 1
    assert translator.translator_metrics.dedup_skipped == 1


@pytest.mark.asyncio
async def test_sse_v1_dedup_distinguishes_payload_difference() -> None:
    """同 event 名 · payload 不同 (e.g. progress 0.5 vs 0.7) · dedup 不误杀."""
    translator = SseV1ToLiuyeAdapter(agent_id="credit", trace_id="trace_diff")
    turn_id = "turn_dedup_002"

    e1 = {"event": "stage", "stage": "scoring", "progress": 0.5}
    e2 = {"event": "stage", "stage": "scoring", "progress": 0.7}

    out1 = [e async for e in translator.translate(e1, turn_id)]
    out2 = [e async for e in translator.translate(e2, turn_id)]

    assert len(out1) == 1
    assert len(out2) == 1, "different payloads must NOT collide on dedup"
    assert translator.translator_metrics.events_translated == 2
    assert translator.translator_metrics.dedup_skipped == 0


# ---------------------------------------------------------------------------
# Test 6: dispatch_via_adapter pushes events to queue · 验 _dispatch 桥真接
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_dispatch_via_adapter_bridges_to_queue(
    app_with_mock_adapter: tuple[FastAPI, MockProducerAdapter, CoworkOrchestrator],
) -> None:
    """``_dispatch_via_adapter`` 把 adapter yield 的 event 写入 per-turn queue ·
    end-of-stream 推 None sentinel · _stream_skeleton 见 None 退出 (NOT timeout)."""
    app, mock, orch = app_with_mock_adapter

    # 起 turn
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/liuye/sessions",
            json={"persona": "rm", "agent_id": "credit", "payload": {}},
        )
        turn_id = resp.json()["turn_id"]

    # dispatch_via_adapter 直接 await · 等 adapter 全部推完 + None sentinel 落 queue
    await _dispatch_via_adapter(
        orchestrator=orch, turn_id=turn_id, message={"text": "审贷"},
    )

    # adapter 真被调
    assert mock.dispatched_count == len(_DEFAULT_11_EVENT_SEQUENCE)

    # queue 应有所有 9 event + None sentinel · drain 验内容
    queue = orch.get_or_create_sse_queue(turn_id)
    queued_events: list[dict[str, Any] | None] = []
    while not queue.empty():
        queued_events.append(queue.get_nowait())
    # 最后一个是 None sentinel (end-of-stream)
    assert queued_events[-1] is None, "missing None sentinel"
    # 前面 9 个是 mock 推的
    business_events = [e for e in queued_events if e is not None]
    assert len(business_events) == len(_DEFAULT_11_EVENT_SEQUENCE)
    # 验顺序保持 (FIFO queue)
    for actual, expected in zip(business_events, _DEFAULT_11_EVENT_SEQUENCE):
        assert actual["event"] == expected["event"]
