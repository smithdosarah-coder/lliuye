# -*- coding: utf-8 -*-
"""Phase B.2 真意 reframe (PM 2026-05-10) · /api/channel/demo/run 改真后端 smoke tests.

PM 真意 verbatim: "演示不是一键切换 · 而是把本地的 mock 数据真实上传 · 通过真实
后端代码跑一遍 · 最后给出结果"

- 旧版 (B.1) yield 写死 fixture event from data/mock/workspace/channel/scenarios/<id>.json
- 新版 (B.2) load channel-kb marketing-preferences docx → seed query → 真后端 pipeline
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_channel.api import app


def _parse_sse_lines(text: str) -> list[dict]:
    """Parse SSE stream `data: {...}\n\n` into list of dicts."""
    out: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            out.append(json.loads(payload))
        except json.JSONDecodeError:
            pass
    return out


def test_demo_run_invalid_scenario_returns_typed_error():
    """scenario_id 不在 easy/medium/hard → typed error code DEMO_SCENARIO_INVALID."""
    client = TestClient(app)
    resp = client.post("/api/channel/demo/run", json={"scenario_id": "garbage"})
    assert resp.status_code == 200
    events = _parse_sse_lines(resp.text)
    assert events, "expected at least 1 SSE event"
    err = next((e for e in events if e.get("event") == "error"), None)
    assert err is not None, f"no error event yielded · events={events!r}"
    assert err.get("code") == "DEMO_SCENARIO_INVALID"


def test_demo_run_emits_demo_context_with_seed_query(monkeypatch):
    """新 endpoint 第一个事件是 demo_context · 含 sample_source / derived_seed_query / sample_files.

    且 seed_query 必须从 channel-kb marketing-preferences 真派生 · 不是硬编。
    """
    # 移除 TAVILY 让 endpoint 在 demo_context 后立刻 typed banner · 不真跑 pipeline
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    client = TestClient(app)
    resp = client.post("/api/channel/demo/run", json={"scenario_id": "easy"})
    assert resp.status_code == 200
    events = _parse_sse_lines(resp.text)
    assert events, "expected at least 1 SSE event"

    ctx = next((e for e in events if e.get("event") == "demo_context"), None)
    assert ctx is not None, f"no demo_context event yielded · events={events!r}"
    assert ctx["sample_source"] == "data/mock/channel-kb/marketing-preferences"
    assert ctx["scenario_id"] == "easy"
    assert isinstance(ctx["sample_files"], list) and ctx["sample_files"], (
        "sample_files 必须 list 且 ≥1 个 docx · 来自 channel-kb 真扫"
    )
    # 至少有一份 marketing-preferences docx
    assert any(".docx" in f for f in ctx["sample_files"])
    # derived_seed_query 必须非空且不是空 query 兜底
    seed = ctx["derived_seed_query"]
    assert isinstance(seed, str) and seed.strip(), "derived_seed_query 不能空"
    assert "贷款 审贷 企业" not in seed, "禁止空 query 兜底 (red line)"
    assert ctx["pipeline"] == "run_channel_search_stream (real)"


def test_demo_run_no_tavily_yields_typed_banner(monkeypatch):
    """TAVILY_API_KEY 缺 → typed banner code TAVILY_KEY_MISSING_FOR_DEMO · 不 silent fallback fake.

    硬线 (per dispatch §不可 GO): channel 单 Tavily 无降级 banner = REJECT
    """
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    client = TestClient(app)
    resp = client.post("/api/channel/demo/run", json={"scenario_id": "medium"})
    assert resp.status_code == 200
    events = _parse_sse_lines(resp.text)
    err = next(
        (e for e in events
         if e.get("event") == "error" and e.get("code") == "TAVILY_KEY_MISSING_FOR_DEMO"),
        None,
    )
    assert err is not None, (
        f"expected typed banner TAVILY_KEY_MISSING_FOR_DEMO · events={events!r}"
    )
    assert "TAVILY" in err.get("message", "")
    # 不 yield 任何 stage event (没真跑 pipeline)
    stage_events = [e for e in events if e.get("event") == "stage"]
    assert not stage_events, f"TAVILY 缺时不应 yield 任何 stage event · got {stage_events!r}"


def test_demo_run_does_not_read_old_fixture_scenarios():
    """硬线 · 新 endpoint 不能再消费 data/mock/workspace/channel/scenarios/<id>.json (反 §3.5).

    检查方式: 实际跑 endpoint, 验证不读 workspace/scenarios/*.json 文件 (PathLib 行为) ·
    也不 yield 旧 mock_forced data_source from fixture · 注释/docstring 提及不算违规.
    """
    # 1) 跑 endpoint with TAVILY 缺 · 验证不 yield fixture stage 序列
    import os
    os.environ.pop("TAVILY_API_KEY", None)
    client = TestClient(app)
    resp = client.post("/api/channel/demo/run", json={"scenario_id": "easy"})
    events = _parse_sse_lines(resp.text)

    # 旧 endpoint 在 TAVILY 缺时仍 yield 全 6 stage running/done + fixture done event ·
    # 新 endpoint TAVILY 缺即 typed banner 后 return · 不 yield 任何 stage event
    stage_events = [e for e in events if e.get("event") == "stage"]
    done_events = [e for e in events if e.get("event") == "done"]
    assert not stage_events, (
        f"硬线 · TAVILY 缺时不应再 yield 旧 fixture 6-stage 流 · got {len(stage_events)} stage events"
    )
    assert not done_events, (
        "硬线 · TAVILY 缺时不应 yield fixture done envelope (反 §3.5 答案给嘴边)"
    )

    # 2) 检查 endpoint body 不 instantiate _SCENARIO_DIR Path (字符串残留 in docstring 不算)
    api_path = Path(__file__).resolve().parents[2] / "agent_channel" / "api.py"
    content = api_path.read_text(encoding="utf-8")
    demo_run_idx = content.find("async def channel_demo_run")
    assert demo_run_idx > 0, "channel_demo_run 函数没找到"
    next_route_idx = content.find("@app.post", demo_run_idx + 1)
    body = content[demo_run_idx:next_route_idx]
    # _SCENARIO_DIR 旧 module-level 常量 (Path 对象) 在 endpoint body 内不应再 use
    assert "_SCENARIO_DIR" not in body, "_SCENARIO_DIR 旧 fixture path 引用不应再活跃"
    # data.get("candidates", []) 是旧 fixture data 解构 pattern · 不应在 demo_run 内
    assert "data.get(\"candidates\"" not in body and "data.get('candidates'" not in body, (
        "fixture data dict 解构 pattern 残留 (旧 yield 写死 candidates)"
    )


def test_demo_run_not_implemented_yields_typed_banner(monkeypatch):
    """run_channel_search_stream raise NotImplementedError → typed banner BACKEND_NOT_IMPLEMENTED.

    硬线 (per dispatch §5): NotImplementedError 任何运行路径 raise = REJECT
    必须 typed banner · 不 silent · 不 fallback fake.
    """
    # 设 TAVILY 让 endpoint 走到 pipeline 调用步
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    # patch run_channel_search_stream raise NotImplementedError
    import agent_channel.realtime_stream as rts

    def boom(*_args, **_kwargs):
        raise NotImplementedError("build_search_provider · no Tavily configured")
        # 让生成器 not iterable 也触发 raise
        yield  # pragma: no cover

    monkeypatch.setattr(rts, "run_channel_search_stream", boom)
    # endpoint 内 from agent_channel.realtime_stream import run_channel_search_stream
    # 是 lazy import (在 def gen() 内) · monkeypatch 模块属性后 endpoint 拿到 patched
    client = TestClient(app)
    resp = client.post("/api/channel/demo/run", json={"scenario_id": "easy"})
    assert resp.status_code == 200
    events = _parse_sse_lines(resp.text)
    err = next(
        (e for e in events
         if e.get("event") == "error" and e.get("code") == "BACKEND_NOT_IMPLEMENTED"),
        None,
    )
    assert err is not None, (
        f"NotImplementedError 应转 typed banner BACKEND_NOT_IMPLEMENTED · events={events!r}"
    )
    assert "NotImplementedError" in err["message"]


def test_demo_run_kb_path_missing_returns_typed_error(tmp_path, monkeypatch):
    """如果 channel-kb 路径不在 (CI 极端 case) → typed error DEMO_KB_MISSING / EMPTY · 不 crash."""
    # 这个 test 不实际删 fs · 而是验证 endpoint 当 kb 解析空时 yield typed error
    # parse_marketing_preferences 在空目录返 [] · build_queries 返 [] · endpoint 应 typed error
    from agent_channel import api as channel_api

    # 注 channel_api._KB_PATH 不存在 · 不能 monkeypatch 模块常量 (没显式公有 KB)
    # 改用 monkey patch parse_marketing_preferences 让它返空
    import agent_channel.seed_query_builder as sqb

    monkeypatch.setattr(sqb, "parse_marketing_preferences", lambda _path: [])
    # 也要 patch endpoint 内的 import (closure 已拿到原函数)
    # endpoint 内 from ... import 在 gen() 第一次调时 resolve · 此时 patch 后 sqb 模块改 · 拿到 patched
    # 注: from agent_channel.seed_query_builder import ... 会 bind module attr at import time
    # → 这里 patch sqb.parse_marketing_preferences 也改了 endpoint 视角 (因为是同一 module obj)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    client = TestClient(app)
    resp = client.post("/api/channel/demo/run", json={"scenario_id": "medium"})
    assert resp.status_code == 200
    events = _parse_sse_lines(resp.text)
    err = next((e for e in events if e.get("event") == "error"), None)
    assert err is not None and err.get("code") in {"DEMO_KB_EMPTY", "DEMO_KB_MISSING"}, (
        f"expected DEMO_KB_EMPTY/MISSING · got {events!r}"
    )
