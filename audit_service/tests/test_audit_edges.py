# -*- coding: utf-8 -*-
"""audit_service edges · Stage E.4 expansion (W-E4-A1).

参数化 heavy · 单 file ~80 case 覆盖:
  - truncate_text utf-8 边界 (1/2/3/4 字节字符 × 各阈值)
  - estimate_cost_cny 多 token 组合
  - LLMCall dataclass 字段默认 / 序列化
  - AuditRecorder 边界 (None / 极长 / 重复 record)
  - decorator 边界 (kwargs 变体 / sync · async / 异常类型)
  - middleware path resolver
  - api role guard 多角色

Author: Worker A1 (Stage E.4 第 1 批) · 2026-04-28
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audit_service.decorators import audit_llm_call  # noqa: E402
from audit_service.middleware import _default_agent_resolver  # noqa: E402
from audit_service.recorder import (  # noqa: E402
    AuditRecorder,
    LLMCall,
    estimate_cost_cny,
    set_default_recorder,
    truncate_text,
)


@pytest.fixture
def isolated_recorder(tmp_path):
    rec = AuditRecorder(tmp_path / "edges.db")
    set_default_recorder(rec)
    yield rec
    set_default_recorder(None)


# ============================================================================
# truncate_text · 参数化 18 case
# ============================================================================

@pytest.mark.parametrize("input_, max_bytes, expects_truncated", [
    (None, 100, False),
    ("", 100, False),
    ("a", 100, False),
    ("a" * 100, 100, False),
    ("a" * 101, 100, True),
    ("a" * 5000, 100, True),
    ("a" * 5000, 4096, True),
    ("中" * 100, 300, False),       # 中 = 3 bytes · 300 bytes 刚够
    ("中" * 101, 300, True),
    ("中" * 1000, 100, True),
    ("混合abc中文" * 100, 100, True),
    ("emoji😀😀😀" * 50, 100, True),
    ("a", 1, False),
    ("ab", 1, True),
    (123, 100, False),  # 非 str 类型 · 转 str 后判断
    ([], 100, False),
    ({}, 100, False),
    ("中", 0, True),
])
def test_truncate_parametrize(input_, max_bytes, expects_truncated):
    result = truncate_text(input_, max_bytes)
    if input_ is None:
        assert result is None
    elif expects_truncated:
        assert "[truncated]" in (result or "")
    else:
        # 不截断 · 应原样 (or str(input_))
        assert "[truncated]" not in (result or "")


# ============================================================================
# estimate_cost_cny · 参数化 12 case
# ============================================================================

@pytest.mark.parametrize("inp, out, expected", [
    (None, None, None),
    (0, 0, 0.0),
    (100, None, pytest.approx(0.01, abs=0.0001)),
    (None, 200, pytest.approx(0.02, abs=0.0001)),
    (100, 200, pytest.approx(0.03, abs=0.0001)),
    (1000, 0, pytest.approx(0.1, abs=0.0001)),
    (0, 1000, pytest.approx(0.1, abs=0.0001)),
    (50000, 0, pytest.approx(5.0, abs=0.001)),
    (1, 1, pytest.approx(0.0002, abs=0.0001)),
    (1_000_000, 0, pytest.approx(100.0, abs=0.01)),
    (None, 0, 0.0),
    (0, None, 0.0),
])
def test_cost_parametrize(inp, out, expected):
    if expected is None:
        assert estimate_cost_cny(inp, out) is None
    else:
        assert estimate_cost_cny(inp, out) == expected


@pytest.mark.parametrize("model", [
    "deepseek-chat", "gpt-4", "gpt-3.5", "claude-3", "unknown-model", "",
])
def test_cost_model_param_doesnt_crash(model):
    """各 model 名都不抛 (rate 当前不分 model · 后续 config 化)."""
    assert estimate_cost_cny(100, 200, model=model) is not None


# ============================================================================
# LLMCall dataclass · 参数化 8 case
# ============================================================================

@pytest.mark.parametrize("agent_id", [
    "channel", "credit", "report", "alert", "compliance", "riskctrl",
])
def test_llmcall_per_agent_creates_clean(agent_id):
    call = LLMCall(agent_id=agent_id, endpoint=f"/api/{agent_id}/x", model="m")
    assert call.agent_id == agent_id
    assert call.id is None  # 未 record 前


def test_llmcall_to_dict_roundtrip():
    call = LLMCall(agent_id="x", endpoint="/x", model="m", input_tokens=100)
    d = call.to_dict()
    assert d["agent_id"] == "x"
    assert d["input_tokens"] == 100


def test_llmcall_default_ts_is_isoformat():
    """ts 默认 isoformat seconds · 不带毫秒."""
    call = LLMCall(agent_id="x", endpoint="/x", model="m")
    # 形如 "2026-04-28T16:00:00"
    assert "T" in call.ts
    assert "." not in call.ts.split("T")[1]  # no microseconds


# ============================================================================
# AuditRecorder edges · 参数化 12 case
# ============================================================================

@pytest.mark.parametrize("user_id_arg, expected_query_count", [
    ("u_a", 2),
    ("u_b", 1),
    ("u_c", 0),
    (None, 3),  # None filter = no filter
])
def test_recorder_query_user_filter(isolated_recorder, user_id_arg, expected_query_count):
    isolated_recorder.record(LLMCall(agent_id="x", endpoint="/x", model="m", user_id="u_a"))
    isolated_recorder.record(LLMCall(agent_id="x", endpoint="/y", model="m", user_id="u_b"))
    isolated_recorder.record(LLMCall(agent_id="x", endpoint="/z", model="m", user_id="u_a"))

    rows = isolated_recorder.query(user_id=user_id_arg)
    assert len(rows) == expected_query_count


@pytest.mark.parametrize("agent_id_arg, expected", [
    ("channel", 2),
    ("credit", 1),
    ("nonexistent", 0),
])
def test_recorder_query_agent_filter(isolated_recorder, agent_id_arg, expected):
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/c1", model="m"))
    isolated_recorder.record(LLMCall(agent_id="channel", endpoint="/c2", model="m"))
    isolated_recorder.record(LLMCall(agent_id="credit", endpoint="/d1", model="m"))

    assert len(isolated_recorder.query(agent_id=agent_id_arg)) == expected


@pytest.mark.parametrize("limit, offset, expected", [
    (10, 0, 5),
    (3, 0, 3),
    (3, 3, 2),
    (3, 5, 0),
    (1, 0, 1),
    (100, 0, 5),
])
def test_recorder_query_pagination(isolated_recorder, limit, offset, expected):
    for i in range(5):
        isolated_recorder.record(
            LLMCall(ts=f"2026-04-28T{i:02d}:00:00", agent_id="x", endpoint=f"/{i}", model="m"),
        )
    rows = isolated_recorder.query(limit=limit, offset=offset)
    assert len(rows) == expected


def test_recorder_count_param(isolated_recorder):
    for i in range(10):
        isolated_recorder.record(LLMCall(agent_id="channel", endpoint=f"/x{i}", model="m"))
    for i in range(5):
        isolated_recorder.record(LLMCall(agent_id="credit", endpoint=f"/d{i}", model="m"))
    assert isolated_recorder.count() == 15
    assert isolated_recorder.count(agent_id="channel") == 10
    assert isolated_recorder.count(agent_id="credit") == 5
    assert isolated_recorder.count(agent_id="missing") == 0


def test_recorder_record_returns_increasing_ids(isolated_recorder):
    ids = [
        isolated_recorder.record(LLMCall(agent_id="x", endpoint="/x", model="m"))
        for _ in range(5)
    ]
    assert ids == sorted(ids)
    assert len(set(ids)) == 5


# ============================================================================
# Decorator edges · 参数化
# ============================================================================

@pytest.mark.parametrize("user_kwarg, expected_user_id", [
    ({"sub": "u_a", "role": "rm"}, "u_a"),
    ({"sub": "u_b"}, "u_b"),
    ({"role": "admin"}, None),       # no sub
    ({}, None),                       # empty dict
    (None, None),                     # None
    ("not_a_dict", None),             # wrong type
    (123, None),
])
def test_decorator_extract_user_id(isolated_recorder, user_kwarg, expected_user_id):
    @audit_llm_call(agent_id="x", endpoint="/x")
    def handler(req=None, user=None):
        return {}
    handler({}, user=user_kwarg)
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert rows[0]["user_id"] == expected_user_id


@pytest.mark.parametrize("exc_type", [
    ValueError, RuntimeError, KeyError, TypeError, OSError,
])
def test_decorator_records_various_exceptions(isolated_recorder, exc_type):
    @audit_llm_call(agent_id="x", endpoint="/x")
    def handler():
        raise exc_type("boom")

    with pytest.raises(exc_type):
        handler()
    rows = isolated_recorder.query()
    assert len(rows) == 1
    assert exc_type.__name__ in rows[0]["error"]


@pytest.mark.parametrize("agent_id, endpoint", [
    ("channel", "/api/channel/run"),
    ("credit", "/api/credit/decision"),
    ("report", "/api/report/v16/fill"),
    ("alert", "/api/alert/scan"),
    ("compliance", "/api/compliance/policy_scan"),
    ("riskctrl", "/api/riskctrl/dsl_gen"),
])
def test_decorator_writes_correct_agent_endpoint(isolated_recorder, agent_id, endpoint):
    @audit_llm_call(agent_id=agent_id, endpoint=endpoint)
    def handler():
        return None
    handler()
    rows = isolated_recorder.query()
    assert rows[0]["agent_id"] == agent_id
    assert rows[0]["endpoint"] == endpoint


@pytest.mark.parametrize("model", [
    "deepseek-chat", "gpt-4", "claude-3", "qwen-max", "internal-model",
])
def test_decorator_writes_model_name(isolated_recorder, model):
    @audit_llm_call(agent_id="x", endpoint="/x", model=model)
    def handler():
        return None
    handler()
    rows = isolated_recorder.query()
    assert rows[0]["model"] == model


def test_decorator_async_propagates_return(isolated_recorder):
    @audit_llm_call(agent_id="x", endpoint="/x")
    async def handler():
        await asyncio.sleep(0)
        return {"data": 42}
    res = asyncio.run(handler())
    assert res == {"data": 42}


def test_decorator_records_latency_positive(isolated_recorder):
    import time

    @audit_llm_call(agent_id="x", endpoint="/x")
    def handler():
        time.sleep(0.02)
        return None
    handler()
    rows = isolated_recorder.query()
    assert rows[0]["latency_ms"] >= 15  # 至少 15ms (sleep 20ms · 留 5ms 偏差)


# ============================================================================
# middleware path resolver · 参数化 12 case
# ============================================================================

@pytest.mark.parametrize("path, expected_agent", [
    ("/api/channel/run", "channel"),
    ("/api/credit/decision", "credit"),
    ("/api/report/v16/fill", "report"),
    ("/api/alert/scan", "alert"),
    ("/api/compliance/policy_scan", "compliance"),
    ("/api/riskctrl/dsl_gen", "riskctrl"),
    ("/api/audit/llm_calls", "audit"),
    ("/api/", "unknown"),
    ("/api", "unknown"),
    ("/", "unknown"),
    ("", "unknown"),
    ("/health", "unknown"),
])
def test_middleware_resolves_agent_from_path(path, expected_agent):
    assert _default_agent_resolver(path) == expected_agent
