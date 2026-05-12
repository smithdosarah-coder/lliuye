# -*- coding: utf-8 -*-
"""liuye_service.tests.test_fallback_tavily_quota — 5 应急 backend dry-run #1.

Per W2-backend brief §3 file 3 (第 4 棒 应急 dry-run W2 #1) + v3 §5.x + root §3.7.3.

**应急场景**: Tavily Tier 4 公开 web 通用搜索 (root §3.5.1 + shared/sources/impls/tavily.py)
返 HTTP 429 quota 耗尽 / API key 失效 / 配额超 · 走 backend channel adapter live
HTTP path. 验:

1. backend HTTP 调 (POST /api/channel/run) 收到 backend 内部的 Tavily 429
   被翻译成 SSE v1 error → adapter 透传成 liuye ``turn.error
   code=ADAPTER_HTTP_ERROR fallback_available=true``
2. ``fallback_available=true`` 是前端 banner 切 DEMO_MODE 的信号 (root §3.5.1
   + W2 backend brief §4.2 perfect-check fix #1)
3. DEMO_MODE 重跑同一 turn · 走 fixture replay path (load_fixture("channel_5candidates"))
   · 后续 step 4-9 不受影响
4. channel adapter 内 fallback 不影响 credit/report 真接 (per W2 channel
   path 独立 · 跨 adapter 隔离)

**反模式**:
- ❌ 把 Tavily error 静默吞掉 (decision flow 看似 OK · 但候选为空 · 客户经理
  evaluate 不到任何 evidence · 比明确 fallback 更危险)
- ❌ adapter 内 retry Tavily (违反 SLA 5s · ChannelAdapter 是 Cowork)
- ❌ live HTTP 504/429 → 强制走 DEMO_MODE (用户没显式 opt-in · 数据来源标错)

**SSOT 引用**:
- ``shared/sources/impls/tavily.py:TavilySource.query()`` (Tavily error 路径)
- ``liuye_service/adapters/channel.py:ChannelAdapter._run_live()`` (HTTP error 翻译)
- ``liuye_service/adapters/channel.py:DEMO_FIXTURE_STEM`` (channel_5candidates fixture)
- root §3.5.1 #6 数据时效 (Tavily Tier 4 不可单一来源 · 必交叉 Tier 2-3)

测试隔离: monkeypatch httpx 模拟 backend 429 · 不需要真起 backend.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator
from unittest.mock import patch

import httpx
import pytest

from liuye_service.adapters.base import reset_seq
from liuye_service.adapters.channel import ChannelAdapter
from liuye_service.adapters.sse_v1_to_liuye import SseV1ToLiuyeAdapter
from liuye_service.config import Settings, set_default_settings


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    """Reset seq counter + settings singleton between tests."""
    reset_seq()
    set_default_settings(None)
    yield
    reset_seq()
    set_default_settings(None)


async def _drain(agen: AsyncIterator[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for evt in agen:
        out.append(evt)
    return out


# ---------------------------------------------------------------------------
# Helper · build a mock httpx.AsyncClient that returns 429 on stream POST
# ---------------------------------------------------------------------------


class _MockResponse:
    """Minimal async ctx manager mocking httpx.Response.stream()."""

    def __init__(self, status_code: int, lines: list[str] | None = None) -> None:
        self.status_code = status_code
        self._lines = lines or []

    async def __aenter__(self) -> "_MockResponse":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


class _MockHttpClient:
    """Minimal async client mocking httpx.AsyncClient for the live HTTP path.

    Channel adapter's ``_run_live`` uses ``client.stream("POST", url, ...)``
    as a context manager. We mimic that surface so the adapter believes
    the backend responded with 429 (Tavily quota propagated upstream).
    """

    def __init__(self, status_code: int = 429) -> None:
        self.status_code = status_code
        self.calls: list[dict[str, Any]] = []

    def stream(self, method: str, url: str, **kwargs: Any) -> _MockResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _MockResponse(self.status_code)

    async def aclose(self) -> None:
        pass


# ---------------------------------------------------------------------------
# 1. Live mode · backend 429 (Tavily quota propagation) → ADAPTER_HTTP_ERROR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tavily_429_propagates_as_adapter_http_error() -> None:
    """Backend channel /run 返 429 (Tavily quota 耗尽) → adapter emit
    ``turn.error code=ADAPTER_HTTP_ERROR fallback_available=true``.

    这是前端 banner 切 DEMO_MODE 的信号 · 不破 decision flow."""
    # 强制 live mode (demo_mode=False)
    set_default_settings(Settings(
        enabled=True,
        demo_mode=False,
        backend_base_url="http://localhost:8000",
    ))

    mock_client = _MockHttpClient(status_code=429)
    adapter = ChannelAdapter(http_client=mock_client)

    events = await _drain(adapter.start_turn(
        turn_id="turn_quota_001",
        persona="rm",
        payload={"trace_id": "trace_quota_001", "query": "look-alike candidates"},
    ))

    # 应有 1 个 turn.error · code=ADAPTER_HTTP_ERROR · fallback_available=true
    error_events = [e for e in events if e["event"] == "turn.error"]
    assert len(error_events) >= 1, f"expected ≥1 turn.error · got events={[e['event'] for e in events]}"
    err = error_events[0]
    payload = err["payload"]
    assert payload["code"] == "ADAPTER_HTTP_ERROR"
    assert payload["fallback_available"] is True
    assert payload["retryable"] is True
    assert "429" in payload["message"]
    # human_hint 用中文 · 银行 UI 友好 (root §3 客户体验)
    assert "获客 Agent" in payload["human_hint"]


@pytest.mark.asyncio
async def test_tavily_429_records_backend_call_for_audit() -> None:
    """Live 调用真打到 backend URL · audit chain 留痕 (NOT 静默吞 retry)."""
    set_default_settings(Settings(
        enabled=True,
        demo_mode=False,
        backend_base_url="http://localhost:8000",
    ))

    mock_client = _MockHttpClient(status_code=429)
    adapter = ChannelAdapter(http_client=mock_client)

    await _drain(adapter.start_turn(
        turn_id="turn_quota_002",
        persona="rm",
        payload={"trace_id": "trace_quota_002", "query": "test"},
    ))

    # 验 backend 真被调到 (1 次 · 不 retry · SLA 5s 不允许多次重试)
    assert len(mock_client.calls) == 1, f"expected 1 backend call · got {len(mock_client.calls)}"
    call = mock_client.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "http://localhost:8000/api/channel/run"
    assert call["json"]["turn_id"] == "turn_quota_002"
    assert call["json"]["trace_id"] == "trace_quota_002"


# ---------------------------------------------------------------------------
# 2. DEMO_MODE fallback · 客户经理 opt-in 切 demo 后 fixture replay 跑通
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demo_mode_fallback_replays_fixture_after_quota_exhaustion() -> None:
    """前端 banner 通知用户 Tavily 不可用 · 用户 opt-in DEMO_MODE → 重跑同 turn
    走 fixture replay (channel_5candidates.json) · 后续 step 4-9 真接 candidate.

    验:
    1. demo_mode=True 时 adapter 走 _run_demo 路径
    2. fixture 缺失 → emit code=DEMO_FIXTURE_MISSING (前端再换 banner)
    3. fixture 存在 → 真 emit 11 event 流 (turn.started / tool.started /
       stage / tool.completed / turn.completed)
    """
    set_default_settings(Settings(
        enabled=True,
        demo_mode=True,
        backend_base_url="http://localhost:8000",
    ))

    # mock load_fixture · 不依赖真 tests/fixtures/channel_5candidates.json
    fake_fixture = {
        "id": "art_channel_quota_demo",
        "snapshot": {
            "candidates": [
                {"name": "candidate_a", "industry": "金融", "geo": "上海",
                 "scale": "中型", "similarity": 0.92},
                {"name": "candidate_b", "industry": "金融", "geo": "杭州",
                 "scale": "大型", "similarity": 0.87},
            ],
            "summary": {"total": 2, "data_source": "demo"},
            "seed": {"search_intent": "金融 look-alike"},
        },
    }
    with patch(
        "liuye_service.adapters.channel.load_fixture",
        return_value=fake_fixture,
    ):
        adapter = ChannelAdapter()
        events = await _drain(adapter.start_turn(
            turn_id="turn_demo_recover_001",
            persona="rm",
            payload={"trace_id": "trace_demo_recover", "query": "金融 candidates"},
        ))

    # 验 demo 流: profile_loaded → tool.started → tool.progress*3 → tool.completed → turn.completed
    event_names = [e["event"] for e in events]
    # demo 走 _synthesise_channel_v1_frames → translator translate · 输出 liuye 事件
    # profile_loaded → turn.started · stage → tool.progress · tool_call → tool.started
    assert "turn.started" in event_names, f"expected turn.started · got {event_names}"
    assert "tool.started" in event_names, f"expected tool.started · got {event_names}"
    assert "tool.progress" in event_names, f"expected tool.progress · got {event_names}"
    assert "tool.completed" in event_names, f"expected tool.completed · got {event_names}"
    assert "turn.completed" in event_names, f"expected turn.completed · got {event_names}"
    # 不应有任何 turn.error (demo 全成功)
    error_events = [e for e in events if e["event"] == "turn.error"]
    assert len(error_events) == 0, f"unexpected turn.error in demo: {error_events}"

    # 验 candidate metadata 4 字段 完整 (per root §3.7.2)
    completed = next(e for e in events if e["event"] == "tool.completed")
    candidates = completed["payload"]["result"]["candidates"]
    assert len(candidates) == 2
    for c in candidates:
        assert "industry" in c
        assert "geo" in c
        assert "scale" in c
        assert "similarity" in c


@pytest.mark.asyncio
async def test_demo_mode_fixture_missing_emits_dedicated_error() -> None:
    """fixture 文件不存在 → emit code=DEMO_FIXTURE_MISSING · 前端再换 banner
    (不是 silent skip · 不是 crash)."""
    set_default_settings(Settings(
        enabled=True,
        demo_mode=True,
    ))

    from liuye_service.adapters.base import FixtureLoadError

    with patch(
        "liuye_service.adapters.channel.load_fixture",
        side_effect=FixtureLoadError("fixture 'channel_5candidates' not found at /nowhere/x.json"),
    ):
        adapter = ChannelAdapter()
        events = await _drain(adapter.start_turn(
            turn_id="turn_demo_missing_001",
            persona="rm",
            payload={"trace_id": "trace_demo_missing", "query": "test"},
        ))

    error_events = [e for e in events if e["event"] == "turn.error"]
    assert len(error_events) >= 1
    err = error_events[0]
    assert err["payload"]["code"] == "DEMO_FIXTURE_MISSING"
    assert err["payload"]["fallback_available"] is True
    # 错误 message 含 fixture 名 · 排错可定位
    assert "channel_5candidates" in err["payload"]["message"]


# ---------------------------------------------------------------------------
# 3. 失败隔离 · channel 挂不影响 credit/report adapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_channel_adapter_failure_does_not_block_subsequent_turn() -> None:
    """channel 429 后 · 同一 adapter 实例下一个 turn 应能正常处理 (no global state pollute)."""
    set_default_settings(Settings(
        enabled=True,
        demo_mode=False,
        backend_base_url="http://localhost:8000",
    ))

    # 第一个 turn · 429 失败
    mock_client_fail = _MockHttpClient(status_code=429)
    adapter = ChannelAdapter(http_client=mock_client_fail)
    events_1 = await _drain(adapter.start_turn(
        turn_id="turn_isolate_001",
        persona="rm",
        payload={"trace_id": "trace_isolate_001"},
    ))
    assert any(e["event"] == "turn.error" and e["payload"]["code"] == "ADAPTER_HTTP_ERROR"
               for e in events_1)

    # 第二个 turn · 用全新 mock 200 OK (mock SSE empty body · 验 adapter 不被
    # 上次 failure 卡死)
    mock_client_ok = _MockHttpClient(status_code=200)
    adapter2 = ChannelAdapter(http_client=mock_client_ok)
    events_2 = await _drain(adapter2.start_turn(
        turn_id="turn_isolate_002",
        persona="rm",
        payload={"trace_id": "trace_isolate_002"},
    ))
    # 第二 turn 不该有 ADAPTER_HTTP_ERROR (mock 200 OK + 空 body 不算 error)
    error_codes = [e["payload"].get("code") for e in events_2 if e["event"] == "turn.error"]
    assert "ADAPTER_HTTP_ERROR" not in error_codes, f"channel adapter contaminated by previous failure · errors={error_codes}"
